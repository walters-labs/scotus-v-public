import csv,json
from pathlib import Path
from collections import defaultdict
import pyarrow as pa
from scvpublic.casesumm import FILES,citation_key,resolve
from scvpublic.hybrid import HybridSearch
from scvpublic.store import connect,search
report=json.load(open('artifacts/abortion-search-coverage.json'))
missing=set(report['missing_from_index']); indexed=set(report['indexed_not_retrieved'])
rows=list(csv.DictReader(open('data/raw/scdb-2026/SCDB_2026_01_caseCentered_Citation.csv',encoding='utf-8-sig')))
citations=defaultdict(list);dockets=defaultdict(list)
for r in rows:citations[citation_key(r['usCite'])].append(r);dockets[r['term'],r['docket']].append(r)
wanted={r['caseId']:r for r in rows if r['caseId'] in missing|indexed}
found=defaultdict(list)
for f in FILES:
 with pa.memory_map('data/raw/casesumm/'+f,'r') as stream:
  for batch in pa.ipc.open_stream(stream):
   for r in batch.to_pylist():
    for id,row in wanted.items():
     if citation_key(r['citation']) and citation_key(r['citation'])==citation_key(row['usCite']):
      doc,reason=resolve(r['citation'],citations,dockets)
      found[id].append(dict(citation=r['citation'],resolution=reason,opinion_words=len((r['opinion'] or '').split()),summary_words=len((r['syllabus'] or '').split())))
engine=HybridSearch('artifacts/semantic-wvs-pilot','artifacts/wvs-pilot.sqlite')
hits={h['case_id']:h for h in engine.search(['abortion'])}
with connect('artifacts/wvs-pilot.sqlite') as db:
 lexical=search(db,'court',['abortion'],limit=None)
 ranks={d['case_id']:i+1 for i,d in enumerate(lexical)}
output={}
for id,row in wanted.items():
 hit=hits.get(id,{})
 output[id]=dict(name=row['caseName'],in_index=id in indexed,caseSumm_matches=found[id],lexical_rank=ranks.get(id),hybrid={k:hit[k] for k in ('score','semantic_score','lexical_score') if k in hit})
Path('artifacts/abortion-gap-trace.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(output,indent=2))
