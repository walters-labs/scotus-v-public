"""Fixed small L2/L12 relevance comparison; no deployment or threshold tuning."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from tokenizers import Tokenizer
from scvpublic.build import digest
from scvpublic.hybrid import HybridSearch
from scvpublic.sources import source_texts
from scripts.build_full_embeddings import token_windows
from scripts.experiment_survey_reranker import Reranker


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('artifacts/court-reranker-l12-pilot'))
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    artifact=Path('artifacts/scdb-issues.sqlite');bundle=Path('artifacts/semantic-scdb-issues')
    benchmark=Path('data/evaluation/court-search-benchmark-v3.json')
    review=Path('data/evaluation/court-dual-source-membership-review.json')
    spec=json.loads(benchmark.read_text())['queries']
    for r in json.loads(review.read_text())['records']:
        labels=spec[r['query']]['court'];k=r['case_id']
        if k in labels and labels[k]['label']!=r['label']:raise ValueError('Label conflict')
        labels[k]={'label':r['label']}
    queries=['birth control','contraception','healthcare','capital punishment']
    # Include every existing binary judgment for the fixed topics, even if the
    # current retriever misses it. This isolates reranking, not retrieval recall.
    cohort={q:{k:v['label'] for k,v in spec[q]['court'].items() if v['label'] in ('direct','irrelevant')} for q in queries}
    modelpaths={'L2':Path('artifacts/survey-reranker-model'),'L12':Path('artifacts/court-reranker-l12-model')}
    args.output.mkdir()
    protocol=dict(queries=queries,cohort=cohort,rule='Same source-verified name/180-token overview/180-token best passage for both models; raw logit >=0 acceptance. Report positive-negative ordering separately. No threshold sweep. Stop before integration if any direct example is rejected or any judged negative accepted.',
        limitations='Diagnostic selected difficult topics, not blind validation; aliases share cases. Logits are not calibrated probabilities. Cases absent from retrieval are explicitly injected for this model-only test.',
        provenance={str(p):digest(p) for p in [artifact,bundle/'manifest.json',benchmark,review,Path(__file__),*[v/'manifest.json' for v in modelpaths.values()]]})
    (args.output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    engine=HybridSearch(bundle,artifact);docs,texts,origins=source_texts(artifact)
    lookup={d['case_id']:d for d in docs};hashes=json.loads((bundle/'sources.json').read_text())
    tok=Tokenizer.from_file(str(bundle/'tokenizer.json'));tok.no_truncation();tok.no_padding()
    rtok=Tokenizer.from_file(str(modelpaths['L2']/'tokenizer.json'));rtok.no_truncation();rtok.no_padding()
    rows=[]
    for q,labels in cohort.items():
        raw=engine.vectors@engine.encoder.encode([q])[0]
        for k,label in labels.items():
            d=lookup[k];text=texts[k]
            if hashlib.sha256(text.encode()).hexdigest()!=hashes[k]['sha256']:raise ValueError('Source mismatch')
            tokens=tok.encode(text,add_special_tokens=False).ids;windows=list(token_windows(tokens))
            indexes=np.flatnonzero(engine.ids==d['doc_id'])
            if len(windows)!=len(indexes):raise ValueError('Window mismatch')
            best=int(np.argmax(raw[indexes]))
            name=rtok.decode(rtok.encode(d['name'],add_special_tokens=False).ids[:40])
            context=f'Case: {name}\nCase overview: {tok.decode(tokens[:180])}\nMatching passage: {tok.decode(windows[best][:180])}'
            rows.append(dict(query=q,case_id=k,name=d['name'],label=label,text=context,source_sha256=hashes[k]['sha256'],best_passage_index=best))
    (args.output/'requests.json').write_text(json.dumps(rows,indent=2)+'\n')
    reports={}
    for model,path in modelpaths.items():
        scorer=Reranker(path);scorer.tokenizer.no_truncation();scorer.tokenizer.no_padding()
        if any(len(scorer.tokenizer.encode(r['query'],r['text']).ids)>512 for r in rows):raise ValueError('Context too long')
        scorer.tokenizer.enable_truncation(max_length=512);scorer.tokenizer.enable_padding()
        results=[];ordering={}
        for q in queries:
            subset=[r for r in rows if r['query']==q];scores=scorer.score(q,[r['text'] for r in subset])
            scored=[dict(query=q,case_id=r['case_id'],name=r['name'],label=r['label'],logit=s) for r,s in zip(subset,scores)]
            positives=[r for r in scored if r['label']=='direct'];negatives=[r for r in scored if r['label']=='irrelevant']
            ordering[q]=dict(correct=sum(p['logit']>n['logit'] for p in positives for n in negatives),total=len(positives)*len(negatives))
            results.extend(scored)
        errors=[r for r in results if (r['logit']>=0)!=(r['label']=='direct')]
        reports[model]=dict(rejected_direct=sum(r['label']=='direct' for r in errors),accepted_irrelevant=sum(r['label']=='irrelevant' for r in errors),pair_ordering=ordering,results=results)
        del scorer
    report=dict(protocol=protocol,request_sha256=digest(args.output/'requests.json'),pairs=len(rows),models=reports,
        passes_small_gate=reports['L12']['rejected_direct']==0 and reports['L12']['accepted_irrelevant']==0,
        status='local_model_only_diagnostic_not_deployed')
    Path('data/evaluation/court-reranker-l12-pilot.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:{a:b for a,b in v.items() if a!='results'} for k,v in reports.items()},indent=2))


if __name__=='__main__':main()
