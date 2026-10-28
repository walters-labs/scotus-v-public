from collections import defaultdict
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import pandas as pd
from scvpublic.ces import join_weights, aggregate_ces
from scvpublic.gss import attach
from scvpublic.store import SCHEMA, series
from scvpublic.web import create_app
from scvpublic.build import digest
from scripts.rebind_hybrid import rebind


class CESTests(unittest.TestCase):
    def setUp(self):
        self.mapping = json.loads(Path('data/ces/response_mappings.json').read_text())
        self.entries = {e['code']: e for e in self.mapping['entries']}

    def test_join_and_weighted_scoring(self):
        policy = pd.DataFrame(dict(year=[2012]*5+[2014], case_id=['1','2','3','4','5','1'],
                                   guns_scale=[1,2,3,1,99,1]))
        weights = pd.DataFrame(dict(year=[2012]*4+[2014], case_id=[1.,2.,3.,5.,1.],
                                    weight=[1.,3.,2.,100.,0.]))
        frame = join_weights(policy, weights)
        totals = defaultdict(lambda: [0.,0.,0])
        aggregate_ces(frame, [self.entries['guns_scale']], totals)
        self.assertEqual(totals, {('guns_scale',2012):[-2.,6.,3]})
        with self.assertRaises(pd.errors.MergeError):
            join_weights(policy, pd.concat([weights,weights]))

    def test_policy_directions_exclusions_and_family(self):
        for code in ['gaymarriage_ban','abortion_coverage','healthcare_aca','guns_permits']:
            self.assertEqual(self.entries[code]['scores']['1'], -1)
        self.assertEqual(self.entries['gaymarriage_legalize']['scores']['1'], 1)
        docs = [dict(self.entries['gaymarriage_ban'], years={'2010':-.4}),
                dict(self.entries['gaymarriage_legalize'], years={'2012':.3})]
        self.assertEqual(series([],docs)[1], {2010:-.4,2012:.3})
        totals=defaultdict(lambda:[0.,0.,0])
        aggregate_ces(pd.DataFrame(dict(year=[2006],weight=[1],abortion_scale=[4])),
                      [self.entries['abortion_scale']],totals)
        self.assertFalse(totals)

    def test_attach_render_and_bundle_rebinding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); base=root/'base.sqlite'; output=root/'ces.sqlite'; source=root/'ces.json'
            with sqlite3.connect(base) as db:
                db.executescript(SCHEMA)
                db.executemany('INSERT INTO meta VALUES (?,?)',[('schema_version','1'),('dataset','"test"')])
                db.execute('INSERT INTO documents VALUES (?,?,?)',('court',0,'{}'))
            documents=[dict(self.entries['guns_bgchecks'],years={'2014':.5,'2016':.6})]
            source.write_text(json.dumps(dict(methodology='explicit-ces-v1',documents=documents,
                                              release='CES test',notes='test',sources={})))
            attach(base,source,output,corpus='ces')
            html=create_app(output).test_client().get('/?q1=gun&view=all').get_data(as_text=True)
            self.assertIn('CES 2014: 0.500',html)
            self.assertIn('CES linear best fit',html)
            self.assertIn('source-heading">CES',html)
            client = create_app(output).test_client()
            combined = client.get('/?q1=gun').get_data(as_text=True)
            self.assertIn('Combined 2014: 0.500; sources: CES; equal weight 1/1 each', combined)
            self.assertIn('Sources contributing to each year', combined)
            self.assertIn('value="gun"', combined)
            self.assertIn('value="combined" selected', combined)
            single = client.get('/?q1=gun&view=ces').get_data(as_text=True)
            self.assertIn('CES 2014: 0.500', single)
            self.assertNotIn('<title>Combined ', single)
            fallback = client.get('/?q1=gun&view=unknown').get_data(as_text=True)
            self.assertIn('value="combined" selected', fallback)
            bundle=root/'bundle';bundle.mkdir()
            (bundle/'manifest.json').write_text(json.dumps(dict(artifact_sha256=digest(base),files={})))
            rebind(base,output,bundle,root/'newbundle')
            self.assertEqual(json.loads((root/'newbundle/manifest.json').read_text())['artifact_sha256'],digest(output))
            with sqlite3.connect(output) as db:
                db.execute("INSERT INTO postings VALUES ('court','changed',0,1)")
            with self.assertRaisesRegex(ValueError,'Court documents or postings changed'):
                rebind(base,output,bundle,root/'badbundle')
