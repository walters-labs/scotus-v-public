"""Compare GSS weight definitions in one current file; not historical-vintage recovery."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scvpublic.build import digest


def main():
    source = Path('data/raw/gss-2024-r3a/gss7224_r3a.dta')
    manifest = Path('data/manifests/gss-2024-r3a.json')
    mappings = Path('data/gss/response_mappings.json')
    protocol = Path('data/research/abortion_protocol.json')
    cohort_path = Path('artifacts/abortion-research-cohort.json')
    if digest(source) != json.loads(manifest.read_text())['dta_sha256']:
        raise ValueError('GSS checksum mismatch')
    codes = json.loads(protocol.read_text())['survey_codes']['GSS']
    entries = {e['code']: e for e in json.loads(mappings.read_text())['entries']}
    columns = ['year', 'wtssall', 'wtssnr', 'wtssps', 'wtssnrps'] + codes
    frame = pd.read_stata(source, convert_categoricals=False, columns=columns)
    cohort = json.loads(cohort_path.read_text())
    rows = []
    for year, group in frame.groupby('year'):
        # Match the original cohort: standard responses, not the later grid expansion.
        modern = group['wtssps' if year < 2004 else 'wtssnrps']
        legacy = group['wtssall' if year < 2004 else 'wtssnr']
        common_weights = np.isfinite(modern) & (modern > 0) & np.isfinite(legacy) & (legacy > 0)
        items = []
        modern_full = []
        for code in codes:
            score = group[code].map({int(k): v for k, v in entries[code]['scores'].items()})
            valid = score.notna() & np.isfinite(modern) & (modern > 0)
            if valid.any():
                modern_full.append(float(np.average(score[valid], weights=modern[valid])))
            common = score.notna() & common_weights
            if not common.any():
                continue
            m = float(np.average(score[common], weights=modern[common]))
            old = float(np.average(score[common], weights=legacy[common]))
            items.append(dict(code=code, respondents=int(common.sum()), modern=m,
                              legacy=old, difference=m-old))
        if not modern_full:
            continue
        reproduced = float(np.mean(modern_full))
        expected = cohort['survey_series']['GSS'][str(int(year))]
        if abs(reproduced - expected) > 1e-10:
            raise ValueError(f'Original cohort reproduction failed: {year}')
        # Only compare years with all seven items to hold questionnaire composition fixed.
        if len(items) != len(codes):
            continue
        m = float(np.mean([r['modern'] for r in items]))
        old = float(np.mean([r['legacy'] for r in items]))
        rows.append(dict(year=int(year), modern=m, legacy=old, difference=m-old,
                         modern_full_sample=reproduced, items=items))
    if not rows:
        raise ValueError('No comparable years')
    report = dict(status='retrospective weight sensitivity; not historically available estimates',
        method='Equal seven-item mean; modern and legacy weights applied to identical valid respondents within each item-year.',
        modern='WTSSPS before 2004, WTSSNRPS from 2004',
        legacy='WTSSALL before 2004, WTSSNR from 2004, as stored in current release',
        comparable_years=len(rows),
        mean_absolute_difference=float(np.mean([abs(r['difference']) for r in rows])),
        maximum_absolute_difference=max(abs(r['difference']) for r in rows),
        sign_disagreements=sum((r['modern'] > 0) != (r['legacy'] > 0) for r in rows),
        years=rows,
        sources={str(p): digest(p) for p in [source, manifest, mappings, protocol, cohort_path, Path(__file__)]},
        limitations=['Legacy variables in a current release are not certified historical values.',
                     'No sampling-error or significance calculation; differences describe weighting sensitivity.',
                     'Common-valid respondent restriction isolates weighting but can differ from either full weighted sample.',
                     'No grid responses; preserves original retrospective cohort definition.'])
    Path('artifacts/gss-weight-sensitivity.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: report[k] for k in ['comparable_years', 'mean_absolute_difference',
          'maximum_absolute_difference', 'sign_disagreements']}))


if __name__ == '__main__':
    main()
