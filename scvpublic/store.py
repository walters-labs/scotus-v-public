"""Disk-backed inverted TF-IDF index. No corpus or matrix in web RAM."""
import json
from math import fsum, isfinite
import re
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE documents (
 corpus TEXT NOT NULL, id INTEGER NOT NULL, payload TEXT NOT NULL,
 PRIMARY KEY (corpus,id)
) WITHOUT ROWID;
CREATE TABLE postings (
 corpus TEXT NOT NULL, term TEXT NOT NULL, doc INTEGER NOT NULL, weight REAL NOT NULL,
 PRIMARY KEY (corpus,term,doc)
) WITHOUT ROWID;
"""


def connect(path):
    db = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    db.execute('PRAGMA query_only=ON')
    db.execute('PRAGMA cache_size=-8192')
    db.execute('PRAGMA temp_store=FILE')
    return db


def metadata(db):
    return {k: json.loads(v) for k, v in db.execute('SELECT key,value FROM meta')}


def search(db, corpus, terms, limit=10, relative_cutoff=0):
    if limit is not None and (not isinstance(limit, int) or limit < 1):
        raise ValueError('limit must be positive or None')
    if not 0 <= relative_cutoff <= 1:
        raise ValueError('relative_cutoff must be between zero and one')
    # Apply the same vocabulary scoring to every query; no topic-specific rules.
    # UNION ALL preserves repeated-query-word weighting.
    clauses, args = [], []
    for phrase in terms:
        words = re.findall(r'(?u)\b\w+\b', phrase.lower())
        expanded = list(words)
        if corpus in ('court', 'public', 'gss', 'ces', 'pew', 'wvs'):
            expanded += [' '.join(pair) for pair in zip(words, words[1:])]
        for term in expanded:
            clauses.append('SELECT doc,weight FROM postings WHERE corpus=? AND term=?')
            args.extend([corpus, term])
    if not clauses:
        return []
    ranked = ('SELECT doc,SUM(weight) AS score FROM (' +
              ' UNION ALL '.join(clauses) + ') GROUP BY doc')
    sql = ('WITH ranked AS (' + ranked + ') SELECT doc,score FROM ranked '
           'WHERE score >= (SELECT MAX(score) FROM ranked) * ? '
           'ORDER BY score DESC,doc ASC')
    args.append(relative_cutoff)
    if limit is not None:
        sql += ' LIMIT ?'
        args.append(limit)
    hits = db.execute(sql, args).fetchall()
    return [dict(json.loads(db.execute(
        'SELECT payload FROM documents WHERE corpus=? AND id=?', (corpus, doc)
    ).fetchone()[0]), score=score) for doc, score in hits]


def survey_search(db, corpus, terms, limit=10):
    """Experimental strict multiword retrieval, applied identically to surveys.

    Multiply the TF-IDF sum by distinct indexed-word coverage. Retain matches
    within 90% of the best score for multiword queries (20% for single words).
    Missing vocabulary does not require an exact phrase or all-word match.
    """
    words = set(re.findall(r'(?u)\b\w+\b', ' '.join(terms).lower()))
    if not words:
        return []
    indexed = {word for word in words if db.execute(
        'SELECT 1 FROM postings WHERE corpus=? AND term=? LIMIT 1',
        (corpus, word)).fetchone()}
    hits = search(db, corpus, terms, limit=None)
    for hit in hits:
        tokens = set(re.findall(r'(?u)\b\w+\b',
            (hit.get('title', '')+' '+hit['question']).lower()))
        hit['score'] *= len(tokens & indexed) / max(len(indexed), 1)
    hits.sort(key=lambda hit: -hit['score'])
    cutoff = .90 if len(words) > 1 else .20
    best = hits[0]['score'] if hits else 0
    return [hit for hit in hits if hit['score'] > 0 and hit['score'] >= cutoff*best][:limit]


def court_counts(court):
    counts = {}
    for opinion in court:
        weight = opinion.get('score', 1.0)
        if not isfinite(weight) or weight <= 0:
            continue
        for case in opinion['cases']:
            if case['polarity'] is not None:
                counts[case['year']] = counts.get(case['year'], 0) + 1
    return dict(sorted(counts.items()))



def series(court, public):
    # Search supplies TF-IDF scores; unranked legacy callers use unit weights.
    court_values = {}
    for opinion in court:
        weight = opinion.get('score', 1.0)
        if not isfinite(weight) or weight <= 0:
            continue
        for case in opinion['cases']:
            if case['polarity'] is not None:
                court_values.setdefault(case['year'], []).append((case['polarity'], weight))
    sc = {year: fsum(value * weight for value, weight in scores) /
                fsum(weight for _, weight in scores)
          for year, scores in court_values.items()}
    values = survey_items(public)
    po = {year: sum(value for _, value in items) / len(items)
          for year, items in values.items()}
    return dict(sorted(sc.items())), dict(sorted(po.items()))


def survey_items(public):
    """Selected question identities and values, using the same rules as the mean."""
    values = {}
    families = {}
    superseded = {(int(year), code) for q in public for year in q['years']
                  for code in q.get('supersedes', [])}
    for question in public:
        if 'family' in question:
            for year, value in question['years'].items():
                if (int(year), question['code']) in superseded:
                    continue
                key = (int(year), question['family'])
                rank = (question.get('priority', 0), question['code'])
                if key not in families or rank > families[key][0]:
                    families[key] = (rank, value)
            continue
        for year, value in question['years'].items():
            values.setdefault(int(year), []).append((question.get('code'), value))
    for (year, _), (rank, value) in families.items():
        values.setdefault(year, []).append((rank[1], value))
    return dict(sorted(values.items()))
