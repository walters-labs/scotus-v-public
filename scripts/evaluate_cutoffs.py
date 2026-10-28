"""Compare fixed hybrid cutoffs on a frozen judged pool; never tune serving."""
import argparse
from collections import Counter
import json
from pathlib import Path


def summary(hits, labels, cutoff):
    selected = [h for h in hits if h['score'] >= cutoff]
    counts = Counter(labels.get(h['case_id'], {}).get('label','unjudged') for h in selected)
    baseline_direct = {h['case_id'] for h in hits if h['score'] >= .30
                       and labels.get(h['case_id'],{}).get('label') == 'direct'}
    ids = {h['case_id'] for h in selected}
    return dict(total=len(selected), labels={k:counts[k] for k in
        ('direct','related','irrelevant','unjudged')},
        direct_retention= len(baseline_direct & ids)/len(baseline_direct) if baseline_direct else None,
        lost_direct=sorted(baseline_direct-ids),
        retained_irrelevant=sorted(h['case_id'] for h in selected
            if labels.get(h['case_id'],{}).get('label')=='irrelevant'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',type=Path,default=Path('artifacts/gss-pilot.sqlite'))
    p.add_argument('--bundle',type=Path,default=Path('artifacts/semantic-source-repair'))
    p.add_argument('--split',choices=['development','validation'],default='development')
    p.add_argument('--cutoffs',type=float,nargs='+',default=[.30,.325,.35,.375,.40,.425,.45,.475,.50])
    p.add_argument('--output',type=Path,default=Path('artifacts/cutoff-development.json'))
    a=p.parse_args()
    if any(not .30 <= c <= 1 for c in a.cutoffs):p.error('cutoffs must be between .30 and 1')
    from scvpublic.hybrid import HybridSearch
    from scvpublic.build import digest
    label_path=Path('data/evaluation/topic-relevance.json')
    extra_path=Path('data/evaluation/death-penalty-review.json')
    data=json.loads(label_path.read_text());extra=json.loads(extra_path.read_text())
    data['queries']['death penalty']['court'].update(extra['judgments'])
    engine=HybridSearch(a.bundle,a.artifact)
    hits={q:engine.search([q]) for q,v in data['queries'].items() if v['split']==a.split}
    out=dict(split=a.split,artifact_sha256=digest(a.artifact),bundle_manifest_sha256=digest(a.bundle/'manifest.json'),
             label_hashes={str(p):digest(p) for p in (label_path,extra_path)},
             definition='Direct retention is relative to known direct cases in the .30 candidate pool, not corpus recall. Unknowns are not negatives.',cutoffs={})
    for cutoff in a.cutoffs:
        rows={q:summary(h,data['queries'][q]['court'],cutoff) for q,h in hits.items()}
        totals={k:sum(r['labels'][k] for r in rows.values()) for k in ('direct','related','irrelevant','unjudged')}
        retention=[r['direct_retention'] for r in rows.values() if r['direct_retention'] is not None]
        out['cutoffs'][str(cutoff)]=dict(queries=rows,totals=totals,
            macro_direct_retention=sum(retention)/len(retention),
            min_topic_direct_retention=min(retention))
        print(cutoff,totals,'macro retention',round(sum(retention)/len(retention),3),'minimum',round(min(retention),3))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2)+'\n')


if __name__=='__main__':main()
