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


def build(artifact, bundle, output, phrases=False, reuse_artifact=None, reuse_bundle=None):
    if output.exists():
        raise FileExistsError(output)
    engine = HybridSearch(bundle, artifact)
    with closing(connect(artifact)) as db:
        rows = list(db.execute("SELECT corpus,id,payload FROM documents WHERE corpus != 'court' ORDER BY corpus,id"))
    texts = [d.get('search_text') or (d.get('title', '')+'. '+d['question']) for _, _, payload in rows for d in [json.loads(payload)]]
    if (reuse_artifact is None) != (reuse_bundle is None):
        raise ValueError('Both reuse artifact and bundle are required')
    if reuse_bundle is not None:
        old = SurveySearch(reuse_bundle, reuse_artifact, engine.encoder)
        old_manifest = json.loads((reuse_bundle/'manifest.json').read_text())
        new_manifest = json.loads((bundle/'manifest.json').read_text())
        for name in ('model.onnx', 'tokenizer.json'):
            if old_manifest['files'][name] != new_manifest['files'][name]:
                raise ValueError('Cannot reuse vectors from a different encoder')
        with closing(connect(reuse_artifact)) as db:
            previous = {}
            for i, (source, doc_id) in enumerate(old.keys):
                doc = json.loads(db.execute('SELECT payload FROM documents WHERE corpus=? AND id=?',
                                           (source, doc_id)).fetchone()[0])
                previous[source, doc['code']] = (doc, old.vectors[i])
        current = {(source, json.loads(payload)['code']): json.loads(payload)
                   for source, _, payload in rows}
        if not previous.keys() <= current.keys() or any(current[k] != d for k, (d, _) in previous.items()):
            raise ValueError('Append-only reuse requires every existing survey record unchanged')
        vectors = np.stack([previous[source, json.loads(payload)['code']][1]
            if (source, json.loads(payload)['code']) in previous else engine.encoder.encode([text])[0]
            for (source, _, payload), text in zip(rows, texts)])
    else:
        vectors = np.concatenate([engine.encoder.encode(texts[i:i+16]) for i in range(0, len(texts), 16)]) if texts else np.empty((0,384), dtype=np.float32)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        target = Path(temporary)/'bundle'
        shutil.copytree(bundle, target)
        np.save(target/SURVEY_FILES[0], vectors, allow_pickle=False)
        (target/SURVEY_FILES[1]).write_text(json.dumps([[source, id] for source, id, _ in rows])+'\n')
        manifest = json.loads((target/'manifest.json').read_text())
        manifest['survey_documents'] = len(rows)
        manifest['survey_text'] = 'search_text when provided, otherwise title + question; encoder truncates at 256 tokens'
        manifest['files'].update({name: digest(target/name) for name in SURVEY_FILES})
        for name in ('survey-phrases.json', 'survey-phrase-vectors.npy'):
            (target/name).unlink(missing_ok=True)
            manifest['files'].pop(name, None)
        manifest.pop('survey_phrase_expansion', None)
        if phrases and reuse_bundle is not None:
            # Freeze expansion vocabulary as well as document vectors. Rebuilding
            # quantized batches can change scores for otherwise unchanged text.
            for name in ('survey-phrases.json', 'survey-phrase-vectors.npy'):
                shutil.copyfile(reuse_bundle/name, target/name)
                manifest['files'][name] = digest(target/name)
            manifest['survey_phrase_expansion'] = old_manifest['survey_phrase_expansion']
            manifest['survey_vector_reuse'] = dict(artifact_sha256=digest(reuse_artifact),
                manifest_sha256=digest(reuse_bundle/'manifest.json'),
                preserved_documents=len(previous), phrase_vocabulary='preserved')
        elif phrases:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from scripts.experiment_survey_phrases import phrases as extract_phrases
            vectorizer = TfidfVectorizer(analyzer=extract_phrases, dtype=np.float32)
            matrix = vectorizer.fit_transform(texts)
            names = vectorizer.get_feature_names_out()
            selected = set()
            for row in matrix:
                ranked = sorted(zip(row.indices, row.data), key=lambda v: (-v[1], names[v[0]]))
                selected.update(i for i, _ in ranked[:8])
            vocabulary = sorted(names[list(selected)].tolist())
            phrase_vectors = np.concatenate([engine.encoder.encode(vocabulary[i:i+16]) for i in range(0,len(vocabulary),16)])
            (target/'survey-phrases.json').write_text(json.dumps(vocabulary)+'\n')
            np.save(target/'survey-phrase-vectors.npy', phrase_vectors, allow_pickle=False)
            manifest['survey_phrase_expansion'] = 'weighted-v1'
            for name in ('survey-phrases.json', 'survey-phrase-vectors.npy'):
                manifest['files'][name] = digest(target/name)

        (target/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        SurveySearch(target, artifact, engine.encoder)
        target.rename(output)
    print(json.dumps(dict(documents=len(rows), vector_bytes=vectors.nbytes, output=str(output))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('artifact', 'bundle', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--phrases', action='store_true')
    parser.add_argument('--reuse-artifact', type=Path)
    parser.add_argument('--reuse-bundle', type=Path)
    args = parser.parse_args()
    build(args.artifact, args.bundle, args.output, args.phrases, args.reuse_artifact, args.reuse_bundle)
