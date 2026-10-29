"""Describe prior-index sign agreement with SCDB direction, not policy causation."""
from collections import Counter
import json
from pathlib import Path
from scvpublic.build import digest
from scvpublic.store import connect


def describe(cases):
    table={s:{'liberal':0,'conservative':0} for s in ('positive','negative','zero')}
    missing=0
    for case in cases:
        value=case['sentiment']
        if value is None:
            missing+=1
            continue
        sign='positive' if value>0 else 'negative' if value<0 else 'zero'
        table[sign]['liberal' if case['liberal'] else 'conservative']+=1
    aligned=table['positive']['liberal']+table['negative']['conservative']
    directional=sum(sum(table[s].values()) for s in ('positive','negative'))
    matched=[c for c in cases if c['sentiment'] is not None]
    return dict(cases=len(cases),missing_prior_index=missing,contingency=table,
        aligned_cases=aligned,directional_cases=directional,
        sign_agreement=aligned/directional if directional else None,
        distinct_survey_years=len({c['survey_year'] for c in matched}),
        lag_counts=dict(sorted(Counter(c['lag_years'] for c in matched).items())),
        interpretation='Descriptive agreement between the sign of the prior survey index and binary SCDB ideological direction. A positive index is not necessarily majority support for a single policy. Cases can share survey observations; case count is not an independent public-opinion sample size.')


def with_index(cases, index):
    index={int(year):value for year,value in index.items()}
    result=[]
    for case in cases:
        decision_year=int(case['date'][:4])
        eligible=[year for year in index if 1<=decision_year-year<=5]
        year=max(eligible) if eligible else None
        result.append(dict(case,sentiment=index[year] if year else None,
                           survey_year=year,lag_years=decision_year-year if year else None))
    return result


if __name__=='__main__':
    path=Path('artifacts/abortion-research-cohort.json')
    cohort=json.loads(path.read_text())
    report=describe(cohort['cases'])
    artifact=Path('artifacts/wvs-pilot.sqlite')
    if digest(artifact)!=cohort['hashes'][str(artifact)]:
        raise ValueError('Survey artifact differs from cohort input')
    questions=[]
    db=connect(artifact)
    try:
        for corpus,source in [('public','ANES'),('gss','GSS'),('ces','CES')]:
            for payload, in db.execute('SELECT payload FROM documents WHERE corpus=?',(corpus,)):
                question=json.loads(payload)
                if question['code'] in cohort['protocol']['survey_codes'][source]:
                    questions.append(dict(source=source,code=question['code'],
                        title=question['title'],
                        **describe(with_index(cohort['cases'],question['years']))))
    finally:
        db.close()
    report['individual_question_sensitivity']=questions
    report['question_comparison_note']='Question-specific coverage differs. Agreement rates are not directly comparable across items and must not be used to select favorable questions.'
    review_path=Path('data/research/abortion_case_review.json')
    review=json.loads(review_path.read_text())
    reviewed={r['case_id']:r for r in review['records']}
    if len(reviewed)!=len(review['records']) or set(reviewed)!={c['case_id'] for c in cohort['cases']}:
        raise ValueError('Case review must cover the exact cohort without duplicates')
    if review['remaining_case_ids'] or any('incomplete' in r['review_status'] for r in reviewed.values()):
        raise ValueError('Unresolved review sources')
    direct=[c for c in cohort['cases'] if reviewed[c['case_id']]['category']=='direct_access_merits']
    unambiguous=[dict(c,liberal=int(reviewed[c['case_id']]['access_direction']=='protective'))
                 for c in direct if reviewed[c['case_id']]['access_direction'] in ('protective','restrictive')]
    broad=[c for c in cohort['cases'] if reviewed[c['case_id']]['category'] in
           ('direct_access_merits','direct_access_and_public_funding','public_funding','public_funding_and_speech')]
    report['case_scope_sensitivity']={name:dict(describe(cases),case_ids=[c['case_id'] for c in cases])
        for name,cases in [('direct_access_scdb',direct),('direct_access_unambiguous',unambiguous),
                           ('broad_access_and_funding_scdb',broad)]}
    report['case_review_sha256']=digest(review_path)
    report['case_review_limit']='Provisional AI coding from source passages, not independent human review. Subsets change the estimand and temporal coverage; none replaces the original cohort.'
    report.update(cohort_sha256=digest(path),analysis_sha256=digest(Path(__file__)),
        status='Exploratory; provisional case review awaiting independent confirmation. No causal or forecasting inference.',
        limitations=['SCDB abortion issue cohort includes procedural and speech disputes.',
            'Question wording and source composition can vary across years.',
            'Survey sampling uncertainty is not represented by these point estimates.',
            'No independence assumption or statistical significance claim is made.'])
    Path('artifacts/abortion-alignment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
