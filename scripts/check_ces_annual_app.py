"""Check the reviewed annual CES candidate without changing the live app."""
import argparse
import json
from pathlib import Path

from scvpublic.build import digest
from scvpublic.store import connect, survey_search
from scvpublic.web import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--check-2022', action='store_true')
    parser.add_argument('--check-2023', action='store_true')
    args = parser.parse_args()
    source = json.loads(args.source.read_text())
    expected = {d['code']: d for d in source['documents']}
    with connect(args.artifact) as db:
        actual = {d['code']: d for (payload,) in db.execute(
            "SELECT payload FROM documents WHERE corpus='ces'")
            for d in [json.loads(payload)]}
        assert actual == expected, 'Attached CES documents differ from processed source'
        queries = ['abortion', 'gun control', 'immigration', 'renewable', 'Medicaid']
        hits = {}
        for query in queries:
            selected = survey_search(db, 'ces', [query])
            hits[query] = [d['code'] for d in selected if '2024' in d['years']]
            assert hits[query], query
        if args.check_2022:
            for query in ['abortion', 'immigration', 'carbon', 'assault rifles']:
                selected = survey_search(db, 'ces', [query])
                assert any('2022' in d['years'] for d in selected), (query, 2022)
        if args.check_2023:
            for query in ['abortion', 'gun control', 'immigration', 'carbon', 'Medicaid']:
                selected = survey_search(db, 'ces', [query])
                assert any('2023' in d['years'] for d in selected), (query, 2023)
    app = create_app(args.artifact, args.bundle)
    requests = 0
    with app.test_client() as client:
        assert client.get('/healthz').json['search_mode'] == 'hybrid'
        for query in queries + ['birth control', 'gay marriage', 'civil rights', 'zzzznomatchzzzz']:
            for view in ['all', 'combined', 'anes', 'gss', 'ces', 'pew', 'wvs']:
                response = client.get('/', query_string={'q1': query, 'view': view})
                assert response.status_code == 200, (query, view)
                html = response.get_data(as_text=True)
                if args.check_2023 and query == 'immigration' and view == 'ces':
                    assert '2023 source documentation' in html
                    assert 'post-election-only' in html
                if query == 'birth control':
                    assert 'GRISWOLD' in html
                if query == 'gay marriage':
                    assert 'OBERGEFELL' in html
                if query == 'zzzznomatchzzzz':
                    assert 'No matching opinions.' in html
                requests += 1
    print(json.dumps(dict(status='passed', hybrid_requests=requests,
        ces_2024_search_hits=hits, artifact_sha256=digest(args.artifact),
        source_sha256=digest(args.source),
        bundle_manifest_sha256=digest(args.bundle / 'manifest.json')), indent=2))


if __name__ == '__main__':
    main()
