"""Extend CES policy documents with an explicitly reviewed annual crosswalk."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from .build import digest
from .ces import respondent_ids


def extend_documents(base, frame, crosswalk):
    import numpy as np
    wave = crosswalk['wave']
    supported = wave == 'pre-election' or (wave == 'post-election-only' and crosswalk['year'] % 2 == 1)
    if not supported or crosswalk['weight'] != 'commonweight':
        raise ValueError('Unsupported CES wave/weight combination')
    ids = respondent_ids(frame['caseid'])
    if ids.duplicated().any():
        raise ValueError('Duplicate annual CES respondent IDs')
    result = deepcopy(base)
    documents = {q['code']: q for q in result['documents']}
    year = str(crosswalk['year'])
    audit = []
    seen = set()
    for entry in crosswalk['entries']:
        question_text = entry.get('question_text') or entry.get('question_text_'+year)
        if not question_text:
            raise ValueError('Missing question wording for annual year '+year)
        code = entry['code']
        if code in seen:
            raise ValueError('Duplicate crosswalk target')
        seen.add(code)
        if entry['existing_item'] != (code in documents):
            raise ValueError('Crosswalk item identity differs from base')
        scores = {int(k): v for k, v in entry['scores'].items()}
        answers = frame[entry['source_code']]
        unknown = answers.notna() & ~answers.isin([*scores, 8, 9])
        if unknown.any():
            raise ValueError('Unreviewed response code: ' + entry['source_code'])
        weights = frame[crosswalk['weight']]
        scored = answers.map(scores)
        valid = scored.notna() & np.isfinite(weights) & (weights > 0)
        if not valid.any():
            raise ValueError('No usable responses: ' + code)
        if code not in documents:
            documents[code] = dict(code=code, title=entry.get('title',question_text),
                question='Support or oppose: '+question_text+'?',
                family=entry['family'], priority=0, dataset='CES', scores=entry['scores'],
                weight=crosswalk['weight'], measurement_type='policy',
                rationale=entry['harmonization'], question_note=year+' '+wave+' policy item.',
                source_url='https://doi.org/'+crosswalk['doi'],
                years={}, respondents={}, weight_sums={})
            result['documents'].append(documents[code])
        document = documents[code]
        if year in document['years']:
            raise ValueError('Refusing to replace an existing CES year: '+code)
        if document['family'] != entry['family'] or document['scores'] != entry['scores']:
            raise ValueError('Existing item scoring or family differs')
        weight_sum = float(weights[valid].sum())
        mean = float((weights[valid]*scored[valid]).sum()/weight_sum)
        document['years'][year] = mean
        document['respondents'][year] = int(valid.sum())
        document['weight_sums'][year] = weight_sum
        document.setdefault('year_provenance', {})[year] = dict(
            source_code=entry['source_code'], weight=crosswalk['weight'], wave=wave,
            question=question_text, doi=crosswalk['doi'],
            harmonization=entry['harmonization'])
        audit.append(dict(code=code, source_code=entry['source_code'], year=int(year),
            valid_responses=int(valid.sum()), excluded=int((~valid).sum()), mean=mean,
            weight_sum=weight_sum))
    result['annual_import_audit'] = dict(rows=len(frame), year=int(year), entries=audit)
    result['release'] = str(result['release'])+'; CES '+year+' reviewed annual extension'
    result['notes'] = ('CES weighted annual policy responses, including a reviewed '+year+
        ' extension. Missing answers and invalid weights excluded. Question wording and available policies vary by year.')
    return result


def main():
    import pandas as pd
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=Path('data/processed/ces-policy/public.json'))
    parser.add_argument('--manifest', type=Path, default=Path('data/manifests/ces-2024-v9.json'))
    parser.add_argument('--crosswalk', type=Path, default=Path('data/research/ces_2024_crosswalk.json'))
    parser.add_argument('--output', type=Path, default=Path('data/processed/ces-2024-candidate/public.json'))
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    manifest = json.loads(args.manifest.read_text())
    crosswalk = json.loads(args.crosswalk.read_text())
    paths = []
    for record in manifest['files']:
        path = Path(record['path'])
        if digest(path) != record['sha256']:
            raise ValueError('Annual source checksum mismatch')
        paths.append(path)
    for name, checksum in crosswalk['sources'].items():
        if digest(Path(name)) != checksum:
            raise ValueError('Crosswalk source changed: '+name)
    response_paths = [p for p in paths if p.suffix in ('.csv', '.dta')]
    if len(response_paths) != 1:
        raise ValueError('Expected one response CSV or Stata file')
    columns = ['caseid', crosswalk['weight']]+[e['source_code'] for e in crosswalk['entries']]
    source = response_paths[0]
    frame = (pd.read_csv(source, usecols=columns) if source.suffix == '.csv'
             else pd.read_stata(source, columns=columns, convert_categoricals=False))
    if len(frame) != manifest['rows']:
        raise ValueError('Unexpected respondent count')
    base = json.loads(args.base.read_text())
    result = extend_documents(base, frame, crosswalk)
    result['sources'].update({str(p): digest(p) for p in paths+
        [args.base, args.manifest, args.crosswalk, Path(__file__)]})
    from .survey_schema import prepare
    prepare(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result['annual_import_audit'], indent=2))


if __name__ == '__main__':
    main()
