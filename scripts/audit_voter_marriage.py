"""Verify the 2016 VOTER marriage estimate and denominator sensitivity."""
import hashlib
import json
from pathlib import Path
import math
import pyreadstat


def audit():
    m=json.loads(Path('data/manifests/voter-policy-batch.json').read_text())
    for filename,expected in m['sources'].items():
        with open(filename,'rb') as stream:
            assert hashlib.file_digest(stream,'sha256').hexdigest()==expected
    wave=next(e for e in m['entries'] if e['code']=='voter_marriage')['waves'][0]
    code,weight=wave['code'],wave['weight']
    frame,meta=pyreadstat.read_dta(m['raw_path'],encoding=m['encoding'],usecols=[code,weight])
    assert {str(int(k)):v for k,v in meta.variable_value_labels[code].items()}==wave['expected_labels']
    not_asked=frame[code].eq(99) | frame[code].isna()
    assert not frame.loc[not_asked,weight].fillna(0).gt(0).any()
    excluded_answered=int((~not_asked & ~frame[weight].gt(0)).sum())
    frame=frame.loc[~not_asked & frame[weight].gt(0)]
    counts={str(int(k)):int(v) for k,v in frame[code].value_counts().items()}
    assert counts==wave['published_counts']
    amounts=frame.groupby(code)[weight].sum()
    total=float(amounts.sum())
    records=json.loads(Path('data/research/marriage-case-study.json').read_text())['survey_records']
    voter=next(r for r in records if r['source']=='VOTER' and r['year']==2016)
    for code,group in [(1,'support'),(2,'oppose'),(8,'unsure'),(98,'nonresponse')]:
        assert math.isclose(100*amounts[code]/total,voter['percent'][group],abs_tol=1e-8)
    lines=['# VOTER marriage audit — 2016','',
        f'The file also contains {excluded_answered} answered records without positive wave weights; these are excluded from the weighted population. Raw-file and guide hashes verified against the manifest. Response counts match the published guide: 4,213 favor, 2,809 oppose, 956 unsure, 22 skipped (8,000 total).',
        '', 'The guide specifies weight_genpop for cross-sectional estimates (p. 4). Fieldwork was November 29–December 29, 2016 (p. 2), reinterviewing an earlier panel. The item and counts are on p. 368.',
        '', '[Original guide](https://www.voterstudygroup.org/uploads/reports/Data/VOTER-Survey-Guide-2021Dec.pdf)',
        '', '| Source | Reported support % | Support among support/oppose only % |', '| --- | ---: | ---: |']
    for r in records:
        if r['year']==2016:
            p=r['percent'];lines.append(f"| {r['source']} | {p['support']:.2f} | {100*p['support']/(p['support']+p['oppose']):.2f} |")
    lines += ['',f'Unweighted VOTER support: {100*counts["1"]/sum(counts.values()):.2f}%. Weighted support: {voter["percent"]["support"]:.2f}%. Weighting increases the relative contribution of unsure respondents; it is not a coding error.',
        '', 'The common binary denominator reduces the CES–VOTER difference from 11.69 to 2.93 percentage points. It does not harmonize survey populations, timing, modes, wording or question context. GSS includes a substantive neutral category, so its binary sensitivity estimate also excludes neutral responses. These are diagnostics, not replacement estimates.',
        '', 'Decision: retain source-specific percentages and weights, show the denominator explanation in the marriage overview, and do not pool the surveys. No causal explanation of the remaining gaps or statistical significance is established. No raw inputs or search scores changed.']
    Path('docs/VOTER_MARRIAGE_AUDIT.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))


if __name__=='__main__':
    audit()
