"""Build an auditable research cohort independently of search rank; no model fitting."""
import csv
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
from contextlib import closing
from scvpublic.build import digest
from scvpublic.store import connect, series
from scvpublic.chart import combine_sources


def assemble_cases(groups, protocol, combined, contributors):
    cases=[];excluded=[]
    for case_id,rows in groups.items():
        signatures={(r['dateDecision'],r['decisionDirection']) for r in rows}
        if len(signatures)!=1:
            excluded.append(dict(case_id=case_id,reason='conflicting duplicate rows'));continue
        row=rows[0]
        if row['decisionDirection'] not in protocol['court_direction']:
            excluded.append(dict(case_id=case_id,reason='unknown direction'));continue
        try:
            date=datetime.strptime(row['dateDecision'],'%m/%d/%Y')
        except (ValueError, TypeError):
            excluded.append(dict(case_id=case_id,reason='missing or invalid decision date'));continue
        earlier=[y for y in combined if 1<=date.year-y<=5]
        year=max(earlier) if earlier else None
        cases.append(dict(case_id=case_id,name=row['caseName'],date=date.date().isoformat(),
            liberal=protocol['court_direction'][row['decisionDirection']],
            survey_year=year,lag_years=date.year-year if year else None,
            sentiment=combined[year] if year else None,sources=contributors[year] if year else [],
            review_status='needs substantive-versus-procedural review'))
    return cases, excluded


def build():
    protocol_path=Path('data/research/abortion_protocol.json')
    protocol=json.loads(protocol_path.read_text())
    scdb=Path('data/raw/scdb-2026/SCDB_2026_01_caseCentered_Citation.csv')
    artifact=Path('artifacts/wvs-pilot.sqlite')
    groups=defaultdict(list)
    with scdb.open(encoding='utf-8-sig') as stream:
        for row in csv.DictReader(stream):
            if row['issue']==protocol['court_issue_code']:groups[row['caseId']].append(row)
    corpus_names={'public':'ANES','gss':'GSS','ces':'CES'}
    questions=defaultdict(list)
    with closing(connect(artifact)) as db:
        for corpus,name in corpus_names.items():
            for payload, in db.execute('SELECT payload FROM documents WHERE corpus=?',(corpus,)):
                q=json.loads(payload)
                if q['code'] in protocol['survey_codes'][name]:questions[name].append(q)
            if {q['code'] for q in questions[name]} != set(protocol['survey_codes'][name]):
                raise ValueError('Missing reviewed survey questions: '+name)
    sources={name:series([],qs)[1] for name,qs in questions.items()}
    combined,contributors=combine_sources(sources)
    cases,excluded=assemble_cases(groups,protocol,combined,contributors)
    report=dict(protocol=protocol,hashes={str(p):digest(p) for p in [protocol_path,scdb,artifact]},
        cases=sorted(cases,key=lambda c:(c['date'],c['case_id'])),excluded=excluded,
        survey_series=sources,combined=combined,
        summary=dict(cases=len(cases),matched_to_prior_sentiment=sum(c['survey_year'] is not None for c in cases),
                     liberal_cases=sum(c['liberal'] for c in cases),excluded=len(excluded)))
    Path('artifacts/abortion-research-cohort.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['summary']))


if __name__=='__main__':build()
