import hashlib
import unittest

from scripts.build_survey_description_bundle import description_text


class SurveyDescriptionTests(unittest.TestCase):
    def setUp(self):
        self.doc = dict(title='Fuel standards', question='Lower the requirement?', years={'2018': .2})
        self.entry = dict(code='fuel', topic='Vehicle efficiency', policy='Support or oppose lowering standards.',
            scope='Cars', equivalent_terms=['fuel economy'],
            source_text_sha256=hashlib.sha256(b'Fuel standards\nLower the requirement?').hexdigest())

    def test_description_preserves_source_and_direction(self):
        before = dict(self.doc)
        text = description_text(self.entry, self.doc)
        self.assertIn('lowering standards', text)
        self.assertIn('fuel economy', text)
        self.assertEqual(self.doc, before)

    def test_changed_wording_invalidates_review(self):
        self.doc['question'] = 'Raise the requirement?'
        with self.assertRaisesRegex(ValueError, 'wording changed'):
            description_text(self.entry, self.doc)

    def test_empty_description_is_rejected(self):
        self.entry['policy'] = ' '
        with self.assertRaisesRegex(ValueError, 'description field'):
            description_text(self.entry, self.doc)
