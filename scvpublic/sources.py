"""Verified source texts for offline embedding generation."""
from collections import defaultdict
from contextlib import closing
import csv
import json
import re
from pathlib import Path
import pyarrow as pa
from .build import digest
from .casesumm import FILES, citation_key, resolve
from .store import connect


# A short source is not necessarily legally unimportant; prefer its fuller
# opinion when it lacks enough text to describe the dispute. No topic rules.
MIN_SUMMARY_WORDS = 40
SOURCE_POLICY = 'summary-min-40-words-or-longer-opinion-v1'


def select_text(syllabus, opinion):
    syllabus, opinion = (syllabus or '').strip(), (opinion or '').strip()
    words = lambda text: len(re.findall(r"\b[\w’'-]+\b", text))
    if not syllabus:
        return opinion, 'opinion_fallback'
    if words(syllabus) < MIN_SUMMARY_WORDS and words(opinion) > words(syllabus):
        return opinion, 'short_syllabus_opinion_fallback'
    return syllabus, 'syllabus'


def source_texts(artifact, official=Path('data/processed/modern/official.json')):
    with closing(connect(artifact)) as db:
        docs = [dict(json.loads(p), doc_id=i) for i,p in db.execute("SELECT id,payload FROM documents WHERE corpus='court' ORDER BY id")]
        source_hashes = json.loads(db.execute("SELECT value FROM meta WHERE key='sources'").fetchone()[0])
    wanted = {d['case_id'] for d in docs}
    citations, dockets = defaultdict(list), defaultdict(list)
    scdb = Path('data/raw/scdb-2026/SCDB_2026_01_caseCentered_Citation.csv')
    if digest(scdb) != source_hashes[str(scdb.resolve())]: raise ValueError('SCDB checksum mismatch')
    with scdb.open(encoding='utf-8-sig') as stream:
        for row in csv.DictReader(stream):
            citations[citation_key(row['usCite'])].append(row)
            dockets[(row['term'], row['docket'])].append(row)
    texts = {}
    origins = {}
    for name, checksum in FILES.items():
        path = Path('data/raw/casesumm')/name
        if digest(path) != checksum: raise ValueError('CaseSumm checksum mismatch')
        with pa.memory_map(str(path), 'r') as stream:
            for batch in pa.ipc.open_stream(stream):
                for record in batch.to_pylist():
                    doc, _ = resolve(record['citation'], citations, dockets)
                    if doc and doc['case_id'] in wanted:
                        texts[doc['case_id']], origins[doc['case_id']] = select_text(
                            record['syllabus'], record['opinion'])
    official = Path(official)
    if digest(official) != source_hashes.get(str(official.resolve())):
        raise ValueError('Supplement checksum mismatch or source absent from artifact manifest')
    for record in json.loads(official.read_text())['records']:
        if record.get('unscored'): key = record['case_id']
        else:
            doc, _ = resolve(record['citation'], citations, dockets)
            key = doc['case_id'] if doc else None
        if key in wanted and key not in texts:
            texts[key] = record['opinion']
            origins[key] = 'official_opinion_fallback'
    if set(texts) != wanted: raise ValueError('Incomplete summary coverage')
    return docs, texts, origins

