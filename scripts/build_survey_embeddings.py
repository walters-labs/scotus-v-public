"""Add survey vectors to a new copy of a validated court embedding bundle."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np
from scvpublic.build import digest
from scvpublic.hybrid import HybridSearch
from scvpublic.store import connect
from scvpublic.survey_search import SurveySearch, SURVEY_FILES


def build(artifact, bundle, output):
    if output.exists():
        raise FileExistsError(output)
    engine = HybridSearch(bundle, artifact)
    with closing(connect(artifact)) as db:
        rows = list(db.execute("SELECT corpus,id,payload FROM documents WHERE corpus != 'court' ORDER BY corpus,id"))
    texts = [d.get('title', '')+'. '+d['question'] for _, _, payload in rows for d in [json.loads(payload)]]
    vectors = np.concatenate([engine.encoder.encode(texts[i:i+16]) for i in range(0, len(texts), 16)]) if texts else np.empty((0,384), dtype=np.float32)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        target = Path(temporary)/'bundle'
        shutil.copytree(bundle, target)
        np.save(target/SURVEY_FILES[0], vectors, allow_pickle=False)
        (target/SURVEY_FILES[1]).write_text(json.dumps([[source, id] for source, id, _ in rows])+'\n')
        manifest = json.loads((target/'manifest.json').read_text())
        manifest['survey_documents'] = len(rows)
        manifest['survey_text'] = 'title + question; encoder truncates at 256 tokens'
        manifest['files'].update({name: digest(target/name) for name in SURVEY_FILES})
        (target/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        SurveySearch(target, artifact, engine.encoder)
        target.rename(output)
    print(json.dumps(dict(documents=len(rows), vector_bytes=vectors.nbytes, output=str(output))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('artifact', 'bundle', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    build(args.artifact, args.bundle, args.output)
