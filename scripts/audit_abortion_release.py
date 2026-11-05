"""Freeze a current-search abortion audit; never alter serving artifacts."""
import argparse
from collections import Counter
from contextlib import closing
import csv
import hashlib
import json
from pathlib import Path

from audit_question_composition import audit, selected_items
from scvpublic.build import digest, case_payload
from scvpublic.chart import combine_sources
from scvpublic.hybrid import HybridSearch, chart_matches
from scvpublic.sources import source_texts
from scvpublic.store import connect, series
from scvpublic.survey_search import SurveySearch


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',type=Path,required=True)
    p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    engine=HybridSearch(args.bundle,args.artifact)
    candidates=engine.search(['abortion'])
    courts=chart_matches(candidates)
    surveys=SurveySearch(args.bundle,args.artifact,engine.encoder).search(['abortion'])
    review_path=Path('data/research/abortion-current-case-review.json')
    prior_path=Path('data/research/abortion_case_review.json')
    review={r['case_id']:r for r in json.loads(review_path.read_text())['records']}
    assert set(review)=={h['case_id'] for h in courts}, 'Review does not cover exact current chart'
    docs,texts,origins=source_texts(args.artifact)
    bundle_sources=json.loads((args.bundle/'sources.json').read_text())
    for k,r in review.items():
        actual=hashlib.sha256(texts[k].encode()).hexdigest()
        assert r['text_sha256']==actual==bundle_sources[k]['sha256'], k
    with closing(connect(args.artifact)) as db:
        all_surveys={}
        for s,v in db.execute("SELECT corpus,payload FROM documents WHERE corpus!='court'"):
            all_surveys.setdefault(s,[]).append(json.loads(v))
    scdb_path=Path('data/raw/scdb-2026/SCDB_2026_01_caseCentered_Citation.csv')
    scdb={r['caseId']:r for r in csv.DictReader(scdb_path.open(encoding='utf-8-sig'))}
    for h in courts:
        for c in h['cases']:
            expected=case_payload(scdb[c['case_id']])
            assert expected['polarity']==c['polarity'], c['case_id']
    source_series={s:series([],hs)[1] for s,hs in surveys.items() if hs}
    combined,contributors=combine_sources(source_series)
    composition={s:audit(selected_items(hs)) for s,hs in surveys.items() if hs}
    source_composition=audit({y:{s:source_series[s][y] for s in names} for y,names in contributors.items()})
    stable_gss_codes={'abany','abdefect','abnomore','abhlth','abpoor','abrape','absingle'}
    gss=[d for d in all_surveys['gss'] if d['code'] in stable_gss_codes]
    assert {d['code'] for d in gss}==stable_gss_codes
    selected_gss=selected_items(gss)
    stable_years={y for y,items in selected_gss.items() if len(items)==7}
    stable_gss={y:v for y,v in series([],gss)[1].items() if y in stable_years}
    gss_any=next(d for d in gss if d['code']=='abany')['years']
    direct=[h for h in courts if review[h['case_id']]['scope']=='direct_access']
    direct_funding=[h for h in courts if review[h['case_id']]['scope'] in ('direct_access','funding')]
    court_series=series(courts,[])[0]
    direct_series=series(direct,[])[0]
    prior=json.loads(prior_path.read_text())['records']
    candidate_ids={h['case_id'] for h in candidates}
    indexed_ids={d['case_id'] for d in docs}
    missing=[dict(case_id=r['case_id'],name=r['name'],category=r['category'],
        status='not_indexed' if r['case_id'] not in indexed_ids else
               'below_chart_cutoff' if r['case_id'] in candidate_ids else 'not_nominated')
        for r in prior if r['case_id'] not in review]
    omitted={}
    for s,ds in all_surveys.items():
        chosen={d['code'] for d in surveys.get(s,[])}
        omitted[s]=[dict(code=d['code'],question=d['question'],years=sorted(d['years']))
            for d in ds if 'abort' in (d.get('title','')+' '+d['question']).lower() and d['code'] not in chosen]
    report=dict(status='Descriptive current-release audit, not a validated alignment estimate',
        court=dict(chart_documents=len(courts),chart_years=len(court_series),scope_counts=dict(Counter(r['scope'] for r in review.values())),
            scores_verified_against_scdb=len(courts),series=court_series,
            direct_access_scdb_series=direct_series,
            direct_access_and_funding_scdb_series=series(direct_funding,[])[0],
            missing_prior_reviewed_cases=missing,
            sign_changes_with_direct_scope=[y for y in direct_series if direct_series[y]*court_series[y]<0],
            records=[dict(case_id=h['case_id'],name=h['name'],score=h['score'],scope=review[h['case_id']]['scope'],cases=h['cases']) for h in courts]),
        surveys=dict(records=sum(map(len,surveys.values())),families=len({(s,h.get('family',h['code'])) for s,hs in surveys.items() for h in hs}),
            sources=len(source_series),observed_years=len(combined),combined=combined,contributors=contributors,
            source_series=source_series,within_source_composition=composition,between_source_composition=source_composition,
            without_moral_acceptability=combine_sources({s:v for s,v in source_series.items() if s!='wvs'})[0],
            fixed_seven_item_gss=stable_gss,gss_any_reason=gss_any,omitted_abortion_label_records=omitted,
            questions={s:[{k:d[k] for k in ('code','family','question','years','scores','question_note','year_provenance') if k in d} for d in ds] for s,ds in surveys.items()}),
        limitations=['Scope labels are provisional assistant review, not independent legal review.',
            'Direct-scope curves retain SCDB ideological direction and vote margins; they are not new access-impact scores.',
            'Prior review is not a complete reference corpus; omitted-case counts are not recall estimates.',
            'Stable item codes do not establish unchanged wording, survey mode or population.',
            'Alternative survey series measure different scopes; none is selected as preferred from agreement with court outcomes.',
            'This audit validates aggregation and court score arithmetic, not every raw survey response or population inference.',
            'No causal, forecasting or statistical-significance claim; no confidence intervals computed.'],
        provenance={str(x):digest(x) for x in [args.artifact,args.bundle/'manifest.json',review_path,prior_path,scdb_path,Path(__file__),Path('scripts/audit_question_composition.py'),Path('scvpublic/store.py'),Path('scvpublic/chart.py')]})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(court_scope=report['court']['scope_counts'],missing_cases=missing,
        sign_changes=report['court']['sign_changes_with_direct_scope'],
        survey_sources=len(source_series),survey_records=report['surveys']['records'],survey_years=len(combined),
        recent={y:dict(combined=combined.get(y),gss_current=source_series['gss'].get(y),gss_seven=stable_gss.get(y),gss_any=gss_any.get(str(y))) for y in [2014,2016,2018,2020,2021,2022,2024]}),indent=2))


if __name__=='__main__':
    main()
