"""Retrospective chronological diagnostic, not a real-time forecasting claim."""
import json
from pathlib import Path
from math import log
from scvpublic.build import digest


def paired_brier_interval(predictions, repetitions=10000, seed=20261029):
    """Resample decision years jointly for both models, holding forecasts fixed.

    This describes uncertainty in the evaluated sample, not uncertainty from
    survey design or model estimation. It assumes exchangeable year clusters;
    serial dependence between years is not captured.
    """
    import numpy as np
    years=sorted({p['year'] for p in predictions})
    if len(years)<2:
        return dict(status='insufficient decision-year clusters')
    totals=[];counts=[]
    for year in years:
        rows=[p for p in predictions if p['year']==year]
        totals.append(sum((p['sentiment_model']-p['actual'])**2-
                          (p['baseline']-p['actual'])**2 for p in rows))
        counts.append(len(rows))
    totals=np.asarray(totals);counts=np.asarray(counts)
    draws=np.random.default_rng(seed).integers(0,len(years),size=(repetitions,len(years)))
    differences=totals[draws].sum(axis=1)/counts[draws].sum(axis=1)
    return dict(status='exploratory conditional interval',
        metric='sentiment Brier minus baseline Brier; negative favors sentiment',
        estimate=float(totals.sum()/counts.sum()),
        percentile_95=[float(x) for x in np.quantile(differences,[.025,.975])],
        clusters=len(years),repetitions=repetitions,seed=seed,
        limitations='Fixed predictions; no refitting. Assumes exchangeable decision-year clusters. Does not capture serial dependence, survey sampling error, source composition uncertainty, or model-selection uncertainty.')


def evaluate(cases, minimum=20):
    from sklearn.linear_model import LogisticRegression
    eligible=[c for c in cases if c['sentiment'] is not None]
    predictions=[]
    for year in sorted({int(c['date'][:4]) for c in eligible}):
        train=[c for c in eligible if int(c['date'][:4])<year]
        test=[c for c in eligible if int(c['date'][:4])==year]
        if len(train)<minimum or len({c['liberal'] for c in train})<2:continue
        baseline=(sum(c['liberal'] for c in train)+1)/(len(train)+2)
        model=LogisticRegression(C=1,solver='lbfgs',max_iter=1000)
        model.fit([[c['sentiment']] for c in train],[c['liberal'] for c in train])
        probs=model.predict_proba([[c['sentiment']] for c in test])[:,1]
        for c,p in zip(test,probs):
            predictions.append(dict(case_id=c['case_id'],year=year,actual=c['liberal'],
                survey_year=c['survey_year'],training_cases=len(train),
                latest_training_year=max(int(t['date'][:4]) for t in train),
                baseline=baseline,sentiment_model=float(p)))
    metrics={}
    for name in ('baseline','sentiment_model'):
        if not predictions:continue
        n=len(predictions)
        metrics[name]=dict(brier=sum((r[name]-r['actual'])**2 for r in predictions)/n,
            log_loss=-sum(r['actual']*log(max(r[name],1e-15))+(1-r['actual'])*log(max(1-r[name],1e-15)) for r in predictions)/n,
            accuracy=sum((r[name]>=.5)==bool(r['actual']) for r in predictions)/n)
    return dict(evaluated_cases=len(predictions),evaluated_years=len({r['year'] for r in predictions}),
                metrics=metrics,predictions=predictions)


def compare_on_common_cases(cases, alternative_index, minimum=20):
    """Keep identical case/training coverage when changing the sentiment series."""
    from scripts.describe_alignment import with_index
    alternative = with_index(cases, alternative_index)
    common_ids = {a['case_id'] for a, original in zip(alternative, cases)
                  if a['sentiment'] is not None and original['sentiment'] is not None}
    original_result = evaluate([c for c in cases if c['case_id'] in common_ids], minimum)
    alternative_result = evaluate([c for c in alternative if c['case_id'] in common_ids], minimum)
    original_predictions = original_result['predictions']
    alternative_predictions = alternative_result['predictions']
    if [(r['case_id'], r['training_cases'], r['baseline']) for r in original_predictions] != [
            (r['case_id'], r['training_cases'], r['baseline']) for r in alternative_predictions]:
        raise ValueError('Sensitivity does not use identical case and baseline coverage')
    return dict(common_eligible_cases=len(common_ids),
                original_index=original_result, fixed_item_index=alternative_result,
                fixed_item_brier_uncertainty=paired_brier_interval(alternative_predictions))


def stable_gss_sensitivity(cohort):
    from contextlib import closing
    from scvpublic.store import connect, survey_items
    artifact = Path('artifacts/wvs-pilot.sqlite')
    if digest(artifact) != cohort['hashes'][str(artifact)]:
        raise ValueError('Sensitivity artifact differs from cohort')
    codes = set(cohort['protocol']['survey_codes']['GSS'])
    with closing(connect(artifact)) as db:
        questions = [json.loads(payload) for payload, in db.execute(
            "SELECT payload FROM documents WHERE corpus='gss'")]
    questions = [q for q in questions if q['code'] in codes]
    if {q['code'] for q in questions} != codes:
        raise ValueError('Missing GSS protocol items')
    index = {year: sum(value for _, value in items)/len(items)
             for year, items in survey_items(questions).items()
             if {code for code, _ in items} == codes}
    result = compare_on_common_cases(cohort['cases'], index,
        cohort['protocol']['retrospective_evaluation']['minimum_training_cases'])
    result.update(status='exploratory sensitivity specified after inspecting composition; not independent validation',
        selection_rule='Use all seven protocol GSS items only in years where all are observed; no interpolation.',
        codes=sorted(codes),survey_years=sorted(index),
        limitations=['Same case/training coverage and baseline, but survey years may differ between predictors.',
                     'Stable codes do not establish stable wording, mode, or population.',
                     'Does not model survey sampling error or historical dataset availability.',
                     'The primary cohort and its original result are retained.'])
    return result


if __name__=='__main__':
    path=Path('artifacts/abortion-research-cohort.json')
    cohort=json.loads(path.read_text())
    settings=cohort['protocol']['retrospective_evaluation']
    result=evaluate(cohort['cases'],settings['minimum_training_cases'])
    result['paired_brier_uncertainty']=paired_brier_interval(result['predictions'])
    result['stable_gss_sensitivity']=stable_gss_sensitivity(cohort)
    result.update(cohort_sha256=digest(path),settings=settings,
        evaluator_sha256=digest(Path(__file__)),
        helper_hashes={str(p):digest(p) for p in [Path('scripts/describe_alignment.py'),
                                               Path('scvpublic/store.py')]},
        limitations=['Small exploratory sample; no untouched external validation set.',
                     'Historical dataset publication dates and revisions are not verified.',
                     'Outcome is SCDB ideology, not adjudicated abortion-access direction.',
                     'Survey sampling error and source-composition changes are not modeled.',
                     'No causal interpretation or statistical significance claim.'])
    Path('artifacts/abortion-retrospective-evaluation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k in ('evaluated_cases','evaluated_years','metrics')},indent=2))
