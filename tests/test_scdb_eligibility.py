import copy
import unittest

from scripts.compare_scdb_eligibility import category, comparison, scenarios


def doc(key, codes, polarity=1, score=1):
    return dict(case_id=key, score=score, cases=[dict(year=2024, polarity=polarity)],
                scdb_issues=dict(status='matched', issue_codes=codes,
                                 records=[dict(issue=c) for c in codes]))


class EligibilityTest(unittest.TestCase):
    def test_mixed_standing_is_preserved(self):
        mixed = doc('mixed', ['50020', '90310'])
        self.assertEqual(category(mixed), 'mixed_codes')
        self.assertEqual(scenarios([mixed])['narrow'], [mixed])
        self.assertEqual(scenarios([mixed])['broad_diagnostic'], [])

    def test_unknown_is_preserved(self):
        for codes in ([], ['invalid']):
            unknown = doc('unknown', codes)
            self.assertEqual(category(unknown), 'unknown')
            self.assertTrue(all(v == [unknown] for v in scenarios([unknown]).values()))
        partial = doc('partial', ['90240'])
        partial['scdb_issues']['records'].append(dict(issue=''))
        self.assertEqual(category(partial), 'unknown')

    def test_duplicates_do_not_multiply_weight_or_modify_input(self):
        a, b = doc('standing', ['90240'], -1, 3), doc('policy', ['50020'], 1, 1)
        a['scdb_issues']['records'] *= 4
        original = copy.deepcopy([a, b])
        candidate = scenarios([a, b])['narrow']
        row = comparison([a, b], candidate)[0]
        self.assertEqual(row['baseline'], -.5)
        self.assertEqual(row['candidate'], 1)
        self.assertEqual(row['baseline_count'], 2)
        self.assertEqual([a, b], original)

    def test_removed_year_is_missing_not_zero(self):
        row = comparison([doc('standing', ['90240'])], [])[0]
        self.assertIsNone(row['candidate'])
        self.assertIsNone(row['delta'])
        self.assertEqual(row['candidate_count'], 0)

    def test_strict_does_not_expand_to_general_judicial_codes(self):
        docs = [doc('explicit', ['90150']), doc('jurisdiction', ['90320'])]
        self.assertEqual([d['case_id'] for d in scenarios(docs)['strict']], ['jurisdiction'])
        self.assertEqual([d['case_id'] for d in scenarios(docs)['narrow']], ['jurisdiction'])
