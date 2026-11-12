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

    def test_marriage_history_preserves_audited_observations(self):
        import json
        from scvpublic.policy_views import load_study
        study=load_study('marriage')
        records=[r for series in study['history'] for r in series['observations']]
        original=json.loads(Path('data/research/marriage-case-study.json').read_text())['survey_records']
        key=lambda r:(r['source'],r['year'],r['variable'])
        self.assertEqual(sorted(records,key=key),sorted(original,key=key))
        self.assertEqual(len(records),28)
        self.assertEqual((min(r['year'] for r in records),max(r['year'] for r in records)),(1988,2024))
        self.assertIn('history',load_study('abortion'))
        for case in study['cases']:
            for component in case['components']:
                for observation in component['observations']:
                    if observation.get('field_end'):
                        self.assertLess(observation['field_end'],case['date'])
                    else:
                        self.assertLess(observation['year'],int(case['date'][:4]))
        page=self.client.get('/policy-comparisons').get_data(as_text=True)
        self.assertIn('Public opinion over time',page)
        self.assertNotIn('style="width:',page)

    def test_abortion_overview_preserves_response_scales(self):
        import json
        from scvpublic.policy_views import load_study
        study=load_study('abortion')
        rows=[r for series in study['history'] for r in series['observations']]+[study['roe_observation']]
        original=json.loads(Path('data/research/abortion-policy-surveys.json').read_text())['survey_records']
        key=lambda r:(r['source'],r['variable'],r['year'])
        self.assertEqual(sorted(rows,key=key),sorted(original,key=key))
        self.assertEqual(len(rows),56)
        self.assertEqual(len([r for r in rows if r['source']=='ANES' and r['year']==1980]),2)
        page=self.client.get('/policy-comparisons?topic=abortion').get_data(as_text=True)
        for text in ['Retain Roe','Overturn Roe','19-month','Never permit','Spousal notification','Where the evidence is still thin','492 adults','Times Mirror']:
            self.assertIn(text,page)

    def test_packaged_view_runs_without_research_code(self):
        import sys
        dest=Path(self.temp.name)/'release'
        subprocess.run([sys.executable,'-m','scripts.package_release',str(self.artifact),'--directory',str(dest)],check=True,capture_output=True)
        self.assertTrue((dest/'scvpublic/policy_views.py').exists())
        self.assertEqual(len(list((dest/'data/research').iterdir())),6)
        self.assertFalse((dest/'scripts/compare_policy.py').exists())
        subprocess.run([sys.executable,'-c',"from scvpublic.web import create_app; c=create_app('artifacts/search.sqlite').test_client(); assert all(c.get('/policy-comparisons?topic='+t).status_code == 200 for t in ['marriage','abortion','capital-punishment','affirmative-action'])"],cwd=dest,check=True,capture_output=True)
