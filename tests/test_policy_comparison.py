import copy
import json
from pathlib import Path
import unittest
from scripts.compare_policy import compare, report


class PolicyComparisonTests(unittest.TestCase):
    def setUp(self):
        self.cases = [dict(case_id='c', name='Example', date='2015-06-26', source='source', components=[dict(
            component_id='one', policy_id='policy', comparison_fit='direct', direction='expands',
            issue='Issue', decision='Decision', scope='Scope', locator='Part I', survey_fit='Direct policy question')])]
        self.mapping = dict(max_prior_years=3, policies={'policy': dict(support_definition='Supports policy', questions=[dict(source='S',variable='q'),dict(source='S',variable='q2')])})
        self.record = dict(source='S', variable='q', year=2014, wording='Question', denominator='All respondents', percent=dict(support=60,oppose=30,neutral=0,unsure=10,nonresponse=0))

    def run_comparison(self, records=None):
        return compare(self.cases, records if records is not None else [self.record], self.mapping)

    def test_timing_and_variants(self):
        records = [self.record, {**self.record,'variable':'q2'}, {**self.record,'year':2015}, {**self.record,'year':2016}]
        rows = self.run_comparison(records)['cases'][0]['components'][0]['comparisons'][0]['observations']
        self.assertEqual([(r['year'],r['variable']) for r in rows], [(2014,'q'),(2014,'q2')])

    def test_verified_dates_and_rounding(self):
        dated={**self.record,'year':2015,'field_start':'2015-04-16','field_end':'2015-04-20'}
        rows=self.run_comparison([self.record,dated])['cases'][0]['components'][0]['comparisons'][0]['observations']
        self.assertEqual(rows,[dated])
        for end in ['2015-06-26','2015-06-27']:
            rows=self.run_comparison([self.record,{**dated,'field_end':end}])['cases'][0]['components'][0]['comparisons'][0]['observations']
            self.assertEqual(rows,[self.record])
        with self.assertRaises(ValueError):
            self.run_comparison([{**dated,'field_end':'2015-01-01'}])
        rounded={k:v for k,v in dated.items() if k!='percent'}
        rounded.update(data_kind='published_topline',response_distribution=[
            dict(code='s',label='Support',percent=62),dict(code='o',label='Oppose',percent=36),dict(code='n',label='No opinion',percent=3)])
        self.run_comparison([rounded])
        with self.assertRaises(ValueError):
            self.run_comparison([{k:v for k,v in rounded.items() if k!='data_kind'}])

    def test_stale_and_missing_distinguished(self):
        for records, status in [([{**self.record,'year':2011}], 'no_prior_observation'),([], 'no_matching_question')]:
            row=self.run_comparison(records)['cases'][0]['components'][0]['comparisons'][0]
            self.assertEqual(row['status'],status)
            self.assertEqual(row['observations'],[])

    def test_procedural_not_zero(self):
        self.cases[0]['components'][0].update(direction='no_merits_ruling',comparison_fit='not_comparable')
        row=self.run_comparison()['cases'][0]['components'][0]
        self.assertEqual(row['direction'],'no_merits_ruling')
        self.assertEqual(row['comparisons'][0]['status'],'not_comparable')
        self.cases[0]['components'][0]['comparison_fit']='direct'
        with self.assertRaises(ValueError): self.run_comparison()

    def test_mixed_and_unresolved_not_collapsed(self):
        for direction in ['mixed','unresolved']:
            self.cases[0]['components'][0]['direction']=direction
            self.assertEqual(self.run_comparison()['cases'][0]['components'][0]['direction'],direction)

    def test_validation(self):
        for field,value in [('direction','typo'),('comparison_fit','typo'),('policy_id','typo')]:
            old=self.cases[0]['components'][0][field]
            self.cases[0]['components'][0][field]=value
            with self.assertRaises(ValueError): self.run_comparison()
            self.cases[0]['components'][0][field]=old
        with self.assertRaises(ValueError): self.run_comparison([self.record,self.record])
        self.record['percent']['support']=float('nan')
        with self.assertRaises(ValueError): self.run_comparison()

    def test_does_not_mutate_inputs(self):
        original=copy.deepcopy((self.cases,self.record,self.mapping))
        result=self.run_comparison()
        result['cases'][0]['components'][0]['comparisons'][0]['observations'][0]['percent']['support']=0
        self.assertEqual((self.cases,self.record,self.mapping),original)

    def test_marriage_extension_preserves_pilot_and_gaps(self):
        def read(name): return json.loads(Path('data/research/'+name+'.json').read_text())
        baseline=read('marriage-case-study')
        result=compare(read('marriage-case-components')['cases'],baseline['survey_records'],read('marriage-policy-mapping'))
        cases={c['case_id']:c for c in result['cases']}
        self.assertEqual(len(cases),5)
        baker=cases['us-409-810']['components'][0]
        self.assertTrue(all(r['status']=='no_prior_observation' for r in baker['comparisons']))
        pavan=cases['2016-081']['components'][0]
        self.assertEqual(pavan['comparison_fit'],'contextual')
        self.assertEqual(len(pavan['comparisons']),4)
        self.assertTrue(all(r['observations'][0]['year']==2016 for r in pavan['comparisons']))
        for cid in ['2012-079','2014-070']:
            case=cases[cid]
            for row in case['components'][0]['comparisons']:
                expected=baseline['prior_observations'][case['date'][:4]][row['source']]
                self.assertEqual(row['observations'],[] if expected is None else [expected])
        self.assertIn('no prior observation',report(result))
        self.assertIn('not comparable',report(result))
