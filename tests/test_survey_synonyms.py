import unittest
from scripts.evaluate_survey_synonyms import compare


class SynonymEvaluationTests(unittest.TestCase):
    def test_empty_agreement_is_not_success(self):
        result = compare([], [], ['direct'], [])
        self.assertIsNone(result['jaccard'])
        self.assertTrue(result['both_empty'])
        self.assertEqual(result['missed_left'], ['direct'])

    def test_equal_wrong_results_still_fail_relevance(self):
        result = compare(['wrong'], ['wrong'], ['direct'], ['wrong'])
        self.assertEqual(result['jaccard'], 1)
        self.assertEqual(result['irrelevant_left'], ['wrong'])
        self.assertEqual(result['missed_right'], ['direct'])
