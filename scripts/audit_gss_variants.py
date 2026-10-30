"""Check a candidate GSS import against unique respondent-level variant unions."""
import json
from pathlib import Path
import pandas as pd
from scvpublic.build import digest


def main():
    raw = Path('data/raw/gss-2024-r3a/gss7224_r3a.dta')
    mapping = Path('data/research/gss_grid_candidate_mappings.json')
    candidate = Path('data/processed/gss-grid-candidate/public.json')
    payload = json.loads(candidate.read_text())
    for p in [raw, mapping]:
        if payload['sources'][str(p.resolve())] != digest(p):
            raise ValueError('Candidate source mismatch')
    entries = json.loads(mapping.read_text())['entries']
    codes = [e['code'] for e in entries if e.get('variants')]
    frame = pd.read_stata(raw, convert_categoricals=False,
        columns=['year', 'wtssnrps']+codes+[c+'g' for c in codes])
    documents = {q['code']: q for q in payload['documents']}
    records = []
    for year, group in frame[frame.year.isin([2021, 2022, 2024])].groupby('year'):
        for code in codes:
            standard = group[code].isin([1, 2])
            grid = group[code+'g'].isin([1, 2])
            overlap = standard & grid
            conflicts = overlap & (group[code] != group[code+'g'])
            if conflicts.any():
                raise ValueError('Conflicting variant answers')
            response = group[code].where(standard, group[code+'g'])
            usable = response.isin([1, 2]) & group.wtssnrps.notna() & (group.wtssnrps > 0)
            score = response.map({1: 1., 2: -1.})
            value = float((score[usable]*group.wtssnrps[usable]).sum()/group.wtssnrps[usable].sum())
            document = documents[code]
            if int(usable.sum()) != document['respondents'][str(int(year))] or abs(value-document['years'][str(int(year))]) > 1e-10:
                raise ValueError('Candidate disagrees with unique-respondent union')
            old = standard & group.wtssnrps.notna() & (group.wtssnrps > 0)
            old_mean = float((score[old]*group.wtssnrps[old]).sum()/group.wtssnrps[old].sum())
            records.append(dict(year=int(year), code=code, standard_valid=int(standard.sum()),
                additional_grid_valid=int((grid & ~standard).sum()), overlap=int(overlap.sum()),
                conflicts=0, weighted_valid=int(usable.sum()), original_mean=old_mean,
                candidate_mean=value, change=value-old_mean))
    report = dict(status='candidate verified; not promoted',
        sources={str(p): digest(p) for p in [raw, mapping, candidate, Path(__file__)]},
        records=records,
        limitations=['Counts across questions are response counts, not distinct people.',
                     'Pooling presentation variants does not remove survey mode or measurement effects.',
                     'Candidate is separate from existing serving and research artifacts.'])
    Path('artifacts/gss-grid-audit.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()
