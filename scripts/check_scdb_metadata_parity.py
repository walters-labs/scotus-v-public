"""Verify metadata enrichment leaves all original content and search/chart values intact."""
from contextlib import closing
from itertools import zip_longest
import json
from pathlib import Path
from scvpublic.store import connect,series,court_counts
from scvpublic.hybrid import HybridSearch
from scvpublic.build import digest


def main():
    old=Path('artifacts/affirmative-action.sqlite');new=Path('artifacts/scdb-issues.sqlite')
    with closing(connect(old)) as a,closing(connect(new)) as b:
        n=0
        for x,y in zip_longest(a.execute('SELECT * FROM documents ORDER BY corpus,id'),b.execute('SELECT * FROM documents ORDER BY corpus,id')):
            if x is None or y is None or x[:2]!=y[:2]:raise ValueError('Document identity changed')
            before,after=json.loads(x[2]),json.loads(y[2])
            if x[0]=='court':
                if 'scdb_issues' not in after:raise ValueError('Missing metadata')
                after.pop('scdb_issues');n+=1
            if before!=after:raise ValueError('Original payload changed')
        postings=0
        for x,y in zip_longest(a.execute('SELECT * FROM postings ORDER BY corpus,term,doc'),b.execute('SELECT * FROM postings ORDER BY corpus,term,doc')):
            if x!=y:raise ValueError('Postings changed')
            postings+=1
        before=dict(a.execute('SELECT * FROM meta'));after=dict(b.execute('SELECT * FROM meta'));after.pop('scdb_issue_metadata')
        if before!=after:raise ValueError('Original metadata changed')
    engines=[HybridSearch(Path(folder),artifact) for folder,artifact in [('artifacts/semantic-affirmative-action',old),('artifacts/semantic-scdb-issues',new)]]
    results=[]
    for query in ['abortion','contraception','civil rights','gun control','gay marriage','healthcare','minimum wage','immigration']:
        x,y=[e.search([query]) for e in engines]
        clean=[{k:v for k,v in r.items() if k!='scdb_issues'} for r in y]
        if x!=clean or series(x,[])!=series(y,[]) or court_counts(x)!=court_counts(y):raise ValueError('Search/chart parity failure: '+query)
        results.append(dict(query=query,cases=len(x),exact_parity=True))
    summary=dict(court_documents=n,postings_compared=postings,original_payloads_and_meta_identical=True,queries=results,
        artifact_sha256=digest(new),size_change_bytes=new.stat().st_size-old.stat().st_size)
    Path('data/evaluation/scdb-metadata-parity.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
