"""Measure single-encoder hybrid retrieval without changing the preview."""
import argparse
import json
from pathlib import Path
import resource
import sys
import time
from scvpublic.hybrid import HybridSearch, chart_matches

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--artifact',default='artifacts/gss-bigram.sqlite')
parser.add_argument('--bundle',default='artifacts/semantic-full')
parser.add_argument('--output',default='artifacts/hybrid-comparison.json')
a=parser.parse_args()
start=time.monotonic()
engine=HybridSearch(a.bundle,a.artifact)
result={'load_seconds':time.monotonic()-start,'queries':{}}
for query in ['birth control','contraception','gay marriage','gun control','civil rights','abortion','health care','zzzznomatchzzzz']:
 start=time.monotonic();hits=engine.search([query]);seconds=time.monotonic()-start
 result['queries'][query]={'seconds':seconds,'candidate_count':len(hits),'chart_count':len(chart_matches(hits)),'hits':hits}
 print(query,len(hits),round(seconds,3),flush=True)
 for h in hits[:10]:print(' ',h['name'],round(h['score'],3),flush=True)
result['peak_rss_mib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(1024**2 if sys.platform=='darwin' else 1024)
Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
print('peak RSS MiB',result['peak_rss_mib'],flush=True)
