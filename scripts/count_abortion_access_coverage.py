"""Count contextual prior-question coverage; never compute alignment or forecasts."""
import csv
import json
from collections import Counter
from contextlib import closing
from pathlib import Path
from scvpublic.build import digest
from scvpublic.store import connect


def prior_year(years, decision_year, max_lag=5):
    eligible=[int(y) for y in years if 1 <= decision_year-int(y) <= max_lag]
    return max(eligible) if eligible else None


def main():
    specpath=Path('data/research/abortion-access-specification.json')
    oldpath=Path('data/research/abortion_case_review.json')
    currentpath=Path('data/research/abortion-current-case-review.json')
    scdbpath=Path('data/raw/scdb-2026/SCDB_2026_01_caseCentered_Citation.csv')
    artifact=Path('artifacts/scdb-issues.sqlite')
    spec=json.loads(specpath.read_text());old=json.loads(oldpath.read_text())['records'];current=json.loads(currentpath.read_text())['records']
    reviews={r['case_id']:dict(r) for r in old}
    for r in current:
        key=r['case_id']
        if key in reviews:
            if r.get('access_direction')!=reviews[key].get('access_direction'):
                raise ValueError(f'Conflicting direction: {key}')
        else:reviews[key]=dict(r,category='direct_access_merits' if r['scope']=='direct_access' else r['scope'])
    with scdbpath.open(encoding='utf-8-sig') as f:
        scdb={r['caseId']:r for r in csv.DictReader(f)}
    wanted={(s,c) for s,cs in spec['survey_codes'].items() for c in cs}
    questions={};indexed=set()
    with closing(connect(artifact)) as db:
        for source,payload in db.execute('SELECT corpus,payload FROM documents'):
            doc=json.loads(payload)
            if source=='court':indexed.add(doc['case_id'])
            elif (source,doc['code']) in wanted:questions[(source,doc['code'])]=doc
    if set(questions)!=wanted:raise ValueError('Missing question')
    records=[];excluded=[]
    for key,r in reviews.items():
        category=r['category'];direction=r.get('access_direction')
        if category not in ('direct_access_merits','direct_access_and_public_funding'):
            excluded.append(dict(case_id=key,category=category));continue
        date=scdb[key]['dateDecision'];year=int(date.split('/')[-1])
        group='primary' if category=='direct_access_merits' and direction in ('protective','restrictive') else 'separate'
        pairs=[]
        for (s,c),doc in sorted(questions.items()):
            y=prior_year(doc['years'],year,spec['timing']['maximum_lag_years'])
            pairs.append(dict(source=s,code=c,survey_year=y,lag_years=year-y if y else None,
                status='contextual_temporal_match_policy_fit_unresolved' if y else 'no_prior_observation_within_five_years'))
        records.append(dict(case_id=key,name=r['name'],decision_date=date,decision_year=year,category=category,
            access_direction=direction,group=group,indexed=key in indexed,review_rationale=r['rationale'],question_matches=pairs))
    records.sort(key=lambda r:(r['decision_year'],r['case_id']))
    summaries={}
    for group in ('primary','separate'):
        rows=[r for r in records if r['group']==group]
        matched=[(r,m) for r in rows for m in r['question_matches'] if m['survey_year'] is not None]
        summaries[group]=dict(cases=len(rows),cases_with_prior_question=len({r['case_id'] for r,m in matched}),
            cases_without_prior_question=[r['case_id'] for r in rows if not any(m['survey_year'] for m in r['question_matches'])],
            contextual_case_question_pairs=len(matched),distinct_question_years=len({(m['source'],m['code'],m['survey_year']) for r,m in matched}),
            distinct_survey_years=len({m['survey_year'] for r,m in matched}),
            by_question=dict(Counter(m['source']+':'+m['code'] for r,m in matched)))
    report=dict(status='Coverage only; policy comparability unresolved, no alignment estimate',
        provenance={str(p):digest(p) for p in (specpath,oldpath,currentpath,scdbpath,artifact,Path(__file__))},
        reviewed_frame_cases=len(reviews),excluded_cases=excluded,summary=summaries,
        questions=[dict(source=s,code=c,question=d['question'],family=d.get('family'),available_years=sorted(map(int,d['years']))) for (s,c),d in sorted(questions.items())],
        records=records,limitations=[spec['interpretation'],'Provisional existing holding labels; no new legal adjudication.','Shared question-years are not independent observations.','Reviewed frame is incomplete; missing indexed text is reported rather than excluding the reviewed case.'])
    Path('data/research/abortion-access-coverage.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':main()
