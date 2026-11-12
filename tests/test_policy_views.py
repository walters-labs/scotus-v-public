from contextlib import redirect_stdout
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from scvpublic.build import demo_matrices, publish
from scvpublic.web import create_app


class PolicyViewsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.artifact=Path(self.temp.name)/'search.sqlite'
        with redirect_stdout(io.StringIO()):
            publish(self.artifact,'Demo',True,demo_matrices())
        self.client=create_app(self.artifact).test_client()

    def test_studies_and_search_navigation(self):
        self.assertIn(b'Policy comparisons',self.client.get('/').data)
        marriage=self.client.get('/policy-comparisons').get_data(as_text=True)
        self.assertIn('Obergefell',marriage)
        for label in ['Direct comparison','Context only','Missing data','Not comparable']:
            self.assertIn(label,marriage)
        self.assertIn('Support/oppose respondents only',marriage)
        abortion=self.client.get('/policy-comparisons?topic=abortion').get_data(as_text=True)
        self.assertIn('54.4%',abortion)
        self.assertIn('Support = retain Roe',abortion)
        self.assertIn('Never permit',abortion)
        self.assertIn('Maintains protection',abortion)
        self.assertNotIn('SCDB decision direction',abortion)
        self.assertEqual(self.client.get('/policy-comparisons?topic=../../.env').status_code,404)

    def test_existing_survey_topics(self):
        capital=self.client.get('/policy-comparisons?topic=capital-punishment')
        self.assertEqual(capital.status_code,200)
        for text in ['Gregg', 'Atkins', 'Roper', 'GSS', '59.9%', 'Missing data', 'Context only']:
            self.assertIn(text,capital.get_data(as_text=True))
        affirmative=self.client.get('/policy-comparisons?topic=affirmative-action')
        self.assertEqual(affirmative.status_code,200)
        for text in ['Fisher', 'CES', 'VOTER', 'Context only', 'Not comparable']:
            self.assertIn(text,affirmative.get_data(as_text=True))
        self.assertNotIn('SCOTUSPoll',capital.get_data(as_text=True)+affirmative.get_data(as_text=True))
        for topic in ['firearms','religion']:
            self.assertEqual(self.client.get('/policy-comparisons?topic='+topic).status_code,404)

    def test_new_topic_timing_and_scope(self):
        from scvpublic.policy_views import load_study
        def observations(component):
            return [(r['source'],r['year']) for r in component['observations']]
        capital=load_study('capital-punishment')['cases']
        self.assertEqual([observations(c['components'][0]) for c in capital],
                         [[('GSS',1975)],[('GSS',2000)],[('GSS',2004)]])
        self.assertEqual(capital[0]['components'][1]['display_fit'],'Missing data')
        self.assertEqual(capital[1]['components'][0]['display_fit'],'Context only')
        affirmative=load_study('affirmative-action')['cases']
        self.assertEqual([observations(c['components'][0]) for c in affirmative],
                         [[],[('CES',2014)],[('VOTER',2020)]])
        self.assertEqual([c['components'][0]['display_fit'] for c in affirmative],
                         ['Not comparable','Context only','Context only'])

    def test_packaged_view_runs_without_research_code(self):
        import sys
        dest=Path(self.temp.name)/'release'
        subprocess.run([sys.executable,'-m','scripts.package_release',str(self.artifact),'--directory',str(dest)],check=True,capture_output=True)
        self.assertTrue((dest/'scvpublic/policy_views.py').exists())
        self.assertEqual(len(list((dest/'data/research').iterdir())),4)
        self.assertFalse((dest/'scripts/compare_policy.py').exists())
        subprocess.run([sys.executable,'-c',"from scvpublic.web import create_app; c=create_app('artifacts/search.sqlite').test_client(); assert c.get('/policy-comparisons?topic=abortion').status_code == 200"],cwd=dest,check=True,capture_output=True)
