"""Hybrid Court search using TF-IDF and precomputed passage embeddings."""
from contextlib import closing
from functools import lru_cache
import json
from pathlib import Path
import re
import threading

from .build import digest
from .encoding import Encoder
from .store import connect, search


class HybridSearch:
    def __init__(self, folder, artifact):
        import numpy as np
        folder = Path(folder)
        manifest = json.loads((folder/'manifest.json').read_text())
        if digest(artifact) != manifest['artifact_sha256']:
            raise ValueError('Embedding bundle does not match artifact')
        # Only the encoder and vectors are needed, never the cross-encoder.
        for name in ('model.onnx', 'tokenizer.json', 'vectors.npy', 'ids.json'):
            if digest(folder/name) != manifest['files'][name]:
                raise ValueError('Embedding checksum mismatch: '+name)
        self.encoder = Encoder(folder)
        self.vectors = np.load(folder/'vectors.npy', mmap_mode='r', allow_pickle=False)
        self.ids = np.asarray(json.loads((folder/'ids.json').read_text()), dtype=np.int64)
        self.count = manifest['document_count']
        if self.vectors.shape != (len(self.ids), 384) or set(self.ids) != set(range(self.count)):
            raise ValueError('Incomplete embedding coverage')
        self.artifact = Path(artifact)
        self.lock = threading.Lock()

    def search(self, terms):
        with self.lock:
            return list(self._cached(tuple(terms)))

    @lru_cache(maxsize=32)
    def _cached(self, terms):
        import numpy as np
        query = ' '.join(t.strip() for t in terms if t.strip())
        if not re.search(r'\w', query):
            return ()
        with closing(connect(self.artifact)) as db:
            lexical = search(db, 'court', terms, limit=None)
            weights = {h['case_id']: h['score']/lexical[0]['score'] for h in lexical}
            lexical_candidates = {h['case_id'] for h in lexical[:100]}
            scores = np.full(self.count, -1., dtype=np.float32)
            np.maximum.at(scores, self.ids, self.vectors @ self.encoder.encode([query])[0])
            # Each retriever nominates candidates independently. Do not discard
            # a lexical hit merely because it misses a semantic relative cutoff.
            semantic_candidates = set(int(i) for i in np.argsort(-scores, kind='stable')[:100]
                                      if scores[i] > 0)
            # An entirely unfamiliar query needs stronger semantic evidence.
            if not lexical and float(scores.max()) < .50:
                return ()
            hits = []
            for i, payload in db.execute("SELECT id,payload FROM documents WHERE corpus='court'"):
                doc = json.loads(payload)
                if i not in semantic_candidates and doc['case_id'] not in lexical_candidates:
                    continue
                cosine = max(0., float(scores[i]))
                lexical_score = weights.get(doc['case_id'], 0.)
                hits.append(dict(doc, score=.9*cosine+.1*lexical_score,
                                 semantic_score=cosine, lexical_score=lexical_score))
        hits.sort(key=lambda h: (-h['score'], h['case_id']))
        if not hits or hits[0]['score'] < CHART_CUTOFF:
            return ()
        return tuple(hits)


# A provisional score threshold, not a calibrated probability of relevance.
CHART_CUTOFF = .30


def chart_matches(hits):
    return [h for h in hits if h['score'] >= CHART_CUTOFF]
