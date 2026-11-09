"""Fresh-input validation of the fixed agreement rule; never imported by serving."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import time

import numpy as np
from tokenizers import Tokenizer
from scvpublic.build import digest
from scvpublic.hybrid import HybridSearch
from scvpublic.sources import source_texts
from scvpublic.store import connect, search
from scripts.build_full_embeddings import token_windows
from scripts.experiment_survey_reranker import Reranker
from scripts.evaluate_frozen_court import compare, gates


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('artifacts/court-agreement-fresh-v1'))
    args=p.parse_args()
    if args.output.exists(): raise FileExistsError(args.output)
    artifact=Path('artifacts/scdb-issues.sqlite'); bundle=Path('artifacts/semantic-scdb-issues')
    oldartifact=Path('artifacts/affirmative-action.sqlite'); summary=Path('artifacts/official-syllabi-v5/bundle')
    modelpath=Path('artifacts/survey-reranker-model')
    benchmark=Path('data/evaluation/court-search-benchmark-v3.json')
    reviewpath=Path('data/evaluation/court-dual-source-membership-review.json')
    engine=HybridSearch(bundle,artifact); supplemental=HybridSearch(summary,oldartifact)
    docs,texts,origins=source_texts(artifact)
    with closing(connect(oldartifact)) as db:
        previous={i:json.loads(payload)['case_id'] for i,payload in db.execute("SELECT id,payload FROM documents WHERE corpus='court'")}
    if any(previous[d['doc_id']]!=d['case_id'] for d in docs): raise ValueError('Document mapping changed')
    for name in ('model.onnx','tokenizer.json'):
        if digest(bundle/name)!=digest(summary/name): raise ValueError('Encoder changed')
    sources=json.loads((bundle/'sources.json').read_text()); other=json.loads((summary/'sources.json').read_text())
    changed=np.array([d['doc_id'] for d in docs if sources[d['case_id']]!=other[d['case_id']]],dtype=np.int64)
    if len(changed)!=196: raise ValueError('Unexpected summary coverage')
    lookup={d['case_id']:d for d in docs}
    tok=Tokenizer.from_file(str(bundle/'tokenizer.json'));tok.no_truncation();tok.no_padding()
    rtok=Tokenizer.from_file(str(modelpath/'tokenizer.json'));rtok.no_truncation();rtok.no_padding()
    reranker=Reranker(modelpath)
    spec=json.loads(benchmark.read_text())['queries']
    for r in json.loads(reviewpath.read_text())['records']:
        labels=spec[r['query']]['court'];k=r['case_id']
        if k in labels and labels[k]['label']!=r['label']:raise ValueError('Label conflict')
        labels[k]={'label':r['label']}
    protocol=dict(rule='Fresh current-source contexts; fixed original candidate pool and ordering. Reject only dual-source score <0.30 AND contextual logit <0. Healthcare uses both existing spellings and retains a case if either nominated spelling supports it. 75/25 source blend, 90/10 semantic/lexical weights, 180 overview +180 best passage +40 name tokens unchanged. No sweep.',
        provenance={str(x):digest(x) for x in (artifact,bundle/'manifest.json',oldartifact,summary/'manifest.json',modelpath/'manifest.json',benchmark,reviewpath,Path(__file__),Path('scvpublic/hybrid.py'))})
    args.output.mkdir();(args.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    cache={};evidence={};results={};rankings={};removed=[];times=[]
    for q,labels in spec.items():
        start=time.perf_counter();before=engine.search([q])
        variants=['healthcare','health care'] if re.fullmatch(r'health(?:\s+|\s*-\s*)?care',q,re.I) else [q]
        by_case={h['case_id']:[] for h in before}
        for variant in variants:
            if variant not in evidence:
                hits=list(engine._single((variant,)))
                vector=engine.encoder.encode([variant])[0]
                raw=engine.vectors@vector
                s=np.full(engine.count,-1.,dtype=np.float32);np.maximum.at(s,engine.ids,raw)
                alt=s.copy();alt[:]=-1;np.maximum.at(alt,supplemental.ids,supplemental.vectors@vector)
                blended=s.copy();blended[changed]=.75*s[changed]+.25*alt[changed]
                with closing(connect(artifact)) as db:lex=search(db,'court',[variant],limit=None)
                weights={h['case_id']:h['score']/lex[0]['score'] for h in lex}
                rows=[]
                for h in hits:
                    k=h['case_id'];i=lookup[k]['doc_id']
                    if k not in cache:
                        if hashlib.sha256(texts[k].encode()).hexdigest()!=sources[k]['sha256']:raise ValueError('Source mismatch')
                        tokens=tok.encode(texts[k],add_special_tokens=False).ids
                        windows=list(token_windows(tokens));indexes=np.flatnonzero(engine.ids==i)
                        if len(windows)!=len(indexes):raise ValueError('Passage mismatch')
                        cache[k]=(tokens,windows,indexes)
                    tokens,windows,indexes=cache[k];best=int(np.argmax(raw[indexes]))
                    name=rtok.decode(rtok.encode(h['name'],add_special_tokens=False).ids[:40])
                    text=f'Case: {name}\nCase overview: {tok.decode(tokens[:180])}\nMatching passage: {tok.decode(windows[best][:180])}'
                    if len(rtok.encode(variant,text).ids)>512:raise ValueError('Context truncation')
                    rows.append(dict(case_id=k,text=text,source_sha256=sources[k]['sha256'],best_passage_index=best,
                        summary_score=.9*max(0.,float(blended[i]))+.1*weights.get(k,0.)))
                logits=reranker.score(variant,[r['text'] for r in rows])
                for r,logit in zip(rows,logits):r['logit']=logit
                evidence[variant]=rows
            for r in evidence[variant]:
                if r['case_id'] in by_case:by_case[r['case_id']].append(r)
        selected=[]
        for h in before:
            rs=by_case[h['case_id']]
            reject=bool(rs) and all(r['summary_score']<.30 and r['logit']<0 for r in rs)
            if reject:
                removed.append(dict(query=q,case_id=h['case_id'],baseline_score=h['score'],
                    label=labels['court'].get(h['case_id'],{}).get('label','unjudged')))
            else:selected.append(h)
        results[q]=compare(before,selected,labels['court']);rankings[q]=selected
        times.append(time.perf_counter()-start)
        print(q, 'removed chart',results[q]['baseline_chart']-results[q]['candidate_chart'],'lost direct',results[q]['lost_direct'],flush=True)
    gate=gates(results)
    report=dict(protocol=protocol,query_count=len(results),abstained_queries=[],gate=gate,passes=all(gate.values()),queries=results,
        removed_chart_pairs=[r for r in removed if r['baseline_score']>=.30],
        local_p95_seconds=float(np.percentile(times,95)),
        limitations=['Previously inspected partial labels, not independent validation.',
            'Removal-only rule cannot introduce new chart memberships; related removals remain a tradeoff.',
            'Offline timings include redundant source/model work and omit Flask; not VPS capacity measurements.'])
    for name,data in [('evidence.json',evidence),('rankings.json',rankings),('all-removals.json',removed)]:
        (args.output/name).write_text(json.dumps(data,indent=2)+'\n')
    Path('data/evaluation/court-agreement-fresh-summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(gate))


if __name__=='__main__':main()
