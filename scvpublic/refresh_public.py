"""Atomically replace public search data while retaining the existing Court index."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
from .build import digest, write_index


def refresh(artifact, source):
    from sklearn.feature_extraction.text import TfidfVectorizer
    import numpy as np
    payload=json.loads(source.read_text())
    if 'schema_version' in payload:
        from .survey_schema import validate
        validate(payload)
    if payload['methodology'] != 'explicit-anes-v1':
        raise ValueError('Unsupported public methodology')
    docs=payload['documents']
    vectorizer=TfidfVectorizer(ngram_range=(1,2),stop_words='english',min_df=.0001,max_df=.30,dtype=np.float32)
    matrix=vectorizer.fit_transform(d['title']+' '+d['question'] for d in docs)
    if not artifact.is_file():
        raise FileNotFoundError(artifact)
    fd,name=tempfile.mkstemp(dir=artifact.parent,prefix='.refresh-',suffix='.sqlite');os.close(fd)
    try:
        shutil.copyfile(artifact,name)
        with sqlite3.connect(name) as db:
            metadata={k:json.loads(v) for k,v in db.execute('SELECT key,value FROM meta')}
            if metadata.get('public_methodology') != payload['methodology']:
                raise ValueError('Existing artifact uses a different methodology')
            db.execute("DELETE FROM postings WHERE corpus='public'")
            db.execute("DELETE FROM documents WHERE corpus='public'")
            write_index(db,'public',matrix,vectorizer.get_feature_names_out(),docs)
            sources=metadata['sources']; sources.update(payload['sources']);sources[str(source.resolve())]=digest(source)
            updates=dict(sources=sources,public_documents=len(docs),plottable_questions=sum(bool(d['years']) for d in docs),public_refresh_sha256=digest(source))
            db.executemany('INSERT OR REPLACE INTO meta VALUES (?,?)',[(k,json.dumps(v)) for k,v in updates.items()])
            db.commit()
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Integrity check failed')
        os.replace(name,artifact)
    finally:
        Path(name).unlink(missing_ok=True)
    print(f'Refreshed {len(docs)} public questions in {artifact}')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',type=Path,default=Path('artifacts/casesumm.sqlite'))
    p.add_argument('--public',type=Path,default=Path('data/processed/anes-20260205/public.json'))
    a=p.parse_args();refresh(a.artifact,a.public)

if __name__=='__main__':main()
