"""Build an isolated survey-description embedding pilot; preserve lexical search."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np

from scvpublic.build import digest
from scvpublic.hybrid import HybridSearch
from scvpublic.store import connect
from scvpublic.survey_search import SurveySearch


def description_text(entry, document):
    source = document.get('title', '')+'\n'+document['question']
    if hashlib.sha256(source.encode()).hexdigest() != entry['source_text_sha256']:
        raise ValueError('Question wording changed: '+entry['code'])
    fields = [entry[k] for k in ('topic', 'policy', 'scope')]
    terms = entry['equivalent_terms']
    if not terms or any(not isinstance(t, str) or not t.strip() for t in fields+terms):
        raise ValueError('Empty or invalid description field')
    return '. '.join(t.rstrip('.') for t in fields)+'. Related terminology: '+', '.join(terms)+'.'


def build(artifact, bundle, descriptions, output):
    if output.exists():
        raise FileExistsError(output)
    engine = HybridSearch(bundle, artifact)
    baseline = SurveySearch(bundle, artifact, engine.encoder)
    spec = json.loads(descriptions.read_text())
    if spec['version'] != 1:
        raise ValueError('Unsupported descriptions')
    with closing(connect(artifact)) as db:
        docs = [json.loads(db.execute('SELECT payload FROM documents WHERE corpus=? AND id=?', key).fetchone()[0]) for key in baseline.keys]
    positions = {(source, d['code']): i for i, ((source, _), d) in enumerate(zip(baseline.keys, docs))}
    texts, indices = [], []
    for entry in spec['entries']:
        index = positions[(entry['source'], entry['code'])]
        if index in indices:
            raise ValueError('Duplicate description')
        texts.append(description_text(entry, docs[index]))
        indices.append(index)
    if not indices:
        raise ValueError('Empty pilot')
    vectors = baseline.vectors.copy()
    vectors[indices] = np.concatenate([engine.encoder.encode(texts[i:i+16]) for i in range(0, len(texts), 16)])
    topic_vectors = baseline.vectors.copy()
    topics = [entry['topic'] for entry in spec['entries']]
    topic_vectors[indices] = np.concatenate([engine.encoder.encode(topics[i:i+16]) for i in range(0, len(topics), 16)])
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        target = Path(temp)/'bundle'
        shutil.copytree(bundle, target)
        np.save(target/'survey-vectors.npy', vectors, allow_pickle=False)
        np.save(target/'survey-topic-vectors.npy', topic_vectors, allow_pickle=False)
        shutil.copyfile(descriptions, target/'survey-descriptions.json')
        manifest = json.loads((target/'manifest.json').read_text())
        manifest['survey_text'] = 'Reviewed description pilot; other question vectors preserved byte-for-byte'
        manifest['survey_description_count'] = len(indices)
        for name in ('survey-vectors.npy', 'survey-descriptions.json', 'survey-topic-vectors.npy'):
            manifest['files'][name] = digest(target/name)
        (target/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        SurveySearch(target, artifact, engine.encoder)
        target.rename(output)
    print(json.dumps(dict(updated=len(indices), unchanged=len(docs)-len(indices), output=str(output))))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('artifact', 'bundle', 'descriptions', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    build(a.artifact, a.bundle, a.descriptions, a.output)
