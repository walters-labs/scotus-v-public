"""Build reviewed PRRI AVS questions; raw files are never needed by Flask."""
import argparse
import json
import math
from pathlib import Path

from .build import digest
from .survey_schema import prepare


def summarize(frame, wave, scores, labels, value_labels):
    code, weight = wave['source_code'], wave['weight']
    if labels[code] != wave['expected_label'] or value_labels != wave['expected_labels']:
        raise ValueError('PRRI labels changed: ' + code)
    allowed = {float(k) for k in value_labels}
    if set(frame[code].dropna()) - allowed:
        raise ValueError('Unexpected PRRI response: ' + code)
    weights = frame[weight]
    valid_weights = weights.gt(0) & weights.lt(float('inf'))
    data = frame.loc[valid_weights]
    distribution = {str(int(k)): float(v) for k, v in data.groupby(code)[weight].sum().items()}
    total = math.fsum(data[weight])
    if not total:
        raise ValueError('No positive finite PRRI weights')
    percentages = {k: 100*distribution.get(k, 0)/total for k in scores}
    for k, expected in wave['published_percentages'].items():
        if abs(percentages[k]-expected) > .51:
            raise ValueError(f'PRRI topline mismatch: {wave["year"]} {code} {k}')
    mapped = data[code].map({float(k):v for k,v in scores.items()})
    valid = mapped.notna()
    denominator = math.fsum(data.loc[valid, weight])
    if not denominator:
        raise ValueError('No scored PRRI answers')
    mean = math.fsum(mapped[valid]*data.loc[valid, weight])/denominator
    grouped = math.fsum(distribution.get(k, 0)*s for k,s in scores.items())/math.fsum(distribution.get(k, 0) for k in scores)
    if abs(mean-grouped) > 1e-10:
        raise ValueError('PRRI grouped validation failed')
    return mean, int(valid.sum()), denominator, percentages


def build(manifest, documents_manifest, mappings, output):
    import pyreadstat
    if output.exists():
        raise FileExistsError(output)
    mapping = json.loads(mappings.read_text())
    if mapping['version'] != 'explicit-prri-v1':
        raise ValueError('Unsupported PRRI mapping')
    files = {f['path']:f['sha256'] for f in json.loads(manifest.read_text())['files']}
    files.update({f['path']:f['sha256'] for f in json.loads(documents_manifest.read_text())})
    sources = {str(p):digest(p) for p in (manifest, documents_manifest, mappings)}
    documents, audit = [], []
    for entry in mapping['entries']:
        d = {k:v for k,v in entry.items() if k != 'waves'}
        d.update(dataset='PRRI', years={}, respondents={}, weight_sums={}, year_provenance={})
        for wave in entry['waves']:
            year = str(wave['year'])
            if year in d['years']:
                raise ValueError('Duplicate PRRI question-year')
            raw = Path(f'data/raw/prri-avs-{year}/responses.dta')
            for p in (raw, raw.with_name('questionnaire.pdf')):
                if digest(p) != files[str(p)]:
                    raise ValueError('PRRI checksum mismatch: '+str(p))
                sources[str(p)] = files[str(p)]
            frame, meta = pyreadstat.read_dta(raw, usecols=[wave['source_code'],wave['weight']])
            values = {str(int(k)):v for k,v in meta.variable_value_labels[wave['source_code']].items()}
            mean, n, weight_sum, percentages = summarize(frame, wave, entry['scores'], meta.column_names_to_labels, values)
            d['years'][year], d['respondents'][year], d['weight_sums'][year] = mean, n, weight_sum
            d['year_provenance'][year] = {k:wave[k] for k in ('source_code','weight','question','doi','wave')}
            audit.append(dict(question=entry['code'], year=year, respondents=n, weighted_percentages=percentages, published_percentages=wave['published_percentages']))
        documents.append(d)
    payload = prepare(dict(methodology=mapping['version'], release='PRRI AVS 2018–2024 pilot', notes=mapping['notes'], sources=sources, documents=documents, validation=audit))
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False)+'\n')
    temporary.replace(output)
    print(json.dumps(dict(questions=len(documents), question_years=len(audit), output=str(output))))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, default=Path('data/manifests/prri-avs-acquisition.json'))
    p.add_argument('--documents-manifest', type=Path, default=Path('data/manifests/prri-policy-documents.json'))
    p.add_argument('--mappings', type=Path, default=Path('data/prri/response_mappings.json'))
    p.add_argument('--output', type=Path, default=Path('data/processed/prri-avs/public.json'))
    p.add_argument('--base-artifact', type=Path)
    p.add_argument('--artifact', type=Path, default=Path('artifacts/prri-pilot.sqlite'))
    a = p.parse_args()
    build(a.manifest, a.documents_manifest, a.mappings, a.output)
    if a.base_artifact:
        from .gss import attach
        attach(a.base_artifact, a.output, a.artifact, corpus='prri')


if __name__ == '__main__':
    main()
