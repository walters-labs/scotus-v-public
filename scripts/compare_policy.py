"""Offline component-level comparison; never infers legal meaning from search scores."""
import argparse
from copy import deepcopy
from datetime import date
import hashlib
import json
import math
from pathlib import Path

DIRECTIONS = {'expands', 'restricts', 'maintains_restriction', 'mixed', 'unresolved', 'no_merits_ruling'}
FITS = {'direct', 'contextual', 'not_comparable'}
GROUPS = {'support', 'oppose', 'neutral', 'unsure', 'nonresponse'}


def compare(cases, surveys, mapping):
    """Select latest strictly earlier calendar year per source, retaining ties.

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
        values = r['percent']
        if set(values) != GROUPS or any(not math.isfinite(v) or v < 0 or v > 100 for v in values.values()):
            raise ValueError('Invalid response shares')
        if not math.isclose(sum(values.values()), 100, abs_tol=1e-6):
            raise ValueError('Response shares must sum to 100')
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
                eligible = [r for r in matched if year-age <= r['year'] < year]
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
            components.append({**deepcopy(component), 'comparisons': comparisons})
        output.append({**deepcopy(case), 'components': components})
    return dict(schema_version=1, timing_rule=f'Latest earlier calendar year per source within {age} years; retain all same-year question variants.',
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
            for comparison in component['comparisons']:
                if not comparison['observations']:
                    lines.append(f"| {comparison['source']}: {comparison['status'].replace('_', ' ')} | — | — | — | — | — |")
                for r in comparison['observations']:
                    percentages = ' | '.join(f"{r['percent'][g]:.1f}%" for g in ['support','oppose','neutral','unsure','nonresponse'])
                    lines.append(f"| {r['source']} {r['year']} ({r['variable']}) | {percentages} |")
                    notes.append(f"- **{r['source']} {r['year']} ({r['variable']}):** {r['wording']} Denominator: {r['denominator']}")
            lines += ['', 'Zero denotes zero in retained categories; it does not prove the original questionnaire lacked other response options.', ''] + notes + ['']
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
