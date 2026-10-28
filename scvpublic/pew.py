"""Offline Pew Wave 25 pilot with reviewed labels and standalone survey weights."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from .build import digest
from .public import aggregate, validate
from .gss import attach


def check_toplines(frame, entries):
    """Validate rounded published percentages using all weighted answers, including refusal."""
    report = {}
    for entry in entries:
        weights = frame[entry['weight']]
        keep = weights.notna() & (weights > 0) & (weights < float('inf'))
        denominator = float(weights[keep].sum())
        if denominator <= 0:
            raise ValueError('No usable Pew weights')
        actual = {code: float(weights[keep & (frame[entry['code']] == float(code))].sum())*100/denominator
                  for code in entry['published_percentages']}
        # Published '*' means <0.5%, encoded as zero here. Integer values rounded.
        if any(abs(actual[code]-expected) > .51 for code, expected in entry['published_percentages'].items()):
            raise ValueError('Pew topline mismatch: '+entry['code'])
        report[entry['code']] = actual
    return report


def build(manifest, mappings, output, audit):
    import pyreadstat
    spec=json.loads(manifest.read_text())
    for record in spec['files']:
        if digest(Path(record['path'])) != record['sha256']:
            raise ValueError('Pew input checksum mismatch: '+record['path'])
    mapping=json.loads(mappings.read_text())
    if mapping['version'] != 'explicit-pew-v1':
        raise ValueError('Unsupported Pew mapping')
    validate(dict(mapping,version='explicit-anes-v1'))
    entries=mapping['entries']
    if any(e['weight'] != 'WEIGHT_W25' for e in entries):
        raise ValueError('Wave 25 pilot requires its standalone weight')
    source=next(Path(r['path']) for r in spec['files'] if r['path'].endswith('.sav'))
    columns=[e['code'] for e in entries]+['WEIGHT_W25']
    frame,meta=pyreadstat.read_sav(str(source),usecols=columns,apply_value_formats=False)
    for e in entries:
        labels={str(int(k)):v for k,v in meta.variable_value_labels[e['code']].items()}
        if labels != e['expected_labels']:
            raise ValueError('Pew response labels changed: '+e['code'])
        if set(frame[e['code']].dropna())-set(map(float,e['expected_labels'])):
            raise ValueError('Unexpected Pew response codes: '+e['code'])
    percentages=check_toplines(frame,entries)
    frame['VCF0004']=mapping['year']
    totals=defaultdict(lambda:[0.,0.,0])
    aggregate(frame,entries,totals)
    documents=[]
    for e in entries:
        total=totals[e['code'],mapping['year']]
        if not total[1]:raise ValueError('No usable answers: '+e['code'])
        public_entry={k:v for k,v in e.items() if k not in ('expected_labels','published_percentages')}
        year=str(mapping['year'])
        documents.append(dict(public_entry,dataset='Pew',years={year:total[0]/total[1]},
                              respondents={year:total[2]},weight_sums={year:total[1]}))
    payload=dict(methodology=mapping['version'],documents=documents,release=spec['release'],notes=mapping['notes'],
                 sources={r['path']:r['sha256'] for r in spec['files']} | {str(mappings):digest(mappings),str(manifest):digest(manifest)})
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix('.tmp');temporary.write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n');temporary.replace(output)
    audit.parent.mkdir(parents=True,exist_ok=True)
    audit.write_text(json.dumps(dict(rows=len(frame),weight='WEIGHT_W25',topline_check='passed within rounding tolerance 0.51 percentage points',weighted_percentages=percentages),indent=2)+'\n')
    print(json.dumps(dict(questions=len(documents),year=mapping['year'],respondents=len(frame),topline_check='passed')))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,default=Path('data/manifests/pew-w25.json'))
    p.add_argument('--mappings',type=Path,default=Path('data/pew/response_mappings.json'))
    p.add_argument('--output',type=Path,default=Path('data/processed/pew-w25/public.json'))
    p.add_argument('--audit',type=Path,default=Path('data/pew/validation.json'))
    p.add_argument('--base-artifact',type=Path)
    p.add_argument('--artifact',type=Path,default=Path('artifacts/pew-pilot.sqlite'))
    a=p.parse_args();build(a.manifest,a.mappings,a.output,a.audit)
    if a.base_artifact:attach(a.base_artifact,a.output,a.artifact,corpus='pew')


if __name__=='__main__':main()
