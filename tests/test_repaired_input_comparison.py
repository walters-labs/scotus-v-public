import unittest
from scripts.compare_repaired_inputs import packet


class ComparisonPacketsTest(unittest.TestCase):
    def test_short_input_is_preserved(self):
        p=packet('case','','Per Curiam. The writ is dismissed.','principal_text_candidate')
        s=p['sections'][0]
        self.assertFalse(s['excerpted'])
        self.assertEqual(''.join(c['text'] for c in s['passages']),'Per Curiam. The writ is dismissed.')

    def test_budget_and_selection_same_for_both_labels(self):
        text='Some long text. '*2000
        old=packet('case','Summary. '*1000,text,'opinion')
        new=packet('case','Summary. '*1000,text,'authored_text_candidate')
        for a,b in zip(old['sections'],new['sections'],strict=True):
            self.assertEqual(a['passages'],b['passages'])
            self.assertEqual(a['excerpted'],b['excerpted'])
        self.assertLessEqual(sum(len(c['text']) for s in old['sections'] for c in s['passages']),16000)
        self.assertTrue(all(s['excerpted'] for s in old['sections']))
