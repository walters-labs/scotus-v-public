"""Offline VOTER import: reviewed mappings and guide-validated wave samples."""
from collections import defaultdict
import argparse
import json
import math
from pathlib import Path

from .build import digest
from .survey_schema import prepare


def summarize(answer, weight, scores, expected):
    """Use the weighted wave sample, excluding unmatched panel records."""
    allowed = {int(k) for k in expected['expected_labels']}
    if set(answer.dropna()) - allowed:
        raise ValueError('Unknown VOTER response code')
    if not scores or set(scores) - allowed or any(not math.isfinite(v) or not -1 <= v <= 1 for v in scores.values()):
        raise ValueError('Invalid VOTER score mapping')
    if (weight.dropna().lt(0) | weight.dropna().eq(float('inf')) | weight.dropna().eq(float('-inf'))).any():
        raise ValueError('Invalid VOTER weight')
    sample = weight.notna() & weight.gt(0)
    counts = {str(int(k)):int(v) for k,v in answer[sample].value_counts().items()}
    if counts != expected['published_counts']:
        raise ValueError('VOTER guide frequency mismatch: '+expected.get('code', ''))
    mapped = answer.map(scores)
    valid = sample & mapped.notna()
    denominator = math.fsum(weight[valid])
    if denominator <= 0:
        raise ValueError('No usable VOTER responses')
    mean = math.fsum(mapped[valid]*weight[valid])/denominator
    sums = {str(k):math.fsum(weight[sample & answer.eq(k)]) for k in sorted(allowed)}
    grouped = math.fsum(sums[str(k)]*v for k,v in scores.items())/math.fsum(sums[str(k)] for k in scores)
    if abs(mean-grouped)>1e-12:
        raise ValueError('VOTER aggregate mismatch')
    return dict(score=mean, respondents=int(valid.sum()), weight_sum=denominator,
                published_counts=counts, category_weight_sums=sums,
                excluded_unweighted_answers=int((mapped.notna() & ~sample).sum()))


def annualize(observations):
    """Equal observed-wave weights, retaining every wave's audit information."""
    grouped = defaultdict(list)
    seen = set()
    for item in observations:
        if item['source_code'] in seen:
            raise ValueError('Duplicate VOTER wave')
        seen.add(item['source_code'])
        grouped[item['year']].append(item)
    return {year: dict(
        score=math.fsum(w['score'] for w in waves)/len(waves),
        respondents=sum(w['respondents'] for w in waves),
        weight_sum=math.fsum(w['weight_sum'] for w in waves),
        waves=waves) for year, waves in sorted(grouped.items())}


def build(manifest, output):
    import pyreadstat
    if output.exists():
        raise FileExistsError(output)
    spec=json.loads(manifest.read_text())
    for filename, checksum in spec['sources'].items():
        if digest(Path(filename)) != checksum:
            raise ValueError('VOTER checksum mismatch: '+filename)
    columns=list(dict.fromkeys(x for e in spec['entries'] for w in e['waves'] for x in (w['code'], w['weight'])))
    frame,meta=pyreadstat.read_dta(spec['raw_path'],encoding=spec['encoding'],usecols=columns)
    documents=[]
    for entry in spec['entries']:
        scores={int(k):v for k,v in entry['scores'].items()}
        doc={k:v for k,v in entry.items() if k!='waves'}
        doc.update(years={},respondents={},weight_sums={},wave_provenance={})
        observations=[]
        for wave in entry['waves']:
            code,year=wave['code'],wave['year']
            labels={str(int(k)):v for k,v in meta.variable_value_labels[code].items()}
            if labels!=wave['expected_labels'] or meta.column_names_to_labels[code]!=wave['expected_label']:
                raise ValueError('VOTER labels changed: '+code)
            result=summarize(frame[code],frame[wave['weight']],scores,wave)
            observations.append(dict(year=year,source_code=code,weight=wave['weight'],question=wave['question'],guide_page=wave['guide_page'],**result))
        for year, result in annualize(observations).items():
            doc['years'][year]=result['score']
            doc['respondents'][year]=result['respondents']
            doc['weight_sums'][year]=result['weight_sum']
            doc['wave_provenance'][year]=result['waves']
        documents.append(doc)
    payload=prepare(dict(methodology='explicit-voter-v1',release=spec['release'],notes=spec['notes'],sources={**spec['sources'],str(manifest):digest(manifest)},documents=documents))
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
    temporary.replace(output)
    print(json.dumps({d['code']:d['years'] for d in documents}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=Path('data/manifests/voter-pilot.json'))
    parser.add_argument('--output',type=Path,default=Path('data/processed/voter-pilot/public.json'))
    parser.add_argument('--base-artifact',type=Path)
    parser.add_argument('--artifact',type=Path,default=Path('artifacts/voter-pilot.sqlite'))
    args=parser.parse_args()
    build(args.manifest,args.output)
    if args.base_artifact:
        from .gss import attach
        attach(args.base_artifact,args.output,args.artifact,corpus='voter')


if __name__=='__main__':
    main()
