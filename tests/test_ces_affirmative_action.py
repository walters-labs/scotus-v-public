import json
from pathlib import Path
import unittest
import pandas as pd
from scripts.build_ces_climate import score_item


class AffirmativeActionTests(unittest.TestCase):
    def test_wording_variants_share_family_without_overlapping_years(self):
        entries=json.loads(Path('data/ces/affirmative-action-mappings.json').read_text())['entries']
        self.assertEqual(len({e['family'] for e in entries}),1)
        years=[y for e in entries for y in e['years']]
        self.assertEqual(sorted(years),[2008,2009,2010,2012,2013,2014])
        self.assertIn('women',entries[0]['question'])
        self.assertNotIn('women',entries[-1]['question'])
        for e in entries:
            self.assertEqual(e['scores'],{'1':1,'2':1/3,'3':-1/3,'4':-1})

    def test_weighted_four_point_scale_and_provenance(self):
        e=json.loads(Path('data/ces/affirmative-action-mappings.json').read_text())['entries'][0]
        e['published_counts']={'2008':{'1':1,'2':1,'3':1,'4':1}}
        frame=pd.DataFrame(dict(year=[2008]*5,affirmativeaction=[1,2,3,4,None],weight=[4,3,2,1,100]))
        doc,_=score_item(frame,e)
        self.assertAlmostEqual(doc['years']['2008'],1/3)
        self.assertEqual(doc['respondents']['2008'],4)
        self.assertEqual(doc['year_provenance']['2008']['question'],e['question'])
        self.assertEqual(doc['year_provenance']['2008']['source_code'],'cc313')
