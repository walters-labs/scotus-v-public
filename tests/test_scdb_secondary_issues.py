import unittest
from scripts.audit_scdb_secondary_issues import compare

class SecondaryIssueTests(unittest.TestCase):
    def test_secondary_standing_is_recovered_without_counting_dockets(self):
        r=compare([{'issue':'50020'}],[{'issue':'50020'},{'issue':'90310'},{'issue':'90310'}])
        self.assertTrue(r['recovered_signal'])
        self.assertEqual(r['all_issues'],['50020','90310'])
        self.assertEqual(r['all_signals'],['standing_issue'])

    def test_missing_signal_does_not_mean_merits(self):
        r=compare([{'issue':'50020'}],[{'issue':'50020'}])
        self.assertFalse(r['recovered_signal'])
        self.assertEqual(r['all_signals'],[])

    def test_existing_signal_is_not_new(self):
        self.assertFalse(compare([{'issue':'90240'}],[{'issue':'90240'},{'issue':'50020'}])['recovered_signal'])
