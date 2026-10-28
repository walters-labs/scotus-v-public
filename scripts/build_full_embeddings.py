"""Embed every token of verified summaries (full opinion fallback), offline."""
import argparse
from collections import Counter
import json
import hashlib
from pathlib import Path
import shutil
import numpy as np
from tokenizers import Tokenizer
from scvpublic.build import digest
from scvpublic.encoding import Encoder
from scvpublic.sources import source_texts, SOURCE_POLICY


def token_windows(tokens, size=254, overlap=40):
    if not 0 <= overlap < size:
        raise ValueError('Invalid overlap')
    for start in range(0, len(tokens), size-overlap):
        yield tokens[start:start+size]
        if start+size >= len(tokens):
            break


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact',type=Path,default=Path('artifacts/gss-bigram.sqlite'))
    parser.add_argument('--model',type=Path,default=Path('artifacts/semantic-model'))
    parser.add_argument('--output',type=Path,default=Path('artifacts/semantic-full'))
    a=parser.parse_args()
    if a.output.exists(): raise FileExistsError(a.output)
    model=json.loads(Path('data/manifests/semantic-model.json').read_text())
    for name,checksum in model['files'].items():
        if digest(a.model/name)!=checksum: raise ValueError('Model checksum mismatch')
    docs,texts,origins=source_texts(a.artifact)
    tokenizer=Tokenizer.from_file(str(a.model/'tokenizer.json'))
    tokenizer.no_truncation();tokenizer.no_padding()
    windows=[]; ids=[]; token_count=0
    for d in docs:
        tokens=tokenizer.encode(texts[d['case_id']],add_special_tokens=False).ids
        if not tokens:raise ValueError('Empty source: '+d['case_id'])
        token_count+=len(tokens)
        for window in token_windows(tokens):
            windows.append(window);ids.append(d['doc_id'])
    a.output.mkdir(parents=True)
    (a.output/'sources.json').write_text(json.dumps({d['case_id']: dict(origin=origins[d['case_id']],
        sha256=hashlib.sha256(texts[d['case_id']].encode()).hexdigest()) for d in docs}, indent=2)+'\n')
    encoder=Encoder(a.model)
    vectors=np.lib.format.open_memmap(a.output/'vectors.npy',mode='w+',dtype='float32',shape=(len(windows),384))
    cls,sep,pad=[tokenizer.token_to_id(t) for t in ('[CLS]','[SEP]','[PAD]')]
    print(f'{len(docs)} cases; {len(windows)} windows; {token_count} source tokens',flush=True)
    for start in range(0,len(windows),16):
        batch=[[cls]+w+[sep] for w in windows[start:start+16]]
        length=max(map(len,batch))
        mask=np.array([[1]*len(b)+[0]*(length-len(b)) for b in batch],dtype=np.int64)
        input_ids=np.array([b+[pad]*(length-len(b)) for b in batch],dtype=np.int64)
        hidden=encoder.session.run(None,dict(input_ids=input_ids,attention_mask=mask,token_type_ids=np.zeros_like(mask)))[0]
        pooled=(hidden*mask[:,:,None]).sum(1)/mask.sum(1)[:,None]
        pooled/=np.maximum(np.linalg.norm(pooled,axis=1,keepdims=True),1e-12)
        vectors[start:start+len(batch)]=pooled.astype('float32')
        if start%1024==0: print(f'{start}/{len(windows)}',flush=True)
    vectors.flush();del vectors
    (a.output/'ids.json').write_text(json.dumps(ids)+'\n')
    for name in model['files']:shutil.copyfile(a.model/name,a.output/name)
    manifest=dict(model=model,document_count=len(docs),artifact_sha256=digest(a.artifact),
        description='All source tokens, 254-token windows with 40-token overlap; maximum passage cosine per case',
        source_policy=SOURCE_POLICY, source_counts=dict(Counter(origins.values())),source_tokens=token_count,windows=len(windows),
        files={p.name:digest(p) for p in a.output.iterdir() if p.is_file()})
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Complete',flush=True)

if __name__=='__main__':main()
