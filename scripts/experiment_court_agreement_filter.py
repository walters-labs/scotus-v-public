"""Offline conjunction of previously tested rejection signals; no threshold tuning."""
import argparse
import json
from pathlib import Path
from scvpublic.build import digest
from scripts.evaluate_frozen_court import compare, gates


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('artifacts/court-agreement-filter-v1'))
    args=parser.parse_args()
    paths={
        'current':Path('artifacts/official-repair-component-rankings.json'),
        'historical':Path('artifacts/court-passage-support-v1/baseline.json'),
        'summary':Path('artifacts/court-candidate-pool-v1/fixed-rankings.json'),
        'reranker':Path('artifacts/court-context-reranker-v1/evaluation.json'),
        'benchmark':Path('data/evaluation/court-search-benchmark-v3.json'),
        'review':Path('data/evaluation/court-dual-source-membership-review.json')}
    data={k:json.loads(p.read_text()) for k,p in paths.items()}
    # Verify cached model evaluations and ranking outputs against their own records.
    for record in ('data/evaluation/court-candidate-pool-summary.json',
                   'data/evaluation/court-context-reranker-summary.json'):
        saved=json.loads(Path(record).read_text())
        for name,expected in saved['protocol']['provenance'].items():
            if digest(Path(name))!=expected:
                raise ValueError(f'Historical input changed: {name}')
    baseline=data['current']['baseline']; prior=data['historical']['queries']
    spec=data['benchmark']['queries']
    for row in data['review']['records']:
        labels=spec[row['query']]['court']; key=row['case_id']
        if key in labels and labels[key]['label']!=row['label']:
            raise ValueError('Conflicting reviewed label')
        labels[key]={'label':row['label']}
    protocol=dict(rule='Preserve current baseline candidates, scores and order. Remove only when historical fixed-pool dual-source score < 0.30 AND contextual reranker logit < 0. Missing evidence or changed baseline query causes abstention. No weights or cutoff sweep.',
        rationale='Each signal alone lost relevant cases. Test whether requiring agreement avoids those losses; no claim of independent errors.',
        provenance={str(p):digest(p) for p in [*paths.values(),Path(__file__)]})
    output=args.output
    if output.exists(): raise FileExistsError(output)
    output.mkdir()
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    results={};rankings={};removed=[];abstained=[]
    for q,hits in baseline.items():
        unchanged=[(h['case_id'],h['score']) for h in hits]==[(h['case_id'],h['score']) for h in prior[q]]
        summary={h['case_id']:h['score'] for h in data['summary'][q]}
        logits={h['case_id']:h['logit'] for h in data['reranker']['queries'][q]['ranked']}
        selected=[]
        if not unchanged: abstained.append(q)
        for h in hits:
            key=h['case_id']
            reject=unchanged and key in summary and key in logits and summary[key]<.30 and logits[key]<0
            if reject:
                removed.append(dict(query=q,case_id=key,baseline_score=h['score'],summary_score=summary[key],
                    reranker_logit=logits[key],label=spec[q]['court'].get(key,{}).get('label','unjudged')))
            else: selected.append(h)
        rankings[q]=selected
        results[q]=compare(hits,selected,spec[q]['court'])
    gate=gates(results)
    report=dict(protocol=protocol,query_count=len(results),abstained_queries=abstained,gate=gate,
        passes=all(gate.values()),removed_chart_pairs=[r for r in removed if r['baseline_score']>=.30],
        removed_below_chart_count=sum(r['baseline_score']<.30 for r in removed),queries=results,
        limitations=['Post-hoc combination of previously inspected signals, not independent validation.',
            'No-new-irrelevant membership is structural for a removal-only rule.',
            'Historical healthcare queries differ from current spelling-union search and are left unchanged.',
            'Unjudged removals are not counted as correct; runtime cost not measured for this combination.'])
    (output/'rankings.json').write_text(json.dumps(rankings,indent=2)+'\n')
    (output/'all-removals.json').write_text(json.dumps(removed,indent=2)+'\n')
    Path('data/evaluation/court-agreement-filter-summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(gate=gate,abstained=abstained,removed_chart_pairs=report['removed_chart_pairs']),indent=2))


if __name__=='__main__':main()
