"""Check education coverage and search regressions against the previous release."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import numpy as np

from scvpublic.build import digest
from scvpublic.encoding import Encoder
from scvpublic.store import connect, series
from scvpublic.survey_search import SurveySearch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline-artifact', 'baseline-bundle', 'artifact', 'bundle', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    encoder = Encoder(args.baseline_bundle)
    before = SurveySearch(args.baseline_bundle, args.baseline_artifact, encoder)
    after = SurveySearch(args.bundle, args.artifact, encoder)
    targets = {'ces': {'student_loan_forgiveness'}, 'prri': {'prri_free_tuition_income_limit'},
               'gss': {'nateduc'}, 'public': {'VCF0890', 'VCF0891'},
               'nationscape': {'nationscape_college', 'nationscape_vouchers'}}
    def identities(results):
        return {s: sorted(h['code'] for h in hits) for s, hits in results.items()}
    for query in ('education',):
        result = after.search([query])
        for source, codes in targets.items():
            assert {h['code'] for h in result[source]} == codes, (query, source)
        assert sum(map(len, result.values())) == 7
    narrow = {
        'school funding': {'gss': {'nateduc'}, 'public': {'VCF0890'},
                           'nationscape': {'nationscape_vouchers'}},
        'college affordability': {'public': {'VCF0891'}, 'nationscape': {'nationscape_college'},
                                 'ces': {'student_loan_forgiveness'},
                                 'prri': {'prri_free_tuition_income_limit'}},
        'student loan forgiveness': {'ces': {'student_loan_forgiveness'}},
        'school vouchers': {'nationscape': {'nationscape_vouchers'}},
        'free college tuition': {'prri': {'prri_free_tuition_income_limit'}},
    }
    for query, expected in narrow.items():
        selected = identities(after.search([query]))
        for source, codes in expected.items():
            assert codes <= set(selected[source]), (query, source, selected)
    paths = [Path('data/evaluation')/name for name in (
        'survey-relevance-development.json', 'survey-climate-relevance.json',
        'survey-description-checks.json', 'survey-synonyms.json')]
    cases = [c for p in paths[:-1] for c in json.loads(p.read_text())['cases']]
    for pair in json.loads(paths[-1].read_text())['pairs']:
        cases.extend(dict(pair, query=q) for q in pair['queries'])
    queries = sorted({c['query'] for c in cases} | {
        'abortion', 'gun control', 'gay marriage', 'death penalty', 'immigration',
        'environmental regulation', 'healthcare', 'education', 'civil rights',
        'taxes', 'marijuana', 'child care', 'health', 'care', 'insurance',
        'climate', 'energy', 'medicaid work requirements', 'school funding',
        'college affordability', 'student loan forgiveness', 'school vouchers', 'free college tuition'})
    results = {q: (identities(before.search([q])), identities(after.search([q])))
               for q in queries}
    regressions = []
    for case in cases:
        old, new = (set(r[case['corpus']]) for r in results[case['query']])
        lost = sorted((old-new) & set(case['relevant']))
        bad = sorted((new-old) & set(case['irrelevant']))
        if lost or bad:
            regressions.append(dict(query=case['query'], source=case['corpus'],
                                    lost_relevant=lost, new_irrelevant=bad))
    changes = {q: dict(before=a, after=b) for q, (a, b) in results.items() if a != b}
    # New data may change scores, but unrelated result identities should stay put.
    assert not regressions, regressions
    assert set(changes) <= {'education', 'school funding', 'college affordability', 'student loan forgiveness', 'free college tuition'}, changes
    with closing(connect(args.baseline_artifact)) as old, closing(connect(args.artifact)) as new:
        def docs(db):
            return {(s, json.loads(p)['code']): json.loads(p) for s, p in db.execute(
                "SELECT corpus,payload FROM documents WHERE corpus!='court'")}
        old_docs, new_docs = docs(old), docs(new)
        assert all(new_docs[k] == d for k, d in old_docs.items())
        assert set(new_docs)-set(old_docs) == {('ces', 'student_loan_forgiveness'), ('prri', 'prri_free_tuition_income_limit')}
        def vectors(engine, db):
            return {(source, json.loads(db.execute(
                'SELECT payload FROM documents WHERE corpus=? AND id=?',
                (source, doc_id)).fetchone()[0])['code']): engine.vectors[i]
                for i, (source, doc_id) in enumerate(engine.keys)}
        old_vectors, new_vectors = vectors(before, old), vectors(after, new)
        assert all(np.array_equal(v, new_vectors[k]) for k, v in old_vectors.items())
    for name in ('survey-phrases.json', 'survey-phrase-vectors.npy', 'vectors.npy', 'model.onnx'):
        assert digest(args.baseline_bundle/name) == digest(args.bundle/name), name
    hits = after.search(['education'])
    years = sorted({y for hs in hits.values() for y in series([], hs)[1]})
    report = dict(status='passed', queries_checked=len(queries), judged_cases=len(cases),
        regressions=regressions, changes=changes, questions=identities(hits),
        public_years=years, existing_survey_records_preserved=len(old_docs),
        narrow_queries_checked=list(narrow),
        limitation='Partial development judgments, not independent relevance validation.',
        sources={str(p): digest(p) for p in paths+[args.artifact,
            args.baseline_artifact, args.bundle/'manifest.json',
            args.baseline_bundle/'manifest.json', Path(__file__)]})
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('sources', 'changes')}))


if __name__ == '__main__':
    main()
