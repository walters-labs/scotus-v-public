import unittest
from scripts.evaluate_cutoffs import summary


class CutoffEvaluationTests(unittest.TestCase):
    def test_cutoff_reports_actual_losses_and_keeps_unknown_separate(self):
        hits=[dict(case_id='a',score=.30),dict(case_id='b',score=.35),
              dict(case_id='c',score=.50),dict(case_id='unknown',score=.55)]
        labels={'a':{'label':'direct'},'b':{'label':'direct'},'c':{'label':'irrelevant'}}
        result=summary(hits,labels,.35)
        self.assertEqual(result['total'],3)
        self.assertEqual(result['lost_direct'],['a'])
        self.assertEqual(result['direct_retention'],.5)
        self.assertEqual(result['labels']['unjudged'],1)
        self.assertEqual(result['retained_irrelevant'],['c'])

    def test_no_known_positives_does_not_claim_perfect_retention(self):
        result=summary([dict(case_id='unknown',score=.4)],{},.35)
        self.assertIsNone(result['direct_retention'])
        self.assertEqual(result['labels']['irrelevant'],0)

    def test_retention_is_relative_to_current_pool_not_all_labeled_cases(self):
        labels={'a':{'label':'direct'},'missing':{'label':'direct'}}
        result=summary([dict(case_id='a',score=.4)],labels,.35)
        self.assertEqual(result['direct_retention'],1)
        self.assertEqual(result['lost_direct'],[])
