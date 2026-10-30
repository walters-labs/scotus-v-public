"""Offline CES policy scoring with explicit response maps and joined survey weights."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

from .build import digest
from .gss import attach
from .public import aggregate, validate


def respondent_ids(values):
    import pandas as pd
    numbers = pd.to_numeric(values, errors='raise')
    if numbers.isna().any() or (numbers % 1 != 0).any():
        raise ValueError('Missing or nonintegral CES respondent ID')
    return numbers.astype('int64')


def join_weights(policy, weights):
    policy, weights = policy.copy(), weights.copy()
    for frame in (policy, weights):
        frame['case_id'] = respondent_ids(frame['case_id'])
    return policy.merge(weights, on=['year', 'case_id'], how='left',
                        validate='one_to_one', indicator=True)


def aggregate_ces(frame, entries, totals):
    frame = frame.copy()
    frame['VCF0004'] = frame['year']
    for entry in entries:
        selected = frame.loc[~frame['year'].isin(entry['exclude_years'])]
        aggregate(selected, [entry], totals)


def build(manifest, mappings, output):
    import pandas as pd
    spec = json.loads(manifest.read_text())
    paths = [Path('data/raw')/f['path'] for f in spec['files']]
    for path, record in zip(paths, spec['files']):
        if digest(path) != record['sha256']:
            raise ValueError('CES source checksum mismatch: '+str(path))
    mapping = json.loads(mappings.read_text())
    if mapping['version'] != 'explicit-ces-v1':
        raise ValueError('Unsupported CES mapping')
    validate(dict(mapping, version='explicit-anes-v1'))
    entries = mapping['entries']
    if any(e['weight'] != 'weight' for e in entries):
        raise ValueError('This CES pilot supports pre-election/single-wave items only')
    policy = pd.read_stata('data/raw/ces-policy/responses.dta',
        columns=['year', 'case_id']+[e['code'] for e in entries], convert_categoricals=False)
    weights = pd.read_feather('data/raw/ces-policy/common.feather',
        columns=['year', 'case_id', 'weight'])
    frame = join_weights(policy, weights)
    totals = defaultdict(lambda: [0., 0., 0])
    aggregate_ces(frame, entries, totals)
    documents = []
    for entry in entries:
        years = {str(y): t for (code, y), t in sorted(totals.items())
                 if code == entry['code'] and t[1] > 0}
        documents.append(dict(entry, dataset='CES',
            years={y: t[0]/t[1] for y, t in years.items()},
            respondents={y: t[2] for y, t in years.items()},
            weight_sums={y: t[1] for y, t in years.items()}))
    payload = dict(methodology=mapping['version'], documents=documents,
        release='CES Policy Preferences V3 (2008–2021 pilot)', notes=mapping['notes'],
        sources={str(p): digest(p) for p in paths+[manifest, mappings]},
        join_audit=dict(rows=len(frame), unmatched=int((frame['_merge'] != 'both').sum())))
    from .survey_schema import prepare
    prepare(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False)+'\n')
    temporary.replace(output)
    print(json.dumps(dict(documents=len(documents), families=len({d['family'] for d in documents}),
                         question_years=sum(len(d['years']) for d in documents), **payload['join_audit'])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('data/manifests/ces-policy-v3.json'))
    parser.add_argument('--mappings', type=Path, default=Path('data/ces/response_mappings.json'))
    parser.add_argument('--output', type=Path, default=Path('data/processed/ces-policy/public.json'))
    parser.add_argument('--base-artifact', type=Path)
    parser.add_argument('--artifact', type=Path, default=Path('artifacts/ces-pilot.sqlite'))
    args = parser.parse_args()
    build(args.manifest, args.mappings, args.output)
    if args.base_artifact:
        attach(args.base_artifact, args.output, args.artifact, corpus='ces')


if __name__ == '__main__':
    main()
