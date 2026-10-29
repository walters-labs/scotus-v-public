"""Offline GSS pilot: explicit response maps, weighted yearly means, local index."""
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

from .build import digest, write_index
from .public import aggregate, validate


def aggregate_gss(frame, entries, totals):
    # Choose the recommended weight by survey year, never by individual response.
    # Missing modern weights must not fall back to a different weighting scheme.
    frame = frame.copy()
    frame['VCF0004'] = frame['year']
    frame['gss_weight'] = frame['wtssps'].astype(float).where(
        frame['year'] < 2004, frame['wtssnrps'].astype(float))
    aggregate(frame, entries, totals)


def build(source, mappings, output, manifest):
    import pandas as pd
    specification = json.loads(manifest.read_text())
    if digest(source) != specification['dta_sha256']:
        raise ValueError('GSS source checksum differs from the reviewed release')
    mapping = json.loads(mappings.read_text())
    if mapping['version'] != 'explicit-gss-v1':
        raise ValueError('Unsupported GSS mapping')
    validate(dict(mapping, version='explicit-anes-v1'))
    entries = mapping['entries']
    if any(e['weight'] != 'gss_weight' for e in entries):
        raise ValueError('Unexpected GSS weight')
    totals = defaultdict(lambda: [0., 0., 0])
    columns = ['year', 'wtssps', 'wtssnrps'] + [e['code'] for e in entries]
    with pd.read_stata(source, convert_categoricals=False, columns=columns, chunksize=2000) as reader:
        for frame in reader:
            aggregate_gss(frame, entries, totals)
    documents = []
    for entry in entries:
        by_year = {str(y): t for (code, y), t in sorted(totals.items())
                   if code == entry['code'] and t[1] > 0}
        documents.append(dict(entry, dataset='GSS',
            years={y: t[0]/t[1] for y, t in by_year.items()},
            respondents={y: t[2] for y, t in by_year.items()},
            weight_sums={y: t[1] for y, t in by_year.items()}))
    payload = dict(methodology=mapping['version'], documents=documents,
        sources={str(p.resolve()): digest(p) for p in [source, mappings, manifest]},
        release=specification['release'], notes=mapping['notes'])
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False)+'\n')
    temporary.replace(output)
    print(json.dumps({d['code']: {'years': len(d['years']),
        'first': min(d['years'], default=None), 'last': max(d['years'], default=None)}
        for d in documents}, indent=2))


def attach(artifact, source, output, corpus="gss"):
    """Copy an artifact and replace an explicitly mapped optional survey corpus."""
    if corpus not in ("gss", "ces", "pew", "wvs"):
        raise ValueError("Unsupported survey corpus")
    from sklearn.feature_extraction.text import TfidfVectorizer
    import numpy as np
    payload = json.loads(source.read_text())
    if payload['methodology'] != f'explicit-{corpus}-v1':
        raise ValueError('Unsupported survey methodology')
    if not artifact.is_file():
        raise FileNotFoundError(artifact)
    if output.exists():
        raise FileExistsError(output)
    documents = payload['documents']
    # A small pilot cannot use ANES's 30% document-frequency ceiling: it
    # would discard terms shared by the two marriage wording variants.
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english', dtype=np.float32)
    matrix = vectorizer.fit_transform(d['title']+' '+d['question'] for d in documents)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=output.parent, prefix=f'.{corpus}-', suffix='.sqlite')
    os.close(fd)
    try:
        shutil.copyfile(artifact, name)
        with sqlite3.connect(name) as db:
            db.execute("DELETE FROM postings WHERE corpus=?", (corpus,))
            db.execute("DELETE FROM documents WHERE corpus=?", (corpus,))
            write_index(db, corpus, matrix, vectorizer.get_feature_names_out(), documents)
            updates = dict(gss_documents=len(documents), gss_release=payload['release'],
                gss_methodology=payload['methodology'], gss_notes=payload['notes'],
                gss_sources=payload['sources'], gss_artifact_sha256=digest(source))
            db.executemany('INSERT OR REPLACE INTO meta VALUES (?,?)',
                           [(k.replace('gss_', corpus+'_', 1), json.dumps(v)) for k, v in updates.items()])
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Integrity check failed')
        os.replace(name, output)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=Path('data/raw/gss-2024-r3a/gss7224_r3a.dta'))
    p.add_argument('--mappings', type=Path, default=Path('data/gss/response_mappings.json'))
    p.add_argument('--manifest', type=Path, default=Path('data/manifests/gss-2024-r3a.json'))
    p.add_argument('--output', type=Path, default=Path('data/processed/gss-2024-r3a/public.json'))
    p.add_argument('--base-artifact', type=Path)
    p.add_argument('--artifact', type=Path, default=Path('artifacts/gss-pilot.sqlite'))
    a = p.parse_args()
    build(a.source, a.mappings, a.output, a.manifest)
    if a.base_artifact:
        attach(a.base_artifact, a.output, a.artifact)


if __name__ == '__main__':
    main()
