"""Isolate nomination effects with fixed scoring and predeclared candidate pools."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import numpy as np
from scvpublic.build import digest
from scvpublic.hybrid import HybridSearch
from scvpublic.store import connect, search
from evaluate_frozen_court import compare, gates


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('artifacts/court-candidate-pool-v1'))
    a=p.parse_args()
    if a.output.exists(): raise FileExistsError(a.output)
    artifact=Path('artifacts/affirmative-action.sqlite')
    original=Path('artifacts/semantic-affirmative-action')
    summary=Path('artifacts/official-syllabi-v5/bundle')
    baseline_path=Path('artifacts/court-passage-support-v1/baseline.json')
    prior_path=Path('artifacts/court-dual-source-v1/rankings.json')
    benchmark_path=Path('data/evaluation/court-search-benchmark-v3.json')
    review_path=Path('data/evaluation/court-dual-source-membership-review.json')
    frozen=json.loads(baseline_path.read_text())
    for path in (artifact,original/'manifest.json',Path('scvpublic/hybrid.py')):
        assert frozen['provenance'][str(path)]==digest(path),path
    baseline=frozen['queries'];prior=json.loads(prior_path.read_text())
    spec=json.loads(benchmark_path.read_text())
    for row in json.loads(review_path.read_text())['records']:
        labels=spec['queries'][row['query']]['court'];key=row['case_id']
        if key in labels: assert labels[key]['label']==row['label']
        else: labels[key]={'label':row['label']}
    a.output.mkdir(parents=True)
    protocol=dict(rule='Unchanged 75/25 original/summary semantic scoring for 196 cases; unchanged lexical weight and .30 cutoff. Compare original fixed pool and union of original/dual-source pools. No additional nomination or weight tuning.',
        limitations='Diagnostic using previously reviewed development cases. Fixed pool is query-specific saved nomination, not a universal case allowlist. Unjudged memberships are not negatives.',
        provenance={str(x):digest(x) for x in (artifact,original/'manifest.json',summary/'manifest.json',baseline_path,prior_path,benchmark_path,review_path,Path(__file__),Path('scripts/evaluate_frozen_court.py'))})
    (a.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    old=HybridSearch(original,artifact);new=HybridSearch(summary,artifact)
    with closing(connect(artifact)) as db:
        docs={json.loads(p)['case_id']:(i,json.loads(p)) for i,p in db.execute("SELECT id,payload FROM documents WHERE corpus='court'")}
    bs=json.loads((original/'sources.json').read_text());cs=json.loads((summary/'sources.json').read_text())
    changed=np.array([i for k,(i,d) in docs.items() if bs[k]!=cs[k]])
    assert len(changed)==196
    rankings={'fixed':{},'union':{}}
    metrics={'previous_dual':{},'fixed':{},'union':{}}
    for q,review in spec['queries'].items():
        vector=old.encoder.encode([q])[0]
        original_scores=np.full(old.count,-1.,dtype=np.float32);summary_scores=original_scores.copy()
        np.maximum.at(original_scores,old.ids,old.vectors@vector)
        np.maximum.at(summary_scores,new.ids,new.vectors@vector)
        scores=original_scores.copy();scores[changed]=.75*original_scores[changed]+.25*summary_scores[changed]
        with closing(connect(artifact)) as db: lex=search(db,'court',[q],limit=None)
        weights={h['case_id']:h['score']/lex[0]['score'] for h in lex}
        def hit(key):
            i,d=docs[key];s=max(0.,float(scores[i]));l=weights.get(key,0.)
            return dict(d,score=.9*s+.1*l,semantic_score=s,lexical_score=l)
        # Verify this really is the previous scoring rule, without any retuning.
        for h in prior[q]: assert abs(hit(h['case_id'])['score']-h['score'])<1e-7
        fixed={h['case_id'] for h in baseline[q]};union=fixed|{h['case_id'] for h in prior[q]}
        metrics['previous_dual'][q]=compare(baseline[q],prior[q],review['court'])
        for name,pool in [('fixed',fixed),('union',union)]:
            hits=sorted((hit(k) for k in pool),key=lambda h:(-h['score'],h['case_id']))
            if hits and hits[0]['score']<.30: hits=[]
            rankings[name][q]=hits
            metrics[name][q]=compare(baseline[q],hits,review['court'])
    report=dict(protocol=protocol,variants={name:dict(gate=gates(rows),queries=rows) for name,rows in metrics.items()})
    for name,rows in metrics.items():
        totals={key:sum(len(r[key]) for r in rows.values()) for key in ['lost_direct','new_irrelevant','removed_irrelevant','lost_direct_top10','added_unjudged','removed_unjudged']}
        report['variants'][name]['totals']=totals
        print(name,totals)
    for name,rows in rankings.items(): (a.output/(name+'-rankings.json')).write_text(json.dumps(rows,indent=2)+'\n')
    (a.output/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
