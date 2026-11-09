from contextlib import closing
import json
import sqlite3
import unittest
from scvpublic.court_details import classified, load_details
import tempfile
from pathlib import Path
from contextlib import redirect_stdout
import io
from scvpublic.build import publish, demo_matrices
from scvpublic.web import create_app


class CourtDetailsTests(unittest.TestCase):
    def test_classification_is_not_inferred_from_score(self):
        doc = dict(cases=[dict(polarity=0)], scdb_issues=dict(records=[
            dict(decisionDirection='3', caseDisposition='7', issueArea='5'),
            dict(decisionDirection='2', caseDisposition='4', issueArea='1')]))
        detail = classified(doc)
        self.assertEqual(detail['directions'], ['Unspecifiable', 'Liberal'])
        self.assertEqual(detail['issue_areas'], ['Privacy', 'Criminal procedure'])
        self.assertEqual(len(detail['dispositions']), 2)
        self.assertEqual(classified({'cases': [{'polarity': 1}]})['directions'], [])

    def test_optional_table_and_no_mutation(self):
        doc = dict(case_id='example', cases=[dict(polarity=.5)])
        before = json.dumps(doc)
        with closing(sqlite3.connect(':memory:')) as db:
            self.assertNotIn('summary_excerpt', load_details(db, [doc])['example'])
            db.execute('CREATE TABLE court_details(case_id TEXT PRIMARY KEY, payload TEXT)')
            db.execute('INSERT INTO court_details VALUES (?,?)', ('example', json.dumps({'summary_excerpt': 'Source words'})))
            self.assertEqual(load_details(db, [doc])['example']['summary_excerpt'], 'Source words')
        self.assertEqual(json.dumps(doc), before)


class CourtDetailsWebTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name)/'search.sqlite'
        with redirect_stdout(io.StringIO()):
            publish(self.path, 'Synthetic demonstration', True, demo_matrices())
        self.client = create_app(self.path).test_client()

    def test_details_escaped_and_chart_unchanged(self):
        before = self.client.get('/?q1=marriage').data
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT id,payload FROM documents WHERE corpus='court'").fetchall()
            db.execute('CREATE TABLE court_details(case_id TEXT PRIMARY KEY, payload TEXT)')
            for id, raw in rows:
                doc = json.loads(raw); doc['case_id'] = str(id)
                db.execute("UPDATE documents SET payload=? WHERE corpus='court' AND id=?", (json.dumps(doc), id))
                db.execute('INSERT INTO court_details VALUES (?,?)', (str(id), json.dumps(dict(
                    decision_type='Signed opinion', summary_excerpt='<script>unsafe</script>',
                    summary_source='CaseSumm syllabus'))))
        after = self.client.get('/?q1=marriage').data
        self.assertIn(b'Case details &amp; source summary', after)
        self.assertIn(b'&lt;script&gt;unsafe&lt;/script&gt;', after)
        self.assertNotIn(b'<script>unsafe', after)
        self.assertEqual(before.split(b'<svg',1)[1].split(b'</svg>',1)[0],
                         after.split(b'<svg',1)[1].split(b'</svg>',1)[0])
