"""Offline WVS U.S. extraction with reviewed scales and original survey weights."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

from .build import digest
from .gss import attach
from .public import aggregate, validate


def aggregate_wvs(frame, entries, totals):
    frame = frame.loc[frame['S003'] == 840].copy()
    frame['VCF0004'] = frame['S020']
    aggregate(frame, entries, totals)


def check_labels(labels, value_labels, entries):
    for entry in entries:
        code = entry['code']
        if labels[code] != entry['expected_label'] or value_labels[code] != entry['expected_labels']:
            raise ValueError('WVS labels changed: ' + code)


def build(source, mappings, output, manifest, audit):
    import pandas as pd
    spec = json.loads(manifest.read_text())
    if digest(source) != spec['sha256']:
        raise ValueError('WVS checksum mismatch')
    mapping = json.loads(mappings.read_text())
    if mapping['version'] != 'explicit-wvs-v1':
        raise ValueError('Unsupported WVS mapping')
    validate(dict(mapping, version='explicit-anes-v1'))
    entries = mapping['entries']
    if any(e['weight'] != 'S017' for e in entries):
        raise ValueError('WVS requires original S017 weights')
    # pandas handles the legacy Stata encoding in this release; readstat rejects it.
    with pd.io.stata.StataReader(source) as reader:
        labels = reader.variable_labels()
        values = reader.value_labels()
        label_names = dict(zip(reader._varlist, reader._lbllist))
        value_labels = {e['code']: {str(int(k)): v for k, v in values[label_names[e['code']]].items()}
                        for e in entries}
    check_labels(labels, value_labels, entries)
    totals = defaultdict(lambda: [0., 0., 0])
    row_counts = defaultdict(int)
    # Count response codes independently to cross-check every aggregate.
    distributions = defaultdict(lambda: defaultdict(float))
    columns = ['S003', 'S020', 'S017'] + [e['code'] for e in entries]
    for frame in pd.read_stata(source, columns=columns, convert_categoricals=False, chunksize=10000):
        us = frame.loc[frame.S003 == 840]
        for year, group in us.groupby('S020'):
            row_counts[int(year)] += len(group)
        for entry in entries:
            code = entry['code']
            actual = set(us[code].dropna())
            if actual - set(map(float, entry['expected_labels'])):
                raise ValueError('Unexpected WVS response: ' + code)
            valid = us.loc[us.S017.gt(0) & us.S017.lt(float('inf'))]
            for (year, answer), weight in valid.groupby(['S020', code]).S017.sum().items():
                distributions[code, int(year)][str(int(answer))] += float(weight)
        aggregate_wvs(frame, entries, totals)
    documents = []
    for entry in entries:
        code = entry['code']
        by_year = {str(y): t for (c, y), t in sorted(totals.items()) if c == code and t[1] > 0}
        if not by_year:
            raise ValueError('No usable U.S. responses: ' + code)
        for year, total in by_year.items():
            dist = distributions[code, int(year)]
            denominator = sum(dist.get(k, 0) for k in entry['scores'])
            expected = sum(dist.get(k, 0)*s for k, s in entry['scores'].items()) / denominator
            if abs(expected - total[0]/total[1]) > 1e-10:
                raise ValueError('WVS weighted distribution check failed')
        public_entry = {k: v for k, v in entry.items() if not k.startswith('expected_')}
        documents.append(dict(public_entry, dataset='WVS', years={y:t[0]/t[1] for y,t in by_year.items()},
                              respondents={y:t[2] for y,t in by_year.items()}, weight_sums={y:t[1] for y,t in by_year.items()}))
    payload = dict(methodology=mapping['version'], documents=documents, release=spec['release'],
                   notes=mapping['notes'], sources={str(p):digest(p) for p in (source, mappings, manifest)})
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False)+'\n')
    temporary.replace(output)
    report = dict(us_rows=sum(row_counts.values()), rows_by_year=dict(sorted(row_counts.items())),
                  questions=len(documents), families=len({d['family'] for d in documents}),
                  question_years=sum(len(d['years']) for d in documents),
                  validation='Every score checked against separately grouped weighted response frequencies',
                  coverage={d['code']:d['respondents'] for d in documents})
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=Path('data/raw/wvs/WVS_Time_Series_1981-2022_stata_v5_0.dta'))
    p.add_argument('--mappings', type=Path, default=Path('data/wvs/response_mappings.json'))
    p.add_argument('--manifest', type=Path, default=Path('data/manifests/wvs-v5.json'))
    p.add_argument('--output', type=Path, default=Path('data/processed/wvs-v5/public.json'))
    p.add_argument('--audit', type=Path, default=Path('data/wvs/validation.json'))
    p.add_argument('--base-artifact', type=Path)
    p.add_argument('--artifact', type=Path, default=Path('artifacts/wvs-pilot.sqlite'))
    a = p.parse_args()
    build(a.source, a.mappings, a.output, a.manifest, a.audit)
    if a.base_artifact:
        attach(a.base_artifact, a.output, a.artifact, corpus='wvs')


if __name__ == '__main__':
    main()
