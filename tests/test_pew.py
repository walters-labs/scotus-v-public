from collections import defaultdict
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import pandas as pd
from scvpublic.public import aggregate
from scvpublic.pew import check_toplines
from scvpublic.gss import attach
from scvpublic.store import SCHEMA
from scvpublic.chart import chart
from scvpublic.web import create_app


class PewTests(unittest.TestCase):
    def setUp(self):
        self.mapping=json.loads(Path('data/pew/response_mappings.json').read_text())
        self.entries={e['code']:e for e in self.mapping['entries']}

    def test_weights_missing_and_orientation(self):
        e=self.entries['GUNSTRICT_W25']
        frame=pd.DataFrame({'VCF0004':[2017]*6,'GUNSTRICT_W25':[1,3,2,99,1,1],
                            'WEIGHT_W25':[3,1,2,100,float('nan'),0]})
        totals=defaultdict(lambda:[0.,0.,0]);aggregate(frame,[e],totals)
        self.assertEqual(totals[('GUNSTRICT_W25',2017)],[2.,6.,3])
        self.assertEqual(self.entries['GUNPRIORITY1F_W25']['scores']['1'],1)
        self.assertEqual(self.entries['GUNPRIORITY2H_W25']['scores']['1'],-1)
        self.assertNotIn('99',e['scores'])

    def test_topline_denominator_includes_refusals_and_rejects_wrong_weights(self):
        e=dict(self.entries['GUNSTRICT_W25'],published_percentages={'1':50,'3':25,'99':25})
        frame=pd.DataFrame({'GUNSTRICT_W25':[1,3,99],'WEIGHT_W25':[2.,1.,1.]})
        self.assertEqual(check_toplines(frame,[e])[e['code']]['1'],50)
        frame['WEIGHT_W25']=[1.,1.,1.]
        with self.assertRaisesRegex(ValueError,'topline mismatch'):check_toplines(frame,[e])

    def test_attached_pew_view_combination_and_one_year(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);base=root/'base.sqlite';dest=root/'pew.sqlite';source=root/'pew.json'
            with sqlite3.connect(base) as db:
                db.executescript(SCHEMA)
                db.executemany('INSERT INTO meta VALUES (?,?)',[('schema_version','1'),('dataset','"test"')])
            e=self.entries['GUNSTRICT_W25']
            source.write_text(json.dumps(dict(methodology='explicit-pew-v1',release='Pew test',notes='2017 only',sources={},documents=[dict(e,years={'2017':.25})])))
            attach(base,source,dest,corpus='pew')
            client=create_app(dest).test_client()
            html=client.get('/?q1=gun&view=pew').get_data(as_text=True)
            self.assertIn('Pew 2017: 0.250',html)
            self.assertIn('source-heading">Pew',html)
            self.assertNotIn('Pew linear best fit',html)
            html=client.get('/?q1=gun').get_data(as_text=True)
            self.assertIn('sources: Pew; equal weight 1/1 each',html)
            svg=chart({}, {2017:-.25},pew={2017:.75},view='combined')
            self.assertIn('Combined 2017: 0.250',svg)
