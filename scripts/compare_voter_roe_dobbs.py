"""Reproduce one prior-opinion/decision comparison without ideological scoring."""
import json
import math
from pathlib import Path
import pyreadstat
from scvpublic.build import digest


def main():
    manifest=Path('data/manifests/voter-policy-batch.json');spec=json.loads(manifest.read_text())
    for name,sha in spec['sources'].items():
        if digest(Path(name))!=sha:raise ValueError('Raw source checksum mismatch')
    entry=next(e for e in spec['entries'] if e['code']=='voter_roevwade');wave=entry['waves'][0]
    code=wave['code'];weight=wave['weight']
    frame,meta=pyreadstat.read_dta(spec['raw_path'],encoding=spec['encoding'],usecols=[code,weight])
    labels={str(int(k)):v for k,v in meta.variable_value_labels[code].items()}
    if labels!=wave['expected_labels']:raise ValueError('Changed response labels')
    if meta.column_names_to_labels[code]!=wave['expected_label']:raise ValueError('Changed question label')
    w=frame[weight];answer=frame[code]
    if any(not math.isfinite(v) or v<0 for v in w.dropna()):raise ValueError('Invalid weight')
    sample=w.notna() & w.gt(0)
    if answer[sample].isna().any():raise ValueError('Unaccounted missing response')
    counts={str(int(k)):int(v) for k,v in answer[sample].value_counts().items()}
    if counts!=wave['published_counts']:raise ValueError('Guide count mismatch')
    total=math.fsum(w[sample]);rows=[]
    names={'1':'Favor overturning Roe','2':'Oppose overturning Roe','3':'Not sure','8':'Skipped','9':'Not asked'}
    for k in sorted(labels,key=int):
        category=sample & answer.eq(int(k));amount=math.fsum(w[category])
        rows.append(dict(code=k,response=names[k],unweighted_count=int(category.sum()),weight_sum=amount,weighted_percent=100*amount/total))
    if abs(sum(r['weighted_percent'] for r in rows)-100)>1e-10:raise ValueError('Shares do not sum to 100')
    # Independent cross-check with a grouped sum instead of the row masks above.
    grouped=frame.loc[sample].groupby(code)[weight].sum()
    for row in rows:
        if abs(float(grouped.get(int(row['code']),0))-row['weight_sum'])>1e-8:raise ValueError('Aggregation mismatch')
    report=dict(status='Single descriptive component comparison; not alignment tracker or forecast',
        survey=dict(release=spec['release'],fieldwork_start='2020-11-13',fieldwork_end='2020-12-07',
            question=wave['question'],response_label_note='Full no-response label on guide page 40 adds maintain abortion rights in all 50 states; raw Stata label is truncated.',
            variable=code,weight=weight,weight_rule='Guide page 4 recommends wave-specific genpop weight for cross-sectional analysis.',
            sample_description='YouGov online panel; 4,943 post-election respondents, drawn from adults invited after the September wave. Do not describe as a simple random sample or restrict to voters without additional filtering.',
            denominator='All positive-weight November-wave respondents, including not sure and skipped; no yes/no-only renormalization.',
            respondents=int(sample.sum()),weight_sum=total,responses=rows,guide_pages=[3,4,40],source_url=spec['source_url']),
        court=dict(case_id='2021-019',name='Dobbs v. Jackson Women’s Health Organization',decision_date='2022-06-24',
            component='Overruled Roe v. Wade (and Casey); not an estimate of support for every part of the opinion or subsequent restrictions.',
            source_url='https://www.supremecourt.gov/opinions/21pdf/19-1392_6j37.pdf'),
        interpretation='The weighted survey majority opposed overturning Roe in late 2020; the Court overruled Roe in June 2022. This is disagreement on that named component across those dates, not a contemporaneous estimate or causal claim.',
        limitations=['About 19 months between fieldwork and decision; attitudes may have changed.',
            'Question framing explicitly references a constitutional right and may affect responses.',
            'Panel recruitment, weighting and nonresponse can affect representativeness; no design-based confidence interval or significance claim.',
            'One selected example cannot estimate overall court-public agreement or predictiveness.',
            'Does not assess Mississippi\u2019s fifteen-week limit, all state restrictions, or the constitutional correctness of the decision.'],
        provenance={**spec['sources'],str(manifest):digest(manifest),str(Path(__file__)):digest(Path(__file__))})
    Path('data/research/voter-roe-dobbs-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(respondents=int(sample.sum()),weight_sum=total,responses=rows),indent=2))


if __name__=='__main__':main()
