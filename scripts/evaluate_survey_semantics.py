"""Exploratory cross-source semantic filters; not a calibrated relevance classifier."""
import json
from pathlib import Path

from scvpublic.build import digest


rankings_path = Path('artifacts/survey-semantic-rankings.json')
judgments_path = Path('data/evaluation/survey-relevance-development.json')
rankings = json.loads(rankings_path.read_text())
assert rankings['judgments_sha256'] == digest(judgments_path)
judgments = json.loads(judgments_path.read_text())
variants = {}
# Prespecified diagnostic grid; do not promote the best row as held-out evidence.
for global_ratio in [.5, .6, .7]:
    for local_ratio in [.7, .8, .9]:
        cases = []
        for case in judgments['cases']:
            query, corpus = case['query'], case['corpus']
            all_scores = [hit['score'] for key, hits in rankings['results'].items()
                          if key.split(':',1)[1] == query for hit in hits]
            hits = rankings['results'][corpus+':'+query]
            threshold = max(.3, global_ratio*max(all_scores), local_ratio*hits[0]['score'])
            selected = [h['code'] for h in hits if h['score'] >= threshold]
            cases.append(dict(query=query, corpus=corpus, threshold=threshold, selected=selected,
                missed_relevant=sorted(set(case['relevant'])-set(selected)),
                retrieved_irrelevant=sorted(set(case['irrelevant']) & set(selected)),
                unjudged=sorted(set(selected)-set(case['relevant'])-set(case['irrelevant']))))
        key = f'global-{global_ratio}:local-{local_ratio}'
        variants[key] = dict(cases=cases,
            missed_relevant=sum(len(c['missed_relevant']) for c in cases),
            retrieved_irrelevant=sum(len(c['retrieved_irrelevant']) for c in cases))
        print(key, variants[key]['missed_relevant'], variants[key]['retrieved_irrelevant'])
Path('artifacts/survey-semantic-filter-evaluation.json').write_text(json.dumps(dict(
    status='development parameter sweep; not selected for deployment', absolute_floor=.3,
    variants=variants, sources={str(p):digest(p) for p in [rankings_path,judgments_path,Path(__file__)]},
    limitations=['Thresholds are exploratory, not calibrated probabilities.',
        'Changing available survey sources can change cross-source filtering.',
        'Partial same-reviewer development labels cannot establish general accuracy.',
        'Do not select a winning setting without independent query review.']),indent=2)+'\n')
