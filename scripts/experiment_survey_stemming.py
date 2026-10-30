"""Offline Snowball expansion experiment; does not change serving search."""
from collections import defaultdict
import argparse
import json
from pathlib import Path
import re

import snowballstemmer
from scvpublic.build import digest
from scvpublic.store import connect, search, survey_search


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--group-variants', action='store_true')
parser.add_argument('--require-all', action='store_true')
args = parser.parse_args()
artifact = Path('artifacts/ces-gapfill-candidate.sqlite')
stemmer = snowballstemmer.stemmer('english')
queries = ['environmental regulation', 'environment', 'gun control', 'birth control',
           'gay marriage', 'abortion', 'immigration', 'death penalty', 'zzzznomatchzzzz']
results = {}
with connect(artifact) as db:
    for corpus in ['public', 'gss', 'ces', 'pew', 'wvs']:
        vocabulary = defaultdict(list)
        for term, in db.execute('SELECT DISTINCT term FROM postings WHERE corpus=?', (corpus,)):
            if ' ' not in term:
                vocabulary[stemmer.stemWord(term)].append(term)
        for query in queries:
            words = re.findall(r'(?u)\b\w+\b', query.lower())
            stems = set(stemmer.stemWords(words))
            indexed = stems & vocabulary.keys()
            alternatives = sorted({term for stem in stems for term in vocabulary.get(stem, [])} - set(words))
            hits = search(db, corpus, [query]+alternatives, limit=None)
            if args.group_variants:
                scores = defaultdict(float)
                for stem in indexed:
                    family = vocabulary[stem]
                    placeholders = ','.join('?' for _ in family)
                    for doc, weight in db.execute(
                        f'SELECT doc,MAX(weight) FROM postings WHERE corpus=? AND term IN ({placeholders}) GROUP BY doc',
                        [corpus]+family):
                        scores[doc] += weight
                for phrase in [' '.join(pair) for pair in zip(words, words[1:])]:
                    for doc, weight in db.execute('SELECT doc,weight FROM postings WHERE corpus=? AND term=?', (corpus, phrase)):
                        scores[doc] += weight
                hits = [dict(json.loads(db.execute('SELECT payload FROM documents WHERE corpus=? AND id=?',
                    (corpus, doc)).fetchone()[0]), score=weight) for doc, weight in scores.items()]
            for hit in hits:
                tokens = re.findall(r'(?u)\b\w+\b', (hit.get('title', '')+' '+hit['question']).lower())
                matched = set(stemmer.stemWords(tokens)) & indexed
                hit['score'] *= len(matched)/max(len(indexed), 1)
                if args.require_all and not stems <= set(stemmer.stemWords(tokens)):
                    hit['score'] = 0
            hits.sort(key=lambda h: -h['score'])
            best = hits[0]['score'] if hits else 0
            cutoff = .9 if len(set(words)) > 1 else .2
            selected = [h for h in hits if h['score'] > 0 and h['score'] >= cutoff*best][:10]
            results[corpus+':'+query] = dict(expansion=alternatives,
                before=[h['code'] for h in survey_search(db, corpus, [query])],
                after=[h['code'] for h in selected],
                questions=[h['question'] for h in selected])
report = dict(status='offline experiment; not deployed', group_variants=args.group_variants, require_all=args.require_all, stemmer='snowballstemmer==3.0.1 English',
    artifact_sha256=digest(artifact), script_sha256=digest(Path(__file__)), results=results,
    limitations=['Word-form similarity does not establish topic relevance.',
                 'Vocabulary expansion changes score calibration; review regressions before adoption.'])
output = 'artifacts/survey-stemming-grouped-experiment.json' if args.group_variants else 'artifacts/survey-stemming-experiment.json'
if args.require_all:
    output = output.replace('.json', '-all-terms.json')
Path(output).write_text(json.dumps(report, indent=2)+'\n')
for key, row in results.items():
    if row['before'] != row['after']:
        print(key, row['before'], '=>', row['after'])
