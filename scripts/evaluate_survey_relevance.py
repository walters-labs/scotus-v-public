"""Evaluate partial, provisional survey judgments without treating unjudged hits as errors."""
import argparse
import json
from pathlib import Path

from scvpublic.build import digest
from scvpublic.store import connect, survey_search


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact', type=Path, default=Path('artifacts/ces-gapfill-candidate.sqlite'))
    p.add_argument('--judgments', type=Path, default=Path('data/evaluation/survey-relevance-development.json'))
    p.add_argument('--experiment', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    judgments = json.loads(args.judgments.read_text())
    experiment = json.loads(args.experiment.read_text()) if args.experiment else None
    if experiment:
        assert experiment['artifact_sha256'] == digest(args.artifact)
    results = []
    with connect(args.artifact) as db:
        for case in judgments['cases']:
            corpus, query = case['corpus'], case['query']
            docs = {d['code']: d for payload, in db.execute(
                'SELECT payload FROM documents WHERE corpus=?', (corpus,))
                for d in [json.loads(payload)]}
            relevant, irrelevant = set(case['relevant']), set(case['irrelevant'])
            assert not relevant & irrelevant
            assert (relevant | irrelevant) <= docs.keys()
            selected = (experiment['results'][corpus+':'+query]['after'] if experiment else
                        [d['code'] for d in survey_search(db, corpus, [query])])
            hits = set(selected)
            results.append(dict(query=query, corpus=corpus, selected=selected,
                missed_relevant=sorted(relevant-hits), retrieved_irrelevant=sorted(irrelevant & hits),
                unjudged=sorted(hits-relevant-irrelevant),
                judged_questions={code: docs[code]['question'] for code in sorted(relevant | irrelevant)}))
    report = dict(status='development evaluation, not independent validation', cases=results,
        missed_relevant=sum(len(r['missed_relevant']) for r in results),
        retrieved_irrelevant=sum(len(r['retrieved_irrelevant']) for r in results),
        sources={str(path): digest(path) for path in
            [args.artifact, args.judgments, Path(__file__), Path('scvpublic/store.py')] +
            ([args.experiment] if args.experiment else [])},
        limitations=['Partial labels: unjudged matches are neither correct nor incorrect by default.',
                     'Development examples selected after observing failures; no general precision/recall claim.'])
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ['status', 'missed_relevant', 'retrieved_irrelevant']}))


if __name__ == '__main__':
    main()
