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

    def test_capital_exemption_polls_and_timing(self):
        import json
        from copy import deepcopy
        from scripts.compare_policy import compare
        root=Path('data/research')
        cases=json.loads((root/'capital-punishment-policy-components.json').read_text())['cases']
        rows=json.loads((root/'capital-punishment-policy-surveys.json').read_text())['survey_records']
        mapping=json.loads((root/'capital-punishment-policy-mapping.json').read_text())
        result=compare(cases,rows,mapping)
        self.assertEqual(result['cases'],json.loads((root/'capital-punishment-policy-comparison.json').read_text())['cases'])
        for index,values in [(1,[13,82,5]),(2,[26,69,5])]:
            selected=result['cases'][index]['components'][0]['comparisons'][0]['observations']
            self.assertEqual(len(selected),1)
            row=selected[0]
            self.assertEqual(row['sample_n'],1012)
            self.assertEqual([x['percent'] for x in row['response_distribution']],values)
            self.assertEqual(row['response_distribution'][0]['label'],'Favor execution')
            self.assertEqual(row['field_end'],'2002-05-09')
        # No generic GSS response may stand in for either exemption question.
        without=[r for r in rows if r['source']!='Gallup']
        reduced=compare(cases,without,mapping)
        for case in reduced['cases'][1:]:
            self.assertFalse(case['components'][0]['comparisons'][0]['observations'])
        late=deepcopy(rows)
        for row in late:
            if row['variable']=='gallup_2002_disability':
                row.update(field_start='2002-06-20',field_end='2002-06-20')
        self.assertFalse(compare(cases,late,mapping)['cases'][1]['components'][0]['comparisons'][0]['observations'])
        html=self.client.get('/policy-comparisons?topic=capital-punishment').get_data(as_text=True)
        for text in ['82%','69%','almost three years','not independent replications','Missing data']:
            self.assertIn(text,html)

    def test_fisher_targeted_polling_dates_and_categories(self):
        import json
        from copy import deepcopy
        from scripts.compare_policy import compare
        root=Path('data/research')
        cases=json.loads((root/'affirmative-action-policy-components.json').read_text())['cases']
        rows=json.loads((root/'affirmative-action-policy-surveys.json').read_text())['survey_records']
        mapping=json.loads((root/'affirmative-action-policy-mapping.json').read_text())
        result=compare(cases,rows,mapping)
        self.assertEqual(result['cases'],json.loads((root/'affirmative-action-policy-comparison.json').read_text())['cases'])
        selected=[r for s in result['cases'][1]['components'][0]['comparisons'] for r in s['observations']]
        self.assertEqual([r['sample_n'] for r in selected],[4373,3335])
        self.assertEqual([[v['percent'] for v in r['response_distribution']] for r in selected],[[67,28,5],[63,30,8]])
        # No residual-imputation or re-normalization of Pew's published rounding.
        self.assertEqual(sum(v['percent'] for v in selected[1]['response_distribution']),101)
        # Even if requested for Fisher I, fieldwork ended after that judgment.
        earlier=deepcopy(cases)
        earlier[0]['components'][0].update(policy_id='admissions_earlier',direction='unresolved',comparison_fit='contextual')
        self.assertFalse(any(s['observations'] for s in compare(earlier,rows,mapping)['cases'][0]['components'][0]['comparisons']))
        late=deepcopy(rows)
        for r in late:
            if r['variable']=='gallup_2013_Q24':
                r.update(year=2016,field_start='2016-06-07',field_end='2016-07-01')
        gallup=next(s for s in compare(cases,late,mapping)['cases'][1]['components'][0]['comparisons'] if s['source']=='Gallup')
        self.assertFalse(gallup['observations'])
        html=self.client.get('/policy-comparisons?topic=affirmative-action').get_data(as_text=True)
        for text in ['63%', '28%', '101%', 'not averaged', 'straddled']:
            self.assertIn(text,html)

    def test_all_panels_observation_integrity(self):
        from datetime import date
        from scvpublic.policy_views import STUDIES, load_study
        self.assertEqual(len(STUDIES),10)
        for topic in STUDIES:
            for case in load_study(topic)['cases']:
                ruling=date.fromisoformat(case['date'])
                for component in case['components']:
                    rows=component['observations']
                    keys=[(r['source'],r['variable'],r['year']) for r in rows]
                    self.assertEqual(len(keys),len(set(keys)))
                    if component['comparison_fit']=='not_comparable':
                        self.assertFalse(rows)
                    for row in rows:
                        self.assertGreaterEqual(row['year'],ruling.year-3)
                        if row.get('field_end'):
                            self.assertLess(date.fromisoformat(row['field_end']),ruling)
                        else:
                            self.assertLess(row['year'],ruling.year)
                        self.assertTrue(row['denominator'])
                        values=(list(row['percent'].values()) if 'percent' in row else
                                [x['percent'] for x in row['response_distribution']])
                        tolerance=0.5*len(values) if row.get('data_kind')=='published_topline' else 1e-6
                        self.assertLessEqual(abs(sum(values)-100),tolerance)

    def test_quality_review_targeted_additions(self):
        import json
        from scvpublic.policy_views import load_study
        from scripts.compare_policy import compare
        root=Path('data/research')
        for topic in ('school-religion','affirmative-action'):
            cases=json.loads((root/f'{topic}-policy-components.json').read_text())['cases']
            rows=json.loads((root/f'{topic}-policy-surveys.json').read_text())['survey_records']
            mapping=json.loads((root/f'{topic}-policy-mapping.json').read_text())
            self.assertEqual(compare(cases,rows,mapping)['cases'],
                             json.loads((root/f'{topic}-policy-comparison.json').read_text())['cases'])
        school=load_study('school-religion')
        self.assertEqual(school['cases'][0]['components'][0]['observations'][0]['year'],1999)
        selected=school['cases'][1]['components'][0]['observations']
        self.assertEqual([r['year'] for r in selected],[2001])
        self.assertEqual([x['percent'] for x in selected[0]['response_distribution']],[72,26,2])
        study=load_study('affirmative-action')
        pew=study['cases'][-1]['components'][-1]
        self.assertEqual(pew['display_fit'],'Context only')
        self.assertEqual(pew['observations'][0]['sample_n'],5079)
        self.assertEqual([x['percent'] for x in pew['observations'][0]['response_distribution']],[11,22,21,29,16,1])
        for case in study['cases'][:-1]:
            self.assertFalse(any(r['variable']=='pew_2023_COLL_RE' for p in case['components'] for r in p['observations']))

    def test_new_context_panels_reproduce_and_preserve_limits(self):
        import json
        from copy import deepcopy
        from scripts.compare_policy import compare, report
        root=Path('data/research')
        for topic in ('school-religion','campaign-finance'):
            cases=json.loads((root/f'{topic}-policy-components.json').read_text())['cases']
            rows=json.loads((root/f'{topic}-policy-surveys.json').read_text())['survey_records']
            mapping=json.loads((root/f'{topic}-policy-mapping.json').read_text())
            result=compare(cases,rows,mapping)
            self.assertEqual(result['cases'],json.loads((root/f'{topic}-policy-comparison.json').read_text())['cases'])
            for case in result['cases']:
                for part in case['components']:
                    for source in part['comparisons']:
                        for observation in source['observations']:
                            self.assertLess(observation['field_end'],case['date'])
            page=self.client.get('/policy-comparisons?topic='+topic)
            self.assertEqual(page.status_code,200)
            html=page.get_data(as_text=True)
            self.assertIn('Context only',html)
            if topic=='school-religion':
                self.assertIn('&lt;0.5%',html)
                self.assertIn('<0.5%',report(result))
                invalid=deepcopy(rows)
                invalid[0]['response_distribution'][2]['percent_upper_bound']=-1
                with self.assertRaises(ValueError):compare(cases,invalid,mapping)
            else:
                self.assertIn('Missing data',html)
                self.assertIn('Remainder not shown in chart',html)
                self.assertNotIn('sample_n',rows[0])
                self.assertEqual(sum(x['percent'] for x in rows[1]['response_distribution']),101)
                self.assertEqual(result['cases'][0]['components'][1]['comparisons'],[])

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

    def test_voter_id_scope_and_distribution(self):
        import json
        from copy import deepcopy
        from scripts.compare_policy import compare
        root=Path('data/research')
        cases=json.loads((root/'voter-id-policy-components.json').read_text())['cases']
        rows=json.loads((root/'voter-id-policy-surveys.json').read_text())['survey_records']
        mapping=json.loads((root/'voter-id-policy-mapping.json').read_text())
        result=compare(cases,rows,mapping)
        published=json.loads((root/'voter-id-policy-comparison.json').read_text())
        self.assertEqual(result['cases'],published['cases'])
        component=result['cases'][0]['components'][0]
        self.assertEqual(component['comparison_fit'],'contextual')
        self.assertEqual([r['percent'] for r in rows[0]['response_distribution']],[78,18,4])
        self.assertEqual(rows[0]['sample_n'],2006)
        late=deepcopy(rows)
        late[0].update(year=2008,field_start='2008-04-28',field_end='2008-04-29')
        self.assertEqual(compare(cases,late,mapping)['cases'][0]['components'][0]['comparisons'][0]['observations'],[])
        page=self.client.get('/policy-comparisons?topic=voter-id')
        self.assertEqual(page.status_code,200)
        for text in ['Crawford','78.0%','18.0%','4.0%','Context only','2,006 adults','6–3','not a trend','2006-10-22']:
            self.assertIn(text,page.get_data(as_text=True))

    def test_firearms_components_and_prior_polls(self):
        import json
        from scripts.compare_policy import compare
        from scvpublic.policy_views import load_study
        root=Path('data/research')
        cases=json.loads((root/'firearms-policy-components.json').read_text())['cases']
        rows=json.loads((root/'firearms-policy-surveys.json').read_text())['survey_records']
        mapping=json.loads((root/'firearms-policy-mapping.json').read_text())
        rebuilt=compare(cases,rows,mapping)
        self.assertEqual(rebuilt['cases'],json.loads((root/'firearms-policy-comparison.json').read_text())['cases'])
        heller,mcdonald=load_study('firearms')['cases']
        key=lambda c:[(r['source'],r['year']) for r in c['components'][0]['observations']]
        self.assertEqual(key(heller),[('Gallup',2007),('Pew Research Center',2008)])
        self.assertEqual(key(mcdonald),[('Gallup',2009),('Pew Research Center',2008)])
        self.assertEqual(heller['components'][1]['display_fit'],'Missing data')
        self.assertEqual(heller['components'][1]['observations'],[])
        self.assertTrue(all(c['components'][0]['display_fit']=='Context only' for c in [heller,mcdonald]))
        self.assertEqual([[a['percent'] for a in r['response_distribution']] for r in rows],[[30,68,2],[28,71,1],[36,59,5],[73,20,7]])
        individual = heller['components'][2]
        self.assertEqual(individual['display_fit'], 'Direct comparison')
        self.assertEqual(len(individual['observations']), 1)
        poll = individual['observations'][0]
        self.assertEqual(poll['variable'], 'second_amendment_individual_right')
        self.assertEqual(poll['sample_n'], 1016)
        self.assertEqual(poll['field_end'], '2008-02-10')
        self.assertLess(poll['field_end'], heller['date'])
        self.assertFalse(any(r['variable'] == poll['variable'] for c in mcdonald['components'] for r in c['observations']))
        page=self.client.get('/policy-comparisons?topic=firearms')
        self.assertEqual(page.status_code,200)
        for text in ['Heller','McDonald','68.0%','71.0%','59.0%','storage','not two independent measurements','historical sample size not stated']:
            self.assertIn(text,page.get_data(as_text=True))

    def test_contraception_preserves_distinct_issues_and_samples(self):
        import json
        from scripts.compare_policy import compare
        from scvpublic.policy_views import load_study
        root=Path('data/research')
        cases=json.loads((root/'contraception-policy-components.json').read_text())['cases']
        rows=json.loads((root/'contraception-policy-surveys.json').read_text())['survey_records']
        mapping=json.loads((root/'contraception-policy-mapping.json').read_text())
        self.assertEqual(compare(cases,rows,mapping)['cases'],json.loads((root/'contraception-policy-comparison.json').read_text())['cases'])
        study=load_study('contraception')
        parts=[c['components'][0] for c in study['cases']]
        self.assertEqual([p['display_fit'] for p in parts],['Missing data','Missing data','Context only','Not comparable'])
        self.assertEqual([len(p['observations']) for p in parts],[0,0,2,0])
        self.assertEqual([r['sample_n'] for r in rows],[1505,993])
        self.assertEqual([[a['percent'] for a in r['response_distribution']] for r in rows],[[41,53,2,4],[40,44,16]])
        self.assertTrue(all(r['field_end'] < '2014-06-30' for r in rows))
        page=self.client.get('/policy-comparisons?topic=contraception')
        self.assertEqual(page.status_code,200)
        for text in ['Griswold','Eisenstadt','Hobby Lobby','Zubik','53.0%','40.0%','n=993','not averaged','without deciding the merits']:
            self.assertIn(text,page.get_data(as_text=True))

    def test_medical_marijuana_timing_and_question_scope(self):
        import json
        from copy import deepcopy
        from scripts.compare_policy import compare
        from scvpublic.policy_views import load_study
        root=Path('data/research')
        cases=json.loads((root/'medical-marijuana-policy-components.json').read_text())['cases']
        rows=json.loads((root/'medical-marijuana-policy-surveys.json').read_text())['survey_records']
        mapping=json.loads((root/'medical-marijuana-policy-mapping.json').read_text())
        self.assertEqual(compare(cases,rows,mapping)['cases'],json.loads((root/'medical-marijuana-policy-comparison.json').read_text())['cases'])
        study=load_study('medical-marijuana')
        observations=[c['components'][0]['observations'] for c in study['cases']]
        self.assertEqual([[(r['source'],r['year']) for r in rs] for rs in observations],[[('Pew Research Center',2001)],[('Gallup',2003)]])
        self.assertEqual([[a['percent'] for a in r['response_distribution']] for r in rows],[[73,21,6],[75,22,3]])
        later=deepcopy(rows[1]);later.update(year=2005,field_start='2005-10-13',field_end='2005-10-16')
        result=compare(cases,rows+[later],mapping)
        self.assertEqual(result['cases'][1]['components'][0]['comparisons'][0]['observations'][0]['year'],2003)
        page=self.client.get('/policy-comparisons?topic=medical-marijuana')
        self.assertEqual(page.status_code,200)
        for text in ['Oakland','Raich','73.0%','75.0%','1,004','Context only','Congress','Marijuana Pain Suffering table','Survey methodology and original release']:
            self.assertIn(text,page.get_data(as_text=True))
        self.assertNotIn('page , item',page.get_data(as_text=True))

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
        for topic in ['unknown-policy','religion']:
            self.assertEqual(self.client.get('/policy-comparisons?topic='+topic).status_code,404)

    def test_new_topic_timing_and_scope(self):
        from scvpublic.policy_views import load_study
        def observations(component):
            return [(r['source'],r['year']) for r in component['observations']]
        capital=load_study('capital-punishment')['cases']
        self.assertEqual([observations(c['components'][0]) for c in capital],
                         [[('GSS',1975)],[('Gallup',2002)],[('Gallup',2002)]])
        self.assertEqual(capital[0]['components'][1]['display_fit'],'Missing data')
        self.assertEqual(capital[1]['components'][0]['display_fit'],'Direct comparison')
        self.assertEqual(capital[2]['components'][0]['display_fit'],'Context only')
        affirmative=load_study('affirmative-action')['cases']
        self.assertEqual([observations(c['components'][0]) for c in affirmative],
                         [[],[('Gallup',2013),('Pew Research Center',2014)],[('VOTER',2020)]])
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
        self.assertEqual(len(list((dest/'data/research').iterdir())),12)
        self.assertFalse((dest/'scripts/compare_policy.py').exists())
        subprocess.run([sys.executable,'-c',"from scvpublic.web import create_app; c=create_app('artifacts/search.sqlite').test_client(); assert all(c.get('/policy-comparisons?topic='+t).status_code == 200 for t in ['marriage','abortion','capital-punishment','affirmative-action','voter-id','firearms','contraception', 'medical-marijuana', 'school-religion', 'campaign-finance'])"],cwd=dest,check=True,capture_output=True)
