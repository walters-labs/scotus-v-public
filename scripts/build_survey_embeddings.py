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


def build(artifact, bundle, output, phrases=False):
    if output.exists():
        raise FileExistsError(output)
    engine = HybridSearch(bundle, artifact)
    with closing(connect(artifact)) as db:
        rows = list(db.execute("SELECT corpus,id,payload FROM documents WHERE corpus != 'court' ORDER BY corpus,id"))
    texts = [d.get('search_text') or (d.get('title', '')+'. '+d['question']) for _, _, payload in rows for d in [json.loads(payload)]]
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
        if phrases:
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
    args = parser.parse_args()
    build(args.artifact, args.bundle, args.output, args.phrases)
