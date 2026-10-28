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
    args = parser.parse_args()
    app = create_app(args.artifact)
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
        assert client.get('/healthz').status_code == 200
        assert client.get('/', query_string={'q1': 'x' * 101}).status_code == 400
    scientific = {'numpy', 'scipy', 'pandas', 'sklearn', 'pyarrow'} & sys.modules.keys()
    assert not scientific, scientific
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps(dict(requests=len(timings), threads=2, max_seconds=max(timings),
        p95_seconds=sorted(timings)[int(len(timings)*.95)],
        peak_rss_mib=rss / (1024**2 if sys.platform == 'darwin' else 1024), hits=hits), indent=2))


if __name__ == '__main__':
    main()
