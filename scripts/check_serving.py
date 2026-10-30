"""Exercise a precomputed artifact using only serving dependencies."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
import resource
import sys
import time
from scvpublic.store import connect, search
from scvpublic.web import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifact')
    parser.add_argument('--hybrid', help='Load the embedding bundle and measure the full hybrid application')
    args = parser.parse_args()
    app = create_app(args.artifact, args.hybrid)
    terms = ['', 'abortion', 'gay marriage', 'gun control', 'government', 'court', 'rights', 'zzzznomatchzzzz']
    def request(term):
        start = time.perf_counter()
        with app.test_client() as client:
            response = client.get('/', query_string={'q1': term})
            assert response.status_code == 200, (term, response.status_code)
            assert response.headers.get('Content-Security-Policy')
        return time.perf_counter() - start
    with ThreadPoolExecutor(max_workers=2) as pool:
        timings = list(pool.map(request, terms * 20))
    with closing(connect(args.artifact)) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        corpora = [row[0] for row in db.execute('SELECT DISTINCT corpus FROM documents')]
        hits = {term: {corpus: len(search(db, corpus, [term])) for corpus in corpora}
                for term in terms[1:]}
    with app.test_client() as client:
        health = client.get('/healthz')
        assert health.status_code == 200
        if args.hybrid:
            assert health.json['search_mode'] == 'hybrid'
        assert client.get('/', query_string={'q1': 'x' * 101}).status_code == 400
    forbidden = {'scipy', 'pandas', 'sklearn', 'pyarrow'}
    if not args.hybrid:
        forbidden.add('numpy')
    scientific = forbidden & sys.modules.keys()
    assert not scientific, scientific
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps(dict(mode='hybrid' if args.hybrid else 'lexical',
        platform=sys.platform, memory_scope='single-process Flask test client; excludes gunicorn master and OS overhead',
        hit_counts_scope='lexical diagnostic only; request timings exercise selected application mode',
        requests=len(timings), threads=2, max_seconds=max(timings),
        p95_seconds=sorted(timings)[int(len(timings)*.95)],
        peak_rss_mib=rss / (1024**2 if sys.platform == 'darwin' else 1024), hits=hits), indent=2))


if __name__ == '__main__':
    main()
