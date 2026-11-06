import unittest
from scripts.audit_scdb_procedure import signal

class ScdbSignalTests(unittest.TestCase):
    def test_explicit_no_merits_is_separate_from_standing(self):
        self.assertEqual(signal('90150'),'explicit_no_merits_issue')
        self.assertEqual(signal('90200'),'explicit_no_merits_issue')
        self.assertEqual(signal('90240'),'standing_issue')

    def test_topic_code_is_unlabeled_not_merits(self):
        self.assertEqual(signal('50020'),'no_selected_signal_not_a_merits_label')
        self.assertEqual(signal('90110'),'no_selected_signal_not_a_merits_label')

    def test_missing_and_non_code_values(self):
        self.assertEqual(signal(''),'missing_issue')
        self.assertEqual(signal(None),'missing_issue')
        self.assertEqual(signal('90151'),'no_selected_signal_not_a_merits_label')

    def test_cameron_and_bellotti_remain_descriptive(self):
        self.assertEqual(signal('90480'),'timeliness_issue')
        self.assertEqual(signal('90070'),'comity_issue')
