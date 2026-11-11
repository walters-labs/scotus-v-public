import unittest
import pandas as pd
from scripts.marriage_case_study import summarize


class MarriageSharesTests(unittest.TestCase):
    def test_unsure_is_retained_not_neutral_or_dropped(self):
        f=pd.DataFrame({'q':[1,2,3,9,None],'w':[2.,1.,1.,100.,50.]})
        r=summarize(f,'q','w',{'1':'support','2':'oppose','3':'unsure'},excluded=['9','missing'])
        self.assertEqual(r['percent'],dict(support=50,oppose=25,neutral=0,unsure=25,nonresponse=0))
        self.assertEqual(r['n'],3)
        self.assertEqual(r['excluded_positive_weight'],2)

    def test_unmapped_answers_fail(self):
        with self.assertRaises(ValueError):
            summarize(pd.DataFrame({'q':[1,8],'w':[1,1]}),'q','w',{'1':'support'})

    def test_invalid_weights_fail(self):
        for w in [-1,float('inf')]:
            with self.assertRaises(ValueError):
                summarize(pd.DataFrame({'q':[1],'w':[w]}),'q','w',{'1':'support'})
