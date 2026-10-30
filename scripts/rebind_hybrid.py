"""Reuse a verified embedding bundle after a survey-only artifact update."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from scvpublic.build import digest
from scvpublic.store import connect


def court_digest(artifact):
    result = hashlib.sha256()
    with closing(connect(artifact)) as db:
        for table, order in [('documents', 'id'), ('postings', 'term,doc')]:
            result.update(table.encode())
            for row in db.execute(f"SELECT * FROM {table} WHERE corpus='court' ORDER BY {order}"):
                result.update((json.dumps(row, ensure_ascii=True)+'\n').encode())
    return result.hexdigest()


def rebind(old, new, bundle, output):
    manifest = json.loads((bundle/'manifest.json').read_text())
    if digest(old) != manifest['artifact_sha256']:
        raise ValueError('Original bundle does not match original artifact')
    if output.exists():
        raise FileExistsError(output)
    fingerprint = court_digest(old)
    if fingerprint != court_digest(new):
        raise ValueError('Court documents or postings changed; rebuild embeddings')
    for name, expected in manifest['files'].items():
        if Path(name).name != name or digest(bundle/name) != expected:
            raise ValueError('Invalid bundle file: '+name)
    # Survey vectors are invalidated by survey-only updates. Rebuild explicitly.
    for name in ('survey-vectors.npy', 'survey-ids.json'):
        manifest['files'].pop(name, None)
    manifest.pop('survey_documents', None)
    manifest.pop('survey_text', None)
    manifest['rebound_from_artifact_sha256'] = manifest['artifact_sha256']
    manifest['court_content_sha256'] = fingerprint
    manifest['artifact_sha256'] = digest(new)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        destination = Path(temporary)/'bundle'
        destination.mkdir()
        for name in manifest['files']:
            shutil.copyfile(bundle/name, destination/name)
        (destination/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        destination.rename(output)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('old', 'new', 'bundle', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    rebind(a.old, a.new, a.bundle, a.output)
