"""Map reviewed weight-introduction evidence to frozen prediction inputs."""
import json
from pathlib import Path
from scvpublic.build import digest


def affected_predictions(cases, predictions, evidence):
    lookup = {c['case_id']: c for c in cases}
    if len(lookup) != len(cases):
        raise ValueError('Duplicate cohort cases')
    result = []
    for prediction in predictions:
        case = lookup[prediction['case_id']]
        if int(case['date'][:4]) != prediction['year']:
            raise ValueError('Prediction year mismatch')
        train = [c for c in cases if c['sentiment'] is not None
                 and int(c['date'][:4]) < prediction['year']]
        if len(train) != prediction['training_cases']:
            raise ValueError('Training count mismatch')
        if case['date'] >= evidence['release_lower_bound']:
            continue
        affected = []
        for c in train + [case]:
            year = c['survey_year']
            if year is None or 'GSS' not in c['sources']:
                continue
            weight = 'WTSSPS' if year < 2004 else 'WTSSNRPS'
            if year in evidence['documented_added_weights'][weight]:
                affected.append(c['case_id'])
        if affected:
            result.append(dict(prediction_case=case['case_id'], decision_date=case['date'],
                               affected_input_cases=affected))
    return result


def main():
    evidence_path = Path('data/research/gss_weight_availability.json')
    cohort_path = Path('artifacts/abortion-research-cohort.json')
    evaluation_path = Path('artifacts/abortion-retrospective-evaluation.json')
    evidence = json.loads(evidence_path.read_text())
    cohort = json.loads(cohort_path.read_text())
    evaluation = json.loads(evaluation_path.read_text())
    if digest(Path(evidence['local_source'])) != evidence['sha256']:
        raise ValueError('Reviewed release notes changed')
    if digest(cohort_path) != evaluation['cohort_sha256']:
        raise ValueError('Evaluation cohort changed')
    rows = affected_predictions(cohort['cases'], evaluation['predictions'], evidence)
    report = dict(status='documented weight-introduction audit; not a corrected evaluation',
        count=len(rows), affected_predictions_before_release_lower_bound=rows,
        sources={str(p): digest(p) for p in [evidence_path,cohort_path,evaluation_path,Path(__file__)]},
        limitations=evidence['limitations'])
    Path('artifacts/gss-weight-availability-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'predictions_with_documented_later_weight_inputs':len(rows)}))


if __name__ == '__main__':
    main()
