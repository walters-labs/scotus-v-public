"""Case-level alignment sensitivity to GSS sampling uncertainty; no causal inference."""
from collections import Counter
import json
from pathlib import Path

from scipy.stats import t
from scvpublic.build import digest


def interval_alignment(estimate, liberal):
    se = estimate.get('standard_error')
    df = estimate.get('design_df', 0)
    if se is None or df <= 0:
        return {'status':'sampling uncertainty unsupported'}
    margin = float(t.ppf(.975, df) * se)
    lower, upper = estimate['mean']-margin, estimate['mean']+margin
    direction = 'positive' if lower > 0 else 'negative' if upper < 0 else 'crosses zero'
    status = ('direction unresolved by marginal interval' if direction == 'crosses zero'
              else 'aligned' if (direction == 'positive') == bool(liberal) else 'opposed')
    return dict(status=status, lower=lower, upper=upper, standard_error=se, design_df=df)


def main():
    cohort_path = Path('artifacts/abortion-research-cohort.json')
    variance_path = Path('artifacts/gss-uncertainty.json')
    review_path = Path('data/research/abortion_case_review.json')
    cohort = json.loads(cohort_path.read_text())
    variance = json.loads(variance_path.read_text())
    review = {r['case_id']: r for r in json.loads(review_path.read_text())['records']}
    codes = set(cohort['protocol']['survey_codes']['GSS'])
    series = {r['year']: r for r in variance['abortion_composite'] if set(r['items']) == codes}
    # Verify semantic inputs even if a report's documentation-only cohort hash changed.
    artifact = Path('artifacts/wvs-pilot.sqlite')
    if digest(artifact) != cohort['hashes'][str(artifact)] or digest(artifact) != variance['point_validation']['hashes'][str(artifact)]:
        raise ValueError('Cohort and uncertainty report use different artifacts')
    for year, r in series.items():
        if abs(r['mean'] - cohort['survey_series']['GSS'][str(year)]) > 1e-10:
            raise ValueError(f'GSS point estimate mismatch: {year}')
    if set(review) != {c['case_id'] for c in cohort['cases']}:
        raise ValueError('Case review coverage differs')
    rows = []
    for case in cohort['cases']:
        years = [y for y in series if 1 <= int(case['date'][:4])-y <= 5]
        row = dict(case_id=case['case_id'], date=case['date'], liberal=case['liberal'],
                   scope=review[case['case_id']]['category'])
        if not years:
            rows.append(dict(row, status='no prior complete seven-item GSS series'))
            continue
        r = series[max(years)]
        row.update(survey_year=r['year'], mean=r['mean'],
                   point_alignment=(r['mean'] > 0) == bool(case['liberal']))
        rows.append(dict(row, **interval_alignment(r, case['liberal'])))
    scopes = {'all_scdb_abortion': rows,
              'direct_access_scdb': [r for r in rows if r['scope']=='direct_access_merits']}
    summary = {name: dict(cases=len(rs), statuses=dict(Counter(r['status'] for r in rs)),
        distinct_survey_years=len({r['survey_year'] for r in rs if 'survey_year' in r}))
        for name,rs in scopes.items()}
    # Compare every prespecified item on exactly the same case/year pairs.
    common = [r for r in rows if 'survey_year' in r and all(
        series[r['survey_year']]['components'][code].get('standard_error') is not None
        and series[r['survey_year']]['components'][code].get('design_df', 0) > 0
        for code in codes)]
    item_comparison = {}
    for code in sorted(codes):
        item_rows = []
        for r in common:
            estimate = series[r['survey_year']]['components'][code]
            item_rows.append(dict(case_id=r['case_id'], survey_year=r['survey_year'],
                mean=estimate['mean'], scope=r['scope'],
                **interval_alignment(estimate, r['liberal'])))
        direct = [r for r in item_rows if r['scope']=='direct_access_merits']
        item_comparison[code] = dict(cases=item_rows,
            all_statuses=dict(Counter(r['status'] for r in item_rows)),
            direct_access_statuses=dict(Counter(r['status'] for r in direct)))
    report = dict(status='exploratory descriptive sensitivity; provisional case coding',
        method='Latest complete seven-item GSS year strictly before decision year, maximum lag five years. Marginal 95% t intervals using existing Taylor SE and design degrees of freedom.',
        summary=summary, cases=rows,
        common_coverage_item_comparison=item_comparison,
        common_coverage_cases=len(common),
        common_coverage_survey_years=len({r['survey_year'] for r in common}),
        sources={str(p):digest(p) for p in [cohort_path,variance_path,review_path,Path(__file__)]},
        limitations=['Intervals are marginal per survey year, not simultaneous or an interval for the alignment rate.',
                     'Multiple cases share survey estimates; they are not independent survey observations.',
                     'Positive average across seven circumstances is not majority support for any single abortion policy.',
                     'No uncertainty for nonresponse bias, question meaning, case coding, or release vintage.',
                     'Source-specific sensitivity changes coverage; does not replace the combined-source primary description.',
                     'SCDB direction and provisional direct-access scope still need independent substantive review.'])
    Path('artifacts/abortion-alignment-uncertainty.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
