"""Read-only inventory of cached CourtListener opinion metadata, not NLP extraction."""
import argparse
from collections import Counter, defaultdict
from contextlib import closing
import gzip
import json
from pathlib import Path
import re
import sqlite3
from scvpublic.build import digest


def records(db, kind):
    return [json.loads(gzip.decompress(payload)) for payload, in db.execute(
        'SELECT payload FROM records WHERE kind=? ORDER BY id', (kind,))]


def resource_id(url):
    return int(str(url).rstrip('/').rsplit('/', 1)[-1])


def citation(value):
    return re.sub(r'[^a-z0-9]', '', value.lower())


def audit(artifact, caches):
    with closing(sqlite3.connect(artifact.resolve().as_uri()+'?mode=ro', uri=True)) as db:
        docs = [json.loads(p) for p, in db.execute("SELECT payload FROM documents WHERE corpus='court'")]
    by_cite = defaultdict(set)
    for doc in docs:
        if doc.get('citation'): by_cite[citation(doc['citation'])].add(doc['case_id'])
    clusters, opinions, inventories = {}, {}, []
    for path in caches:
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)) as db:
            cs, ops = records(db, 'clusters'), records(db, 'opinions')
            inventories.append(dict(path=str(path), sha256=digest(path), clusters=len(cs), opinions=len(ops),
                multiple_opinion_references=sum(len(c['sub_opinions']) > 1 for c in cs),
                streams=[dict(kind=k, pages=p, rows=r, complete=n is None)
                         for k,n,p,r in db.execute('SELECT kind,next_url,pages,rows FROM state')]))
            for c in cs:
                if c['id'] in clusters and clusters[c['id']] != c: raise ValueError('Conflicting cached cluster')
                clusters[c['id']] = c
            for o in ops:
                if o['id'] in opinions and opinions[o['id']] != o: raise ValueError('Conflicting cached opinion')
                opinions[o['id']] = o
    matches = []
    for c in clusters.values():
        ids = set()
        for ref in c.get('citations', []):
            ids |= by_cite.get(citation(f"{ref['volume']} {ref['reporter']} {ref['page']}"), set())
        if len(ids) == 1:
            refs = [resource_id(u) for u in c['sub_opinions']]
            available = [opinions[i] for i in refs if i in opinions]
            matches.append(dict(case_id=next(iter(ids)), cluster_id=c['id'], name=c['case_name'],
                references=len(refs), cached_opinions=len(available),
                complete_referenced_set=bool(refs) and len(refs)==len(available),
                types=dict(Counter(o.get('type') for o in available))))
    return dict(artifact=str(artifact), artifact_sha256=digest(artifact), corpus_cases=len(docs),
        caches=inventories, unique_clusters=len(clusters), unique_opinions=len(opinions),
        types=dict(Counter(o.get('type') for o in opinions.values())),
        author_field_present=sum('author' in o for o in opinions.values()),
        joined_by_field_present=sum('joined_by' in o for o in opinions.values()),
        opinion_url_present=sum(bool(o.get('absolute_url')) for o in opinions.values()),
        uniquely_citation_matched_clusters=len(matches),
        uniquely_matched_corpus_cases=len({m['case_id'] for m in matches}),
        complete_referenced_sets=sum(m['complete_referenced_set'] for m in matches),
        matches=matches,
        limitations=['Nonrandom incomplete API crawls; not an estimate of provider-wide coverage.',
                    'Author and joinder fields omitted by original downloader; absence is not a provider null.',
                    'Combined opinions do not identify separate authors or legal holdings.',
                    'Multiple cluster records may represent the same case; matches are not deduplicated opinions.'])


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',type=Path,default=Path('artifacts/court-details.sqlite'))
    p.add_argument('--output',type=Path,default=Path('data/evaluation/courtlistener-metadata-audit.json'))
    a=p.parse_args()
    result=audit(a.artifact,[Path('data/raw/rebuild/courtlistener.sqlite'),Path('data/raw/sample/courtlistener.sqlite')])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('matches','caches')},indent=2))
