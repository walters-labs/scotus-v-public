"""Audit SCDB metadata as partial evidence, never a binary merits classifier."""
import csv
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import sqlite3

FIELDS=['decisionType','jurisdiction','issue','issueArea','caseDisposition','declarationUncon','lawType','decisionDirection']
PILOT=['1972-048','1975-172','1979-148','1985-077','1990-077','1991-117','2005-020','2006-031','2013-068','2021-006','2021-019','2023-049']


from scvpublic.scdb_metadata import signal


def main():
    source=Path('data/raw/scdb-2026/SCDB_2026_01_caseCentered_Citation.csv')
    artifact=Path('artifacts/affirmative-action.sqlite')
    with source.open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    bycase=defaultdict(list)
    for row in rows:bycase[row['caseId']].append(row)
    with sqlite3.connect(f'file:{artifact}?mode=ro',uri=True) as db:
        docs=[json.loads(p) for (p,) in db.execute("SELECT payload FROM documents WHERE corpus='court'")]
    ids={d['case_id'] for d in docs}
    categories=Counter();conflicts=[];missing=[];audited=[]
    for key in sorted(ids):
        matches=bycase.get(key,[])
        if not matches:missing.append(key);continue
        values={field:sorted({r[field] for r in matches}) for field in FIELDS}
        issue=values['issue']
        category=signal(issue[0]) if len(issue)==1 else 'conflicting_issue'
        categories[category]+=1
        if any(len(v)>1 for v in values.values()):conflicts.append(key)
        audited.append(dict(case_id=key,name=matches[0]['caseName'],fields=values,signal=category))
    output=dict(status='Read-only metadata audit; no classifier or chart exclusion',
        provenance={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,artifact,Path(__file__)]},
        court_documents=len(docs),unique_court_case_ids=len(ids),matched_cases=len(audited),unmatched_case_ids=missing,
        raw_rows=len(rows),raw_unique_cases=len(bycase),signal_counts=dict(categories),conflicting_metadata_case_ids=conflicts,
        field_missing_cases={field:sum(all(v=='' for v in r['fields'][field]) for r in audited) for field in FIELDS},
        pilot=[r for r in audited if r['case_id'] in PILOT],
        limitations=['Issue labels are not binary merits/procedural ground truth.','No selected signal is unlabeled, not a negative training example.','Judicial-power categories are broad; they can involve substantive questions.','Citation-centered file may omit secondary issue detail; inspect issue/legal-provision data before building labels.'])
    dest=Path('artifacts/scdb-procedure-audit');dest.mkdir(exist_ok=True)
    (dest/'case-signals.json').write_text(json.dumps(audited,indent=2)+'\n')
    Path('data/evaluation/scdb-procedure-audit.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k not in ('pilot','provenance','conflicting_metadata_case_ids','unmatched_case_ids')},indent=2))

if __name__=='__main__':main()
