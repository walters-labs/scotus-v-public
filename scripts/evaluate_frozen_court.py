"""Apply a versioned court benchmark to saved rankings without retuning search."""
import argparse
import hashlib
import json
from pathlib import Path


def compare(before, after, labels, cutoff=.30):
    b = {h['case_id'] for h in before if h['score'] >= cutoff}
    a = {h['case_id'] for h in after if h['score'] >= cutoff}
    direct = {k for k,v in labels.items() if v['label']=='direct'}
    bad = {k for k,v in labels.items() if v['label']=='irrelevant'}
    return dict(baseline_chart=len(b),candidate_chart=len(a),
        lost_direct=sorted((b-a)&direct),new_irrelevant=sorted((a-b)&bad),
        removed_irrelevant=sorted((b-a)&bad),
        lost_direct_top10=sorted(({h['case_id'] for h in before[:10]}-
                                 {h['case_id'] for h in after[:10]})&direct),
        added_unjudged=sorted((a-b)-set(labels)),removed_unjudged=sorted((b-a)-set(labels)))


def gates(results):
    return dict(no_lost_direct=not any(r['lost_direct'] for r in results.values()),
        no_new_irrelevant=not any(r['new_irrelevant'] for r in results.values()),
        no_lost_direct_top10=not any(r['lost_direct_top10'] for r in results.values()),
        removes_known_irrelevant=any(r['removed_irrelevant'] for r in results.values()))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,default=Path('artifacts/court-passage-support-v1/baseline.json'))
    p.add_argument('--candidate',type=Path,default=Path('artifacts/court-dual-source-v1/rankings.json'))
    p.add_argument('--benchmark',type=Path,default=Path('data/evaluation/court-search-benchmark-v3.json'))
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    before=json.loads(args.baseline.read_text())['queries']
    after=json.loads(args.candidate.read_text())
    spec=json.loads(args.benchmark.read_text())
    if set(before)!=set(spec['queries']) or set(after)!=set(spec['queries']):
        raise ValueError('Ranking queries must match the benchmark exactly')
    for rankings in (before,after):
        for hits in rankings.values():
            if len({h['case_id'] for h in hits}) != len(hits):
                raise ValueError('Duplicate case in ranking')
    results={q:compare(before[q],after[q],review['court']) for q,review in spec['queries'].items()}
    gate=gates(results)
    report=dict(status='Offline evaluation of unchanged saved rankings; production unchanged',
        benchmark_labels=sum(len(q['court']) for q in spec['queries'].values()),
        provenance={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in
                    (args.baseline,args.candidate,args.benchmark,Path(__file__))},
        gate=gate,passes=all(gate.values()),queries=results)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(gate))


if __name__=='__main__': main()
