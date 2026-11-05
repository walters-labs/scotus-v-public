"""Read-only wording/source-score diagnostic; no search parameter changes."""
import json
from pathlib import Path
import hashlib
import numpy as np
from tokenizers import Tokenizer
from scvpublic.hybrid import HybridSearch
from scvpublic.sources import source_texts
from scvpublic.build import digest
from build_full_embeddings import token_windows


def main():
    artifact=Path('artifacts/affirmative-action.sqlite')
    base=Path('artifacts/semantic-affirmative-action')
    candidate=Path('artifacts/official-syllabi-v5/bundle')
    baseline_path=Path('artifacts/court-passage-support-v1/baseline.json')
    fixed_path=Path('artifacts/court-candidate-pool-v1/fixed-rankings.json')
    baseline=json.loads(baseline_path.read_text())['queries'];fixed=json.loads(fixed_path.read_text())
    old=HybridSearch(base,artifact);new=HybridSearch(candidate,artifact)
    docs,texts,origins=source_texts(artifact);lookup={d['case_id']:d['doc_id'] for d in docs}
    summaries=json.loads(Path('artifacts/official-syllabi-v5/texts.json').read_text())
    tok=Tokenizer.from_file(str(base/'tokenizer.json'));tok.no_padding();tok.no_truncation()
    queries=['healthcare','health care'];vectors=np.stack([old.encoder.encode([q])[0] for q in queries])
    result=dict(provenance={str(p):digest(p) for p in [artifact,base/'manifest.json',candidate/'manifest.json',baseline_path,fixed_path,Path(__file__)]},
                query_cosine=float(vectors[0]@vectors[1]),queries={})
    keys={'2024-019','2022-054','2011-077','2021-027','2024-055'}
    for q,v in zip(queries,vectors):
        original_scores=old.vectors@v;summary_scores=new.vectors@v
        records=[]
        for key in sorted(keys):
            record=dict(case_id=key)
            for label,engine,scores,source in [('original',old,original_scores,texts[key]),('summary',new,summary_scores,summaries.get(key,texts[key]))]:
                expected=json.loads(((base if label=='original' else candidate)/'sources.json').read_text())[key]['sha256']
                assert hashlib.sha256(source.encode()).hexdigest()==expected
                indexes=np.flatnonzero(engine.ids==lookup[key]);windows=list(token_windows(tok.encode(source,add_special_tokens=False).ids))
                assert len(windows)==len(indexes)
                win=int(np.argmax(scores[indexes]))
                record[label]=dict(max_cosine=float(scores[indexes[win]]),passage_index=win,passages=len(windows),
                    source_sha256=expected,winning_passage=tok.decode(windows[win]))
            for label,hits in [('baseline',baseline[q]),('fixed',fixed[q])]:
                match=next(((i+1,h) for i,h in enumerate(hits) if h['case_id']==key),None)
                record[label]=dict(rank=match[0],score=match[1]['score'],lexical=match[1]['lexical_score'],semantic=match[1]['semantic_score']) if match else None
            if record['baseline']:
                assert abs(record['original']['max_cosine']-record['baseline']['semantic'])<1e-7, (q,key)
            if record['fixed']:
                expected=.75*record['original']['max_cosine']+.25*record['summary']['max_cosine'] if key in summaries else record['original']['max_cosine']
                assert abs(expected-record['fixed']['semantic'])<1e-7, (q,key)
            records.append(record)
        compact=lambda hits:[dict(case_id=h['case_id'],name=h['name'],score=h['score']) for h in hits if h['score']>=.30]
        result['queries'][q]=dict(tokens=tok.encode(q,add_special_tokens=False).tokens,baseline_chart=compact(baseline[q]),fixed_chart=compact(fixed[q]),cases=records)
    Path('data/evaluation/healthcare-wording-diagnostic.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Query cosine:',result['query_cosine'])
    for q,r in result['queries'].items():
        print(q,r['tokens'],'chart counts',len(r['baseline_chart']),len(r['fixed_chart']))
        for x in r['cases']:
            print(x['case_id'],x['baseline'],x['fixed'])
            if x['case_id']=='2024-019':
                print('ORIGINAL',x['original']);print('SUMMARY',x['summary'])


if __name__=='__main__':main()
