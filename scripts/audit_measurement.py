"""Inspect benchmark measurement differences without changing production scoring."""
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
from scvpublic.build import digest
from scvpublic.store import series
from scvpublic.chart import combine_sources


def audit(coverage, scdb):
    report=json.loads(coverage.read_text())
    rows=defaultdict(list)
    with scdb.open(encoding='utf-8-sig') as stream:
        for row in csv.DictReader(stream):rows[row['caseId']].append(row)
    results={}
    for topic,data in report['topics'].items():
        issues=Counter(); directions=Counter(); examples=[]
        for match in data['court_matches']:
            candidates=rows.get(match['case_id'],[])
            codes=sorted({r['issue'] for r in candidates})
            direction=sorted({r['decisionDirection'] for r in candidates})
            issues.update(codes);directions.update(direction)
            examples.append(dict(case_id=match['case_id'],name=match['name'],score=match['score'],
                                 scdb_issue_codes=codes,scdb_direction_codes=direction,
                                 multiple_scdb_rows=len(candidates)>1))
        policy_sources={};types=Counter()
        for source,detail in data['sources'].items():
            questions=detail['questions']
            types.update(q['measurement_type'] or 'unspecified' for q in questions)
            # Strict sensitivity subset, not automatic adjudication of mixed categories.
            policy=[q for q in questions if q['measurement_type']=='policy']
            policy_sources[source]=series([],policy)[1]
        policy,contributors=combine_sources(policy_sources)
        original={int(y):v for y,v in data['combined_scores'].items()}
        differences={y:policy[y]-original[y] for y in policy if y in original}
        results[topic]=dict(scdb_issue_counts=dict(issues),scdb_direction_counts=dict(directions),
            matched_measurement_types=dict(types),strict_policy_scores=policy,
            strict_policy_contributors=contributors,
            strict_policy_minus_app=differences,
            max_absolute_difference=max(map(abs,differences.values()),default=None),
            court_review=examples)
    return dict(coverage_sha256=digest(coverage),scdb_sha256=digest(scdb),topics=results,
        limitations=['Strict policy sensitivity excludes mixed policy_or_self_placement labels; this is not a final reviewed policy-only estimate.',
                     'SCDB issue counts identify coding diversity, not relevance judgments.',
                     'No significance, causal, or predictive claims; no production behavior changed.'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--coverage',type=Path,default=Path('artifacts/topic-coverage.json'))
    p.add_argument('--scdb',type=Path,default=Path('data/raw/scdb-2026/SCDB_2026_01_caseCentered_Citation.csv'))
    p.add_argument('--output',type=Path,default=Path('artifacts/measurement-audit.json'))
    a=p.parse_args();r=audit(a.coverage,a.scdb)
    a.output.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    for topic,d in r['topics'].items():
        print(topic,dict(measurements=d['matched_measurement_types'],issue_codes=len(d['scdb_issue_counts']),max_score_change=d['max_absolute_difference']))
