"""Weight-concentration diagnostics, not design-based CES confidence intervals."""
import argparse
import csv
import json
import math
from pathlib import Path

from scvpublic.build import digest


def source_rows(path, columns):
    if path.suffix == '.dta':
        import pandas as pd
        frame = pd.read_stata(path, columns=columns, convert_categoricals=False)
        yield from frame.to_dict(orient='records')
    elif path.suffix == '.csv':
        with path.open() as handle:
            yield from csv.DictReader(handle)
    else:
        raise ValueError('Unsupported response format')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--crosswalk', type=Path, default=Path('data/research/ces_2024_historical_crosswalk.json'))
    p.add_argument('--candidate', type=Path, default=Path('data/processed/ces-expanded-candidate/public.json'))
    p.add_argument('--output', type=Path, default=Path('artifacts/ces-2024-weight-diagnostics.json'))
    p.add_argument('--source', type=Path, default=Path('data/raw/ces-2024-v9/responses.csv'))
    args = p.parse_args()
    source = args.source
    mapping = json.loads(args.crosswalk.read_text())
    year = str(mapping['year'])
    documents = {d['code']: d for d in json.loads(args.candidate.read_text())['documents']}
    weights = {e['code']: [] for e in mapping['entries']}
    weighted_scores = {e['code']: [] for e in mapping['entries']}
    columns = [mapping['weight']]+[e['source_code'] for e in mapping['entries']]
    for row in source_rows(source, columns):
        raw_weight = row[mapping['weight']]
        weight = float(raw_weight) if raw_weight not in ('', None, 'NA', 'NaN', 'nan') else float('nan')
        if not math.isfinite(weight) or weight <= 0:
            continue
        for entry in mapping['entries']:
            answer = row[entry['source_code']]
            answer = float(answer) if answer not in ('', None, 'NA', 'NaN', 'nan') else float('nan')
            key = str(int(answer)) if math.isfinite(answer) and answer.is_integer() else None
            if key in entry['scores']:
                weights[entry['code']].append(weight)
                weighted_scores[entry['code']].append(weight * entry['scores'][key])
    results = {}
    for code, values in weights.items():
        n = len(values)
        total = math.fsum(values)
        squares = math.fsum(w*w for w in values)
        effective_n = total*total/squares
        assert 0 < effective_n <= n*(1+1e-12)
        assert abs(math.fsum(weighted_scores[code])/total - documents[code]['years'][year]) < 1e-10
        assert n == documents[code]['respondents'][year]
        assert math.isclose(total, documents[code]['weight_sums'][year], rel_tol=1e-10)
        results[code] = dict(n=n, kish_effective_n=effective_n,
            weight_only_design_effect=n/effective_n,
            maximum_normalized_weight_share=max(values)/total)
    args.output.write_text(json.dumps(dict(
        status='weight-concentration diagnostic only', items=results,
        formula='Kish effective n = (sum w)^2 / sum(w^2)',
        limitations=['Not a survey-design variance estimate or confidence interval.',
            'Does not capture opt-in selection bias, matching, calibration, clustering, or outcome-weight relationships.',
            'Different questions share respondents; item sample sizes must not be summed.',
            'Published weights may use information unavailable at the interview date; publication vintage must be checked before predictive use.'],
        sources={str(p): digest(p) for p in [source, args.crosswalk, args.candidate, Path(__file__)]}
    ), indent=2)+'\n')
    print(json.dumps(dict(items=len(results), min_effective_n=min(x['kish_effective_n'] for x in results.values()),
        max_effective_n=max(x['kish_effective_n'] for x in results.values())), indent=2))


if __name__ == '__main__':
    main()
