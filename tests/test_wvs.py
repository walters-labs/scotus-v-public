from collections import defaultdict
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import pandas as pd
from scvpublic.wvs import aggregate_wvs, check_labels
from scvpublic.gss import attach
from scvpublic.store import SCHEMA
from scvpublic.web import create_app
from scvpublic.chart import chart


class WVSTests(unittest.TestCase):
    def setUp(self):
        self.entries = {e['code']:e for e in json.loads(Path('data/wvs/response_mappings.json').read_text())['entries']}

    def test_country_missing_weights_and_reversed_scale(self):
        frame = pd.DataFrame(dict(S003=[840,840,840,840,840,840,124], S020=[2017]*7,
            S017=[3,1,100,0,float('nan'),float('inf'),1000], F144_02=[1,10,-1,1,1,1,10]))
        totals = defaultdict(lambda:[0.,0.,0])
        aggregate_wvs(frame,[self.entries['F144_02']],totals)
        self.assertEqual(totals[('F144_02',2017)],[2.,4.,2])
        self.assertEqual(self.entries['F120']['scores']['10'],1)
        self.assertEqual(self.entries['E037']['scores']['10'],1)
        self.assertEqual(self.entries['E035']['scores']['10'],-1)
        self.assertNotIn('3',self.entries['B008']['scores'])
        self.assertEqual(self.entries['E129C']['scores']['0'],-1)

    def test_label_drift_rejected(self):
        e=self.entries['F120']
        labels={e['code']:e['expected_label']}
        values={e['code']:copy.deepcopy(e['expected_labels'])}
        check_labels(labels,values,[e])
        values[e['code']]['10']='Never justifiable'
        with self.assertRaisesRegex(ValueError,'labels changed'):
            check_labels(labels,values,[e])

    def test_wvs_search_view_combination_and_disclosure(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);base=root/'base.sqlite';dest=root/'wvs.sqlite';source=root/'public.json'
            with sqlite3.connect(base) as db:
                db.executescript(SCHEMA)
                db.executemany('INSERT INTO meta VALUES (?,?)',[('schema_version','1'),('dataset','"test"')])
            entry=dict(self.entries['F120'],years={'1995':-.4,'2017':.2})
            source.write_text(json.dumps(dict(methodology='explicit-wvs-v1',release='WVS test',notes='U.S. only',sources={},documents=[entry])))
            attach(base,source,dest,corpus='wvs')
            client=create_app(dest).test_client()
            html=client.get('/?q1=abortion&view=wvs').get_data(as_text=True)
            self.assertIn('WVS 2017: 0.200',html)
            self.assertIn('Moral acceptability, not support for a particular law.',html)
            self.assertIn('WVS linear best fit',html)
            combined=client.get('/?q1=abortion').get_data(as_text=True)
            self.assertIn('sources: WVS; equal weight 1/1 each',combined)
            self.assertIn('Combined 2017: 0.000',chart({}, {2017:-.2},wvs={2017:.2},view='combined'))
