"""Offline contextual court reranking against a frozen baseline; never used by Flask."""
import argparse
import gc
import json
from pathlib import Path
import resource
import sys
import time

import numpy as np
from tokenizers import Tokenizer
from experiment_survey_reranker import Reranker
from build_full_embeddings import token_windows
from scvpublic.build import digest
from scvpublic.hybrid import HybridSearch
from scvpublic.sources import source_texts


def prepare(args):
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    frozen=json.loads((args.baseline/'baseline.json').read_text())
    assert frozen['provenance'][str(args.artifact)]==digest(args.artifact)
    assert frozen['provenance'][str(args.bundle/'manifest.json')]==digest(args.bundle/'manifest.json')
    assert frozen['provenance']['scvpublic/hybrid.py']==digest(Path('scvpublic/hybrid.py'))
    engine=HybridSearch(args.bundle,args.artifact)
    docs,texts,origins=source_texts(args.artifact)
    lookup={d['case_id']:d['doc_id'] for d in docs}
    tok=Tokenizer.from_file(str(args.bundle/'tokenizer.json'))
    tok.no_padding();tok.no_truncation()
    rtok=Tokenizer.from_file(str(args.model/'tokenizer.json'))
    rtok.no_padding();rtok.no_truncation()
    requests=[]
    source_hashes=json.loads((args.bundle/'sources.json').read_text())
    cache={}
    import hashlib
    for query,hits in frozen['queries'].items():
        raw=engine.vectors @ engine.encoder.encode([query])[0]
        rows=[]
        for h in hits:
            k=h['case_id']
            if k not in cache:
                text=texts[k]
                assert hashlib.sha256(text.encode()).hexdigest()==source_hashes[k]['sha256']
                tokens=tok.encode(text,add_special_tokens=False).ids
                cache[k]=(tokens,list(token_windows(tokens)),np.flatnonzero(engine.ids==lookup[k]))
            tokens,windows,indexes=cache[k]
            assert len(windows)==len(indexes)
            best=int(np.argmax(raw[indexes]))
            overview=tok.decode(tokens[:180])
            passage=tok.decode(windows[best][:180])
            name=rtok.decode(rtok.encode(h['name'],add_special_tokens=False).ids[:40])
            text=f'Case: {name}\nCase overview: {overview}\nMatching passage: {passage}'
            assert len(rtok.encode(query,text).ids)<=512, (query,k)
            rows.append(dict(case_id=k,name=h['name'],text=text,baseline_score=h['score'],
                source_origin=origins[k],source_sha256=source_hashes[k]['sha256'],best_passage_index=best))
        requests.append(dict(query=query,rows=rows))
    (args.output/'requests.json').write_text(json.dumps(requests,indent=2)+'\n')
    provenance={str(p):digest(p) for p in [args.artifact,args.bundle/'manifest.json',
        args.model/'manifest.json',args.baseline/'baseline.json',Path('data/evaluation/court-search-benchmark-v2.json'),
        Path(__file__),Path('scripts/experiment_survey_reranker.py')]}
    (args.output/'protocol.json').write_text(json.dumps(dict(
        hypothesis='A cross-encoder assessing overview plus matching passage can reject incidental mentions without losing central-topic synonym matches.',
        rule='Same nominated cases; 180 overview tokens + 180 best-passage tokens + up to 40 name tokens; rerank by raw cross-encoder logit; accept logit >= 0. No threshold sweep.',
        limitations='Logits are not calibrated relevance probabilities. Development judgments are not independent validation.',
        provenance=provenance),indent=2)+'\n')
    print(json.dumps(dict(requests=len(requests),pairs=sum(len(x['rows']) for x in requests))))


def evaluate(args):
    protocol=json.loads((args.output/'protocol.json').read_text())
    for name,sha in protocol['provenance'].items():
        assert digest(Path(name))==sha,name
    requests=json.loads((args.output/'requests.json').read_text())
    spec=json.loads(Path('data/evaluation/court-search-benchmark-v2.json').read_text())
    model=Reranker(args.model)
    results={};timings=[]
    for request in requests:
        query=request['query'];rows=request['rows']
        start=time.perf_counter()
        logits=model.score(query,[r['text'] for r in rows])
        elapsed=time.perf_counter()-start;timings.append(elapsed)
        ranked=sorted([dict(r,logit=v) for r,v in zip(rows,logits)],key=lambda r:(-r['logit'],r['case_id']))
        selected=[r for r in ranked if r['logit']>=0]
        old={r['case_id'] for r in rows if r['baseline_score']>=.30}
        new={r['case_id'] for r in selected}
        direct={k for k,r in spec['queries'][query]['court'].items() if r['label']=='direct'}
        bad={k for k,r in spec['queries'][query]['court'].items() if r['label']=='irrelevant'}
        oldtop={r['case_id'] for r in rows[:10]}
        newtop={r['case_id'] for r in selected[:10]}
        results[query]=dict(seconds=elapsed,candidates=len(rows),baseline_chart=len(old),candidate_chart=len(new),
            lost_direct=sorted((old-new)&direct),new_direct=sorted((new-old)&direct),
            removed_irrelevant=sorted((old-new)&bad),new_irrelevant=sorted((new-old)&bad),
            lost_direct_top10=sorted((oldtop-newtop)&direct),
            baseline_judged_direct=sorted(old&direct),candidate_judged_direct=sorted(new&direct),
            baseline_judged_irrelevant=sorted(old&bad),candidate_judged_irrelevant=sorted(new&bad),
            ranked=[{k:r[k] for k in ('case_id','name','logit','baseline_score')} for r in ranked])
        print(query,len(old),'->',len(new),'lost',len(results[query]['lost_direct']),round(elapsed,2),'seconds',flush=True)
    gate=dict(no_lost_direct=all(not r['lost_direct'] for r in results.values()),
        no_new_irrelevant=all(not r['new_irrelevant'] for r in results.values()),
        no_lost_direct_top10=all(not r['lost_direct_top10'] for r in results.values()),
        removes_known_irrelevant=any(r['removed_irrelevant'] for r in results.values()))
    report=dict(protocol=protocol,queries=results,gate=gate,passes_development_gate=all(gate.values()),
        p95_rerank_seconds=float(np.percentile(timings,95)),max_rerank_seconds=max(timings),
        peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if sys.platform=='darwin' else 1024),
        memory_scope='Offline evaluation process: reranker and all request text; excludes hybrid model and web service. Not deployment footprint.',
        requests_sha256=digest(args.output/'requests.json'))
    (args.output/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(gate=gate,p95=report['p95_rerank_seconds'])))


def profile(args):
    # Separate fresh process, both models loaded, only one request retained.
    requests=json.loads((args.output/'requests.json').read_text())
    request=next(r for r in requests if r['query']=='abortion')
    del requests
    gc.collect()
    engine=HybridSearch(args.bundle,args.artifact)
    model=Reranker(args.model)
    timings=[]
    for _ in range(3):
        start=time.perf_counter()
        engine.search(['abortion'])
        model.score('abortion',[r['text'] for r in request['rows']])
        timings.append(time.perf_counter()-start)
    report=dict(platform=sys.platform,requests=3,candidates=len(request['rows']),seconds=timings,
        peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if sys.platform=='darwin' else 1024),
        scope='Fresh process with both models; one serial query. Excludes Gunicorn master, survey search, concurrent requests and context lookup; not a VPS/cgroup measurement.')
    (args.output/'local-profile.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['prepare','evaluate','profile'])
    p.add_argument('--artifact',type=Path,default=Path('artifacts/affirmative-action.sqlite'))
    p.add_argument('--bundle',type=Path,default=Path('artifacts/semantic-affirmative-action'))
    p.add_argument('--baseline',type=Path,default=Path('artifacts/court-passage-support-v1'))
    p.add_argument('--model',type=Path,default=Path('artifacts/survey-reranker-model'))
    p.add_argument('--output',type=Path,default=Path('artifacts/court-context-reranker-v1'))
    args=p.parse_args()
    globals()[args.mode](args)
