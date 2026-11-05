"""Offline spelling-variant experiment using original search; never used by Flask."""
import argparse
import json
from pathlib import Path
import re
from scvpublic.build import digest
from scvpublic.hybrid import HybridSearch, CHART_CUTOFF
from scripts.evaluate_frozen_court import compare


def variants(query):
    # A bounded spelling equivalence, not an inferred policy synonym or case rule.
    if re.fullmatch(r'health(?:\s+|\s*-\s*)?care', query.strip(), flags=re.I):
        return ['healthcare', 'health care']
    return [query]


def merge(hits_by_variant):
    """Deduplicate cases; retain strongest returned whole-query score, never sum."""
    merged={}
    for query,hits in hits_by_variant.items():
        for hit in hits:
            key=hit['case_id']
            if key not in merged or hit['score']>merged[key]['score']:
                merged[key]=dict(hit,winning_variant=query)
    return sorted(merged.values(),key=lambda h:(-h['score'],h['case_id']))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('artifacts/healthcare-variants-v1'))
    a=p.parse_args()
    if a.output.exists(): raise FileExistsError(a.output)
    artifact=Path('artifacts/affirmative-action.sqlite');bundle=Path('artifacts/semantic-affirmative-action')
    frozen_path=Path('artifacts/court-passage-support-v1/baseline.json')
    benchmark_path=Path('data/evaluation/court-search-benchmark-v3.json')
    review_path=Path('data/evaluation/court-dual-source-membership-review.json')
    frozen=json.loads(frozen_path.read_text());spec=json.loads(benchmark_path.read_text())
    for path in (artifact,bundle/'manifest.json',Path('scvpublic/hybrid.py')):
        assert frozen['provenance'][str(path)]==digest(path),path
    for row in json.loads(review_path.read_text())['records']:
        labels=spec['queries'][row['query']]['court'];key=row['case_id']
        if key in labels: assert labels[key]['label']==row['label']
        else: labels[key]={'label':row['label']}
    # Equivalent spellings receive the same already-reviewed relevance labels.
    healthcare_labels={}
    for q in ['healthcare','health care']:
        for key,label in spec['queries'][q]['court'].items():
            if key in healthcare_labels: assert healthcare_labels[key]['label']==label['label']
            healthcare_labels[key]=label
    a.output.mkdir(parents=True)
    protocol=dict(rule='Original retrieval only. Exact healthcare/health care/health-care queries expand to healthcare and health care. Union returned candidates, deduplicate by case ID, use maximum returned complete hybrid score. Same .30 cutoff; no summary blend, parameter sweep, or extra cases.',
        limitations='Small explicit spelling equivalence for a development experiment, not general synonym discovery. Maximum scores are not calibrated probabilities; retaining old plotted cases follows by construction. New memberships need review.',
        provenance={str(x):digest(x) for x in [artifact,bundle/'manifest.json',frozen_path,benchmark_path,review_path,Path(__file__),Path('scripts/evaluate_frozen_court.py')]})
    (a.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    engine=HybridSearch(bundle,artifact);rankings={};metrics={};added={};anchors={}
    for q,review in spec['queries'].items():
        original=engine.search([q]);saved=frozen['queries'][q]
        assert [h['case_id'] for h in original]==[h['case_id'] for h in saved],q
        assert all(abs(h['score']-s['score'])<1e-7 for h,s in zip(original,saved)),q
        hits=merge({v:engine.search([v]) for v in variants(q)})
        rankings[q]=hits
        labels=healthcare_labels if len(variants(q))>1 else review['court']
        metrics[q]=compare(saved,hits,labels)
        before={h['case_id'] for h in saved if h['score']>=CHART_CUTOFF}
        added[q]=[dict(case_id=h['case_id'],name=h['name'],score=h['score'],winning_variant=h['winning_variant'],label=labels.get(h['case_id'],{}).get('label','unjudged')) for h in hits if h['score']>=CHART_CUTOFF and h['case_id'] not in before]
        if len(variants(q))==1:
            assert [h['case_id'] for h in hits]==[h['case_id'] for h in saved]
            assert all(h['score']==s['score'] for h,s in zip(hits,saved))
        else:
            anchors[q]={key:next((dict(rank=i+1,score=h['score'],winning_variant=h['winning_variant']) for i,h in enumerate(hits) if h['case_id']==key),None) for key in ['2024-019','2011-077']}
    report=dict(protocol=protocol,queries=metrics,added_chart_pairs=added,anchors=anchors)
    (a.output/'rankings.json').write_text(json.dumps(rankings,indent=2)+'\n')
    (a.output/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    for q in ['healthcare','health care']: print(q,metrics[q],anchors[q])
    print('Other 22 query rankings and scores unchanged')


if __name__=='__main__':main()
