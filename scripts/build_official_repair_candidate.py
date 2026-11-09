"""Build an isolated search candidate; preserve surveys, scores and CaseSumm text."""
import argparse
from collections import defaultdict
from contextlib import closing
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

import numpy as np
import pyarrow as pa
from tokenizers import Tokenizer
from scvpublic.build import digest, write_index
from scvpublic.casesumm import FILES, resolve, citation_key, court_vectorizer
from scvpublic.encoding import Encoder
from scvpublic.sources import source_texts
from scripts.build_full_embeddings import token_windows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', type=Path, default=Path('artifacts/scdb-issues.sqlite'))
    p.add_argument('--bundle', type=Path, default=Path('artifacts/semantic-scdb-issues'))
    p.add_argument('--output', type=Path, default=Path('artifacts/official-repair-candidate.sqlite'))
    p.add_argument('--output-bundle', type=Path, default=Path('artifacts/semantic-official-repair-candidate'))
    a = p.parse_args()
    if a.output.exists() or a.output_bundle.exists():
        raise FileExistsError('Choose new candidate paths')
    manifest = json.loads((a.bundle/'manifest.json').read_text())
    if digest(a.baseline) != manifest['artifact_sha256']:
        raise ValueError('Baseline binding mismatch')
    for name, expected in manifest['files'].items():
        if Path(name).name != name or digest(a.bundle/name) != expected:
            raise ValueError('Bundle checksum mismatch')
    summary = json.loads(Path('data/evaluation/official-repair-summary.json').read_text())
    repaired = Path(summary['output'])
    original = Path('data/processed/modern/official.json')
    if digest(repaired) != summary['output_sha256'] or digest(original) != summary['source_sha256']:
        raise ValueError('Repair checksum mismatch')
    docs, semantic, origins = source_texts(a.baseline)
    old = {r['case_id']:r for r in json.loads(original.read_text())['records']}
    new = {r['case_id']:r for r in json.loads(repaired.read_text())['records']}
    changed = {k for k in old if old[k]['opinion'] != new[k]['opinion']}
    if len(changed) != 65 or any(origins.get(k) != 'official_opinion_fallback' for k in changed):
        raise ValueError('Unexpected repair scope')
    citations, dockets = defaultdict(list), defaultdict(list)
    with Path('data/raw/scdb-2026/SCDB_2026_01_caseCentered_Citation.csv').open(encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            citations[citation_key(r['usCite'])].append(r)
            dockets[(r['term'], r['docket'])].append(r)
    lexical = {}
    for name in FILES:
        with pa.memory_map(str(Path('data/raw/casesumm')/name), 'r') as f:
            for batch in pa.ipc.open_stream(f):
                for r in batch.to_pylist():
                    doc, reason = resolve(r['citation'], citations, dockets)
                    if doc and not reason:
                        key = doc['case_id']; text = ' '.join((r['opinion'] or '').split())
                        if key in lexical and lexical[key] != text:
                            raise ValueError('Conflicting source text')
                        lexical[key] = text
    for d in docs:
        k = d['case_id']
        if origins[k] == 'official_opinion_fallback':
            lexical[k] = new[k]['opinion']
        if k in changed:
            semantic[k] = new[k]['opinion']
    print('Rebuilding court TF-IDF with 65 repaired sources', flush=True)
    vectorizer = court_vectorizer()
    matrix = vectorizer.fit_transform(lexical[d['case_id']] for d in docs)
    del lexical
    shutil.copyfile(a.baseline, a.output)
    with closing(sqlite3.connect(a.output)) as db:
        db.execute("DELETE FROM postings WHERE corpus='court'")
        db.execute("DELETE FROM documents WHERE corpus='court'")
        payloads = []
        for d in docs:
            d = dict(d); d.pop('doc_id')
            if d['case_id'] in changed:
                d['pdf_pages'] = new[d['case_id']]['pdf_pages']
            payloads.append(d)
        write_index(db, 'court', matrix, vectorizer.get_feature_names_out(), payloads)
        sources = json.loads(db.execute("SELECT value FROM meta WHERE key='sources'").fetchone()[0])
        sources[str(repaired.resolve())] = digest(repaired)
        db.execute("UPDATE meta SET value=? WHERE key='sources'", (json.dumps(sources),))
        db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)', ('official_repair_candidate', json.dumps(dict(
            baseline_sha256=manifest['artifact_sha256'], repaired_cases=sorted(changed), status='local_experiment'))))
        db.commit()
        db.execute('VACUUM')
    del matrix
    print('Encoding only changed opinion passages', flush=True)
    shutil.copytree(a.bundle, a.output_bundle)
    tokenizer = Tokenizer.from_file(str(a.bundle/'tokenizer.json'))
    tokenizer.no_truncation(); tokenizer.no_padding()
    windows=[]; ids=[]
    for d in docs:
        if d['case_id'] in changed:
            tokens=tokenizer.encode(semantic[d['case_id']],add_special_tokens=False).ids
            for w in token_windows(tokens): windows.append(w); ids.append(d['doc_id'])
    encoder=Encoder(a.bundle)
    cls,sep,pad=[tokenizer.token_to_id(t) for t in ('[CLS]','[SEP]','[PAD]')]
    fresh=[]
    for start in range(0,len(windows),16):
        batch=[[cls]+w+[sep] for w in windows[start:start+16]]
        length=max(map(len,batch))
        mask=np.array([[1]*len(b)+[0]*(length-len(b)) for b in batch],dtype=np.int64)
        inputs=np.array([b+[pad]*(length-len(b)) for b in batch],dtype=np.int64)
        hidden=encoder.session.run(None,dict(input_ids=inputs,attention_mask=mask,token_type_ids=np.zeros_like(mask)))[0]
        pooled=(hidden*mask[:,:,None]).sum(1)/mask.sum(1)[:,None]
        pooled/=np.maximum(np.linalg.norm(pooled,axis=1,keepdims=True),1e-12)
        fresh.append(pooled.astype('float32'))
        if start%256==0: print(f'{start}/{len(windows)} passages',flush=True)
    old_ids=np.array(json.loads((a.bundle/'ids.json').read_text()))
    changed_ids={d['doc_id'] for d in docs if d['case_id'] in changed}
    keep=~np.isin(old_ids,list(changed_ids))
    vectors=np.load(a.bundle/'vectors.npy',allow_pickle=False)
    np.save(a.output_bundle/'vectors.npy',np.concatenate([vectors[keep]]+fresh),allow_pickle=False)
    (a.output_bundle/'ids.json').write_text(json.dumps(old_ids[keep].tolist()+ids)+'\n')
    source_manifest=json.loads((a.bundle/'sources.json').read_text())
    for k in changed: source_manifest[k]['sha256']=hashlib.sha256(semantic[k].encode()).hexdigest()
    (a.output_bundle/'sources.json').write_text(json.dumps(source_manifest,indent=2)+'\n')
    manifest['artifact_sha256']=digest(a.output)
    manifest['windows']=int(keep.sum())+len(ids)
    manifest['source_tokens']=sum(len(tokenizer.encode(semantic[d['case_id']],add_special_tokens=False).ids) for d in docs)
    for key in ('court_content_sha256','rebound_from_artifact_sha256','metadata_enriched_from_artifact_sha256'):
        manifest.pop(key,None)
    manifest['official_repair_candidate']=dict(baseline_manifest_sha256=digest(a.bundle/'manifest.json'),
        changed_cases=sorted(changed),reencoded_windows=len(ids),unchanged_windows_reused=int(keep.sum()))
    manifest['files']={name:digest(a.output_bundle/name) for name in manifest['files']}
    (a.output_bundle/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Candidate complete',flush=True)


if __name__=='__main__': main()
