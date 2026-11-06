"""Compare issue/legal-provision/split-vote SCDB rows without changing serving data."""
import csv
from collections import defaultdict
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import zipfile
from scripts.audit_scdb_procedure import signal,PILOT

URL='https://scdb.la.psu.edu/?jet_download=3ec1f4346994212fb72570497da9c546951a6d7b'
FIELDS=['docketId','caseIssuesId','voteId','issue','issueArea','lawType','lawSupp','caseDisposition','decisionDirection','majVotes','minVotes']


def compare(base,expanded):
    old={r['issue'] for r in base if r['issue']};new={r['issue'] for r in expanded if r['issue']}
    chosen=lambda codes:{signal(c) for c in codes}-{ 'missing_issue','no_selected_signal_not_a_merits_label'}
    return dict(primary_issues=sorted(old),all_issues=sorted(new),added_issues=sorted(new-old),
                primary_signals=sorted(chosen(old)),all_signals=sorted(chosen(new)),
                recovered_signal=not chosen(old) and bool(chosen(new)))


def main():
    base=Path('data/raw/scdb-2026/SCDB_2026_01_caseCentered_Citation.csv');archive=Path('data/raw/scdb-2026/issues-split.zip')
    with base.open(encoding='utf-8-sig') as f:primary=list(csv.DictReader(f))
    with zipfile.ZipFile(archive) as z:
        member='SCDB_2026_01_caseCentered_Vote.csv';raw=z.read(member)
    expanded=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    a=defaultdict(list);b=defaultdict(list)
    for r in primary:a[r['caseId']].append(r)
    for r in expanded:b[r['caseId']].append(r)
    artifact=Path('artifacts/affirmative-action.sqlite')
    with sqlite3.connect(f'file:{artifact}?mode=ro',uri=True) as db:
        ids={json.loads(p)['case_id'] for (p,) in db.execute("SELECT payload FROM documents WHERE corpus='court'")}
    records=[]
    for key in sorted(ids & a.keys() & b.keys()):
        records.append(dict(case_id=key,name=a[key][0]['caseName'],**compare(a[key],b[key]),row_count=len(b[key]),
            directions=sorted({r['decisionDirection'] for r in b[key] if r['decisionDirection']}),
            rows=[{f:r[f] for f in FIELDS} for r in b[key]]))
    out=Path('artifacts/scdb-secondary-issues');out.mkdir(exist_ok=True)
    (out/'cases.json').write_text(json.dumps(records,indent=2)+'\n')
    summary=dict(status='Offline metadata comparison, no automatic merits classification',download_url=URL,release_page='https://scdb.la.psu.edu/data/2026-release-01/',
        provenance={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [base,archive,artifact,Path(__file__)]},csv_member=member,csv_sha256=hashlib.sha256(raw).hexdigest(),
        expanded_rows=len(expanded),expanded_unique_cases=len(b),indexed_cases_compared=len(records),
        missing_expanded_case_ids=sorted(ids-b.keys()),primary_cases_missing_in_expanded=sorted(a.keys()-b.keys()),
        indexed_cases_with_added_issues=sum(bool(r['added_issues']) for r in records),
        indexed_cases_with_new_signal=sum(r['recovered_signal'] for r in records),
        indexed_cases_with_multiple_directions=sum(len(r['directions'])>1 for r in records),
        recovered_cases=[{k:r[k] for k in ['case_id','name','primary_issues','all_issues','all_signals']} for r in records if r['recovered_signal']],
        pilot=[r for r in records if r['case_id'] in PILOT],
        limitations=['Multiple rows may represent dockets, legal provisions or vote coalitions, not independent decisions.',
        'A procedural issue coexisting with a policy issue does not prove the entire case avoids merits.',
        'Direction codes may differ by issue; no row averaging or polarity replacement performed.',
        'No signal remains unlabeled; remedy-only decisions can still be missed.'])
    Path('data/evaluation/scdb-secondary-issues-audit.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['provenance','pilot','recovered_cases','limitations']},indent=2))

if __name__=='__main__':main()
