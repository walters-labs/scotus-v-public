"""Offline component-level comparison; never infers legal meaning from search scores."""
import argparse
from copy import deepcopy
from datetime import date
import hashlib
import json
import math
from pathlib import Path

DIRECTIONS = {'expands', 'restricts', 'maintains_restriction', 'maintains_protection', 'maintains_permission', 'mixed', 'unresolved', 'no_merits_ruling'}
FITS = {'direct', 'contextual', 'not_comparable'}
GROUPS = {'support', 'oppose', 'neutral', 'unsure', 'nonresponse'}


def compare(cases, surveys, mapping):
    """Select latest eligible year per source, retaining eligible variants.

    Verified fieldwork must end before the ruling; otherwise require a prior year.

    Mapping explicitly lists source/variable pairs measuring each policy. All
    support shares must already be oriented toward the policy in the mapping.
    No pooled score, case weighting, interpolation, or inferred legal coding.
    """
    age = mapping['max_prior_years']
    if type(age) is not int or age < 1:
        raise ValueError('max_prior_years must be a positive integer')
    policies = mapping['policies']
    selectors = {}
    for policy, spec in policies.items():
        if not spec['support_definition']:
            raise ValueError('Missing support definition')
        keys = [(s['source'], s['variable']) for s in spec['questions']]
        if len(keys) != len(set(keys)):
            raise ValueError('Duplicate question selector')
        selectors[policy] = set(keys)
    seen = set()
    for r in surveys:
        key = (r['source'], r['variable'], r['year'])
        if key in seen or type(r['year']) is not int:
            raise ValueError('Duplicate observation or invalid year')
        seen.add(key)
        if ('percent' in r) == ('response_distribution' in r):
            raise ValueError('Provide exactly one response representation')
        if 'percent' in r:
            values = r['percent']
            if set(values) != GROUPS:
                raise ValueError('Invalid response groups')
            numbers = list(values.values())
        else:
            distribution = r['response_distribution']
            codes = [c['code'] for c in distribution]
            if not codes or len(codes) != len(set(codes)) or any(not c['label'] for c in distribution):
                raise ValueError('Invalid response distribution')
            numbers = [c['percent'] for c in distribution]
            for category in distribution:
                if 'percent_upper_bound' in category:
                    bound = category['percent_upper_bound']
                    if (r.get('data_kind') != 'published_topline' or
                            not math.isfinite(bound) or not 0 <= category['percent'] < bound <= 100):
                        raise ValueError('Invalid response upper bound')
        if any(not math.isfinite(v) or v < 0 or v > 100 for v in numbers):
            raise ValueError('Invalid response shares')
        tolerance = len(numbers) * 0.5 if r.get('data_kind') == 'published_topline' else 1e-6
        if abs(sum(numbers) - 100) > tolerance:
            raise ValueError('Response shares must sum to 100')
        if 'field_start' in r or 'field_end' in r:
            start, end = date.fromisoformat(r['field_start']), date.fromisoformat(r['field_end'])
            if start > end or end.year != r['year']:
                raise ValueError('Invalid fieldwork dates')
        if not r['denominator'] or not r['wording']:
            raise ValueError('Missing survey meaning/denominator')
    output = []
    case_ids = set()
    for case in sorted(cases, key=lambda c: (c['date'], c['case_id'])):
        if case['case_id'] in case_ids:
            raise ValueError('Duplicate case')
        case_ids.add(case['case_id'])
        year = date.fromisoformat(case['date']).year
        components = []
        component_ids = set()
        for component in case['components']:
            cid = component['component_id']
            if cid in component_ids:
                raise ValueError('Duplicate component')
            component_ids.add(cid)
            direction, fit = component['direction'], component['comparison_fit']
            if direction not in DIRECTIONS or fit not in FITS:
                raise ValueError('Unknown direction or comparison fit')
            if direction == 'no_merits_ruling' and fit != 'not_comparable':
                raise ValueError('Procedural components cannot receive policy comparisons')
            policy = component['policy_id']
            if policy not in policies:
                raise ValueError('Unknown policy')
            if not case['source'] or not component['locator'] or not component['survey_fit']:
                raise ValueError('Missing interpretation provenance')
            records = [r for r in surveys if (r['source'], r['variable']) in selectors[policy]]
            sources = sorted({s for s, _ in selectors[policy]})
            comparisons = []
            for source in sources:
                matched = [r for r in records if r['source'] == source]
                eligible = [r for r in matched if year-age <= r['year'] <= year
                            and (date.fromisoformat(r['field_end']) < date.fromisoformat(case['date'])
                                 if r.get('field_end') else r['year'] < year)]
                selected = []
                if fit == 'not_comparable':
                    status = 'not_comparable'
                elif not matched:
                    status = 'no_matching_question'
                elif not eligible:
                    status = 'no_prior_observation'
                else:
                    latest = max(r['year'] for r in eligible)
                    selected = sorted((deepcopy(r) for r in eligible if r['year'] == latest), key=lambda r: r['variable'])
                    status = 'available'
                comparisons.append(dict(source=source, status=status, observations=selected))
            components.append({**deepcopy(component), 'comparisons': comparisons,
                               'coverage_status': 'no_matching_question' if not sources else 'see_source_comparisons'})
        output.append({**deepcopy(case), 'components': components})
    return dict(schema_version=1, timing_rule=f'Latest eligible year per source within {age} years; dated fieldwork must end before the decision, otherwise an earlier calendar year is required. Retain all eligible question variants in that year.',
                policies=deepcopy(policies), cases=output,
                limitations=['Explicit source-based legal coding is an input, not an automated legal classifier.',
                             'Contextual matches do not measure approval of the specific holding.',
                             'Mixed and unresolved components retain their labels; no scalar direction is inferred.',
                             'No pooling, confidence intervals, causal claims, or prediction.'])


def report(result):
    lines = ['# Policy comparison report', '', result['timing_rule'], '',
             'Offline research only. Shares retain each source’s denominator. No combined alignment score.', '']
    for case in result['cases']:
        lines += [f"## {case['name']} ({case['date']})", '', f"[Decision source]({case['source']})", '']
        if case.get('interpretation_limit'):
            lines += [case['interpretation_limit'], '']
        if case.get('coverage_note'):
            lines += [case['coverage_note'], '']
        for component in case['components']:
            lines += [f"### {component['issue']}", '',
                      f"**{component['direction']} · {component['comparison_fit']}**", '',
                      component['decision'], '', component['scope'], '', component['survey_fit'], '',
                      f"Source locator: {component['locator']}", '',
                      '| Source/year | Support | Oppose | Neutral | Unsure | Nonresponse |',
                      '| --- | ---: | ---: | ---: | ---: | ---: |']
            notes = []
            distributions = []
            if not component['comparisons']:
                lines.append('| No matching question in this selection | — | — | — | — | — |')
            for comparison in component['comparisons']:
                if not comparison['observations']:
                    lines.append(f"| {comparison['source']}: {comparison['status'].replace('_', ' ')} | — | — | — | — | — |")
                for r in comparison['observations']:
                    if 'response_distribution' in r:
                        lines.append(f"| {r['source']} {r['year']} ({r['variable']}): categories below | — | — | — | — | — |")
                        distributions += [f"**{r['source']} {r['year']} ({r['variable']}) — original policy categories**", '',
                                          '| Answer | Percent |', '| --- | ---: |']
                        distributions += [f"| {c['label']} | " + (f"<{c['percent_upper_bound']}%" if 'percent_upper_bound' in c else f"{c['percent']:.1f}%") + ' |' for c in r['response_distribution']]
                        distributions += ['', r['wording'], '', 'Denominator: '+r['denominator'], '']
                        continue
                    percentages = ' | '.join(f"{r['percent'][g]:.1f}%" for g in ['support','oppose','neutral','unsure','nonresponse'])
                    lines.append(f"| {r['source']} {r['year']} ({r['variable']}) | {percentages} |")
                    notes.append(f"- **{r['source']} {r['year']} ({r['variable']}):** {r['wording']} Denominator: {r['denominator']}")
            lines += ['', 'Zero denotes zero in retained categories; it does not prove the original questionnaire lacked other response options.', ''] + notes + [''] + distributions
    lines += ['## Limits', ''] + [f'- {x}' for x in result['limitations']]
    return '\n'.join(lines)+'\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=Path, required=True)
    p.add_argument('--surveys', type=Path, required=True)
    p.add_argument('--mapping', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    cases = json.loads(args.cases.read_text())
    surveys = json.loads(args.surveys.read_text())
    result = compare(cases['cases'], surveys['survey_records'], json.loads(args.mapping.read_text()))
    result['input_sha256'] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in [args.cases, args.surveys, args.mapping]}
    result['survey_provenance'] = surveys.get('provenance', {})
    for path in [args.output, args.report]:
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    args.report.write_text(report(result))
    print(f"Compared {len(result['cases'])} cases; wrote {args.output} and {args.report}")


if __name__ == '__main__':
    main()
