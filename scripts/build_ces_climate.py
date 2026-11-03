"""Append reviewed historical CES climate items to an existing survey artifact."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

from scvpublic.build import digest
from scvpublic.ces import join_weights
from scvpublic.ces_annual import extend_documents
from scvpublic.gss import attach
from scvpublic.public import validate
from scvpublic.store import connect, metadata
from scvpublic.survey_schema import prepare


def score_item(frame, entry):
    """Check published unweighted frequencies before computing weighted scores."""
    doc = {k: deepcopy(v) for k, v in entry.items() if k not in
           ('years', 'published_counts', 'expected_labels', 'original_codes')}
    doc.update(dataset='CES', years={}, respondents={}, weight_sums={}, year_provenance={})
    audit = []
    scores = {int(k): v for k, v in entry['scores'].items()}
    for year in entry['years']:
        group = frame.loc[frame.year == year]
        answers = group[entry['source_code']]
        counts = {str(int(k)): int(v) for k, v in answers.value_counts().items()}
        if counts != entry['published_counts'][str(year)]:
            raise ValueError(f'Published frequencies differ: {entry["code"]} {year}')
        if not answers.dropna().isin(scores).all():
            raise ValueError('Unreviewed response code')
        weights = group[entry['weight']]
        valid = answers.isin(scores) & np.isfinite(weights) & (weights > 0)
        if not valid.any():
            raise ValueError('No usable responses')
        total = float(weights[valid].sum())
        mean = float((answers[valid].map(scores) * weights[valid]).sum() / total)
        by_answer = weights[valid].groupby(answers[valid]).sum()
        independent = sum(float(w) * scores[int(a)] for a, w in by_answer.items()) / total
        if not np.isclose(mean, independent, rtol=0, atol=1e-12):
            raise ValueError('Grouped score differs')
        y = str(year)
        doc['years'][y] = mean
        doc['respondents'][y] = int(valid.sum())
        doc['weight_sums'][y] = total
        doc['year_provenance'][y] = dict(source_code=entry['original_codes'][y],
            cumulative_code=entry['source_code'], weight='weight',
            wave='pre-election/single-wave', question=entry['question'],
            doi='10.7910/DVN/OSXDQO')
        audit.append(dict(code=entry['code'], year=year, frequencies=counts,
            weighted_mean=mean, valid_responses=int(valid.sum()),
            invalid_weight_responses=int((answers.notna() & ~valid).sum())))
    return doc, audit


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-artifact', type=Path, required=True)
    p.add_argument('--artifact', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--audit', type=Path, required=True)
    p.add_argument('--mappings', type=Path, default=Path('data/ces/climate-mappings.json'))
    args = p.parse_args()
    for path in (args.artifact, args.output, args.audit):
        if path.exists():
            raise FileExistsError(path)
    manifest_path = Path('data/manifests/ces-policy-v3.json')
    manifest = json.loads(manifest_path.read_text())
    sources = {}
    for record in manifest['files']:
        path = Path('data/raw') / record['path']
        if digest(path) != record['sha256']:
            raise ValueError('Source checksum changed: ' + str(path))
        sources[str(path)] = record['sha256']
    spec = json.loads(args.mappings.read_text())
    validate(dict(spec, version='explicit-anes-v1'))
    policy_path = Path('data/raw/ces-policy/responses.dta')
    _, meta = pyreadstat.read_dta(policy_path, metadataonly=True)
    for entry in spec['entries']:
        labels = {str(k): v for k, v in meta.variable_value_labels[entry['source_code']].items()}
        if labels != entry['expected_labels']:
            raise ValueError('Response labels changed')
    policy = pd.read_stata(policy_path, convert_categoricals=False,
        columns=['year', 'case_id'] + sorted({e['source_code'] for e in spec['entries']}))
    weights = pd.read_feather('data/raw/ces-policy/common.feather', columns=['year', 'case_id', 'weight'])
    frame = join_weights(policy, weights)
    with connect(args.base_artifact) as db:
        info = metadata(db)
        docs = [json.loads(v) for v, in db.execute("SELECT payload FROM documents WHERE corpus='ces' ORDER BY id")]
    existing = {d['code'] for d in docs}
    audit = []
    for entry in spec['entries']:
        if entry['code'] in existing:
            raise ValueError('Refusing to replace existing CES item')
        doc, checks = score_item(frame, entry)
        docs.append(doc)
        audit.extend(checks)
    for path in (args.base_artifact, args.mappings, manifest_path, Path(__file__)):
        sources[str(path)] = digest(path)
    payload = prepare(dict(methodology='explicit-ces-v1', documents=docs,
        release=info['ces_release']+'; reviewed climate extension',
        notes=info['ces_notes']+' '+spec['notes'], sources={**info['ces_sources'], **sources}))
    annual = spec['annual']
    annual_manifest = Path(annual['manifest'])
    annual_spec = json.loads(annual_manifest.read_text())
    for record in annual_spec['files']:
        path = Path(record['path'])
        if digest(path) != record['sha256']:
            raise ValueError('Annual source checksum changed')
        sources[str(path)] = record['sha256']
    sources[str(annual_manifest)] = digest(annual_manifest)
    frame = pd.read_csv('data/raw/ces-2022-v4/responses.csv',
        usecols=['caseid', 'commonweight']+[e['source_code'] for e in annual['entries']])
    if len(frame) != annual_spec['rows']:
        raise ValueError('Annual respondent count changed')
    payload = extend_documents(payload, frame, annual)
    for entry in annual['entries']:
        answers = frame[entry['source_code']]
        scores = {int(k): v for k, v in entry['scores'].items()}
        counts = {str(int(k)): int(v) for k, v in answers[answers.isin(scores)].value_counts().items()}
        if counts != entry['published_counts']:
            raise ValueError('Annual published frequencies differ: '+entry['code'])
        valid = answers.isin(scores) & np.isfinite(frame.commonweight) & (frame.commonweight > 0)
        grouped = frame.loc[valid].groupby(entry['source_code']).commonweight.sum()
        mean = sum(float(w)*scores[int(a)] for a, w in grouped.items()) / float(grouped.sum())
        doc = next(d for d in payload['documents'] if d['code'] == entry['code'])
        if not np.isclose(mean, doc['years']['2022'], rtol=0, atol=1e-12):
            raise ValueError('Annual grouped score differs')
        audit.append(dict(code=entry['code'], year=2022, frequencies=counts, weighted_mean=mean,
            valid_responses=int(valid.sum()), invalid_weight_responses=int((answers.isin(scores) & ~valid).sum())))
    payload['sources'].update(sources)
    prepare(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, allow_nan=False)+'\n')
    attach(args.base_artifact, args.output, args.artifact, corpus='ces')
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(dict(sources=sources, checks=audit, deferred=spec['deferred']), indent=2)+'\n')
    print(json.dumps(dict(added_questions=len(spec['entries'])+sum(not e['existing_item'] for e in annual['entries']), added_question_years=len(audit))))


if __name__ == '__main__':
    main()
