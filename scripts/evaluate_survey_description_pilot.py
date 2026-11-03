"""Paired, partially judged evaluation of an isolated description bundle."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import numpy as np

from scvpublic.build import digest
from scvpublic.encoding import Encoder
from scvpublic.store import connect
from scvpublic.survey_search import SurveySearch


def evaluate(artifact, baseline_bundle, candidate_bundle, output, multi_field=False, retention=.9, topic_routing=False):
    encoder = Encoder(baseline_bundle)
    engines = {name: SurveySearch(bundle, artifact, encoder) for name, bundle in
               [('baseline', baseline_bundle), ('candidate', candidate_bundle)]}
    if topic_routing:
        from scvpublic.survey_topics import TopicSearch
        engines['candidate'] = TopicSearch(engines['baseline'], candidate_bundle/'survey-descriptions.json')
    routing_enabled = topic_routing or getattr(engines['candidate'], 'topic_router', None) is not None
    metadata_path = candidate_bundle/'survey-descriptions.json'
    if not metadata_path.exists():
        metadata_path = candidate_bundle/'survey-topic-metadata.json'
    if multi_field:
        class MultiFieldVectors:
            def __matmul__(self, query):
                return np.maximum.reduce([v @ query for v in fields])
        manifest = json.loads((candidate_bundle/'manifest.json').read_text())
        topic_path = candidate_bundle/'survey-topic-vectors.npy'
        assert digest(topic_path) == manifest['files']['survey-topic-vectors.npy']
        topics = np.load(topic_path, allow_pickle=False)
        fields = [engines['baseline'].vectors, engines['candidate'].vectors, topics]
        assert all(v.shape == fields[0].shape and np.isfinite(v).all() for v in fields)
        engines['candidate'].vectors = MultiFieldVectors()
    paths = [Path('data/evaluation')/name for name in
        ('survey-relevance-development.json', 'survey-climate-relevance.json',
         'survey-description-checks.json', 'survey-synonyms.json')]
    cases = []
    for path in paths[:-1]:
        cases.extend(json.loads(path.read_text())['cases'])
    for pair in json.loads(paths[-1].read_text())['pairs']:
        cases.extend(dict(pair, query=q) for q in pair['queries'])
    merged = {}
    for case in cases:
        key = (case['query'].lower(), case['corpus'])
        row = merged.setdefault(key, dict(relevant=set(), irrelevant=set()))
        for label in row:
            row[label].update(case[label])
    with closing(connect(artifact)) as db:
        docs = {(source, d['code']): d for source, payload in db.execute(
            "SELECT corpus,payload FROM documents WHERE corpus!='court'") for d in [json.loads(payload)]}
    for (_, source), case in merged.items():
        assert not case['relevant'] & case['irrelevant']
        assert all((source, code) in docs for code in case['relevant'] | case['irrelevant'])
    def candidate_selection(query, cutoff):
        engine = engines['candidate']
        scores = engine.vectors @ encoder.encode([query])[0]
        floor = max(.30, .60*float(scores.max()))
        selected = {}
        with closing(connect(artifact)) as db:
            for source in sorted({s for s, _ in engine.keys}):
                lexical = engine.lexical_weights(db, source, [query])
                hits = []
                for (s, id), semantic in zip(engine.keys, scores):
                    if s != source or float(semantic) < floor:
                        continue
                    d = json.loads(db.execute('SELECT payload FROM documents WHERE corpus=? AND id=?', (s,id)).fetchone()[0])
                    lex = lexical.get(d['code'], 0.)
                    if not lex and semantic < .40:
                        continue
                    hits.append((d['code'], .9*float(semantic)+.1*lex))
                hits.sort(key=lambda h: (-h[1], h[0]))
                selected[source] = [code for code, score in hits if score >= cutoff*hits[0][1]][:10] if hits else []
        return selected
    results = {name: {query: {s: [d['code'] for d in hits] for s, hits in engine.search([query]).items()}
                     for query in sorted({q for q, _ in merged})} for name, engine in engines.items()}
    if retention != .9:
        for query in results['candidate']:
            assert candidate_selection(query, .9) == results['candidate'][query], 'Experiment selection differs from serving logic'
            results['candidate'][query] = candidate_selection(query, retention)
    judgments, regressions, changes = [], [], []
    for (query, source), case in merged.items():
        item = dict(query=query, source=source)
        for name in engines:
            selected = set(results[name][query].get(source, []))
            item[name] = dict(missed=sorted(case['relevant']-selected),
                              false_matches=sorted(case['irrelevant'] & selected))
        before = set(results['baseline'][query].get(source, []))
        after = set(results['candidate'][query].get(source, []))
        lost, added = sorted((before-after) & case['relevant']), sorted((after-before) & case['irrelevant'])
        if lost or added:
            regressions.append(dict(query=query, source=source, lost_relevant=lost, added_irrelevant=added))
        judgments.append(item)
    for query, sources in results['candidate'].items():
        for source, codes in sources.items():
            before, after = set(results['baseline'][query].get(source, [])), set(codes)
            if before != after:
                changes.append(dict(query=query, source=source,
                    added=[dict(code=c, question=docs[source,c]['question']) for c in sorted(after-before)],
                    removed=[dict(code=c, question=docs[source,c]['question']) for c in sorted(before-after)]))
    summary = {name: dict(missed=sum(len(j[name]['missed']) for j in judgments),
                         false_matches=sum(len(j[name]['false_matches']) for j in judgments)) for name in engines}
    report = dict(status='Development pilot; partial assistant judgments, not independent validation', multi_field=multi_field, retention=retention, topic_routing=routing_enabled,
        summary=summary, regressions=regressions, judgments=judgments, changes=changes, results=results,
        sources={str(p): digest(p) for p in paths+[artifact, baseline_bundle/'manifest.json',
            candidate_bundle/'manifest.json', metadata_path, Path(__file__), Path('scvpublic/survey_search.py')]+
            ([Path('scvpublic/survey_topics.py')] if routing_enabled else [])})
    output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(summary=summary, regressions=regressions), indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('artifact', 'baseline-bundle', 'candidate-bundle', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--multi-field', action='store_true')
    p.add_argument('--retention', type=float, default=.9)
    p.add_argument('--topic-routing', action='store_true')
    a = p.parse_args()
    if not 0 < a.retention <= 1:
        p.error('retention must be in (0,1]')
    if a.topic_routing and (a.multi_field or a.retention != .9):
        p.error('Topic routing is an isolated experiment; do not combine other changes')
    evaluate(a.artifact, a.baseline_bundle, a.candidate_bundle, a.output, a.multi_field, a.retention, a.topic_routing)
