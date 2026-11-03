"""Offline survey-only reranking experiment; never imported by the Flask app."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import resource
import sys
import time

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from scvpublic.build import digest
from scvpublic.encoding import Encoder
from scvpublic.store import connect
from scvpublic.survey_search import SurveySearch


class Reranker:
    def __init__(self, folder):
        manifest = json.loads((folder/'manifest.json').read_text())
        for name, checksum in manifest['files'].items():
            if digest(folder/name) != checksum:
                raise ValueError('Reranker checksum mismatch: '+name)
        self.tokenizer = Tokenizer.from_file(str(folder/'tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=512)
        self.tokenizer.enable_padding()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        options.enable_cpu_mem_arena = False
        options.enable_mem_pattern = False
        self.session = ort.InferenceSession(str(folder/'model.onnx'), sess_options=options,
                                           providers=['CPUExecutionProvider'])

    def score(self, query, texts):
        values = []
        for start in range(0, len(texts), 4):
            encoded = self.tokenizer.encode_batch([(query, text) for text in texts[start:start+4]])
            inputs = {name: np.array([getattr(e, attr) for e in encoded], dtype=np.int64)
                      for name, attr in [('input_ids','ids'), ('attention_mask','attention_mask'),
                                         ('token_type_ids','type_ids')]}
            values.extend(self.session.run(None, inputs)[0].reshape(-1).tolist())
        if not np.isfinite(values).all():
            raise ValueError('Nonfinite reranker score')
        return values


def peak_mib():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if sys.platform=='darwin' else 1024)


def judgments():
    paths = [Path('data/evaluation')/f for f in ['survey-relevance-development.json',
        'survey-climate-relevance.json', 'survey-description-checks.json', 'survey-synonyms.json']]
    cases = []
    for path in paths[:-1]:
        cases.extend(json.loads(path.read_text())['cases'])
    for pair in json.loads(paths[-1].read_text())['pairs']:
        cases.extend(dict(pair, query=q) for q in pair['queries'])
    merged = {}
    for case in cases:
        key = (case['query'].lower(), case['corpus'])
        entry = merged.setdefault(key, dict(relevant=set(), irrelevant=set()))
        for label in entry:
            entry[label].update(case[label])
    return merged, paths


def evaluate(args):
    started = time.perf_counter()
    encoder = Encoder(args.bundle)
    search = SurveySearch(args.bundle, args.artifact, encoder)
    model = Reranker(args.model)
    checks, paths = judgments()
    with closing(connect(args.artifact)) as db:
        documents = [json.loads(db.execute('SELECT payload FROM documents WHERE corpus=? AND id=?', k).fetchone()[0]) for k in search.keys]
    keys = [(source, d['code']) for (source, _), d in zip(search.keys, documents)]
    lookup = {key:i for i,key in enumerate(keys)}
    for (_, source), case in checks.items():
        assert not case['relevant'] & case['irrelevant']
        assert all((source,c) in lookup for c in case['relevant']|case['irrelevant'])
    results, requests = {}, []
    queries = sorted({q for q,_ in checks}|{'zzzznomatchzzzz'})
    for query in queries:
        begin = time.perf_counter()
        baseline = search.search([query])
        similarities = search.vectors @ encoder.encode([query])[0]
        with closing(connect(args.artifact)) as db:
            weights = {s:search.lexical_weights(db,s,[query]) for s in sorted({s for s,_ in keys})}
        # Broad nominations have no acceptance floor; the cross-encoder makes
        # the final decision. Never force judged positives into the pool.
        semantic = sorted(range(len(keys)), key=lambda i:(-float(similarities[i]), keys[i]))[:60]
        lex_scores = [weights[s].get(c,0.) for s,c in keys]
        lexical = sorted((i for i,v in enumerate(lex_scores) if v>0), key=lambda i:(-lex_scores[i],keys[i]))[:40]
        baseline_ids = {lookup[s,d['code']] for s,hits in baseline.items() for d in hits}
        selected = sorted(set(semantic)|set(lexical)|baseline_ids)
        texts = [documents[i].get('search_text') or documents[i].get('title','')+'. '+documents[i]['question'] for i in selected]
        rerank_start = time.perf_counter()
        scores = model.score(query,texts)
        inference = time.perf_counter()-rerank_start
        rows = [dict(source=keys[i][0], code=keys[i][1], logit=score,
                     semantic=float(similarities[i]), question=documents[i]['question']) for i,score in zip(selected,scores)]
        rows.sort(key=lambda r:(-r['logit'],r['source'],r['code']))
        choices = {'baseline':{s:[d['code'] for d in hits] for s,hits in baseline.items()}}
        # Two cutoffs fixed before scoring; logits are not probabilities.
        for threshold in (0.,3.):
            choices[str(threshold)] = {s:[r['code'] for r in rows if r['source']==s and r['logit']>=threshold][:10] for s,_ in keys}
        results[query] = dict(choices=choices, candidates=rows, candidate_count=len(rows),
                             inference_seconds=inference, total_seconds=time.perf_counter()-begin)
        requests.append(dict(query=query,texts=texts))
    metrics = {}
    for name in ('baseline','0.0','3.0'):
        cases, regressions = [], []
        for (query,source), labels in checks.items():
            hits=set(results[query]['choices'][name].get(source,[]))
            before=set(results[query]['choices']['baseline'].get(source,[]))
            pool={r['code'] for r in results[query]['candidates'] if r['source']==source}
            lost=sorted((before-hits)&labels['relevant']); added=sorted((hits-before)&labels['irrelevant'])
            if lost or added:
                regressions.append(dict(query=query,source=source,lost_relevant=lost,added_irrelevant=added))
            cases.append(dict(query=query,source=source,missed=sorted(labels['relevant']-hits),
                false_matches=sorted(labels['irrelevant']&hits),candidate_misses=sorted(labels['relevant']-pool)))
        metrics[name] = dict(missed=sum(len(c['missed']) for c in cases),
            false_matches=sum(len(c['false_matches']) for c in cases), regressions=regressions,cases=cases)
    report = dict(status='Offline development experiment, not independent validation',
        model=json.loads((args.model/'manifest.json').read_text()), max_tokens=512,batch_size=4,
        candidate_rule='top 60 semantic union top 40 positive weighted lexical union deployed selections',
        metrics=metrics,results=results,peak_rss_mib=peak_mib(),platform=sys.platform,
        elapsed_seconds=time.perf_counter()-started,
        sources={str(p):digest(p) for p in paths+[args.artifact,args.bundle/'manifest.json',Path(__file__)]})
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    if args.requests:
        args.requests.write_text(json.dumps(requests)+'\n')
    print(json.dumps(dict(metrics={n:{k:v for k,v in m.items() if k!='cases'} for n,m in metrics.items()},
        peak_rss_mib=report['peak_rss_mib'], max_seconds=max(r['total_seconds'] for r in results.values())),indent=2))


def profile(args):
    from scvpublic.web import create_app
    app = create_app(args.artifact,args.bundle)
    model = Reranker(args.model)
    timings = []
    for request in json.loads(args.requests.read_text()):
        begin=time.perf_counter()
        with app.test_client() as client:
            response=client.get('/',query_string={'q1':request['query']})
            assert response.status_code==200
        model.score(request['query'],request['texts'])
        timings.append(time.perf_counter()-begin)
    report=dict(requests=len(timings),platform=sys.platform,peak_rss_mib=peak_mib(),
        p95_seconds=sorted(timings)[int(.95*len(timings))],max_seconds=max(timings),
        scope='Single process: existing Flask request plus reranking precomputed candidates; includes both models. Not a concurrent service/cgroup measurement.')
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('artifact','bundle','model','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--requests',type=Path)
    p.add_argument('--profile-only',action='store_true')
    a=p.parse_args()
    if a.profile_only and not a.requests:
        p.error('--profile-only requires --requests')
    (profile if a.profile_only else evaluate)(a)
