import unittest
from datetime import datetime, timezone
from scripts.audit_prediction_availability import audit_cases


class PredictionAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.cases = [dict(case_id='train', date='2000-06-01', sentiment=.1, sources=['A']),
                      dict(case_id='test', date='2001-06-01', sentiment=.2, sources=['B'])]
        self.predictions = [dict(case_id='test', year=2001, training_cases=1)]

    def audit(self, bounds):
        return audit_cases(self.cases, self.predictions, bounds)[0]

    def test_later_training_input_is_detected_without_later_test_input(self):
        r = self.audit({'A': datetime(2002,1,1,tzinfo=timezone.utc)})
        self.assertEqual(r['training_cases_using_later_release'], ['train'])
        self.assertFalse(r['later_release_in_test_features'])
        self.assertEqual(r['unverified_sources'], ['B'])
        self.assertEqual(r['status'], 'known later-release input')

    def test_same_date_release_is_unresolved_without_decision_time(self):
        for hour in [0,12,23]:
            r = self.audit({'B': datetime(2001,6,1,hour,tzinfo=timezone.utc)})
            self.assertFalse(r['later_release_in_test_features'])
            self.assertEqual(r['status'], 'availability unresolved')
        self.assertTrue(self.audit({'B': datetime(2001,6,2,tzinfo=timezone.utc)})['later_release_in_test_features'])

    def test_earlier_lower_bound_does_not_certify_availability(self):
        r = self.audit({s:datetime(1990,1,1,tzinfo=timezone.utc) for s in ['A','B']})
        self.assertEqual(r['status'], 'availability unresolved')

    def test_mismatched_training_count_year_and_duplicate_cases_fail(self):
        self.predictions[0]['training_cases']=2
        with self.assertRaisesRegex(ValueError,'count'):
            self.audit({})
        self.predictions[0].update(training_cases=1,year=2002)
        with self.assertRaisesRegex(ValueError,'year'):
            self.audit({})
        self.predictions[0]['year']=2001
        self.cases.append(self.cases[0])
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            self.audit({})

    def test_weight_introduction_uses_the_weight_for_the_survey_year(self):
        from scripts.audit_gss_weight_availability import affected_predictions
        evidence = dict(release_lower_bound='2022-11-01',
                        documented_added_weights={'WTSSPS':[2002,2004], 'WTSSNRPS':[]})
        cases = [dict(case_id='a',date='2003-06-01',sentiment=.2,survey_year=2002,sources=['GSS']),
                 dict(case_id='b',date='2005-06-01',sentiment=.2,survey_year=2004,sources=['GSS'])]
        rows=affected_predictions(cases,[dict(case_id='b',year=2005,training_cases=1)],evidence)
        self.assertEqual(rows[0]['affected_input_cases'],['a'])
        # Being after the lower-bound month does not certify availability; it is simply unflagged.
        cases[1]['date']='2023-06-01'
        self.assertEqual(affected_predictions(cases,[dict(case_id='b',year=2023,training_cases=1)],evidence),[])
