import copy
import unittest

import pandas as pd

from scripts.build_ces_climate import score_item


class ClimateScoringTests(unittest.TestCase):
    def setUp(self):
        self.entry = dict(code='lower', source_code='fuel', title='Lower standards',
            question='Lower fuel efficiency?', family='fuel', weight='weight',
            scores={'1': -1, '2': 1}, years=[2018],
            original_codes={'2018': 'CC18_415b'},
            published_counts={'2018': {'1': 2, '2': 2}})
        self.frame = pd.DataFrame(dict(year=[2018]*5, fuel=[1, 2, 1, 2, None],
            weight=[1, 3, 0, float('inf'), 100]))

    def test_reversed_policy_and_invalid_weights(self):
        doc, audit = score_item(self.frame, self.entry)
        self.assertEqual(doc['years']['2018'], .5)
        self.assertEqual(doc['respondents']['2018'], 2)
        self.assertEqual(doc['weight_sums']['2018'], 4)
        self.assertEqual(audit[0]['invalid_weight_responses'], 2)
        self.assertEqual(doc['year_provenance']['2018']['source_code'], 'CC18_415b')

    def test_source_frequency_mismatch_fails(self):
        entry = copy.deepcopy(self.entry)
        entry['published_counts']['2018']['1'] = 3
        with self.assertRaisesRegex(ValueError, 'frequencies differ'):
            score_item(self.frame, entry)

    def test_unreviewed_year_is_not_scored(self):
        extra = self.frame.copy()
        extra['year'] = 2019
        doc, _ = score_item(pd.concat([self.frame, extra]), self.entry)
        self.assertEqual(set(doc['years']), {'2018'})
