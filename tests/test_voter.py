import copy
import unittest
import pandas as pd
from scvpublic.voter import summarize
from scvpublic.chart import chart


class VoterTests(unittest.TestCase):
    def setUp(self):
        self.answer=pd.Series([1,2,8,1,1])
        self.weight=pd.Series([3.,1.,20.,0.,float('nan')])
        self.expected=dict(expected_labels={'1':'Favor','2':'Oppose','8':'Unknown'},published_counts={'1':1,'2':1,'8':1})

    def test_weighted_sample_and_missing_answers(self):
        result=summarize(self.answer,self.weight,{1:1,2:-1},self.expected)
        self.assertEqual(result['score'],.5)
        self.assertEqual(result['respondents'],2)
        self.assertEqual(result['weight_sum'],4)
        self.assertEqual(result['excluded_unweighted_answers'],2)

    def test_reject_unknown_codes_weights_and_count_drift(self):
        for value in [-1,float('inf'),float('-inf')]:
            weights=self.weight.copy(); weights[0]=value
            with self.assertRaisesRegex(ValueError,'weight'):
                summarize(self.answer,weights,{1:1,2:-1},self.expected)
        answers=self.answer.copy(); answers[0]=77
        with self.assertRaisesRegex(ValueError,'response code'):
            summarize(answers,self.weight,{1:1,2:-1},self.expected)
        expected=copy.deepcopy(self.expected);expected['published_counts']['1']=2
        with self.assertRaisesRegex(ValueError,'frequency mismatch'):
            summarize(self.answer,self.weight,{1:1,2:-1},expected)

    def test_midpoint_and_mapping_validation(self):
        result=summarize(self.answer,self.weight,{1:1,2:0},self.expected)
        self.assertEqual(result['score'],.75)
        for scores in [{1:2},{1:float('nan')},{99:1},{}]:
            with self.assertRaisesRegex(ValueError,'mapping'):
                summarize(self.answer,self.weight,scores,self.expected)

    def test_voter_chart_and_equal_source_contribution(self):
        self.assertIn('VOTER 2020: 0.500',chart({}, {}, voter={2020:.5},view='voter'))
        combined=chart({}, {2020:-.5},voter={2020:.5},view='combined')
        self.assertIn('Combined 2020: 0.000',combined)
        self.assertIn('equal weight 1/2 each',combined)

    def test_annual_means_weight_waves_equally_and_reject_duplicates(self):
        from scvpublic.voter import annualize
        observations=[dict(source_code='a_2019Jan',year='2019',score=-.5,respondents=100,weight_sum=100),dict(source_code='a_2019Nov',year='2019',score=.5,respondents=1000,weight_sum=1000)]
        result=annualize(observations)['2019']
        self.assertEqual(result['score'],0)
        self.assertEqual(result['respondents'],1100)
        self.assertEqual(len(result['waves']),2)
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            annualize(observations+[observations[0]])

    def test_reviewed_direction_traps(self):
        import json
        from pathlib import Path
        spec=json.loads(Path('data/manifests/voter-policy-batch.json').read_text())
        entries={d['code']:d for d in spec['entries']}
        repeal=entries['voter_aca_favor']
        self.assertIn('repeal and replace',repeal['question'])
        self.assertEqual(repeal['scores']['1'],-1)
        self.assertEqual(repeal['scores']['4'],1)
        self.assertEqual(entries['voter_govtreg_banks']['scores'],{'1':1,'2':-1,'3':0})
        self.assertEqual(entries['voter_view_deathpen']['scores'],{'1':-1,'2':1})
        for entry in entries.values():
            for wave in entry['waves']:
                for code in entry['scores']:
                    label=wave['expected_labels'][code].lower()
                    self.assertFalse(any(x in label for x in ['know','skipped','not asked']))
