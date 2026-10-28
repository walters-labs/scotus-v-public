import unittest
from scvpublic.chart import chart, combine_sources


class CombinedTests(unittest.TestCase):
    def test_equal_sources_and_no_interpolation(self):
        values, contributors = combine_sources({'ANES': {2000: 1, 2004: 0},
            'GSS': {2000: -1, 2002: .6}, 'CES': {2000: .6}})
        self.assertAlmostEqual(values[2000], .2)
        self.assertEqual(values[2002], .6)
        self.assertEqual(values[2004], 0)
        self.assertNotIn(2001, values)
        self.assertEqual(contributors[2002], ['GSS'])
        self.assertEqual(combine_sources({}), ({}, {}))

    def test_chart_selection_and_provenance(self):
        args = dict(court={2000: -.5}, public={2000: 1}, gss={2000: -1}, ces={2000: .6})
        combined = chart(**args, view='combined')
        self.assertEqual(combined.count('<circle'), 2)
        self.assertIn('Combined 2000: 0.200; sources: ANES, GSS, CES; equal weight 1/3 each', combined)
        single = chart(**args, view='gss')
        self.assertEqual(single.count('<circle'), 2)
        self.assertIn('GSS 2000: -1.000', single)
        self.assertNotIn('CES 2000:', single)
        self.assertEqual(chart(**args, view='all').count('<circle'), 4)
