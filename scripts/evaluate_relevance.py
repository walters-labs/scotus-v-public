"""Evaluate frozen topic judgments without changing serving or treating unknowns as negatives."""
import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path


def evaluate_hits(hits, judgments, key):
    ids = [key(h) for h in hits]
    counts = Counter(judgments.get(i, {}).get('label', 'unjudged') for i in ids)
    direct = {i for i, j in judgments.items() if j['label'] == 'direct'}
    return dict(total=len(ids), labels={label: counts[label] for label in
                ('direct', 'related', 'irrelevant', 'unjudged')},
                known_direct_found=sorted(direct.intersection(ids)),
                known_direct_missing=sorted(direct.difference(ids)),
                known_irrelevant_found=sorted(i for i in ids
                    if judgments.get(i, {}).get('label') == 'irrelevant'),
                ids=ids)


def regressions(current, baseline):
    failures = []
    for topic, before in baseline['queries'].items():
        after = current['queries'].get(topic)
        if after is None:
            failures.append(f'{topic}: missing topic')
            continue
        for section in ('display', 'chart', 'surveys'):
            lost = set(before[section]['known_direct_found']) - set(after[section]['known_direct_found'])
            added = set(after[section]['known_irrelevant_found']) - set(before[section]['known_irrelevant_found'])
            if lost: failures.append(f'{topic}/{section}: lost known relevant {sorted(lost)}')
            if added: failures.append(f'{topic}/{section}: added known irrelevant {sorted(added)}')
    return failures


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact', type=Path, default=Path('artifacts/gss-pilot.sqlite'))
    p.add_argument('--bundle', type=Path, default=Path('artifacts/semantic-full'))
    p.add_argument('--labels', type=Path, default=Path('data/evaluation/topic-relevance.json'))
    p.add_argument('--split', choices=['development', 'validation', 'all'], default='development')
    p.add_argument('--output', type=Path, default=Path('artifacts/relevance-evaluation.json'))
    p.add_argument('--baseline', type=Path, help='Fail on lost known positives or new known negatives')
    args = p.parse_args()
    from scvpublic.hybrid import HybridSearch, chart_matches, CHART_CUTOFF
    from scvpublic.store import connect, survey_search
    from scvpublic.build import digest
    labels = json.loads(args.labels.read_text())
    engine = HybridSearch(args.bundle, args.artifact)
    result = dict(schema_version=1, split=args.split, artifact_sha256=digest(args.artifact),
                  bundle_manifest_sha256=digest(args.bundle/'manifest.json'),
                  labels_sha256=digest(args.labels), chart_cutoff=CHART_CUTOFF,
                  search_code_sha256={name:digest(Path('scvpublic')/name) for name in
                                      ('hybrid.py', 'encoding.py', 'store.py')}, queries={})
    with closing(connect(args.artifact)) as db:
        for q, entry in labels['queries'].items():
            if args.split != 'all' and entry['split'] != args.split: continue
            hits = engine.search([q])
            chart = chart_matches(hits)
            surveys = [dict(h, benchmark_id=c+':'+h['code']) for c in ('public', 'gss')
                       for h in survey_search(db, c, [q])]
            result['queries'][q] = dict(split=entry['split'], candidate_count=len(hits),
                display=evaluate_hits(hits[:10], entry['court'], lambda h:h['case_id']),
                chart=evaluate_hits(chart, entry['court'], lambda h:h['case_id']),
                scored_chart_cases=sum(any(c['polarity'] is not None for c in h['cases']) for h in chart),
                surveys=evaluate_hits(surveys, entry['surveys'], lambda h:h['benchmark_id']),
                survey_sources={c:sum(h['benchmark_id'].startswith(c+':') for h in surveys)
                                for c in ('public','gss')})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    for q, r in result['queries'].items():
        print(f"{q}: chart {r['chart']['total']}, known off-topic {r['chart']['labels']['irrelevant']}, "
              f"unjudged {r['chart']['labels']['unjudged']}; surveys {r['surveys']['labels']}")
    if args.baseline:
        baseline = json.loads(args.baseline.read_text())
        if baseline['labels_sha256'] != result['labels_sha256']:
            raise SystemExit('Judgments changed; review and regenerate the baseline explicitly.')
        # Permit split-specific runs against an all-topic baseline.
        baseline['queries'] = {q:r for q,r in baseline['queries'].items()
                               if args.split == 'all' or r['split'] == args.split}
        errors = regressions(result, baseline)
        if errors: raise SystemExit('\n'.join(errors))
        print('No regressions against reviewed baseline; existing relevance failures remain.')


if __name__ == '__main__':
    main()
