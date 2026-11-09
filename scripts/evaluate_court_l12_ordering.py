"""Offline L12 display-order trial; chart membership and original scores fixed."""
import argparse
import json
from pathlib import Path
import re
import time

from scvpublic.build import digest
from scvpublic.hybrid import HybridSearch, chart_matches
from scripts.experiment_survey_reranker import Reranker


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('artifacts/court-l12-ordering-v1'))
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError(args.output)
    artifact=Path('artifacts/scdb-issues.sqlite');bundle=Path('artifacts/semantic-scdb-issues')
    model=Path('artifacts/court-reranker-l12-model')
    evidence_path=Path('artifacts/court-agreement-fresh-v1/evidence.json')
    prior_path=Path('artifacts/court-agreement-fresh-v1/protocol.json')
    benchmark=Path('data/evaluation/court-search-benchmark-v3.json')
    review=Path('data/evaluation/court-dual-source-membership-review.json')
    prior=json.loads(prior_path.read_text())
    for path in (artifact,bundle/'manifest.json',benchmark,review,Path('scvpublic/hybrid.py')):
        if digest(path)!=prior['provenance'][str(path)]:raise ValueError(f'Context provenance mismatch: {path}')
    engine=HybridSearch(bundle,artifact);reranker=Reranker(model)
    evidence=json.loads(evidence_path.read_text());sources=json.loads((bundle/'sources.json').read_text())
    spec=json.loads(benchmark.read_text())['queries']
    for row in json.loads(review.read_text())['records']:
        labels=spec[row['query']]['court'];key=row['case_id']
        if key in labels and labels[key]['label']!=row['label']:raise ValueError('Label conflict')
        labels[key]={'label':row['label']}
    protocol=dict(rule='Rerank all currently nominated cases by L12 raw logit, case_id tie break. No logit cutoff, score blending, candidate expansion or filtering. Healthcare merges its existing spelling-specific nominations by maximum logit. Chart uses original baseline hits and scores, never the reranked list.',
        gate='No loss of known direct top-ten cases; no new known irrelevant top-ten cases; at least one known irrelevant top-ten removal. Report replacements and rank movements separately; no threshold tuning.',
        provenance={str(p):digest(p) for p in (artifact,bundle/'manifest.json',model/'manifest.json',evidence_path,prior_path,benchmark,review,Path(__file__),Path('scvpublic/hybrid.py'))})
    args.output.mkdir();(args.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    cache={};results={};rankings={};times={}
    for query,entry in spec.items():
        before=engine.search([query]);original_chart=[(h['case_id'],h['score']) for h in chart_matches(before)]
        variants=['healthcare','health care'] if re.fullmatch(r'health(?:\s+|\s*-\s*)?care',query,re.I) else [query]
        scores={}
        for variant in variants:
            if variant not in cache:
                rows=evidence[variant]
                expected={h['case_id'] for h in engine._single((variant,))}
                if len(rows)!=len(expected) or {r['case_id'] for r in rows}!=expected:raise ValueError('Candidate/context coverage mismatch')
                for row in rows:
                    if row['source_sha256']!=sources[row['case_id']]['sha256']:raise ValueError('Source changed')
                reranker.tokenizer.no_truncation();reranker.tokenizer.no_padding()
                if any(len(reranker.tokenizer.encode(variant,r['text']).ids)>512 for r in rows):raise ValueError('Context too long')
                reranker.tokenizer.enable_truncation(max_length=512);reranker.tokenizer.enable_padding()
                started=time.perf_counter();values=reranker.score(variant,[r['text'] for r in rows]);times[variant]=time.perf_counter()-started
                cache[variant]={r['case_id']:v for r,v in zip(rows,values)}
            for key,value in cache[variant].items():scores[key]=max(scores.get(key,float('-inf')),value)
        if set(scores)!={h['case_id'] for h in before}:raise ValueError('Nominations differ')
        after=sorted(before,key=lambda h:(-scores[h['case_id']],h['case_id']))
        if original_chart!=[(h['case_id'],h['score']) for h in chart_matches(before)]:raise ValueError('Chart changed')
        labels=entry['court'];direct={k for k,v in labels.items() if v['label']=='direct'};bad={k for k,v in labels.items() if v['label']=='irrelevant'}
        b={h['case_id'] for h in before[:10]};a={h['case_id'] for h in after[:10]}
        oldrank={h['case_id']:i+1 for i,h in enumerate(before)};newrank={h['case_id']:i+1 for i,h in enumerate(after)}
        results[query]=dict(candidates=len(before),chart_unchanged=True,
            baseline_direct_top10=len(b&direct),candidate_direct_top10=len(a&direct),
            baseline_irrelevant_top10=len(b&bad),candidate_irrelevant_top10=len(a&bad),
            lost_direct_top10=sorted((b-a)&direct),gained_direct_top10=sorted((a-b)&direct),
            new_irrelevant_top10=sorted((a-b)&bad),removed_irrelevant_top10=sorted((b-a)&bad),
            added_unjudged_top10=sorted((a-b)-set(labels)),
            judged_rank_movements=[dict(case_id=k,label=labels[k]['label'],before=oldrank[k],after=newrank[k]) for k in sorted(set(labels)&set(oldrank))])
        rankings[query]=dict(chart=original_chart,baseline=[h['case_id'] for h in before],
            reranked=[dict(case_id=h['case_id'],original_score=h['score'],logit=scores[h['case_id']]) for h in after])
        print(query, 'direct top10',len(b&direct),'->',len(a&direct),'lost',len((b-a)&direct),flush=True)
    gate=dict(no_lost_direct_top10=all(not r['lost_direct_top10'] for r in results.values()),
        no_new_irrelevant_top10=all(not r['new_irrelevant_top10'] for r in results.values()),
        removes_known_irrelevant_top10=any(r['removed_irrelevant_top10'] for r in results.values()),chart_unchanged=True)
    report=dict(protocol=protocol,query_count=len(results),gate=gate,passes=all(gate.values()),queries=results,
        local_rerank_seconds=times,limitations=['Previously inspected partial labels; not independent validation or whole-result precision.',
            'Aliases overlap; counts are query/case memberships, not independent cases.',
            'Offline model timings are not deployment memory/latency measurements.'],status='offline_not_deployed')
    (args.output/'rankings.json').write_text(json.dumps(rankings,indent=2)+'\n')
    Path('data/evaluation/court-l12-ordering-summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(gate))


if __name__=='__main__':main()
