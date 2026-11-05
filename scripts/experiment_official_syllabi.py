"""Offline official-syllabus candidate; never modifies serving sources or scoring."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urldefrag
import hashlib
import numpy as np
from tokenizers import Tokenizer
from scvpublic.build import digest
from scvpublic.sources import source_texts
from scvpublic.hybrid import HybridSearch, CHART_CUTOFF
from build_full_embeddings import token_windows

ARTIFACT = Path('artifacts/affirmative-action.sqlite')
BASE = Path('artifacts/semantic-affirmative-action')
OFFICIAL = Path('data/processed/modern/official.json')
FROZEN = Path('artifacts/court-passage-support-v1/baseline.json')
BENCHMARK = Path('data/evaluation/court-search-benchmark-v2.json')


def extract(text):
    """Require contiguous syllabus pages, followed by a principal-opinion header."""
    selected = []
    ended = False
    for page in text.split('\f'):
        lines = [line.strip() for line in page.splitlines() if line.strip()]
        header = next((i for i, line in enumerate(lines[:6]) if line == 'Syllabus'), None)
        if header is not None:
            if ended:
                raise ValueError('noncontiguous_syllabus')
            body = '\n'.join(lines[header + 1:])
            body = re.sub(r'Page\s+Proof\s+Pending\s+Publication', '', body)
            selected.append(body)
        elif selected:
            ended = bool(re.search(r'Opinion of the Court|Per Curiam|Opinion of [A-Z]', ' '.join(lines[:6])))
            break
    if not selected or not ended:
        raise ValueError('no_bounded_syllabus')
    text = '\n'.join(selected)
    text = re.sub(r'(?<=[A-Za-z])-\s*\n\s*(?=[a-z])', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text.split()) < 40 or not re.search(r'\bHeld\b', text):
        raise ValueError('no_substantive_holding')
    # Bound summaries at their reported disposition, before vote/counsel lists.
    # Reject uncertain endings rather than silently admitting counsel text.
    dispositions = list(re.finditer(
        r'\b\d{1,4}\s+(?:F\.|U\.\s*S\.|S\.\s*W\.|So\.|A\.|P\.)'
        r'[^;]{0,100}?,\s*(?:affirmed|affrmed|reversed|vacated|dismissed)[^.]*\.', text))
    dispositions = [m for m in dispositions if m.start() > text.index('Held')]
    if len(dispositions) != 1:
        raise ValueError('no_unique_disposition_boundary')
    if re.search(r'\([a-z]\)', text[dispositions[0].end():]):
        raise ValueError('analysis_after_disposition')
    text = text[:dispositions[0].end()]
    if re.search(r'argued the cause|Briefs of amici', text):
        raise ValueError('counsel_inside_summary')
    return text, len(selected)


def prepare(args):
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    docs, texts, origins = source_texts(ARTIFACT)
    frozen = json.loads(FROZEN.read_text())
    for path in (ARTIFACT, BASE/'manifest.json', Path('scvpublic/hybrid.py')):
        assert frozen['provenance'][str(path)] == digest(path), path
    rows = []; replacements = {}
    for record in json.loads(OFFICIAL.read_text())['records']:
        key = record['case_id']
        if origins.get(key) != 'official_opinion_fallback':
            continue
        url, fragment = urldefrag(record['source_url'])
        start = int(fragment.split('=')[1]) if fragment else 1
        pdf = Path('data/raw/official-scotus') / url.rsplit('/', 1)[-1]
        assert digest(pdf) == record['pdf_sha256']
        # Include the first principal page to establish the end boundary.
        end = record['pdf_pages'][0]
        text = subprocess.check_output([args.pdftotext, '-f', str(start), '-l', str(end),
                                       '-layout', str(pdf), '-'], timeout=60).decode()
        row = dict(case_id=key, source_url=record['source_url'], pdf_sha256=record['pdf_sha256'])
        try:
            syllabus, pages = extract(text)
            # Confirm the docket from the source's machine-readable citation.
            docket = record['citation'].split('_', 1)[1]
            normalized = syllabus.replace('–', '-').replace('—', '-')
            if docket not in normalized[:1800]:
                raise ValueError('docket_not_confirmed')
            replacements[key] = syllabus
            row.update(status='candidate', pages=pages, words=len(syllabus.split()),
                       text_sha256=hashlib.sha256(syllabus.encode()).hexdigest())
        except ValueError as error:
            row.update(status='fallback', reason=str(error))
        rows.append(row)
    report = dict(rule='Only bounded, docket-confirmed official syllabi with Held; unchanged model, windows, lexical index and scoring. No threshold tuning.',
                  provenance={str(p):digest(p) for p in (ARTIFACT, BASE/'manifest.json', OFFICIAL, FROZEN, BENCHMARK, Path(__file__))},
                  records=rows, counts=dict(Counter(r['status'] for r in rows)))
    (args.output/'extraction.json').write_text(json.dumps(report, indent=2)+'\n')
    (args.output/'texts.json').write_text(json.dumps(replacements, indent=2)+'\n')
    print(report['counts'], flush=True)


def build(args):
    report = json.loads((args.output/'extraction.json').read_text())
    for path, sha in report['provenance'].items():
        assert digest(Path(path)) == sha, path
    replacements = json.loads((args.output/'texts.json').read_text())
    docs, _, _ = source_texts(ARTIFACT)
    engine = HybridSearch(BASE, ARTIFACT)
    tok = Tokenizer.from_file(str(BASE/'tokenizer.json')); tok.no_padding(); tok.no_truncation()
    windows = []; ids = []
    for doc in docs:
        if doc['case_id'] in replacements:
            for window in token_windows(tok.encode(replacements[doc['case_id']], add_special_tokens=False).ids):
                windows.append(window); ids.append(doc['doc_id'])
    cls, sep, pad = [tok.token_to_id(t) for t in ('[CLS]', '[SEP]', '[PAD]')]
    new = np.empty((len(windows), 384), dtype=np.float32)
    for start in range(0, len(windows), 16):
        batch = [[cls]+w+[sep] for w in windows[start:start+16]]
        length = max(map(len, batch))
        mask = np.array([[1]*len(b)+[0]*(length-len(b)) for b in batch], dtype=np.int64)
        inputs = np.array([b+[pad]*(length-len(b)) for b in batch], dtype=np.int64)
        hidden = engine.encoder.session.run(None, dict(input_ids=inputs, attention_mask=mask, token_type_ids=np.zeros_like(mask)))[0]
        pooled = (hidden*mask[:,:,None]).sum(1)/mask.sum(1)[:,None]
        pooled /= np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)
        new[start:start+len(batch)] = pooled
        if start % 512 == 0: print(start, '/', len(windows), flush=True)
    keep = ~np.isin(engine.ids, list(set(ids)))
    vectors = np.concatenate([engine.vectors[keep], new])
    all_ids = np.concatenate([engine.ids[keep], ids])
    order = np.argsort(all_ids, kind='stable')
    folder = args.output/'bundle'; folder.mkdir()
    np.save(folder/'vectors.npy', vectors[order])
    (folder/'ids.json').write_text(json.dumps(all_ids[order].tolist())+'\n')
    sources = json.loads((BASE/'sources.json').read_text())
    for key, text in replacements.items():
        sources[key] = dict(origin='official_syllabus_candidate', sha256=hashlib.sha256(text.encode()).hexdigest())
    (folder/'sources.json').write_text(json.dumps(sources, indent=2)+'\n')
    manifest = json.loads((BASE/'manifest.json').read_text())
    for name in manifest['model']['files']: shutil.copyfile(BASE/name, folder/name)
    manifest.update(source_policy='offline-official-syllabus-candidate-v1', windows=len(all_ids),
                    source_counts=dict(Counter(x['origin'] for x in sources.values())),
                    experiment_sha256=digest(args.output/'extraction.json'))
    manifest.pop('source_tokens', None)
    manifest['files'] = {p.name:digest(p) for p in folder.iterdir()}
    (folder/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Candidate built:', len(all_ids), 'windows', flush=True)


def evaluate(args):
    engine = HybridSearch(args.output/'bundle', ARTIFACT)
    baseline = json.loads(FROZEN.read_text())['queries']
    spec = json.loads(BENCHMARK.read_text())
    results = {}; rankings = {}
    for query, review in spec['queries'].items():
        before = baseline[query]; after = engine.search([query]); rankings[query] = after
        b = {h['case_id'] for h in before if h['score'] >= CHART_CUTOFF}
        a = {h['case_id'] for h in after if h['score'] >= CHART_CUTOFF}
        direct = {k for k,v in review['court'].items() if v['label']=='direct'}
        bad = {k for k,v in review['court'].items() if v['label']=='irrelevant'}
        results[query] = dict(baseline_chart=len(b), candidate_chart=len(a),
            lost_direct=sorted((b-a)&direct), new_direct=sorted((a-b)&direct),
            new_irrelevant=sorted((a-b)&bad), removed_irrelevant=sorted((b-a)&bad),
            lost_direct_top10=sorted(({h['case_id'] for h in before[:10]}-{h['case_id'] for h in after[:10]})&direct))
        print(query, results[query], flush=True)
    gate = dict(no_lost_direct=not any(r['lost_direct'] for r in results.values()),
                no_new_irrelevant=not any(r['new_irrelevant'] for r in results.values()),
                no_lost_direct_top10=not any(r['lost_direct_top10'] for r in results.values()),
                removes_known_irrelevant=any(r['removed_irrelevant'] for r in results.values()))
    (args.output/'rankings.json').write_text(json.dumps(rankings, indent=2)+'\n')
    (args.output/'evaluation.json').write_text(json.dumps(dict(gate=gate, passes=all(gate.values()), queries=results,
        candidate_manifest_sha256=digest(args.output/'bundle/manifest.json'), benchmark_sha256=digest(BENCHMARK)), indent=2)+'\n')
    print(gate)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['prepare', 'build', 'evaluate'])
    p.add_argument('--output', type=Path, default=Path('artifacts/official-syllabi-v1'))
    p.add_argument('--pdftotext', default='pdftotext')
    args = p.parse_args()
    globals()[args.mode](args)
