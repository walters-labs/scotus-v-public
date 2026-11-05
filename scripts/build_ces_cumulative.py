"""Append reviewed cumulative CES items using published-count validation."""
import argparse
from contextlib import closing
import json
from pathlib import Path

import pandas as pd
import pyreadstat

from build_ces_climate import score_item
from scvpublic.build import digest
from scvpublic.ces import join_weights
from scvpublic.gss import attach
from scvpublic.public import validate
from scvpublic.store import connect, metadata
from scvpublic.survey_schema import prepare


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('base-artifact', 'artifact', 'output', 'audit', 'mappings', 'documents-manifest'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args()
    for path in (args.artifact, args.output, args.audit):
        if path.exists():
            raise FileExistsError(path)
    manifest_path = Path('data/manifests/ces-policy-v3.json')
    manifest = json.loads(manifest_path.read_text())
    sources = {}
    records = [dict(r, path=str(Path('data/raw')/r['path'])) for r in manifest['files']]
    records += json.loads(args.documents_manifest.read_text())
    for record in records:
        path = Path(record['path'])
        if digest(path) != record['sha256']:
            raise ValueError('CES source checksum changed: '+str(path))
        sources[str(path)] = record['sha256']
    spec = json.loads(args.mappings.read_text())
    validate(dict(spec, version='explicit-anes-v1'))
    if any(e['weight'] != 'weight' for e in spec['entries']):
        raise ValueError('Only pre-election/single-wave weights are supported')
    raw = 'data/raw/ces-policy/responses.dta'
    _, meta = pyreadstat.read_dta(raw, metadataonly=True)
    for entry in spec['entries']:
        labels = {str(k): v for k, v in meta.variable_value_labels[entry['source_code']].items()}
        if labels != entry['expected_labels']:
            raise ValueError('CES response labels changed')
    policy = pd.read_stata(raw, convert_categoricals=False,
        columns=['year', 'case_id']+sorted({e['source_code'] for e in spec['entries']}))
    weights = pd.read_feather('data/raw/ces-policy/common.feather', columns=['year','case_id','weight'])
    frame = join_weights(policy, weights)
    included_years = {y for e in spec['entries'] for y in e['years']}
    if (frame.loc[frame.year.isin(included_years), '_merge'] != 'both').any():
        raise ValueError('Unmatched CES respondents in included years')
    with closing(connect(args.base_artifact)) as db:
        info = metadata(db)
        docs = [json.loads(v) for v, in db.execute("SELECT payload FROM documents WHERE corpus='ces' ORDER BY id")]
    existing = {d['code'] for d in docs}
    checks = []
    for entry in spec['entries']:
        if entry['code'] in existing:
            raise ValueError('Refusing to replace existing CES item')
        doc, audit = score_item(frame, entry)
        docs.append(doc)
        checks.extend(audit)
    for path in (args.base_artifact,args.mappings,args.documents_manifest,manifest_path,
                 Path(__file__),Path('scripts/build_ces_climate.py')):
        sources[str(path)] = digest(path)
    payload = prepare(dict(methodology='explicit-ces-v1',documents=docs,
        release=info['ces_release']+'; reviewed affirmative-action extension',
        notes=info['ces_notes']+' '+spec['notes'], sources={**info['ces_sources'],**sources}))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
    attach(args.base_artifact,args.output,args.artifact,corpus='ces')
    args.audit.parent.mkdir(parents=True,exist_ok=True)
    args.audit.write_text(json.dumps(dict(sources=sources,checks=checks,deferred=spec['deferred']),indent=2)+'\n')
    print(json.dumps(dict(added_records=len(spec['entries']),added_question_years=len(checks))))


if __name__ == '__main__':
    main()
