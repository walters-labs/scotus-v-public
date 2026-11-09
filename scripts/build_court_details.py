"""Attach display metadata and source-summary excerpts without rebuilding search."""
import argparse
from contextlib import closing
import csv
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
from scvpublic.build import digest
from scvpublic.court_details import DECISION_TYPES
from scvpublic.sources import source_texts

SCDB = Path('data/raw/scdb-2026/SCDB_2026_01_caseCentered_Citation.csv')
SCDB_SHA = 'b3cc84bd73a7a0325856cca52ae6fc5bd6a39433113f83fef248556ad4488528'


def excerpt(text, limit=3500):
    text = ' '.join(text.split())
    return text if len(text) <= limit else text[:limit].rsplit(' ', 1)[0] + '…'


def build(artifact, bundle, output, output_bundle):
    if output.exists() or output_bundle.exists():
        raise FileExistsError('Choose new output paths')
    if digest(SCDB) != SCDB_SHA:
        raise ValueError('SCDB checksum mismatch')
    manifest = json.loads((bundle/'manifest.json').read_text())
    if manifest['artifact_sha256'] != digest(artifact):
        raise ValueError('Bundle does not match artifact')
    for name, sha in manifest['files'].items():
        if Path(name).name != name or digest(bundle/name) != sha:
            raise ValueError('Bundle checksum mismatch')
    # source_texts validates all raw source checksums. Fallback opinions are NOT
    # relabeled summaries. Excerpts may be incomplete in the upstream source.
    docs, texts, origins = source_texts(artifact)
    with SCDB.open(encoding='utf-8-sig') as f:
        rows = {r['caseId']: r for r in csv.DictReader(f)}
    official = json.loads(Path('data/processed/modern/official.json').read_text())['records']
    links = {r['case_id']: r['source_url'] for r in official
             if r.get('case_id') and r.get('source_url', '').startswith('https://www.supremecourt.gov/')}
    output.parent.mkdir(parents=True, exist_ok=True)
    output_bundle.parent.mkdir(parents=True, exist_ok=True)
    counts = dict(cases=0, scdb=0, summary_excerpts=0)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        candidate = Path(temp)/'details.sqlite'
        with closing(sqlite3.connect(artifact.resolve().as_uri()+'?mode=ro', uri=True)) as source, closing(sqlite3.connect(candidate)) as db:
            source.backup(db)
            db.execute('CREATE TABLE court_details (case_id TEXT PRIMARY KEY, payload TEXT NOT NULL) WITHOUT ROWID')
            for doc in docs:
                key = doc['case_id']; row = rows.get(key, {})
                detail = dict(decision_type=DECISION_TYPES.get(row.get('decisionType')),
                              docket=row.get('docket'), scdb_release='SCDB_2026_01' if row else None)
                if key in links: detail['source_url'] = links[key]
                if origins[key] == 'syllabus':
                    detail['summary_excerpt'] = excerpt(texts[key])
                    detail['summary_source'] = 'CaseSumm syllabus'
                    counts['summary_excerpts'] += 1
                db.execute('INSERT INTO court_details VALUES (?,?)', (key, json.dumps(detail)))
                counts['cases'] += 1; counts['scdb'] += bool(row)
            provenance = dict(counts, scdb_sha256=SCDB_SHA,
                              input_artifact_sha256=manifest['artifact_sha256'],
                              summary_policy='CaseSumm syllabus only; whitespace normalized; first 3500 characters at word boundary; upstream completeness not assumed')
            db.execute('INSERT INTO meta VALUES (?,?)', ('court_details', json.dumps(provenance)))
            db.commit()
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Invalid artifact')
        with tempfile.TemporaryDirectory(dir=output_bundle.parent) as bt:
            target = Path(bt)/'bundle'
            shutil.copytree(bundle, target)
            manifest['metadata_enriched_from_artifact_sha256'] = manifest['artifact_sha256']
            manifest['artifact_sha256'] = digest(candidate)
            (target/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
            target.rename(output_bundle)
        candidate.rename(output)
    print(json.dumps(provenance, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('artifact', 'bundle', 'output', 'output-bundle'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    build(a.artifact, a.bundle, a.output, a.output_bundle)
