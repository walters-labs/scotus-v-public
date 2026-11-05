"""Freeze hybrid baseline and test one offline passage-support score; no serving edits."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from tokenizers import Tokenizer

from scvpublic.build import digest
from scvpublic.hybrid import HybridSearch, CHART_CUTOFF
from scvpublic.sources import source_texts
from build_full_embeddings import token_windows


def selected(hits):
    return {h['case_id'] for h in hits if h['score'] >= CHART_CUTOFF}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',type=Path,required=True)
    p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    benchmark_path=Path('data/evaluation/court-search-benchmark-v2.json')
    spec=json.loads(benchmark_path.read_text())
    engine=HybridSearch(args.bundle,args.artifact)
    docs,texts,origins=source_texts(args.artifact)
    by_case={d['case_id']:d for d in docs}
    source_hashes=json.loads((args.bundle/'sources.json').read_text())
    tokenizer=Tokenizer.from_file(str(args.bundle/'tokenizer.json'))
    tokenizer.no_padding();tokenizer.no_truncation()
    provenance={str(x):digest(x) for x in [args.artifact,args.bundle/'manifest.json',
        benchmark_path,Path(__file__),Path('scvpublic/hybrid.py'),Path('scripts/build_full_embeddings.py')]}
    baseline={}; trials={}; metrics={}; evidence=[]
    for query,review in spec['queries'].items():
        start=time.perf_counter()
        hits=engine.search([query])
        baseline[query]=hits
        raw=engine.vectors @ engine.encoder.encode([query])[0]
        counts=np.bincount(engine.ids,minlength=engine.count)
        means=np.bincount(engine.ids,weights=raw,minlength=engine.count)/counts
        # Predeclared one-shot trial: require some average passage support.
        candidate=[]
        for h in hits:
            i=by_case[h['case_id']]['doc_id']
            semantic=.75*h['semantic_score']+.25*max(0.,float(means[i]))
            candidate.append(dict(h,score=.9*semantic+.1*h['lexical_score'],
                                  mean_passage_cosine=float(means[i])))
        candidate.sort(key=lambda h:(-h['score'],h['case_id']))
        if candidate and candidate[0]['score']<CHART_CUTOFF:
            candidate=[]
        trials[query]=candidate
        before,after=selected(hits),selected(candidate)
        labels={k:v['label'] for k,v in review['court'].items()}
        direct={k for k,v in labels.items() if v=='direct'}
        bad={k for k,v in labels.items() if v=='irrelevant'}
        btop={h['case_id'] for h in hits[:10]};atop={h['case_id'] for h in candidate[:10]}
        metrics[query]=dict(split=review['split'],alias_of=review.get('alias_of'),
            baseline_chart=len(before),candidate_chart=len(after),
            baseline_judged_direct=sorted(before&direct),candidate_judged_direct=sorted(after&direct),
            baseline_judged_irrelevant=sorted(before&bad),candidate_judged_irrelevant=sorted(after&bad),
            lost_direct=sorted((before-after)&direct),new_irrelevant=sorted((after-before)&bad),
            removed_irrelevant=sorted((before-after)&bad),
            lost_direct_top10=sorted((btop-atop)&direct),
            baseline_unjudged=len(before-set(labels)),candidate_unjudged=len(after-set(labels)),
            missing_indexed_direct=sorted((direct&set(by_case))-before),
            direct_not_indexed=sorted(direct-set(by_case)),elapsed_seconds=time.perf_counter()-start)
        # Highest-ranked known false positives and lowest-scored retained positives.
        samples=[h for h in hits if h['case_id'] in bad][:2]
        samples += sorted([h for h in hits if h['case_id'] in direct and h['score']>=CHART_CUTOFF],key=lambda h:h['score'])[:2]
        if query=='abortion':
            anchor={'2004-024','1991-117','2021-019','1991-039','2025-013'}
            samples += [h for h in hits if h['case_id'] in anchor]
        seen=set()
        for h in samples:
            k=h['case_id']
            if k in seen:continue
            seen.add(k)
            text=texts[k]
            assert hashlib.sha256(text.encode()).hexdigest()==source_hashes[k]['sha256']
            indexes=np.flatnonzero(engine.ids==by_case[k]['doc_id'])
            windows=list(token_windows(tokenizer.encode(text,add_special_tokens=False).ids))
            assert len(indexes)==len(windows),k
            best=int(np.argmax(raw[indexes]))
            evidence.append(dict(query=query,case_id=k,name=h['name'],label=labels[k],
                source_origin=origins[k],text_sha256=source_hashes[k]['sha256'],
                score=h['score'],lexical=h['lexical_score'],maximum=h['semantic_score'],
                mean=float(means[by_case[k]['doc_id']]),first=float(raw[indexes[0]]),
                passages=len(windows),best_passage_index=best,
                first_passage=tokenizer.decode(windows[0]),
                best_passage=tokenizer.decode(windows[best])))
    summary=dict(status='Offline experiment only',
        experiment='Keep candidate nomination, lexical weight and 0.30 cutoff; semantic score = 0.75*maximum + 0.25*max(0, mean passage cosine). No tuning sweep.',
        production_unchanged=True,provenance=provenance,queries=metrics,
        gate=dict(no_lost_direct=all(not m['lost_direct'] for m in metrics.values()),
            no_new_irrelevant=all(not m['new_irrelevant'] for m in metrics.values()),
            no_lost_direct_top10=all(not m['lost_direct_top10'] for m in metrics.values()),
            removes_known_irrelevant=any(m['removed_irrelevant'] for m in metrics.values())),
        limitations=spec['limitations'])
    summary['passes_development_gate']=all(summary['gate'].values())
    for name,value in [('baseline',dict(provenance=provenance,queries=baseline)),
                       ('candidate',trials),('passage-evidence',evidence),('summary',summary)]:
        (args.output/(name+'.json')).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(gate=summary['gate'],queries=len(metrics),judgments=sum(len(v['court']) for v in spec['queries'].values()),
        failures={q:{k:m[k] for k in ['lost_direct','lost_direct_top10','new_irrelevant']} for q,m in metrics.items() if m['lost_direct'] or m['lost_direct_top10'] or m['new_irrelevant']},
        removed={q:len(m['removed_irrelevant']) for q,m in metrics.items() if m['removed_irrelevant']}),indent=2))


if __name__=='__main__':
    main()
