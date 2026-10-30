from copy import deepcopy
import unittest
from scvpublic.survey_schema import prepare, validate, VERSION


class SurveySchemaTests(unittest.TestCase):
    def setUp(self):
        self.payload = dict(methodology='explicit-anes-v1', sources={'mapping.json': 'a'*64},
            documents=[dict(code='q1', family='policy', title='Policy', question='Original wording?',
                weight='survey_weight', years={'2020': .25}, respondents={'2020': 20})])

    def test_legacy_validation_is_nonmutating_and_prepare_versions(self):
        original = deepcopy(self.payload)
        self.assertEqual(validate(self.payload), dict(questions=1, question_years=1))
        self.assertEqual(self.payload, original)
        prepare(self.payload)
        self.assertEqual(self.payload['schema_version'], VERSION)
        self.assertNotIn('weight_sums', self.payload['documents'][0])

    def test_unknown_version_and_checksum_are_rejected(self):
        for update in [dict(schema_version='future'), dict(sources={'input': 'bad'})]:
            with self.subTest(update=update), self.assertRaises(ValueError):
                validate(dict(self.payload, **update))

    def test_duplicate_question_rejected_but_shared_family_allowed(self):
        self.payload['documents'].append(deepcopy(self.payload['documents'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate'): validate(self.payload)
        self.payload['documents'][1]['code'] = 'q2'
        validate(self.payload)

    def test_scores_counts_and_years(self):
        for fields in [dict(years={'2020': float('nan')}), dict(years={'2020': 1.01}),
                       dict(respondents={'2021': 20}), dict(respondents={'2020': True}),
                       dict(respondents={'2020': 0}), dict(years={'bad': 0}, respondents={'bad': 20})]:
            p = deepcopy(self.payload); p['documents'][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(ValueError): validate(p)

    def test_optional_metadata_is_checked_when_present(self):
        for fields in [dict(search_text=''), dict(weight_sums={'2020': -1}),
                       dict(weight_sums={'2021': 20}), dict(scores={'1': float('inf')}),
                       dict(year_provenance={'2020': {}})]:
            p = deepcopy(self.payload); p['documents'][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(ValueError): validate(p)

    def test_empty_observations_and_partial_provenance_are_supported(self):
        d = self.payload['documents'][0]
        d.update(years={}, respondents={}, year_provenance={})
        validate(self.payload)

    def test_failed_prepare_does_not_add_version(self):
        self.payload['documents'][0]['years']['2020'] = 2
        with self.assertRaises(ValueError): prepare(self.payload)
        self.assertNotIn('schema_version', self.payload)
