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
        for topic, value, name in [('firearms','52.6%','Bruen'),('religion','44.3%','Shurtleff')]:
            page=self.client.get('/policy-comparisons?topic='+topic)
            self.assertEqual(page.status_code,200)
            html=page.get_data(as_text=True)
            for text in [value,name,'2022-04-06','Survey methods','Published survey results','SCOTUSPoll']:
                self.assertIn(text,html)
        self.assertEqual(self.client.get('/policy-comparisons?topic=../../.env').status_code,404)

    def test_packaged_view_runs_without_research_code(self):
        import sys
        dest=Path(self.temp.name)/'release'
        subprocess.run([sys.executable,'-m','scripts.package_release',str(self.artifact),'--directory',str(dest)],check=True,capture_output=True)
        self.assertTrue((dest/'scvpublic/policy_views.py').exists())
        self.assertEqual(len(list((dest/'data/research').iterdir())),4)
        self.assertFalse((dest/'scripts/compare_policy.py').exists())
        subprocess.run([sys.executable,'-c',"from scvpublic.web import create_app; c=create_app('artifacts/search.sqlite').test_client(); assert c.get('/policy-comparisons?topic=abortion').status_code == 200"],cwd=dest,check=True,capture_output=True)
