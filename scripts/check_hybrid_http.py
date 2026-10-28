"""Smoke-test the hybrid search service."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import time
from urllib.parse import urlencode
from urllib.request import urlopen

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--url',default='http://127.0.0.1:8004')
a=p.parse_args()
with urlopen(a.url+'/healthz',timeout=30) as r:
    assert json.load(r)['search_mode']=='hybrid'

def check(q):
    start=time.monotonic()
    with urlopen(a.url+'/?'+urlencode({'q1':q}),timeout=30) as r:
        assert r.status==200
        html=r.read().decode()
    assert 'Court search: TF-IDF + embeddings' in html
    if q=='birth control':
        for word in ['EISENSTADT','GRISWOLD','HOBBY LOBBY','POPULATION SERVICES']:
            assert word in html,word
        for word in ['NGUYEN','LEXMARK','SAFFORD','MANUEL v.']:
            assert word not in html,word
    if q=='gay marriage':
        assert 'OBERGEFELL' in html and 'WINDSOR' in html
    if q=='zzzznomatchzzzz':assert 'No matching opinions.' in html
    return time.monotonic()-start
queries=['birth control','gay marriage','gun control','civil rights','abortion','health care','zzzznomatchzzzz']
first=[check(q) for q in queries]
with ThreadPoolExecutor(max_workers=4) as pool:
    cached=list(pool.map(check,queries*5))
print(json.dumps(dict(requests=len(first)+len(cached),first_max_seconds=max(first),cached_max_seconds=max(cached)),indent=2))
