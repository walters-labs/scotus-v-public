"""Check equivalent survey queries for overlap AND question-level relevance."""
import argparse
from contextlib import closing
import json
from pathlib import Path

from scvpublic.build import digest
from scvpublic.encoding import Encoder
from scvpublic.store import connect
from scvpublic.survey_search import SurveySearch


def compare(left, right, relevant, irrelevant):
    left, right, relevant, irrelevant = map(set, (left, right, relevant, irrelevant))
    union = left | right
    return dict(jaccard=len(left & right)/len(union) if union else None,
                both_empty=not union,
                missed_left=sorted(relevant-left), missed_right=sorted(relevant-right),
                irrelevant_left=sorted(left & irrelevant), irrelevant_right=sorted(right & irrelevant))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--judgments', type=Path, default=Path('data/evaluation/survey-synonyms.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    engine = SurveySearch(args.bundle, args.artifact, Encoder(args.bundle))
    rows = []
    with closing(connect(args.artifact)) as db:
        for pair in json.loads(args.judgments.read_text())['pairs']:
            docs = {json.loads(p)['code'] for p, in db.execute(
                'SELECT payload FROM documents WHERE corpus=?', (pair['corpus'],))}
            assert set(pair['relevant']+pair['irrelevant']) <= docs
            assert not set(pair['relevant']) & set(pair['irrelevant'])
            left, right = [[h['code'] for h in engine.search([q]).get(pair['corpus'], [])]
                           for q in pair['queries']]
            rows.append(dict(pair, left=left, right=right,
                             **compare(left, right, pair['relevant'], pair['irrelevant'])))
    report = dict(status='development evaluation, not independent validation', pairs=rows,
                  sources={str(p): digest(p) for p in [args.artifact, args.bundle/'manifest.json',
                           args.judgments, Path(__file__), Path('scvpublic/survey_search.py')]})
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
