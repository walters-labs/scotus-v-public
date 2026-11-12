import copy
import json
from pathlib import Path
import unittest
from scripts.compare_policy import compare

class DatedSurveyTests(unittest.TestCase):
    def setUp(self):
        root=Path('data/research')
        self.cases=json.loads((root/'firearms-policy-components.json').read_text())['cases']
        self.mapping=json.loads((root/'firearms-policy-mapping.json').read_text())
        saved=json.loads((root/'firearms-policy-comparison.json').read_text())
        self.observations=[c['components'][0]['comparisons'][0]['observations'][0] for c in saved['cases']]

    def run_compare(self):return compare(self.cases,self.observations,self.mapping)

    def first(self):return self.run_compare()['cases'][0]['components'][0]['comparisons'][0]

    def test_dated_opt_in_and_unknown_timing(self):
        self.assertEqual(self.first()['status'],'available')
        self.mapping.pop('allow_same_year_with_dates')
        self.assertEqual(self.first()['status'],'no_prior_observation')
        self.mapping['allow_same_year_with_dates']=True
        self.observations[0].pop('fieldwork_source')
        self.assertEqual(self.first()['status'],'no_prior_observation')

    def test_same_day_or_later_excluded(self):
        for end in ['2022-06-23','2022-06-24']:
            self.observations[0]['fieldwork_end']=end
            self.assertEqual(self.first()['status'],'no_prior_observation')

    def test_invalid_intervals_fail(self):
        original=copy.deepcopy(self.observations[0])
        for changes in [dict(fieldwork_end='2022-03-01'),dict(fieldwork_end='2023-04-06'),dict(fieldwork_start=None)]:
            self.observations[0]={**original,**changes}
            with self.assertRaises(ValueError):self.run_compare()

    def test_rahimi_remains_contextual(self):
        c=self.run_compare()['cases'][1]['components'][0]
        self.assertEqual(c['comparison_fit'],'contextual')
        self.assertEqual(c['comparisons'][0]['observations'][0]['response_distribution'][1]['percent'],74.0)

    def test_published_values_and_denominators(self):
        spec=json.loads(Path('data/scotuspoll/policy-toplines.json').read_text())
        self.assertEqual({r['variable']:(r['item_n'],[a[2] for a in r['answers']]) for r in spec['rows']},
          {'bruen_2022':(2133,[52.6,47.4]),'rahimi_2024':(2218,[26.0,74.0]),'carson_2022':(2130,[48.7,51.3]),'shurtleff_2022':(2132,[44.3,55.7])})
        for row in spec['rows']:
            self.assertAlmostEqual(sum(a[2] for a in row['answers']),100)

    def test_saved_outputs_reproduce(self):
        for topic in ['firearms','religion']:
            root=Path('data/research')
            saved=json.loads((root/f'{topic}-policy-comparison.json').read_text())
            cases=json.loads((root/f'{topic}-policy-components.json').read_text())['cases']
            mapping=json.loads((root/f'{topic}-policy-mapping.json').read_text())
            records=[c['components'][0]['comparisons'][0]['observations'][0] for c in saved['cases']]
            self.assertEqual(compare(cases,records,mapping)['cases'],saved['cases'])
