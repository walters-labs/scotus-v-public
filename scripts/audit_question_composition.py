"""Audit changes in item/source composition without interpolating survey years."""
import json
from contextlib import closing
from math import fsum
from pathlib import Path

from scvpublic.build import digest
from scvpublic.store import connect, series, survey_items


def mean(values):
    return fsum(values) / len(values)


def selected_items(questions):
    """Use exactly the serving aggregation's selected question identities."""
    return {year: dict(items) for year, items in survey_items(questions).items()}


def audit(years):
    """Adjacent observed-year differences; common-item contrast is descriptive."""
    years = dict(sorted(years.items()))
    transitions = []
    for before, after in zip(years, list(years)[1:]):
        old, new = years[before], years[after]
        common = sorted(old.keys() & new.keys())
        change = mean(list(new.values())) - mean(list(old.values()))
        common_change = mean([new[k] - old[k] for k in common]) if common else None
        transitions.append(dict(before=before, after=after, gap=after-before,
            added=sorted(new.keys()-old.keys()), removed=sorted(old.keys()-new.keys()),
            common=common, observed_change=change, common_item_change=common_change,
            composition_contrast=change-common_change if common else None))
    signatures = {}
    for year, items in years.items():
        signatures.setdefault(tuple(sorted(items)), []).append(year)
    fixed = [dict(items=list(items), years=observed,
                  series={y: mean(list(years[y].values())) for y in observed})
             for items, observed in signatures.items()]
    return dict(transitions=transitions, fixed_composition_groups=fixed)


def main():
    protocol_path = Path('data/research/abortion_protocol.json')
    artifact = Path('artifacts/wvs-pilot.sqlite')
    protocol = json.loads(protocol_path.read_text())
    results = {}; source_years = {}
    with closing(connect(artifact)) as db:
        for corpus, source in [('public', 'ANES'), ('gss', 'GSS'), ('ces', 'CES')]:
            questions = [json.loads(row[0]) for row in db.execute(
                'SELECT payload FROM documents WHERE corpus=?', (corpus,))]
            questions = [q for q in questions if q['code'] in protocol['survey_codes'][source]]
            if {q['code'] for q in questions} != set(protocol['survey_codes'][source]):
                raise ValueError('Missing protocol questions: ' + source)
            selected = selected_items(questions)
            expected = series([], questions)[1]
            for year, items in selected.items():
                value = mean(list(items.values()))
                if abs(value - expected[year]) > 1e-12:
                    raise ValueError('Selection differs from serving aggregation')
                source_years.setdefault(year, {})[source] = value
            results[source] = dict(selected=selected, **audit(selected))
    report = dict(status='exploratory composition audit; not a causal decomposition',
        sources={str(p): digest(p) for p in [protocol_path, artifact, Path(__file__), Path('scvpublic/store.py')]},
        limitations=['Common-item differences are unadjusted descriptive comparisons, not statistical significance tests.',
                     'Fixed codes do not establish invariant wording, survey mode, population, or respondent composition.',
                     'Common-source differences can still contain within-source question changes.',
                     'Groups retain only observed years; no interpolation or claim of equal calendar intervals.',
                     'Composition contrast is the full change minus the change in common items; undefined without overlap.'],
        within_source=results, between_sources=audit(source_years))
    Path('artifacts/abortion-composition-audit.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    for source, result in results.items():
        print(source, [(len(g['items']), len(g['years']), min(g['years']), max(g['years']))
                       for g in result['fixed_composition_groups']])
        for row in result['transitions']:
            if row['added'] or row['removed']:
                print('composition change', row)


if __name__ == '__main__':
    main()
