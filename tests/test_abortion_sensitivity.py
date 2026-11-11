import copy
import unittest
from scripts.abortion_sensitivity import correlation, compare, variants


class SensitivityTests(unittest.TestCase):
    def test_isolates_margin_and_relevance_without_mutating_hits(self):
        hits=[dict(case_id='a',score=2,cases=[dict(year=2000,polarity=1)]),
              dict(case_id='b',score=1,cases=[dict(year=2000,polarity=-1/9)])]
        original=copy.deepcopy(hits)
        result=variants(hits,{'a':1,'b':-1})
        self.assertAlmostEqual(result['current'][2000],17/27)
        self.assertAlmostEqual(result['no_vote_margin'][2000],1/3)
        self.assertAlmostEqual(result['equal_cases'][2000],4/9)
        self.assertEqual(result['equal_cases_direction'][2000],0)
        self.assertEqual(hits,original)

    def test_metrics_use_only_explicit_years_and_exclude_zero_signs(self):
        result=compare({1:-1,2:0,3:1,4:100},{1:-1,2:0,3:1},[1,2,3])
        self.assertEqual(result['pearson_r'],1)
        self.assertEqual((result['same_sign'],result['sign_denominator']),(2,2))
        self.assertIsNone(correlation([1,1,1],[1,2,3]))
        self.assertIsNone(correlation([1,2],[1,2]))
