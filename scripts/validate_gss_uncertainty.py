"""Compare the GSS pilot with samplics 0.4.31 in an optional isolated environment.

This is an offline validation tool, not a serving dependency. Item estimates
use independently calculated survey ratios. Composite checks validate PSU
variance aggregation of supplied linearizations, not their derivation.
"""
import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from samplics.estimation import TaylorEstimator
from samplics.utils.types import PopParam

from scvpublic.build import digest


def main():
    if version('samplics') != '0.4.31':
        raise ValueError('Validation requires samplics 0.4.31')
    pilot_path = Path('artifacts/gss-uncertainty.json')
    pilot = json.loads(pilot_path.read_text())
    for path, checksum in pilot['sources'].items():
        if digest(Path(path)) != checksum:
            raise ValueError(f'Pilot input changed: {path}')
    source = Path('data/raw/gss-2024-r3a/gss7224_r3a.dta')
    entries = json.loads(Path('data/gss/response_mappings.json').read_text())['entries']
    mappings = {e['code']: {int(k): v for k, v in e['scores'].items()} for e in entries}
    frame = pd.read_stata(source, convert_categoricals=False,
                          columns=['year', 'vstrat', 'vpsu', 'wtssps', 'wtssnrps', *mappings])
    item_rows = {(r['year'], r['code']): r for r in pilot['estimates']}
    composite_rows = {r['year']: r for r in pilot['abortion_composite']}
    checks = []
    for year, group in frame.groupby('year'):
        weights = group['wtssps' if year < 2004 else 'wtssnrps']
        group = group.loc[np.isfinite(weights) & (weights > 0)]
        weights = weights.loc[group.index].to_numpy()
        design = dict(stratum=group.vstrat.to_numpy(), psu=group.vpsu.to_numpy())
        for code, mapping in mappings.items():
            expected = item_rows.get((int(year), code))
            if not expected or expected.get('standard_error') is None:
                continue
            score = group[code].map(mapping).to_numpy()
            valid = np.isfinite(score)
            estimator = TaylorEstimator(PopParam.ratio)
            estimator.estimate(y=np.where(valid, score, 0.), x=valid.astype(float),
                               samp_weight=weights, **design)
            checks.append(dict(year=int(year), code=code, kind='item ratio',
                               mean_difference=float(estimator.point_est - expected['mean']),
                               se_difference=float(estimator.stderror - expected['standard_error'])))
        expected = composite_rows.get(int(year))
        if not expected or expected.get('standard_error') is None:
            continue
        linearized = np.zeros(len(group))
        for code in expected['items']:
            score = group[code].map(mappings[code]).to_numpy()
            valid = np.isfinite(score)
            denominator = weights[valid].sum()
            mean = np.sum(weights[valid] * score[valid]) / denominator
            linearized[valid] += weights[valid] * (score[valid] - mean) / denominator
        linearized /= len(expected['items'])
        # samplics computes a coefficient of variation even when coef_var=False;
        # a zero total raises ZeroDivisionError. Add exactly one per PSU. This
        # shifts every PSU total equally and leaves within-stratum variance intact.
        cluster_sizes = group.groupby(['vstrat', 'vpsu']).year.transform('size').to_numpy()
        estimator = TaylorEstimator(PopParam.total)
        estimator.estimate(y=linearized + 1. / cluster_sizes,
                           samp_weight=np.ones(len(group)), **design)
        checks.append(dict(year=int(year), kind='composite linearized total',
                           se_difference=float(estimator.stderror - expected['standard_error'])))
    tolerance = 1e-10
    failures = [r for r in checks if abs(r['se_difference']) > tolerance
                or abs(r.get('mean_difference', 0.)) > tolerance]
    report = dict(status='passed' if not failures else 'failed', tolerance=tolerance,
                  versions={p: version(p) for p in ['samplics', 'numpy', 'pandas', 'scipy']},
                  sources={str(p): digest(p) for p in [pilot_path, Path(__file__)]},
                  limitations=['Only years with supported design identifiers and no singleton strata.',
                               'Composite check validates aggregation of supplied linearizations, not an independent derivation.',
                               'Composite totals add one per PSU to avoid a zero-total coefficient-of-variation error; this leaves within-stratum variance unchanged.',
                               'Agreement between implementations does not validate survey measurement assumptions.'],
                  item_checks=sum(r['kind'] == 'item ratio' for r in checks),
                  composite_checks=sum(r['kind'] != 'item ratio' for r in checks),
                  checks=checks, failures=failures)
    Path('artifacts/gss-uncertainty-validation.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print({k: report[k] for k in ['status', 'item_checks', 'composite_checks']})
    if failures:
        raise AssertionError(f'{len(failures)} survey validation discrepancies')


if __name__ == '__main__':
    main()
