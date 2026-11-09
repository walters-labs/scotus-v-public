"""Offline 2x2 source-repair experiment using unchanged production search logic."""
import copy
from contextlib import closing
import json
from pathlib import Path

import numpy as np
from scvpublic.build import digest
from scvpublic.hybrid import HybridSearch, CHART_CUTOFF
from scvpublic.store import connect, search
from scripts.evaluate_frozen_court import compare, gates


def identity(path):
    with closing(connect(path)) as db:
        rows = []
        for i, payload in db.execute("SELECT id,payload FROM documents WHERE corpus='court' ORDER BY id"):
            doc = json.loads(payload)
            doc.pop('pdf_pages', None)
            rows.append((i, doc))
        return rows


def diagnostic(engine, query, case_id):
    with closing(connect(engine.artifact)) as db:
        lexical = search(db, 'court', [query], limit=None)
        docs = {json.loads(p)['case_id']: i for i,p in db.execute(
            "SELECT id,payload FROM documents WHERE corpus='court'")}
    scores = np.full(engine.count, -1., dtype=np.float32)
    np.maximum.at(scores, engine.ids, engine.vectors @ engine.encoder.encode([query])[0])
    index = docs[case_id]
    semantic_rank = int(np.flatnonzero(np.argsort(-scores, kind='stable') == index)[0]) + 1
    lexical_rank = next((i+1 for i,h in enumerate(lexical) if h['case_id']==case_id), None)
    lexical_score = next((h['score']/lexical[0]['score'] for h in lexical if h['case_id']==case_id), 0.)
    hits = engine.search([query])
    hit = next((h for h in hits if h['case_id']==case_id), None)
    return dict(lexical_rank=lexical_rank, semantic_rank=semantic_rank,
        lexical_nominated=lexical_rank is not None and lexical_rank <= 100,
        semantic_nominated=semantic_rank <= 100 and float(scores[index]) > 0,
        semantic_score=float(scores[index]), lexical_score=lexical_score,
        returned=hit is not None, chart=hit is not None and hit['score'] >= CHART_CUTOFF,
        returned_score=hit['score'] if hit else None)


def main():
    old=Path('artifacts/scdb-issues.sqlite'); new=Path('artifacts/official-repair-candidate.sqlite')
    ob=Path('artifacts/semantic-scdb-issues'); nb=Path('artifacts/semantic-official-repair-candidate')
    benchmark=Path('data/evaluation/court-search-benchmark-v3.json')
    previous_path=Path('data/evaluation/official-repair-search-comparison.json')
    previous=json.loads(previous_path.read_text())
    for path in (old,new,ob/'manifest.json',nb/'manifest.json',benchmark):
        if digest(path)!=previous['provenance'][str(path)]:
            raise ValueError(f'Previous experiment input changed: {path}')
    if identity(old)!=identity(new):
        raise ValueError('Court document mapping or scoring differs')
    baseline=HybridSearch(ob,old); combined=HybridSearch(nb,new)
    for name in ('model.onnx','tokenizer.json'):
        if digest(ob/name)!=digest(nb/name): raise ValueError('Encoder differs')
    # Deliberately mix only in this offline process after verifying both original
    # bindings and identical document mappings. Never fabricate bundle manifests.
    lexical=copy.copy(combined)
    lexical.vectors, lexical.ids = baseline.vectors, baseline.ids
    semantic=copy.copy(baseline)
    semantic.vectors, semantic.ids = combined.vectors, combined.ids
    engines=dict(baseline=baseline,tfidf_only=lexical,embeddings_only=semantic,combined=combined)
    spec=json.loads(benchmark.read_text())
    rankings={name:{} for name in engines}
    results={name:{} for name in engines if name!='baseline'}
    for query,review in spec['queries'].items():
        for name,engine in engines.items():
            rankings[name][query]=[dict(case_id=h['case_id'],score=h['score']) for h in engine.search([query])]
        for name in results:
            results[name][query]=compare(rankings['baseline'][query],rankings[name][query],review['court'],CHART_CUTOFF)
    saved=json.loads(Path('artifacts/official-repair-rankings.json').read_text())
    for now,then in [('baseline','baseline'),('combined','candidate')]:
        for query,hits in rankings[now].items():
            prior=saved[then][query]
            if [h['case_id'] for h in hits]!=[h['case_id'] for h in prior] or any(
                abs(a['score']-b['score'])>1e-7 for a,b in zip(hits,prior)):
                raise ValueError(f'Failed to reproduce previous {now}: {query}')
    report=dict(status='offline_component_experiment_not_deployed',
        protocol='Fixed 24-query v3 benchmark, unchanged production HybridSearch, weights, nomination limits and chart cutoff. Cross baseline/repaired TF-IDF and passage embeddings in memory; no tuning.',
        query_count=len(spec['queries']), baseline_and_combined_reproduced=True,
        provenance={str(p):digest(p) for p in (old,new,ob/'manifest.json',nb/'manifest.json',benchmark,
            previous_path,Path('artifacts/official-repair-rankings.json'),Path(__file__),Path('scvpublic/hybrid.py'))},
        variants={name:dict(gate=gates(r),queries=r) for name,r in results.items()},
        grants_pass_capital_punishment={name:diagnostic(engine,'capital punishment','2023-056') for name,engine in engines.items()},
        delligatti_capital_punishment={name:diagnostic(engine,'capital punishment','2024-015') for name,engine in engines.items()},
        limitations=['Reuses existing repaired vectors; text, passage-boundary and encoding-batch effects are not separated.',
                    'Frozen labels are not exhaustive; unchanged or unjudged results are not proof of improved relevance.',
                    'No serving artifact, production configuration or survey search changed.'])
    for name in results:
        report['variants'][name]['identical_chart_membership_queries'] = sum(
            {h['case_id'] for h in rankings[name][q] if h['score'] >= CHART_CUTOFF} ==
            {h['case_id'] for h in rankings['baseline'][q] if h['score'] >= CHART_CUTOFF}
            for q in spec['queries'])
    Path('artifacts/official-repair-component-rankings.json').write_text(json.dumps(rankings,indent=2)+'\n')
    Path('data/evaluation/official-repair-components.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(gates={n:r['gate'] for n,r in report['variants'].items()},
        grants_pass=report['grants_pass_capital_punishment']),indent=2))


if __name__=='__main__': main()
