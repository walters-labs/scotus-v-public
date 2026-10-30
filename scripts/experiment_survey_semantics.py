"""Rank survey questions offline with the existing encoder; select no cutoff."""
import json
from pathlib import Path
import time

import numpy as np
from scvpublic.build import digest
from scvpublic.encoding import Encoder
from scvpublic.store import connect


artifact = Path('artifacts/ces-gapfill-candidate.sqlite')
bundle = Path('artifacts/semantic-ces-gapfill-candidate')
manifest = json.loads((bundle/'manifest.json').read_text())
assert digest(artifact) == manifest['artifact_sha256']
for name in ['model.onnx', 'tokenizer.json']:
    assert digest(bundle/name) == manifest['files'][name]
encoder = Encoder(bundle)
documents = []
with connect(artifact) as db:
    for corpus, payload in db.execute("SELECT corpus,payload FROM documents WHERE corpus != 'court' ORDER BY corpus,id"):
        documents.append(dict(json.loads(payload), corpus=corpus))
texts = [d.get('title', '')+'. '+d['question'] for d in documents]
start = time.monotonic()
vectors = np.concatenate([encoder.encode(texts[i:i+16]) for i in range(0,len(texts),16)])
judgments_path = Path('data/evaluation/survey-relevance-development.json')
judgments = json.loads(judgments_path.read_text())
queries = sorted({c['query'] for c in judgments['cases']} | {'immigration', 'zzzznomatchzzzz'})
# Match serving's one-query call; quantized inference can depend on batch padding.
query_vectors = np.concatenate([encoder.encode([query]) for query in queries])
results = {}
for query, vector in zip(queries, query_vectors):
    scores = vectors @ vector
    for corpus in sorted({d['corpus'] for d in documents}):
        ranked = sorted((i for i,d in enumerate(documents) if d['corpus']==corpus),
                        key=lambda i: -scores[i])[:10]
        results[corpus+':'+query] = [dict(code=documents[i]['code'],
            question=documents[i]['question'], score=float(scores[i])) for i in ranked]
report = dict(status='offline rankings only; no acceptance threshold',
    documents=len(documents), vector_bytes=vectors.nbytes, elapsed_seconds=time.monotonic()-start,
    artifact_sha256=digest(artifact), bundle_manifest_sha256=digest(bundle/'manifest.json'),
    script_sha256=digest(Path(__file__)), judgments_sha256=digest(judgments_path), results=results,
    limitations=['Cosine similarity is not a probability of relevance.',
        'Text over 256 tokens is truncated by the existing encoder.',
        'Top-ranked items can all be irrelevant; no matches are accepted by this experiment.'])
Path('artifacts/survey-semantic-rankings.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['documents','vector_bytes','elapsed_seconds']}))
for key in ['ces:environmental regulation','public:gay marriage','gss:gay marriage','gss:gun control']:
    print(key,[(d['code'],round(d['score'],3)) for d in results[key][:4]])
