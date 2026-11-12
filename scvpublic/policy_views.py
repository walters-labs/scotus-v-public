"""Read only the published, precomputed policy examples."""
import json
from pathlib import Path

STUDIES = {'marriage': 'Marriage equality', 'abortion': 'Abortion', 'capital-punishment': 'Capital punishment',
           'affirmative-action': 'Affirmative action', 'voter-id': 'Voter ID', 'firearms': 'Handgun rights', 'contraception': 'Contraception', 'medical-marijuana': 'Medical marijuana', 'school-religion': 'School religion', 'campaign-finance': 'Campaign finance'}
DATA = Path(__file__).resolve().parent.parent / 'data' / 'research'
DIRECTIONS = {'expands': 'Expands protection or access', 'restricts': 'Restricts protection or access',
              'maintains_protection': 'Maintains protection', 'maintains_restriction': 'Allows or maintains a restriction',
              'maintains_permission': 'Maintains legal permission',
              'no_merits_ruling': 'Procedural ruling', 'mixed': 'Mixed outcome', 'unresolved': 'Unresolved'}


def load_study(topic):
    if topic not in STUDIES:
        raise KeyError(topic)
    study = json.loads((DATA / f'{topic}-policy-comparison.json').read_text())
    for case in study['cases']:
        for component in case['components']:
            observations = [r for comparison in component['comparisons'] for r in comparison['observations']]
            component['observations'] = observations
            fit = component['comparison_fit']
            component['display_fit'] = ('Not comparable' if fit == 'not_comparable' else
                                        'Missing data' if not observations else
                                        'Direct comparison' if fit == 'direct' else 'Context only')
            component['display_direction'] = DIRECTIONS[component['direction']]
    if topic == 'marriage':
        history = json.loads((DATA / 'marriage-opinion-history.json').read_text())
        records = history['survey_records']
        study['history'] = [
            {'source': source, 'observations': sorted(
                [r for r in records if r['source'] == source],
                key=lambda r: (r['year'], r['variable']))}
            for source in sorted({r['source'] for r in records})]
    if topic == 'abortion':
        records = json.loads((DATA / 'abortion-opinion-history.json').read_text())['survey_records']
        groups = [
            ('ANES', 'VCF0837', 'When should abortion be permitted? · earlier wording'),
            ('ANES', 'VCF0838', 'When should abortion be permitted? · later wording'),
            ('GSS', 'abany', 'Legal abortion for any reason'),
            ('PRRI', None, 'Abortion legal in all or most cases')]
        study['history'] = [dict(source=source, title=title, observations=sorted(
            [r for r in records if r['source'] == source and (variable is None or r['variable'] == variable)],
            key=lambda r: r['year'])) for source, variable, title in groups]
        study['roe_topline'] = next(r for c in study['cases'] for part in c['components'] for r in part['observations'] if r['source'] == 'Gallup')
        study['roe_observation'] = next(r for r in records if r['source'] == 'VOTER')
    return study
