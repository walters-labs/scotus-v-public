"""One offline dual-source trial; fixed 75% original / 25% official summary."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import time
import numpy as np
from scvpublic.build import digest
from scvpublic.hybrid import HybridSearch, CHART_CUTOFF
from scvpublic.store import connect, search


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=Path('artifacts/court-dual-source-v1'))
    args = p.parse_args()
    if args.output.exists(): raise FileExistsError(args.output)
    artifact = Path('artifacts/affirmative-action.sqlite')
    base = Path('artifacts/semantic-affirmative-action')
    candidate = Path('artifacts/official-syllabi-v5/bundle')
    frozen = Path('artifacts/court-passage-support-v1/baseline.json')
    benchmark = Path('data/evaluation/court-search-benchmark-v2.json')
    baseline = json.loads(frozen.read_text())
    for path in (artifact, base/'manifest.json', Path('scvpublic/hybrid.py')):
        assert baseline['provenance'][str(path)] == digest(path), path
    args.output.mkdir(parents=True)
    protocol = dict(rule='Semantic = 0.75 original maximum passage cosine + 0.25 official summary maximum passage cosine for the 196 replaced cases; other sources unchanged. Same top-100 lexical/semantic nomination, 0.1 lexical/0.9 semantic weighting and 0.30 cutoff. No parameter sweep.',
        limitations='Previously inspected, partial judgments; not blind validation. Original sources are primarily syllabi, with full-opinion fallback. This trial supplements only the 196 official cases with validated candidate syllabi.',
        provenance={str(x):digest(x) for x in (artifact, base/'manifest.json', candidate/'manifest.json', frozen, benchmark, Path(__file__), Path('scvpublic/hybrid.py'))})
    (args.output/'protocol.json').write_text(json.dumps(protocol, indent=2)+'\n')
    original = HybridSearch(base, artifact)
    revised = HybridSearch(candidate, artifact)
    spec = json.loads(benchmark.read_text())
    with closing(connect(artifact)) as db:
        docs = {i:json.loads(payload) for i,payload in db.execute("SELECT id,payload FROM documents WHERE corpus='court'")}
    bs = json.loads((base/'sources.json').read_text()); cs = json.loads((candidate/'sources.json').read_text())
    changed = np.array([i for i,d in docs.items() if bs[d['case_id']] != cs[d['case_id']]], dtype=np.int64)
    assert len(changed) == 196
    results = {}; rankings = {}; times = []
    for query, review in spec['queries'].items():
        start = time.perf_counter()
        vector = original.encoder.encode([query])[0]
        old_scores = np.full(original.count, -1., dtype=np.float32)
        new_scores = np.full(original.count, -1., dtype=np.float32)
        np.maximum.at(old_scores, original.ids, original.vectors @ vector)
        np.maximum.at(new_scores, revised.ids, revised.vectors @ vector)
        scores = old_scores.copy()
        scores[changed] = .75*old_scores[changed]+.25*new_scores[changed]
        with closing(connect(artifact)) as db:
            lexical = search(db, 'court', [query], limit=None)
        weights = {h['case_id']:h['score']/lexical[0]['score'] for h in lexical}
        lexical_candidates = {h['case_id'] for h in lexical[:100]}
        semantic_candidates = set(int(i) for i in np.argsort(-scores, kind='stable')[:100] if scores[i]>0)
        hits = []
        if lexical or float(scores.max()) >= .50:
            for i,d in docs.items():
                if i not in semantic_candidates and d['case_id'] not in lexical_candidates: continue
                cosine = max(0., float(scores[i])); lex = weights.get(d['case_id'], 0.)
                hits.append(dict(d,score=.9*cosine+.1*lex,semantic_score=cosine,lexical_score=lex))
        hits.sort(key=lambda h:(-h['score'],h['case_id']))
        if hits and hits[0]['score'] < CHART_CUTOFF: hits=[]
        times.append(time.perf_counter()-start)
        before = baseline['queries'][query]
        b = {h['case_id'] for h in before if h['score']>=CHART_CUTOFF}
        a = {h['case_id'] for h in hits if h['score']>=CHART_CUTOFF}
        direct = {k for k,v in review['court'].items() if v['label']=='direct'}
        bad = {k for k,v in review['court'].items() if v['label']=='irrelevant'}
        lost_top = ({h['case_id'] for h in before[:10]}-{h['case_id'] for h in hits[:10]})&direct
        ranks = []
        for key in sorted(lost_top):
            ranks.append(dict(case_id=key,before=next(i+1 for i,h in enumerate(before) if h['case_id']==key),
                after=next((i+1 for i,h in enumerate(hits) if h['case_id']==key),None)))
        results[query] = dict(baseline_chart=len(b),candidate_chart=len(a),lost_direct=sorted((b-a)&direct),
            new_direct=sorted((a-b)&direct),new_irrelevant=sorted((a-b)&bad),removed_irrelevant=sorted((b-a)&bad),
            lost_direct_top10=sorted(lost_top),rank_regressions=ranks)
        rankings[query] = hits
    gate = dict(no_lost_direct=not any(r['lost_direct'] for r in results.values()),
        no_new_irrelevant=not any(r['new_irrelevant'] for r in results.values()),
        no_lost_direct_top10=not any(r['lost_direct_top10'] for r in results.values()),
        removes_known_irrelevant=any(r['removed_irrelevant'] for r in results.values()))
    report = dict(protocol=protocol,gate=gate,passes=all(gate.values()),queries=results,
        local_p95_seconds=float(np.percentile(times,95)),timing_scope='Offline process with both bundles and redundant unchanged vectors; not optimized deployment memory/latency.')
    (args.output/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    (args.output/'rankings.json').write_text(json.dumps(rankings,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__': main()
