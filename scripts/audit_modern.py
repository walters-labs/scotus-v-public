"""Identify SCDB cases since 2017 not already covered by pinned CaseSumm text."""
import argparse
from collections import defaultdict, Counter
import csv
import json
from pathlib import Path
import pyarrow as pa
from scvpublic.build import digest
from scvpublic.casesumm import select, citation_key, FILES


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scdb',type=Path,default=Path('data/raw/scdb-2026/SCDB_2026_01_caseCentered_Citation.csv'))
    p.add_argument('--source',type=Path,default=Path('data/raw/casesumm'))
    p.add_argument('--output',type=Path,default=Path('data/processed/modern'))
    args=p.parse_args()
    with args.scdb.open(encoding='utf-8-sig') as stream: rows=list(csv.DictReader(stream))
    citations,dockets=defaultdict(list),defaultdict(list)
    for row in rows:
        if citation_key(row['usCite']):citations[citation_key(row['usCite'])].append(row)
        dockets[(row['term'],row['docket'])].append(row)
    def records():
        for name,sha in FILES.items():
            if digest(args.source/name)!=sha:raise ValueError(f'Checksum mismatch: {name}')
            with pa.memory_map(str(args.source/name),'r') as stream:
                for batch in pa.ipc.open_stream(stream):yield from batch.to_pylist()
    selected,excluded,stats=select(records(),citations,dockets,1950,2026)
    ids={doc['case_id'] for doc,text in selected}
    missing=[row for row in rows if int(row['dateDecision'].split('/')[-1])>=2017 and row['caseId'] not in ids]
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'missing-scdb.json').write_text(json.dumps(missing,indent=2)+'\n')
    report=dict(scdb_sha256=digest(args.scdb),matched=len(selected),
                matched_by_year=dict(sorted(Counter(doc['cases'][0]['year'] for doc,text in selected).items())),
                missing_since_2017=len(missing),stats=stats)
    (args.output/'casesumm-coverage.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
