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

    def test_four_point_scale_excludes_missing_from_score_only(self):
        entry = next(e for e in json.loads(Path('data/prri/response_mappings.json').read_text())['entries'] if e['code']=='prri_abortion')
        wave=copy.deepcopy(entry['waves'][-1])
        c,w=wave['source_code'],wave['weight']
        # A hand-calculable distribution with both skipped and system-missing answers.
        frame=pd.DataFrame({c:[1,2,3,4,-1,float('nan')],w:[30,20,10,20,10,10]})
        wave['published_percentages']={'1':30,'2':20,'3':10,'4':20}
        mean,n,total,_=summarize(frame,wave,entry['scores'],{c:wave['expected_label']},wave['expected_labels'])
        self.assertAlmostEqual(mean,1/6)
        self.assertEqual((n,total),(4,80))

    def test_abortion_defers_unreproduced_year(self):
        spec=json.loads(Path('data/prri/response_mappings.json').read_text())
        entry=next(e for e in spec['entries'] if e['code']=='prri_abortion')
        self.assertNotIn(2022,[w['year'] for w in entry['waves']])
        self.assertTrue(any(d['year']==2022 and d['code']==entry['code'] for d in spec['deferred']))
        wave=copy.deepcopy(self.wave)
        wave['published_percentages']={'1':29,'2':71}
        frame=pd.DataFrame({'Q':[1,2],'W':[28.427,71.573]})
        with self.assertRaisesRegex(ValueError,'topline mismatch'):
            self.run_summary(wave=wave,frame=frame)
