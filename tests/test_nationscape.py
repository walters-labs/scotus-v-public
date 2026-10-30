import copy
import unittest
import pandas as pd
from scvpublic.nationscape import summarize, annualize
from scvpublic.chart import chart


class NationscapeTests(unittest.TestCase):
    def setUp(self):
        self.frame=pd.DataFrame({'gov_insurance':[1,2,999,float('nan')],'weight':[3,1,1,10]})
        self.expected={'published_n':3,'published_percentages':{'1':60,'2':20,'999':20}}

    def test_unsure_in_toplines_but_not_polarity(self):
        result=summarize(self.frame,self.expected)
        self.assertEqual(result['score'],.5)
        self.assertEqual(result['respondents'],2)
        self.assertEqual(result['weight_sum'],4)

    def test_invalid_input_and_topline_drift(self):
        for column,value in [('gov_insurance',888),('weight',0),('weight',float('inf'))]:
            frame=self.frame.copy();frame.loc[0,column]=value
            with self.assertRaises(ValueError):summarize(frame,self.expected)
        expected=copy.deepcopy(self.expected);expected['published_percentages']['1']=62
        with self.assertRaisesRegex(ValueError,'percentage mismatch'):summarize(self.frame,expected)
        expected=copy.deepcopy(self.expected);expected['published_n']=4
        with self.assertRaisesRegex(ValueError,'count mismatch'):summarize(self.frame,expected)

    def test_equal_wave_weights_and_duplicate_guard(self):
        weeks=[dict(date='2020-01-01',score=1,respondents=100),dict(date='2020-01-08',score=-1,respondents=1000),dict(date='2021-01-01',score=.5,respondents=20)]
        self.assertEqual(annualize(weeks),{'2020':0,'2021':.5})
        with self.assertRaisesRegex(ValueError,'Duplicate'):annualize(weeks+[weeks[0]])
        self.assertIn('Combined 2020: 0.000',chart({}, {2020:-.5},nationscape={2020:.5},view='combined'))
        self.assertIn('Nationscape 2020: 0.500',chart({}, {},nationscape={2020:.5},view='nationscape'))

    def test_validation_weights_do_not_change_primary_estimate(self):
        expected={'published_n':3,'published_percentages':{'1':20,'2':60,'999':20}}
        check=pd.Series([1,3,1,10])
        result=summarize(self.frame,expected,check)
        self.assertEqual(result['score'],.5)
        self.assertEqual(result['percentages']['1'],20)
