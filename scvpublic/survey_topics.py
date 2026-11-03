"""Optional routing through reviewed survey topic metadata."""
from contextlib import closing
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from .build import digest
from .store import connect


def topic_contains_query(topic, query):
    """Match a whole phrase, allowing spacing/hyphen variants, not substrings.

    All query words must be covered. A modifier absent from the label therefore
    keeps a specific policy query on the normal retrieval path.
    """
    def words(text):
        return re.findall(r'[^\W_]+', unicodedata.normalize('NFKC', text).casefold())
    wanted = ''.join(words(query))
    tokens = words(topic)
    return bool(wanted) and any(''.join(tokens[start:end]) == wanted
        for start in range(len(tokens)) for end in range(start+1, len(tokens)+1))


def topic_components(topic):
    return re.split(r'\s+and\s+|[,;/]', topic, flags=re.I)


def is_parent_topic(topic, query):
    """Retain a baseline hit when its complete topic is named in the query."""
    return any(topic_contains_query(query, part) for part in topic_components(topic))


class TopicSearch:
    """Use explicit topic membership only when two reviewed families support it.

    Reviewed questions outside the matched topic or its parents are excluded.
    Unreviewed questions retain their baseline behavior. Specific/unknown topics
    and multiple-input searches retain the entire baseline result unchanged.
    """
    def __init__(self, baseline, descriptions, checksum=None):
        descriptions = Path(descriptions)
        if checksum is not None and digest(descriptions) != checksum:
            raise ValueError('Topic metadata checksum mismatch')
        specification = json.loads(descriptions.read_text())
        if specification['version'] != 1:
            raise ValueError('Unsupported topic metadata')
        self.baseline = baseline
        self.entries = {}
        with closing(connect(baseline.artifact)) as db:
            rows = [(i, source, json.loads(db.execute(
                'SELECT payload FROM documents WHERE corpus=? AND id=?', (source, doc)).fetchone()[0]))
                for i, (source, doc) in enumerate(baseline.keys)]
        documents = {(source, doc['code']): (i, doc) for i, source, doc in rows}
        for entry in specification['entries']:
            key = (entry['source'], entry['code'])
            if key in self.entries or key not in documents:
                raise ValueError('Duplicate or missing topic question')
            i, doc = documents[key]
            text = doc.get('title', '')+'\n'+doc['question']
            if hashlib.sha256(text.encode()).hexdigest() != entry['source_text_sha256']:
                raise ValueError('Topic question wording changed')
            if not isinstance(entry['topic'], str) or not entry['topic'].strip():
                raise ValueError('Empty topic label')
            self.entries[key] = dict(index=i, document=doc, topic=entry['topic'])

    def search(self, terms):
        # Share the encoder/search lock; do not hold it while baseline.search
        # acquires the same non-reentrant lock.
        base = self.baseline.search(terms)
        with self.baseline.lock:
            return {source: list(hits) for source, hits in self._route(tuple(terms), base).items()}

    def _route(self, terms, base):
        active = [t.strip() for t in terms if t.strip()]
        if len(active) != 1:
            return base
        matches = self.matching_topics(active[0])
        families = {(source, self.entries[source, code]['document'].get('family', code))
                    for source, code in matches}
        if len(families) < 2:
            return base
        query = active[0]
        # A lone word inside a longer label is not enough to classify scope:
        # e.g. a broad word may name only one part of a compound policy label.
        # Permit single-word queries only when they name a complete component.
        words = re.findall(r'[^\W_]+', unicodedata.normalize('NFKC', query).casefold())
        if len(words) == 1 and not any(
            ''.join(re.findall(r'[^\W_]+', part.casefold())) == words[0]
            for key in matches
            for part in topic_components(self.entries[key]['topic'])):
            return base
        scores = self.baseline.vectors @ self.baseline.encoder.encode([query])[0]
        result = {}
        with closing(connect(self.baseline.artifact)) as db:
            for source, hits in base.items():
                # Missing metadata means unknown, not irrelevant.
                selected = {h['code']: h for h in hits if (source, h['code']) not in self.entries
                    or is_parent_topic(self.entries[source,h['code']]['topic'],query)}
                keys = sorted(key for key in matches if key[0] == source)
                weights = self.baseline.lexical_weights(db, source, terms) if keys else {}
                for key in keys:
                    entry = self.entries[key]
                    semantic = float(scores[entry['index']])
                    lexical = weights.get(key[1], 0.)
                    selected[key[1]] = dict(entry['document'], score=.9*semantic+.1*lexical,
                        semantic_score=semantic, lexical_score=lexical,
                        topic_match=entry['topic'])
                result[source] = sorted(selected.values(), key=lambda h: (-h['score'],h['code']))[:10]
        return result

    @lru_cache(maxsize=32)
    def matching_topics(self, query):
        return frozenset(key for key, entry in self.entries.items()
                         if topic_contains_query(entry['topic'], query))
