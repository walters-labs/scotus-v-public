"""Describe composition changes in searches against the annual CES candidate."""
import argparse
from contextlib import closing
import json
from pathlib import Path

from audit_question_composition import audit, selected_items
from scvpublic.build import digest
from scvpublic.chart import chart
from scvpublic.store import connect, series, survey_search


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    results = {}
    with closing(connect(args.artifact)) as db:
        for query in ['abortion', 'gun control', 'immigration', 'environment', 'Medicaid']:
            questions = survey_search(db, 'ces', [query])
            selected = selected_items(questions)
            values = series([], questions)[1]
            assert 2024 in values, query
            result = audit(selected)
            transitions = [t for t in result['transitions'] if t['after'] == 2024]
            svg = chart({}, {}, ces=values, view='ces',
                        question_ids={'CES': {y: list(items) for y, items in selected.items()}})
            if transitions and (transitions[0]['added'] or transitions[0]['removed']):
                assert 'CES questions changed since previous observation' in svg
            results[query] = dict(selected=selected, series=values,
                transition_to_2024=transitions[0] if transitions else None,
                chart_composition_annotation_checked=True)
    paths = [args.artifact, Path(__file__), Path('scripts/audit_question_composition.py'),
             Path('scvpublic/store.py'), Path('scvpublic/chart.py')]
    report = dict(status='descriptive candidate audit', results=results,
        sources={str(path): digest(path) for path in paths},
        limitations=['Search-selected items are not a prespecified research cohort.',
            'Common-item changes are descriptive, not significance tests or causal effects.',
            'Identical item codes do not prove invariant wording or respondent composition.',
            'A single observed year cannot establish a trend.'])
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    for query, result in results.items():
        print(query, json.dumps(result['transition_to_2024']))


if __name__ == '__main__':
    main()
