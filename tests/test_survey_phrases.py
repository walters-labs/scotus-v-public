import unittest
from scripts.experiment_survey_phrases import phrases


class PhraseExtractionTests(unittest.TestCase):
    def test_preserves_boundaries_and_does_not_join_removed_words(self):
        extracted = set(phrases('Health care. Birth control; clean and safe water'))
        self.assertIn('health care', extracted)
        self.assertIn('birth control', extracted)
        self.assertNotIn('care birth', extracted)
        self.assertNotIn('clean safe', extracted)
        self.assertNotIn('control clean', extracted)

    def test_deterministic_with_no_phrases_for_punctuation(self):
        self.assertEqual(list(phrases('!?')), [])
        self.assertEqual(list(phrases('Gun control')), list(phrases('gun control')))


class WeightedExpansionTests(unittest.TestCase):
    def test_synonym_confidence_survives_normalization_and_duplicates(self):
        from unittest.mock import patch
        from scvpublic.survey_search import weighted_lexical
        def retrieve(db, corpus, terms, **kwargs):
            return [] if terms == ['original'] else [dict(code='match', score=2.)]
        with patch('scvpublic.survey_search.search', side_effect=retrieve):
            weights = weighted_lexical(None, 'gss', ['original'], [('alias', .7), ('alias2', .6)])
        self.assertAlmostEqual(weights['match'], .7)

    def test_no_expansion_preserves_original_relative_scores(self):
        from unittest.mock import patch
        from scvpublic.survey_search import weighted_lexical
        with patch('scvpublic.survey_search.search', return_value=[
                dict(code='first', score=2.), dict(code='second', score=1.)]):
            self.assertEqual(weighted_lexical(None, 'gss', ['query'], []),
                             {'first': 1., 'second': .5})
