"""Compare bounded title-aware survey rankers without changing serving behavior."""
import argparse
import json
from pathlib import Path
import numpy as np
from scvpublic.build import digest
from scvpublic.hybrid import HybridSearch
from scvpublic.survey_search import SurveySearch
from scvpublic.store import connect


def run(artifact, bundle, output):
    engine = HybridSearch(bundle, artifact)
    search = SurveySearch(bundle, artifact, engine.encoder)
    with connect(artifact) as db:
        docs = [json.loads(db.execute('SELECT payload FROM documents WHERE corpus=? AND id=?', key).fetchone()[0]) for key in search.keys]
        titles = [d.get('title') or d['question'] for d in docs]
        vectors = np.concatenate([engine.encoder.encode(titles[i:i+16]) for i in range(0,len(titles),16)])
        cases = json.loads(Path('data/evaluation/survey-relevance-development.json').read_text())['cases']
        for pair in json.loads(Path('data/evaluation/survey-synonyms.json').read_text())['pairs']:
            cases += [dict(pair, query=q) for q in pair['queries']]
        cases += json.loads(Path('data/evaluation/survey-climate-relevance.json').read_text())['cases']
        # Existing suites overlap. Count each judged query/source/document once.
        merged = {}
        for case in cases:
            key = (case['query'].lower(), case['corpus'])
            item = merged.setdefault(key, dict(query=key[0], corpus=key[1], relevant=set(), irrelevant=set()))
            for label in ('relevant', 'irrelevant'):
                item[label].update(case[label])
        cases = list(merged.values())
        known = {(source, d['code']) for (source, _), d in zip(search.keys, docs)}
        for case in cases:
            assert not case['relevant'] & case['irrelevant']
            assert all((case['corpus'], code) in known for code in case['relevant'] | case['irrelevant'])
        configs = [dict(name='baseline')]+[dict(name=f'title-{w}-cutoff-{r}', title_weight=w, cutoff=r, floor_ratio=.6)
            for w in [.35,.7] for r in [.9,.75,.55]]
        configs += [dict(name='title-only-broad', title_weight=1., cutoff=.5, floor_ratio=.45)]
        results = {c['name']:{} for c in configs}
        for query in sorted({c['query'] for c in cases}):
            terms = [query.lower()]
            q = engine.encoder.encode(terms)[0]
            full, title = search.vectors @ q, vectors @ q
            lexical = {s:search.lexical_weights(db,s,terms) for s in sorted({k[0] for k in search.keys})}
            results['baseline'][query] = {s:[d['code'] for d in ds] for s,ds in search.search(terms).items()}
            for config in configs[1:]:
                semantic = (1-config['title_weight'])*full+config['title_weight']*title
                floor = max(.30, config['floor_ratio']*float(semantic.max()))
                selected = {}
                for source in lexical:
                    hits = []
                    for i,((s,_),d) in enumerate(zip(search.keys,docs)):
                        if s != source or semantic[i] < floor:continue
                        lex = lexical[s].get(d['code'],0.)
                        if not lex and semantic[i]<.40:continue
                        hits.append((d['code'],float(.9*semantic[i]+.1*lex)))
                    hits.sort(key=lambda v:(-v[1],v[0]))
                    selected[source] = [c for c,score in hits if score >= config['cutoff']*hits[0][1]][:10] if hits else []
                results[config['name']][query] = selected
    metrics = {}
    for config in configs:
        rows=[]
        for case in cases:
            selected=set(results[config['name']][case['query']].get(case['corpus'],[]))
            rows.append(dict(query=case['query'],corpus=case['corpus'],
                missed=sorted(set(case['relevant'])-selected), false_matches=sorted(set(case['irrelevant'])&selected)))
        metrics[config['name']]=dict(missed=sum(len(r['missed']) for r in rows),false_matches=sum(len(r['false_matches']) for r in rows),cases=rows)
    baseline=results['baseline']
    for name, metric in metrics.items():
        regressions = []
        for case in cases:
            before = set(baseline[case['query']].get(case['corpus'], []))
            after = set(results[name][case['query']].get(case['corpus'], []))
            lost = sorted((before-after) & case['relevant'])
            added = sorted((after-before) & case['irrelevant'])
            if lost or added:
                regressions.append(dict(query=case['query'], corpus=case['corpus'], lost_relevant=lost, added_irrelevant=added))
        target = next(c for c in cases if c['query']=='climate change' and c['corpus']=='ces')
        climate_missing = sorted(target['relevant']-set(results[name]['climate change']['ces']))
        metric.update(regressions=regressions, climate_missing=climate_missing,
                      passes_gate=not regressions and not climate_missing)
    changes={name:{q:{s:dict(added=sorted(set(codes)-set(baseline[q].get(s,[]))),removed=sorted(set(baseline[q].get(s,[]))-set(codes))) for s,codes in sources.items() if set(codes)!=set(baseline[q].get(s,[]))} for q,sources in queries.items()} for name,queries in results.items() if name!='baseline'}
    output.write_text(json.dumps(dict(status='Development experiment; partial judgments, not independent validation',
        gate='Retrieve five judged CES climate matches, lose no baseline judged positives, and add no judged negatives. Unjudged changes still need review.',
        sources={str(p):digest(p) for p in [Path(__file__),Path('data/evaluation/survey-relevance-development.json'),Path('data/evaluation/survey-synonyms.json'),Path('data/evaluation/survey-climate-relevance.json'),Path('scvpublic/survey_search.py')]},
        artifact_sha256=digest(artifact),bundle_manifest_sha256=digest(bundle/'manifest.json'),configs=configs,metrics=metrics,changes=changes,results=results),indent=2)+'\n')
    for name,m in metrics.items():print(name,m['missed'],m['false_matches'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',type=Path,required=True)
    p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.artifact,a.bundle,a.output)
