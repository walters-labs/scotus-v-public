import unittest
import pandas as pd
from scripts.gss_uncertainty import estimate, estimate_composite


class SurveyVarianceTests(unittest.TestCase):
    def test_correlated_items_do_not_artificially_shrink_error(self):
        f=pd.DataFrame(dict(a=[1.,1.,-1.,-1.],b=[1.,1.,-1.,-1.],weight=[1.]*4,
                            stratum=[1]*4,psu=[1,1,2,2]))
        r=estimate_composite(f,['a','b'])
        self.assertEqual(r['standard_error'],1.)
        self.assertAlmostEqual(r['independence_assumption_standard_error'],2**-.5)
        f.b=-f.a
        self.assertEqual(estimate_composite(f,['a','b'])['standard_error'],0.)

    def test_known_cluster_totals_and_weight_scale_invariance(self):
        f=pd.DataFrame(dict(score=[1.,1.,-1.,-1.],weight=[1.]*4,
                            stratum=[1]*4,psu=[1,1,2,2]))
        r=estimate(f)
        self.assertEqual(r['mean'],0.)
        self.assertEqual(r['standard_error'],1.)
        f.weight*=10
        self.assertEqual(estimate(f)['standard_error'],1.)

    def test_missing_responses_retain_sampling_units(self):
        f=pd.DataFrame(dict(score=[1.,-1.,float('nan')],weight=[1.]*3,
                            stratum=[1]*3,psu=[1,2,3]))
        r=estimate(f)
        self.assertEqual(r['psus'],3)
        self.assertAlmostEqual(r['standard_error']**2,.75)

    def test_unsupported_design_does_not_claim_zero_uncertainty(self):
        f=pd.DataFrame(dict(score=[1.,-1.],weight=[1.,1.],stratum=[1,2],psu=[1,1]))
        self.assertIsNone(estimate(f)['standard_error'])
        f.stratum=float('nan')
        self.assertEqual(estimate(f)['status'],'missing design identifiers')
