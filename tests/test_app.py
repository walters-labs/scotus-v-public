from contextlib import closing, redirect_stdout
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, load_npz
from scvpublic.build import case_payload, demo_matrices, public_documents, publish, write_index
from scvpublic.store import SCHEMA, connect, search, series
from scvpublic.web import create_app
from scvpublic.chart import chart
from scvpublic.ingest import bulk, legacy
from scvpublic.download import fetch


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'search.sqlite'
        with redirect_stdout(io.StringIO()):
            publish(self.path, 'Synthetic demonstration', True, demo_matrices())
        self.client = create_app(self.path).test_client()

    def test_web_and_security(self):
        response = self.client.get('/?q1=marriage')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<svg', response.data)
        self.assertIn(b'Demonstration data', response.data)
        self.assertNotIn('Set-Cookie', response.headers)
        self.assertIn("default-src 'self'", response.headers['Content-Security-Policy'])
        self.assertEqual(self.client.get('/healthz').json['status'], 'ok')
        with self.client.get('/static/style.css') as css:
            self.assertEqual(css.status_code, 200)
        self.assertEqual(self.client.get('/?q1='+'x'*101).status_code, 400)
        self.assertEqual(self.client.post('/').status_code, 405)
        self.assertIn(b'No matching opinions', self.client.get('/?q1=unknown').data)
        self.assertNotIn(b'<script>', self.client.get('/?q1=<script>').data)

    def test_read_only_and_fail_fast(self):
        with closing(connect(self.path)) as db:
            with self.assertRaises(sqlite3.OperationalError):
                db.execute('DELETE FROM meta')
        with self.assertRaises(sqlite3.OperationalError):
            create_app(Path(self.temp.name)/'absent.sqlite')

    def test_ranking_duplicates_and_ties(self):
        matrix = csr_matrix([[.5,.1],[.5,.4],[.2,.5]])
        with sqlite3.connect(':memory:') as db:
            db.executescript(SCHEMA)
            write_index(db, 'test', matrix, ['a','b'], [dict(id=i) for i in range(3)])
            self.assertEqual([d['id'] for d in search(db,'test',['a'])], [0,1,2])
            for terms in [['a','b'],['a','a','b'],['unknown'],[]]:
                expected = [(i,sum(matrix[i,['a','b'].index(t)] for t in terms if t in ['a','b'])) for i in range(3)]
                expected = sorted([p for p in expected if p[1]], key=lambda p:-p[1])
                result = search(db,'test',terms)
                self.assertEqual([d['id'] for d in result],[p[0] for p in expected])
                np.testing.assert_allclose([d['score'] for d in result],[p[1] for p in expected])

    def test_annual_case_average_and_question_means(self):
        court = [dict(cases=[dict(year=2000,polarity=.5),dict(year=2000,polarity=-.3)])]
        public = [dict(years={'2000':.5}),dict(years={'2000':-.1,'2002':.8})]
        self.assertEqual(series(court,public), ({2000:.1},{2000:.2,2002:.8}))
        self.assertIn('<circle',chart({2000:.1},{}))
        self.assertEqual(chart({},{}),'')
        self.assertNotIn('nan',chart({2000:0,2002:0},{}))

    def test_court_average_is_order_independent_and_excludes_missing(self):
        court = [dict(cases=[dict(year=2000, polarity=1)]),
                 dict(cases=[dict(year=2000, polarity=-1),
                             dict(year=2000, polarity=0),
                             dict(year=2001, polarity=.5),
                             dict(year=2002, polarity=None)])]
        expected = ({2000: 0, 2001: .5}, {})
        self.assertEqual(series(court, []), expected)
        self.assertEqual(series(list(reversed(court)), []), expected)
        self.assertEqual(series([], []), ({}, {}))

    def test_survey_legacy_scaling_and_unlabeled(self):
        book = pd.DataFrame({'vcf_code':['Q','U'],'question':['A question','Unlabeled']})
        responses = pd.DataFrame({'VCF0004':[2000,2000,2002,2002],
            'Q':pd.Categorical(['No','Yes','Missing',None],categories=['Missing','No','Yes']),
            'U':pd.Categorical(['Yes']*4)})
        labels = pd.DataFrame({'vcf_code':['Q'],'ques_class':[-1]})
        result = list(public_documents(book,responses,labels))
        self.assertEqual(result[0]['years'],{'2000':-.5,'2002':1.0})
        self.assertEqual(result[1]['years'],{})

    def test_case_force(self):
        row = dict(dateDecision='06/01/2000',caseName='Example',majVotes='6',minVotes='3',decisionDirection='2')
        self.assertAlmostEqual(case_payload(row)['polarity'],1/3)
        row['decisionDirection']='1'
        self.assertAlmostEqual(case_payload(row)['polarity'],-1/3)
        row['majVotes']=row['minVotes']='0'
        self.assertIsNone(case_payload(row)['polarity'])

    def test_tracked_public_index_parity(self):
        root = Path(__file__).resolve().parents[1]/'data/tf-idf/public_opinion'
        matrix = load_npz(root/'tfidf_matrix.npz')
        vocab = pd.read_csv(root/'tfidf_cols.csv')['0'].tolist()
        docs = [dict(id=i) for i in range(matrix.shape[0])]
        with sqlite3.connect(':memory:') as db:
            db.executescript(SCHEMA)
            write_index(db,'public',matrix,vocab,docs)
            for terms in [['marriage'],['civil rights','black'],['government','government','health']]:
                # Multiword input now includes its words plus adjacent survey bigrams.
                expanded = []
                for term in terms:
                    words = term.split()
                    expanded.extend(words)
                    expanded.extend(' '.join(pair) for pair in zip(words, words[1:]))
                cols = [vocab.index(t) for t in expanded if t in vocab]
                scores = np.asarray(matrix[:,cols].sum(axis=1)).ravel()
                expected = sorted(np.flatnonzero(scores), key=lambda i:-scores[i])[:10]
                result = search(db,'public',terms)
                self.assertEqual([r['id'] for r in result],list(expected))
                np.testing.assert_allclose([r['score'] for r in result],scores[expected])

    def test_download_path_validation(self):
        with self.assertRaises(ValueError):
            fetch(dict(url='https://example.com/file',sha256='0'*64,path='../escape'), Path(self.temp.name))

    def test_legacy_import_missing_fields(self):
        path = Path(self.temp.name)/'one.json'
        path.write_text(json.dumps({'absolute_url':'/opinion/1/example/','plain_text':'123 U.S. 456\ntext'}))
        result = list(legacy(Path(self.temp.name)))
        self.assertEqual(result[0]['citation'],'123 U.S. 456')
        self.assertEqual(result[0]['case_name'],'example')

    def test_bulk_filters_other_courts(self):
        import csv
        def table(name, rows):
            path=Path(self.temp.name)/name
            with path.open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=rows[0].keys(), escapechar='\\', doublequote=False)
                writer.writeheader(); writer.writerows(rows)
            return path
        d=table('d.csv',[dict(id='1',court_id='scotus'),dict(id='2',court_id='ca9')])
        c=table('c.csv',[dict(id='10',docket_id='1',case_name='Example'),dict(id='20',docket_id='2',case_name='Other')])
        cites=table('ci.csv',[dict(cluster_id='10',reporter='U.S.',volume='123',page='456')])
        text = 'Example "quoted" opinion, with\nnewlines and \\ backslash'
        o=table('o.csv',[dict(cluster_id='10',plain_text=text),dict(cluster_id='20',plain_text='Other')])
        self.assertEqual(list(bulk(d,c,cites,o)),[dict(citation='123 U.S. 456',case_name='Example',opinion=text)])


if __name__ == '__main__':
    unittest.main()
