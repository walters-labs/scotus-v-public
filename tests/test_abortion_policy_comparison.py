import copy
import json
from pathlib import Path
import unittest
from scripts.compare_policy import compare, report

ROOT=Path('data/research')

def load(name):
    return json.loads((ROOT/(name+'.json')).read_text())


class AbortionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.cases=load('abortion-policy-components')['cases']
        self.surveys=load('abortion-policy-surveys')['survey_records']
        self.mapping=load('abortion-policy-mapping')

    def result(self):
        return compare(self.cases,self.surveys,self.mapping)

    def test_named_roe_question_orientation_matches_previous_audit(self):
        cases={c['case_id']:c for c in self.result()['cases']}
        row=cases['2021-019']['components'][0]['comparisons'][0]['observations'][0]
        old=load('voter-roe-dobbs-comparison')['survey']
        expected={r['code']:r['weighted_percent'] for r in old['responses']}
        self.assertEqual(row['percent']['support'],expected['2'])
        self.assertEqual(row['percent']['oppose'],expected['1'])
        self.assertEqual(row['percent']['unsure'],expected['3'])
        self.assertEqual(row['year'],2020)

    def test_historical_categories_not_forced_into_binary(self):
        roe=self.result()['cases'][0]['components'][0]
        record=next(c for c in roe['comparisons'] if c['source']=='ANES')['observations'][0]
        self.assertEqual(record['year'],1972)
        self.assertNotIn('percent',record)
        self.assertEqual([c['code'] for c in record['response_distribution']],['1','2','3','4','9'])
        self.assertAlmostEqual(sum(c['percent'] for c in record['response_distribution']),100)

    def test_specific_policy_gaps_and_mixed_case(self):
        result=self.result()
        casey=next(c for c in result['cases'] if c['case_id']=='1991-117')
        self.assertEqual({c['direction'] for c in casey['components']},{'expands','maintains_protection','maintains_restriction'})
        for c in casey['components'][1:]:
            self.assertEqual(c['coverage_status'],'no_matching_question')
            self.assertEqual(c['comparisons'],[])
        harris=next(c for c in result['cases'] if c['case_id']=='1979-148')
        self.assertEqual(harris['components'][0]['comparisons'],[])
        self.assertIn('No matching question in this selection',report(result))

    def test_distribution_validation(self):
        record=next(r for r in self.surveys if 'response_distribution' in r)
        original=copy.deepcopy(record)
        for bad in [-1,float('nan'),101]:
            record['response_distribution'][0]['percent']=bad
            with self.assertRaises(ValueError): self.result()
        record.clear();record.update(original)
        record['response_distribution'][1]['code']=record['response_distribution'][0]['code']
        with self.assertRaises(ValueError): self.result()

    def test_deterministic_saved_result_and_strict_timing(self):
        result=self.result()
        saved=load('abortion-policy-comparison')
        self.assertEqual(result['cases'],saved['cases'])
        for case in result['cases']:
            year=int(case['date'][:4])
            for component in case['components']:
                for comparison in component['comparisons']:
                    for observation in comparison['observations']:
                        self.assertTrue(year-3<=observation['year']<year)
