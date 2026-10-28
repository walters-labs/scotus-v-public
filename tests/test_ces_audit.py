import unittest
import pandas as pd
from scripts.audit_ces import respondent_ids


class CESIdentifiersTests(unittest.TestCase):
    def test_numeric_and_string_identifiers_join_without_decimal_suffix(self):
        self.assertEqual(respondent_ids(pd.Series(['439219','130918481'])).tolist(),
                         respondent_ids(pd.Series([439219.0,130918481.0])).tolist())

    def test_invalid_identifiers_are_not_silently_truncated(self):
        for values in ([123.5], [None], ['invalid']):
            with self.assertRaises((ValueError,TypeError)):
                respondent_ids(pd.Series(values))
