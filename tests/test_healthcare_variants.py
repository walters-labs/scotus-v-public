import unittest
from scripts.experiment_healthcare_variants import variants, merge


class HealthcareVariantTests(unittest.TestCase):
    def test_exact_spelling_variants_only(self):
        for q in ['healthcare','health care','health-care',' HEALTH CARE ','health  care']:
            self.assertEqual(variants(q),['healthcare','health care'])
        for q in ['child care','health career','mental health care','birth control']:
            self.assertEqual(variants(q),[q])

    def test_max_score_not_sum_and_no_duplicate_cases(self):
        hits=merge({'a':[{'case_id':'one','score':.2},{'case_id':'two','score':.4}],
                    'b':[{'case_id':'one','score':.5}]})
        self.assertEqual([(h['case_id'],h['score']) for h in hits],[('one',.5),('two',.4)])
        self.assertEqual(hits[0]['winning_variant'],'b')

    def test_stable_tie_order(self):
        hits=merge({'a':[{'case_id':'z','score':.5},{'case_id':'a','score':.5}]})
        self.assertEqual([h['case_id'] for h in hits],['a','z'])
