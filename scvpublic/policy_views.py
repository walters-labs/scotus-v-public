"""Read only the published, precomputed policy examples."""
import json
from pathlib import Path

STUDIES = {'marriage': 'Marriage equality', 'abortion': 'Abortion',
           'firearms': 'Firearm rights', 'religion': 'Religion in public programs'}
DATA = Path(__file__).resolve().parent.parent / 'data' / 'research'
DIRECTIONS = {'expands': 'Expands protection or access', 'restricts': 'Restricts protection or access',
              'maintains_protection': 'Maintains protection', 'maintains_restriction': 'Allows or maintains a restriction',
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
    return study
