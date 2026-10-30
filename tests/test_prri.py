import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import pandas as pd
from scvpublic.prri import summarize
from scvpublic.gss import attach
from scvpublic.store import SCHEMA
from scvpublic.web import create_app
from scvpublic.chart import chart


class PRRITests(unittest.TestCase):
    def setUp(self):
        self.wave = dict(source_code='Q', weight='W', year=2024, expected_label='Question',
                         expected_labels={'1':'Yes','2':'No','99':'Skipped'},
                         published_percentages={'1':50,'2':25})
        self.labels = {'Q':'Question'}
        self.frame = pd.DataFrame({'Q':[1,2,99,1,2,1,1], 'W':[2,1,1,0,-1,float('nan'),float('inf')]})

    def run_summary(self, wave=None, frame=None, values=None):
        return summarize(self.frame if frame is None else frame, wave or self.wave, {'1':1,'2':-1}, self.labels, values or self.wave['expected_labels'])

    def test_weighting_missing_and_topline_denominators(self):
        mean,n,weight,percent = self.run_summary()
        self.assertAlmostEqual(mean,1/3)
        self.assertEqual((n,weight),(2,3))
        self.assertEqual(percent,{'1':50,'2':25})

    def test_unknown_codes_labels_and_toplines_fail(self):
        frame=self.frame.copy();frame.loc[0,'Q']=7
        with self.assertRaisesRegex(ValueError,'Unexpected'):
            self.run_summary(frame=frame)
        with self.assertRaisesRegex(ValueError,'labels changed'):
            self.run_summary(values={'1':'No','2':'Yes','99':'Skipped'})
        wave=copy.deepcopy(self.wave);wave['published_percentages']['1']=60
        with self.assertRaisesRegex(ValueError,'topline mismatch'):
            self.run_summary(wave=wave)

    def test_source_view_and_combined(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);base=root/'base.sqlite';dest=root/'prri.sqlite';source=root/'public.json'
            with sqlite3.connect(base) as db:
                db.executescript(SCHEMA)
                db.executemany('INSERT INTO meta VALUES (?,?)',[('schema_version','1'),('dataset','"test"')])
            source.write_text(json.dumps(dict(methodology='explicit-prri-v1',release='PRRI test',notes='Original survey weights',sources={},documents=[dict(code='marriage',family='marriage',title='Marriage',question='Same-sex marriage',years={'2023':.2,'2024':.3},question_note='Reviewed scale',source_url='https://example.org')])) )
            attach(base,source,dest,corpus='prri')
            client=create_app(dest).test_client()
            html=client.get('/?q1=marriage&view=prri').get_data(as_text=True)
            self.assertIn('PRRI 2024: 0.300',html)
            self.assertIn('Reviewed scale',html)
            self.assertIn('value="prri"',html)
            combined=client.get('/?q1=marriage').get_data(as_text=True)
            self.assertIn('sources: PRRI; equal weight 1/1 each',combined)
            self.assertIn('Combined 2024: 0.000',chart({}, {2024:-.3},prri={2024:.3},view='combined'))
