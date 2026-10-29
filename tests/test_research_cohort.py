import unittest
from scripts.build_research_cohort import assemble_cases


class ResearchCohortTests(unittest.TestCase):
    def test_sensitivity_uses_same_case_training_coverage(self):
        from scripts.evaluate_research_cohort import compare_on_common_cases
        cases = [dict(case_id=str(year), date=f'{year}-06-01', liberal=year % 2,
                      sentiment=.1, survey_year=year-1, lag_years=1)
                 for year in range(2000, 2008)]
        result = compare_on_common_cases(cases, {2001: .2, 2004: -.1, 2007: .8}, minimum=2)
        self.assertEqual(result['common_eligible_cases'], 6)
        old = result['original_index']['predictions']
        new = result['fixed_item_index']['predictions']
        self.assertEqual(len(new), 4)
        for a, b in zip(old, new):
            self.assertEqual(a['case_id'], b['case_id'])
            self.assertEqual(a['training_cases'], b['training_cases'])
            self.assertEqual(a['baseline'], b['baseline'])
            self.assertLess(b['survey_year'], b['year'])
            self.assertLess(b['latest_training_year'], b['year'])

    def test_alignment_excludes_missing_and_neutral_indices(self):
        from scripts.describe_alignment import describe
        rows=[dict(sentiment=s,liberal=y,survey_year=2000,lag_years=1)
              for s,y in [(1,1),(-1,0),(1,0),(-1,1),(0,1),(None,0)]]
        result=describe(rows)
        self.assertEqual(result['sign_agreement'],.5)
        self.assertEqual(result['directional_cases'],4)
        self.assertEqual(result['missing_prior_index'],1)
        self.assertEqual(result['distinct_survey_years'],1)
        self.assertIsNone(describe([])['sign_agreement'])

    def test_paired_interval_direction_and_identical_models(self):
        from scripts.evaluate_research_cohort import paired_brier_interval
        rows=[dict(year=2000+i//2,actual=i%2,baseline=.5,sentiment_model=i%2)
              for i in range(8)]
        result=paired_brier_interval(rows,repetitions=100)
        self.assertEqual(result['estimate'],-.25)
        self.assertEqual(result['percentile_95'],[-.25,-.25])
        identical=[dict(r,sentiment_model=r['baseline']) for r in rows]
        self.assertEqual(paired_brier_interval(identical,repetitions=100)['percentile_95'],[0.,0.])
        self.assertEqual(paired_brier_interval(rows[:1])['status'],'insufficient decision-year clusters')

    def row(self, date='6/1/2000', direction='2'):
        return dict(dateDecision=date,decisionDirection=direction,caseName='Example')

    def test_no_same_year_or_future_sentiment_and_five_year_limit(self):
        protocol={'court_direction':{'1':0,'2':1}}
        series={1994:-.9,1995:-.2,1999:.3,2000:.8,2001:1}
        names={y:['ANES'] for y in series}
        cases,_=assemble_cases({'a':[self.row()]},protocol,series,names)
        self.assertEqual(cases[0]['survey_year'],1999)
        self.assertEqual(cases[0]['sentiment'],.3)
        cases,_=assemble_cases({'a':[self.row()]},protocol,{1995:-.2},names)
        self.assertEqual(cases[0]['lag_years'],5)
        cases,_=assemble_cases({'a':[self.row()]},protocol,{1994:-.9,2000:.8},names)
        self.assertIsNone(cases[0]['sentiment'])
        self.assertEqual(cases[0]['sources'],[])

    def test_duplicates_unknown_and_invalid_dates(self):
        groups={'ok':[self.row(),self.row()],
                'conflict':[self.row(),self.row(direction='1')],
                'unknown':[self.row(direction='3')],
                'missing':[self.row(date='')],
                'invalid':[self.row(date='2/30/2000')]}
        cases,excluded=assemble_cases(groups,{'court_direction':{'1':0,'2':1}}, {}, {})
        self.assertEqual(len(cases),1)
        self.assertEqual(cases[0]['liberal'],1)
        self.assertEqual({e['case_id'] for e in excluded},{'conflict','unknown','missing','invalid'})

    def test_evaluation_never_trains_on_current_or_future_year(self):
        from scripts.evaluate_research_cohort import evaluate
        cases=[dict(case_id=str(i),date=f'{2000+i//2}-06-01',liberal=i%2,
                    sentiment=(-1)**i*.4,survey_year=1999+i//2) for i in range(12)]
        result=evaluate(cases,minimum=4)
        self.assertEqual(result['evaluated_cases'],8)
        for r in result['predictions']:
            self.assertLess(r['latest_training_year'],r['year'])
            self.assertLess(r['survey_year'],r['year'])
        altered=[dict(c,liberal=1-c['liberal']) if c['date'].startswith('2005') else c for c in cases]
        changed=evaluate(altered,minimum=4)
        self.assertEqual([r['sentiment_model'] for r in result['predictions']],
                         [r['sentiment_model'] for r in changed['predictions']])
