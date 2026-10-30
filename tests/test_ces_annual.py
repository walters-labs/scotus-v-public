from copy import deepcopy
import unittest
import pandas as pd
from scvpublic.ces_annual import extend_documents


class AnnualCESTests(unittest.TestCase):
    def setUp(self):
        self.entry = dict(source_code='raw', code='policy', scores={'1': 1, '2': -1},
                          family='ces:policy', existing_item=True,
                          question_text_2024='Policy', harmonization='same proposal')
        self.crosswalk = dict(year=2024, wave='pre-election', weight='commonweight',
                              doi='example', entries=[self.entry])
        self.base = dict(release='old', documents=[dict(code='policy', family='ces:policy',
            scores={'1': 1, '2': -1}, years={'2020': .2}, respondents={'2020': 10},
            weight_sums={'2020': 10.})])
        self.frame = pd.DataFrame(dict(caseid=[1,2,3,4,5], raw=[1.,2.,8.,9.,1.],
                                       commonweight=[3.,1.,100.,100.,float('nan')]))

    def test_weighted_extension_preserves_history_and_excludes_nonresponse(self):
        before = deepcopy(self.base)
        result = extend_documents(self.base, self.frame, self.crosswalk)
        self.assertEqual(self.base, before)
        doc = result['documents'][0]
        self.assertEqual(doc['years'], {'2020': .2, '2024': .5})
        self.assertEqual(doc['respondents']['2024'], 2)
        self.assertEqual(doc['year_provenance']['2024']['source_code'], 'raw')

    def test_rejects_duplicates_unknown_codes_and_overwrite(self):
        duplicate = self.frame.copy(); duplicate.loc[1,'caseid']=1
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            extend_documents(self.base, duplicate, self.crosswalk)
        unknown = self.frame.copy(); unknown.loc[0,'raw']=7
        with self.assertRaisesRegex(ValueError, 'Unreviewed'):
            extend_documents(self.base, unknown, self.crosswalk)
        base = extend_documents(self.base, self.frame, self.crosswalk)
        with self.assertRaisesRegex(ValueError, 'replace'):
            extend_documents(base, self.frame, self.crosswalk)

    def test_new_item_stays_separate_and_scoring_must_match(self):
        crosswalk = deepcopy(self.crosswalk)
        crosswalk['entries'][0].update(code='new', family='ces:new', existing_item=False)
        result=extend_documents(self.base,self.frame,crosswalk)
        self.assertEqual(len(result['documents']),2)
        self.assertEqual(result['documents'][0],self.base['documents'][0])
        self.crosswalk['entries'][0]['scores']={'1':-1,'2':1}
        with self.assertRaisesRegex(ValueError,'scoring'):
            extend_documents(self.base,self.frame,self.crosswalk)

    def test_other_year_requires_its_own_wording(self):
        self.crosswalk['year'] = 2022
        with self.assertRaisesRegex(ValueError, 'Missing question wording'):
            extend_documents(self.base, self.frame, self.crosswalk)
        self.entry['question_text'] = 'Reviewed 2022 wording'
        result = extend_documents(self.base, self.frame, self.crosswalk)
        self.assertEqual(result['documents'][0]['year_provenance']['2022']['question'],
                         'Reviewed 2022 wording')

    def test_odd_year_wave_is_preserved_and_even_year_post_is_rejected(self):
        self.crosswalk.update(year=2023, wave='post-election-only')
        self.entry['question_text']='Reviewed odd-year wording'
        result=extend_documents(self.base,self.frame,self.crosswalk)
        self.assertEqual(result['documents'][0]['year_provenance']['2023']['wave'],
                         'post-election-only')
        self.crosswalk['year']=2024
        with self.assertRaisesRegex(ValueError,'wave/weight'):
            extend_documents(self.base,self.frame,self.crosswalk)
