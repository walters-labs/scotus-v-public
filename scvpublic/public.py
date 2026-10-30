"""Offline numeric ANES scoring with explicit answer maps and documented weights."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import math
from .build import digest


def validate(mapping):
    if mapping['version'] != 'explicit-anes-v1':
        raise ValueError('Unsupported response mapping version')
    seen = set()
    for entry in mapping['entries']:
        if entry['code'] in seen or not entry['scores']:
            raise ValueError('Duplicate or empty mapping')
        seen.add(entry['code'])
        if any(not math.isfinite(float(v)) or not -1 <= float(v) <= 1 for v in entry['scores'].values()):
            raise ValueError('Scores must be finite and within [-1,1]')


def aggregate(frame, entries, totals):
    import pandas as pd
    for entry in entries:
        scores = frame[entry['code']].map({float(k):v for k,v in entry['scores'].items()})
        weights = pd.to_numeric(frame[entry['weight']], errors='coerce')
        keep = scores.notna() & weights.notna() & (weights > 0) & (weights < float('inf'))
        selected = pd.DataFrame({'year':frame.loc[keep,'VCF0004'],
                                 'weighted':scores[keep]*weights[keep], 'weight':weights[keep]})
        for year, group in selected.groupby('year'):
            if not math.isfinite(year) or year % 1:
                raise ValueError('Invalid survey year')
            total = totals[(entry['code'], int(year))]
            total[0] += float(group.weighted.sum()); total[1] += float(group.weight.sum()); total[2] += len(group)


def build(source, mappings, output):
    import pandas as pd
    mapping = json.loads(mappings.read_text()); validate(mapping)
    entries = mapping['entries']
    columns = sorted({'VCF0004'} | {e['code'] for e in entries} | {e['weight'] for e in entries})
    totals = defaultdict(lambda: [0.,0.,0])
    with pd.read_stata(source, convert_categoricals=False, columns=columns, chunksize=2000) as reader:
        for frame in reader:
            aggregate(frame, entries, totals)
    documents = []
    for entry in entries:
        by_year = {str(y): total for (code,y),total in sorted(totals.items()) if code == entry['code'] and total[1]>0}
        documents.append(dict(code=entry['code'], question=entry['question'], title=entry['title'],
            family=entry['family'], priority=entry['priority'],
            years={year: values[0]/values[1] for year,values in by_year.items()},
            respondents={year:values[2] for year,values in by_year.items()},
            weight=entry['weight'], scores=entry['scores'], rationale=entry['rationale'],
            measurement_type=entry.get('measurement_type','policy_or_self_placement'),
            supersedes=entry.get('supersedes',[])))
    payload=dict(methodology=mapping['version'], sources={str(p.resolve()):digest(p) for p in [source,mappings]},
                 documents=documents, notes='Weighted within question; one preferred variant per family/year; equal family means. Unmapped answers excluded.')
    from .survey_schema import prepare
    prepare(payload)
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix('.tmp');temporary.write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n');temporary.replace(output)
    print(json.dumps({'output':str(output),'questions':len(documents),'plottable':sum(bool(d['years']) for d in documents),'bytes':output.stat().st_size},indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('data/raw/rebuild/anes-20260205/anes_timeseries_cdf_stata_20260205.dta'))
    parser.add_argument('--mappings',type=Path,default=Path('data/anes/response_mappings.json'))
    parser.add_argument('--output',type=Path,default=Path('data/processed/anes-20260205/public.json'))
    args=parser.parse_args();build(args.source,args.mappings,args.output)

if __name__=='__main__':main()
