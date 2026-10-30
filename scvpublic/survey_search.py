"""Optional survey retrieval using the already-loaded court encoder."""
from contextlib import closing
from functools import lru_cache
import json
from pathlib import Path
import re
import threading

from .build import digest
from .store import connect, search

SURVEY_FILES = ('survey-vectors.npy', 'survey-ids.json')


def weighted_lexical(db, corpus, terms, expansions):
    original = search(db, corpus, terms, limit=None)
    base = {h['code']: h['score'] for h in original}
    additions = {}
    scale = max(base.values(), default=0.)
    for phrase, confidence in expansions:
        hits = search(db, corpus, [phrase], limit=None)
        scale = max(scale, max((h['score'] for h in hits), default=0.))
        for hit in hits:
            code = hit['code']
            # Multiple near-identical expansions must not accumulate evidence.
            additions[code] = max(additions.get(code, 0.), confidence*hit['score'])
    # Normalize against unweighted evidence so confidence does not cancel when
    # the original query has no lexical hits (the synonym-only case).
    return {code: max(base.get(code, 0.), additions.get(code, 0.))/scale
            for code in base.keys() | additions.keys()} if scale else {}


class SurveySearch:
    def __init__(self, folder, artifact, encoder):
        import numpy as np
        folder = Path(folder)
        manifest = json.loads((folder/'manifest.json').read_text())
        if digest(artifact) != manifest['artifact_sha256']:
            raise ValueError('Survey embeddings do not match artifact')
        for name in SURVEY_FILES:
            if digest(folder/name) != manifest['files'].get(name):
                raise ValueError('Survey embedding checksum mismatch: '+name)
        self.vectors = np.load(folder/SURVEY_FILES[0], mmap_mode='r', allow_pickle=False)
        self.keys = json.loads((folder/SURVEY_FILES[1]).read_text())
        with closing(connect(artifact)) as db:
            expected = [list(row) for row in db.execute(
                "SELECT corpus,id FROM documents WHERE corpus != 'court' ORDER BY corpus,id")]
        if self.keys != expected or self.vectors.shape != (len(expected), 384):
            raise ValueError('Incomplete survey embedding coverage')
        if not np.isfinite(self.vectors).all():
            raise ValueError('Nonfinite survey embeddings')
        self.encoder, self.artifact = encoder, artifact
        self.phrase_vectors = None
        if manifest.get('survey_phrase_expansion'):
            for name in ('survey-phrases.json', 'survey-phrase-vectors.npy'):
                if digest(folder/name) != manifest['files'].get(name):
                    raise ValueError('Phrase checksum mismatch: '+name)
            self.phrases = json.loads((folder/'survey-phrases.json').read_text())
            self.phrase_vectors = np.load(folder/'survey-phrase-vectors.npy', mmap_mode='r', allow_pickle=False)
            if self.phrase_vectors.shape != (len(self.phrases), 384) or not np.isfinite(self.phrase_vectors).all():
                raise ValueError('Invalid phrase vectors')
        self.lock = threading.Lock()

    def search(self, terms):
        with self.lock:
            return {source: list(hits) for source, hits in self._cached(tuple(terms)).items()}

    @lru_cache(maxsize=32)
    def expansions(self, terms):
        if self.phrase_vectors is None or not self.phrases:
            return ()
        import numpy as np
        query = ' '.join(t.strip() for t in terms if t.strip())
        if not re.search(r'\w', query):
            return ()
        scores = self.phrase_vectors @ self.encoder.encode([query])[0]
        order = np.argsort(-scores, kind='stable')[:5]
        return tuple((self.phrases[i], float(scores[i])) for i in order
                     if scores[i] >= max(.65, .90*float(scores.max())) and self.phrases[i] != query.lower())

    def lexical_weights(self, db, source, terms):
        if self.phrase_vectors is not None:
            return weighted_lexical(db, source, terms, self.expansions(tuple(terms)))
        hits = search(db, source, terms, limit=None)
        return {h['code']: h['score']/hits[0]['score'] for h in hits}

    @lru_cache(maxsize=32)
    def _cached(self, terms):
        query = ' '.join(term.strip() for term in terms if term.strip())
        corpora = sorted({source for source, _ in self.keys})
        result = {source: () for source in corpora}
        if not re.search(r'\w', query) or not self.keys:
            return result
        scores = self.vectors @ self.encoder.encode([query])[0]
        # A weak source must not nominate an irrelevant question just because
        # it is that source's best match. These are provisional relevance rules,
        # not probabilities; the cross-source floor depends on corpus coverage.
        floor = max(.30, .60 * float(scores.max()))
        with closing(connect(self.artifact)) as db:
            for source in corpora:
                weights = self.lexical_weights(db, source, terms)
                hits = []
                for i, (corpus, doc) in enumerate(self.keys):
                    if corpus != source or float(scores[i]) < floor:
                        continue
                    payload = json.loads(db.execute(
                        'SELECT payload FROM documents WHERE corpus=? AND id=?', (source, doc)).fetchone()[0])
                    semantic = float(scores[i])
                    lexical_score = weights.get(payload['code'], 0.)
                    if not lexical_score and semantic < .40:
                        continue
                    hits.append(dict(payload, score=.9*semantic+.1*lexical_score,
                                     semantic_score=semantic, lexical_score=lexical_score))
                hits.sort(key=lambda h: (-h['score'], h['code']))
                if hits:
                    result[source] = tuple(h for h in hits if h['score'] >= .9*hits[0]['score'])[:10]
        return result
