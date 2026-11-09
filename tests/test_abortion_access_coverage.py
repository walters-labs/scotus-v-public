import unittest
from scripts.count_abortion_access_coverage import prior_year


class PriorCoverageTests(unittest.TestCase):
    def test_same_year_and_future_are_excluded(self):
        self.assertIsNone(prior_year(['2022','2024'],2022))

    def test_five_year_boundary_is_inclusive(self):
        self.assertEqual(prior_year(['2016','2017'],2022),2017)
        self.assertIsNone(prior_year(['2016'],2022))

    def test_latest_prior_year_without_interpolation(self):
        self.assertEqual(prior_year(['2018','2020','2022'],2022),2020)

    def test_empty_coverage(self):
        self.assertIsNone(prior_year([],1971))
