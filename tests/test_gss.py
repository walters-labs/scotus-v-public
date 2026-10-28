from collections import defaultdict
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import pandas as pd

from scvpublic.gss import aggregate_gss, attach
from scvpublic.chart import chart
from scvpublic.store import SCHEMA, search, series
from scvpublic.web import create_app


class GSSTests(unittest.TestCase):
    def setUp(self):
        self.mapping = json.loads(Path('data/gss/response_mappings.json').read_text())
        self.entries = {e['code']: e for e in self.mapping['entries']}

    def test_weights_change_by_year_without_missing_weight_fallback(self):
        frame = pd.DataFrame(dict(year=[2002, 2002, 2004, 2004, 2004, 2004, 2004],
            gunlaw=[1, 2, 1, 2, 1, float('nan'), 1],
            wtssps=[3, 1, 100, 1, 100, 100, 100],
            wtssnrps=[float('nan'), float('nan'), 1, 3, float('nan'), 10, 0]))
        totals = defaultdict(lambda: [0., 0., 0])
        aggregate_gss(frame.iloc[:3], [self.entries['gunlaw']], totals)
        aggregate_gss(frame.iloc[3:], [self.entries['gunlaw']], totals)
        self.assertEqual(totals[('gunlaw', 2002)], [2, 4, 2])
        self.assertEqual(totals[('gunlaw', 2004)], [-2, 4, 2])

    def test_orientation_and_marriage_family(self):
        self.assertEqual(self.entries['cappun']['scores'], {'1': -1, '2': 1})
        self.assertEqual(self.entries['abany']['scores'], {'1': 1, '2': -1})
        self.assertEqual(self.entries['marsame']['scores']['3'], 0)
        docs = [dict(self.entries['marsame'], years={'2004': 1}),
                dict(self.entries['marsame1'], years={'2004': -1, '2006': .5})]
        self.assertEqual(series([], docs)[1], {2004: 1, 2006: .5})

    def test_expanded_policy_directions_and_scale_midpoints(self):
        self.assertEqual(self.entries['courts']['scores'], {'1': 1, '2': -1, '3': 0})
        self.assertEqual(self.entries['prayer']['scores']['1'], 1)
        self.assertEqual(self.entries['natarms']['scores']['1'], -1)
        self.assertEqual(self.entries['natenvir']['scores']['1'], 1)
        self.assertEqual(self.entries['eqwlth']['scores']['4'], 0)
        self.assertNotIn(0, self.entries['pillok']['scores'].values())
        self.assertNotEqual(self.entries['abrape']['family'], self.entries['abany']['family'])
        for code in ('natdrug', 'natcrime', 'homosex', 'tax'):
            self.assertNotIn(code, self.entries)

    def test_attach_preserves_existing_corpora_and_serves_separate_series(self):
        with tempfile.TemporaryDirectory() as folder:
            base, output, source = [Path(folder)/n for n in ['base.sqlite', 'gss.sqlite', 'public.json']]
            with sqlite3.connect(base) as db:
                db.executescript(SCHEMA)
                db.executemany('INSERT INTO meta VALUES (?,?)', [('schema_version','1'), ('dataset','"test"')])
                db.execute('INSERT INTO documents VALUES (?,?,?)', ('public', 0, json.dumps(dict(code='A', question='gun', years={'2000': -1}))))
                db.execute('INSERT INTO postings VALUES (?,?,?,?)', ('public', 'gun', 0, .7))
            docs = [dict(e, years={'2000': 1, '2024': .5}, respondents={'2000': 10, '2024': 20})
                    for e in self.mapping['entries']]
            source.write_text(json.dumps(dict(methodology='explicit-gss-v1', documents=docs,
                release='test GSS', notes='test notes', sources={})))
            attach(base, source, output)
            with sqlite3.connect(output) as db:
                self.assertEqual(search(db, 'public', ['gun'])[0]['years'], {'2000': -1})
                self.assertEqual(search(db, 'gss', ['gun'])[0]['code'], 'gunlaw')
                self.assertTrue(search(db, 'gss', ['death penalty']))
            response = create_app(output).test_client().get('/?q1=gun&view=all')
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertIn('ANES 2000: -1.000', html)
            self.assertIn('GSS 2000: 1.000', html)
            from html.parser import HTMLParser
            class Columns(HTMLParser):
                def __init__(self):
                    super().__init__(); self.depth = 0; self.survey_depth = None; self.gss_in_survey = False
                def handle_starttag(self, tag, attrs):
                    if tag == 'section':
                        self.depth += 1
                        if ('class', 'survey-results') in attrs: self.survey_depth = self.depth
                def handle_endtag(self, tag):
                    if tag == 'section':
                        if self.depth == self.survey_depth: self.survey_depth = None
                        self.depth -= 1
                def handle_data(self, data):
                    if data == 'GSS' and self.survey_depth is not None: self.gss_in_survey = True
            layout = Columns(); layout.feed(html)
            self.assertTrue(layout.gss_in_survey)
            with self.assertRaises(FileExistsError):
                attach(base, source, output)

    def test_gss_only_plot_and_no_invented_years(self):
        svg = chart({}, {}, gss={1988: -.5, 2024: .5})
        self.assertIn('GSS linear best fit', svg)
        self.assertEqual(svg.count('<circle'), 2)


if __name__ == '__main__':
    unittest.main()
