"""Audit known release boundaries without treating unknown sources as available."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path

from scvpublic.build import digest
from scvpublic.store import connect, metadata
from contextlib import closing


def audit_cases(cohort_cases, predictions, release_bounds):
    cases = {c['case_id']: c for c in cohort_cases}
    if len(cases) != len(cohort_cases):
        raise ValueError('Duplicate cohort case IDs')
    rows = []
    for prediction in predictions:
        case = cases[prediction['case_id']]
        if prediction['year'] != int(case['date'][:4]):
            raise ValueError('Prediction year differs from decision year')
        # Decision time is unknown: a release later on the same date is unresolved.
        cutoff = datetime.fromisoformat(case['date']).replace(tzinfo=timezone.utc) + timedelta(days=1)
        train = [c for c in cases.values() if c['sentiment'] is not None and int(c['date'][:4]) < prediction['year']]
        if len(train) != prediction['training_cases']:
            raise ValueError('Training-case count mismatch')
        later_sources = lambda c: sorted(source for source in c['sources']
            if source in release_bounds and release_bounds[source] >= cutoff)
        test_sources = later_sources(case)
        future_test = bool(test_sources)
        future_train = [c['case_id'] for c in train if later_sources(c)]
        unknown = sorted({source for c in train+[case] for source in c['sources'] if source not in release_bounds})
        rows.append(dict(case_id=case['case_id'], decision_date=case['date'],
            later_release_in_test_features=future_test,
            later_release_test_sources=test_sources,
            later_release_training_sources=sorted({s for c in train for s in later_sources(c)}),
            training_cases_using_later_release=future_train, unverified_sources=unknown,
            status='known later-release input' if future_test or future_train else 'availability unresolved'))
    return rows


def main():
    cohort_path = Path('artifacts/abortion-research-cohort.json')
    evaluation_path = Path('artifacts/abortion-retrospective-evaluation.json')
    availability_path = Path('artifacts/ces-release-availability.json')
    cohort = json.loads(cohort_path.read_text())
    evaluation = json.loads(evaluation_path.read_text())
    if evaluation['cohort_sha256'] != digest(cohort_path):
        raise ValueError('Evaluation cohort hash mismatch')
    availability = json.loads(availability_path.read_text())
    ces_records = [r for r in availability['records'] if r.get('input_role') in ['policy-v3','common-v12']]
    if {r['input_role'] for r in ces_records} != {'policy-v3','common-v12'} or len(ces_records) != 2:
        raise ValueError('Missing or duplicate CES release records')
    ces_available = max(datetime.fromisoformat(r['conservative_available_at'].replace('Z','+00:00')) for r in ces_records)
    # Bind release evidence to the exact artifact used to derive the cohort.
    artifact = Path('artifacts/wvs-pilot.sqlite')
    if cohort['hashes'][str(artifact)] != digest(artifact):
        raise ValueError('Cohort artifact hash mismatch')
    anes_path = Path('data/raw/rebuild/anes-20260205/sources.json')
    gss_path = Path('data/manifests/gss-2024-r3a.json')
    anes = json.loads(anes_path.read_text())
    gss = json.loads(gss_path.read_text())
    with closing(connect(artifact)) as db:
        meta = metadata(db)
    for record in ces_records:
        if record['file_sha256'] not in meta['ces_sources'].values():
            raise ValueError('CES artifact provenance mismatch')
    for name, expected in anes['files'].items():
        if name.endswith('.dta'):
            matches = [h for p, h in meta['sources'].items() if Path(p).name == name]
            if matches != [expected]:
                raise ValueError('ANES artifact provenance mismatch')
    if meta['gss_release'] != gss['release']:
        raise ValueError('GSS release mismatch')
    if gss['release'] != 'GSS 1972–2024 cumulative Release 3a (July 2026)':
        raise ValueError('Unreviewed GSS release')
    if [h for p,h in meta['gss_sources'].items() if Path(p).name == 'gss7224_r3a.dta'] != [gss['dta_sha256']]:
        raise ValueError('GSS artifact provenance mismatch')
    # July 1 is a lower bound, not an invented exact publication day.
    release_bounds = {
        'CES': ces_available,
        'ANES': datetime.fromisoformat(anes['release']).replace(tzinfo=timezone.utc),
        'GSS': datetime(2026, 7, 1, tzinfo=timezone.utc),
    }
    rows = audit_cases(cohort['cases'], evaluation['predictions'], release_bounds)
    report = dict(status='input-vintage diagnostic, not a corrected forecasting evaluation',
        evaluated_cases=len(rows),
        known_later_release_cases=sum(r['status']=='known later-release input' for r in rows),
        unresolved_cases=sum(r['status']=='availability unresolved' for r in rows),
        verified_as_of_cases=0, cases=rows,
        release_lower_bounds={k:v.isoformat() for k,v in release_bounds.items()},
        release_precision={'ANES':'day','GSS':'month; first day is lower bound only','CES':'version timestamp'},
        sources={str(p):digest(p) for p in [cohort_path,evaluation_path,availability_path,anes_path,gss_path,artifact,Path(__file__)]},
        limitations=['This tests exact ANES/GSS artifact provenance and downloaded CES inputs, not equivalence to earlier versions.',
            'Equivalence to earlier ANES/GSS/CES vintages and court-label availability remain unverified.',
            'Later file vintages do not prove that historical answers or weights changed. This is not a corrected evaluation.'])
    Path('artifacts/prediction-availability-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['evaluated_cases','known_later_release_cases','unresolved_cases','verified_as_of_cases']}))


if __name__ == '__main__':
    main()
