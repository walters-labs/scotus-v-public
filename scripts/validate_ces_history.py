"""Independently recalculate historical CES environment means using keyed weights."""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path

import pandas as pd
from scvpublic.build import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    args = parser.parse_args()
    base = Path('data/processed/ces-policy/public.json')
    policy = Path('data/raw/ces-policy/responses.dta')
    common = Path('data/raw/ces-policy/common.feather')
    payload = json.loads(args.candidate.read_text())
    documents = {d['code']: d for d in payload['documents']}
    for old in json.loads(base.read_text())['documents']:
        for field in ['years', 'respondents', 'weight_sums']:
            for year, value in old[field].items():
                assert documents[old['code']][field][year] == value
    columns = ['enviro_carbon', 'enviro_renewable', 'enviro_airwateracts']
    frame = pd.read_stata(policy, columns=['year', 'case_id']+columns,
                          convert_categoricals=False)
    weights_frame = pd.read_feather(common, columns=['year', 'case_id', 'weight'])
    assert not weights_frame.duplicated(['year', 'case_id']).any()
    assert not frame.duplicated(['year', 'case_id']).any()
    weights = {(int(y), int(i)): w for y, i, w in
               weights_frame.itertuples(index=False, name=None)}
    totals = defaultdict(lambda: [0, 0., 0.])
    for year, respondent, *answers in frame.itertuples(index=False, name=None):
        weight = weights.get((int(year), int(respondent)), float('nan'))
        if not math.isfinite(weight) or weight <= 0:
            continue
        for code, answer in zip(columns, answers):
            if answer not in (1, 2) or (code == 'enviro_airwateracts' and year == 2014):
                continue
            total = totals[code, str(int(year))]
            total[0] += 1
            total[1] += weight
            total[2] += weight * (1 if answer == 1 else -1)
    for (code, year), (count, weight, score) in totals.items():
        assert documents[code]['respondents'][year] == count
        assert abs(documents[code]['years'][year] - score/weight) < 1e-10
        assert math.isclose(documents[code]['weight_sums'][year], weight, rel_tol=1e-10)
    assert len(totals) == 23
    print(json.dumps(dict(status='passed', historical_item_years=len(totals),
        sources={str(p): digest(p) for p in [args.candidate, base, policy, common, Path(__file__)]}), indent=2))


if __name__ == '__main__':
    main()
