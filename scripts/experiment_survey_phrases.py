"""Offline phrase expansion experiment; never modifies serving code or artifacts."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import re
from unittest.mock import patch

import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

from scvpublic.build import digest
from scvpublic.encoding import Encoder
from scvpublic.store import connect, search
from scvpublic.survey_search import SurveySearch, weighted_lexical
from scripts.evaluate_survey_synonyms import compare


def phrases(text):
    # Contiguous phrases only; deleting stopwords first would invent phrases.
    for segment in re.split(r'[.!?;:\n]+', text.lower()):
        words = re.findall(r'(?u)\b[a-z]+\b', segment)
        for width in (1, 2, 3):
            for i in range(len(words)-width+1):
                span = words[i:i+width]
                if all(len(w) > 2 and w not in ENGLISH_STOP_WORDS for w in span):
                    yield ' '.join(span)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact', type=Path, required=True)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--weighted', action='store_true')
    a = p.parse_args()
    relevance_path = Path('data/evaluation/survey-relevance-development.json')
    pairs_path = Path('data/evaluation/survey-synonyms.json')
    judgments = json.loads(relevance_path.read_text())['cases']
    pairs = json.loads(pairs_path.read_text())['pairs']
    encoder = Encoder(a.bundle)
    engine = SurveySearch(a.bundle, a.artifact, encoder)
    with closing(connect(a.artifact)) as db:
        docs = [json.loads(payload) for payload, in db.execute(
            "SELECT payload FROM documents WHERE corpus != 'court' ORDER BY corpus,id")]
    # Retain eight informative phrases per question, independent of test queries.
    vectorizer = TfidfVectorizer(analyzer=phrases, dtype=np.float32)
    matrix = vectorizer.fit_transform(d.get('title', '')+'. '+d['question'] for d in docs)
    names = vectorizer.get_feature_names_out()
    selected = set()
    for row in matrix:
        ranked = sorted(zip(row.indices, row.data), key=lambda v: (-v[1], names[v[0]]))
        selected.update(i for i, _ in ranked[:8])
    vocabulary = sorted(names[list(selected)].tolist())
    vectors = np.concatenate([encoder.encode(vocabulary[i:i+16]) for i in range(0,len(vocabulary),16)])
    queries = sorted({c['query'] for c in judgments} | {q for pair in pairs for q in pair['queries']} |
                     {'immigration', 'civil rights', 'climate change', 'zzzznomatchzzzz'})
    expansions, before, after = {}, {}, {}
    for query in queries:
        scores = vectors @ encoder.encode([query])[0]
        order = np.argsort(-scores, kind='stable')[:5]
        # Fixed before viewing results. Similarity is not a synonym probability.
        accepted = [int(i) for i in order if scores[i] >= max(.65, .90*float(scores.max()))
                    and vocabulary[i] != query.lower()]
        additions = [vocabulary[i] for i in accepted]
        expansions[query] = dict(added=additions, nearest=[dict(phrase=vocabulary[i], score=float(scores[i])) for i in order])
        before[query] = engine.search([query])
        engine._cached.cache_clear()
        # Only lexical evidence changes. Encode the original query, preserving
        # semantic guards and all deployed ranking/acceptance rules.
        def expanded_search(db, corpus, terms, **kwargs):
            return search(db, corpus, list(terms)+additions, **kwargs)
        if a.weighted:
            def lexical_weights(db, corpus, terms):
                return weighted_lexical(db, corpus, terms, [(vocabulary[i], float(scores[i])) for i in accepted])
            with patch.object(engine, 'lexical_weights', side_effect=lexical_weights):
                after[query] = engine.search([query])
        else:
            with patch('scvpublic.survey_search.search', side_effect=expanded_search):
                after[query] = engine.search([query])
        engine._cached.cache_clear()
    def codes(results, query, corpus):
        return [h['code'] for h in results[query].get(corpus, [])]
    summaries = {}
    for label, results in [('before', before), ('after', after)]:
        cases=[]
        for c in judgments:
            hits=set(codes(results,c['query'],c['corpus']))
            cases.append(dict(query=c['query'],corpus=c['corpus'],
                selected=sorted(hits),missed=sorted(set(c['relevant'])-hits),
                irrelevant=sorted(set(c['irrelevant'])&hits),
                unjudged=sorted(hits-set(c['relevant'])-set(c['irrelevant']))))
        pair_results=[]
        for pair in pairs:
            left,right=[codes(results,q,pair['corpus']) for q in pair['queries']]
            pair_results.append(dict(pair,left=left,right=right,
                **compare(left,right,pair['relevant'],pair['irrelevant'])))
        summaries[label]=dict(missed=sum(len(c['missed']) for c in cases),
            irrelevant=sum(len(c['irrelevant']) for c in cases),
            pair_irrelevant=sum(len(p['irrelevant_left'])+len(p['irrelevant_right']) for p in pair_results),
            pair_missed=sum(len(p['missed_left'])+len(p['missed_right']) for p in pair_results),
            cases=cases,pairs=pair_results)
    no_regression = all(summaries['after'][metric] <= summaries['before'][metric]
                        for metric in ('missed', 'irrelevant', 'pair_irrelevant', 'pair_missed'))
    report=dict(no_labeled_regressions=no_regression, status='offline development experiment; not deployed',phrase_count=len(vocabulary),
        vector_bytes=vectors.nbytes,parameters=dict(phrases_per_document=8,max_expansions=5,
        absolute_similarity=.65,relative_similarity=.90,weighted=a.weighted),expansions=expansions,
        evaluation=summaries,rankings={q:{label:{c:[{k:h[k] for k in ('code','score','semantic_score','lexical_score')} for h in hs] for c,hs in values[q].items()} for label,values in [('before',before),('after',after)]} for q in queries},results={q:{label:{c:[h['code'] for h in hs] for c,hs in values[q].items()}
        for label,values in [('before',before),('after',after)]} for q in queries},
        sources={str(path):digest(path) for path in [a.artifact,a.bundle/'manifest.json',
        relevance_path,pairs_path,Path(__file__),Path('scvpublic/survey_search.py')]},
        limitations=['Development labels are partial and not held out.',
        'Phrase similarity does not establish equivalence.',
        'Unjudged results require review, even if labeled error counts improve.'])
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(phrases=len(vocabulary),vectors_bytes=vectors.nbytes,
        evaluation={k:{m:v[m] for m in ['missed','irrelevant','pair_missed','pair_irrelevant']} for k,v in summaries.items()})))
    for q in queries:
        print(q, '=>', expansions[q]['added'])


if __name__ == '__main__':
    main()
