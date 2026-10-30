import unittest
from scripts.experiment_clean_survey_text import clean_text


class CleanSurveyTextTests(unittest.TestCase):
    def test_original_remains_intact_and_policy_parentheses_survive(self):
        doc = {'title': 'Policy', 'question': '2004: Should coverage (including children) expand? V083151'}
        before = dict(doc)
        result = clean_text(doc)
        self.assertEqual(doc, before)
        self.assertIn('(including children)', result)
        self.assertNotIn('V083151', result)
        self.assertNotIn('2004:', result)

    def test_removes_interviewer_instruction_and_duplicate_sentence(self):
        result = clean_text({'title': 'Policy', 'question':
            'Now I would like you to look at a card. Should coverage expand? Should coverage expand?'})
        self.assertEqual(result, 'Policy. Should coverage expand?')
