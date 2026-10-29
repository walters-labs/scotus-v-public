"""Offline pilot of stratified PSU Taylor linearization for GSS question means.

Retains zero-contribution PSUs for missing questionnaire responses. Missing
design data and singleton strata are explicit failures, not zero uncertainty.
No finite-population correction. See the separate independent-validation report.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scvpublic.build import digest
from scvpublic.store import connect


def design_error(f):
    """Variance of supplied respondent linearizations with the full design."""
    if f[['stratum','psu']].isna().any().any():
        return dict(status='missing design identifiers',standard_error=None)
    totals=f.groupby(['stratum','psu']).linearized.sum()
    counts=totals.groupby(level=0).size()
    result=dict(strata=len(counts),psus=len(totals),design_df=int(len(totals)-len(counts)))
    if (counts<2).any():
        return dict(result,status='singleton stratum requires reviewed adjustment',standard_error=None)
    variance=0.
    for _,cluster_totals in totals.groupby(level=0):
        n=len(cluster_totals)
        variance+=n/(n-1)*float(((cluster_totals-cluster_totals.mean())**2).sum())
    return dict(result,status='pilot Taylor estimate',standard_error=float(np.sqrt(variance)))


def estimate(frame):
    f=frame.loc[np.isfinite(frame.weight) & (frame.weight>0)].copy()
    valid=np.isfinite(f.score)
    if not valid.any():
        return dict(status='no valid responses')
    denominator=float(f.loc[valid,'weight'].sum())
    mean=float((f.loc[valid,'weight']*f.loc[valid,'score']).sum()/denominator)
    f['linearized']=0.
    f.loc[valid,'linearized']=f.loc[valid,'weight']*(f.loc[valid,'score']-mean)/denominator
    return dict(mean=mean,respondents=int(valid.sum()),weight_sum=denominator,**design_error(f))


def estimate_composite(frame, columns):
    """Equal mean of observed item estimates, preserving shared-sample covariance."""
    f=frame.loc[np.isfinite(frame.weight) & (frame.weight>0)].copy()
    f['linearized']=0.
    components={}
    for column in columns:
        valid=np.isfinite(f[column])
        if not valid.any():continue
        item=estimate(f[['weight','stratum','psu',column]].rename(columns={column:'score'}))
        components[column]=item
        f.loc[valid,'linearized']+=f.loc[valid,'weight']*(f.loc[valid,column]-item['mean'])/item['weight_sum']
    if not components:return dict(status='no valid responses')
    n=len(components)
    f.linearized/=n
    errors=[r.get('standard_error') for r in components.values()]
    return dict(mean=float(np.mean([r['mean'] for r in components.values()])),
        items=list(components),components=components,
        independence_assumption_standard_error=float(np.sqrt(sum(s*s for s in errors))/n)
            if all(s is not None for s in errors) else None,
        **design_error(f))


def main():
    source=Path('data/raw/gss-2024-r3a/gss7224_r3a.dta')
    manifest=Path('data/manifests/gss-2024-r3a.json')
    mappings=Path('data/gss/response_mappings.json')
    if digest(source)!=json.loads(manifest.read_text())['dta_sha256']:
        raise ValueError('GSS source checksum mismatch')
    entries=json.loads(mappings.read_text())['entries']
    columns=['year','vstrat','vpsu','wtssps','wtssnrps']+[e['code'] for e in entries]
    frame=pd.read_stata(source,convert_categoricals=False,columns=columns)
    results=[];composites=[]
    protocol=Path('data/research/abortion_protocol.json')
    abortion_codes=json.loads(protocol.read_text())['survey_codes']['GSS']
    for year,g in frame.groupby('year'):
        scored=pd.DataFrame(dict(weight=g['wtssps' if year<2004 else 'wtssnrps'],stratum=g.vstrat,psu=g.vpsu))
        for e in entries:
            scored[e['code']]=g[e['code']].map({int(k):v for k,v in e['scores'].items()})
            f=pd.DataFrame(dict(score=g[e['code']].map({int(k):v for k,v in e['scores'].items()}),
                weight=g['wtssps' if year<2004 else 'wtssnrps'],stratum=g.vstrat,psu=g.vpsu))
            result=estimate(f)
            if result['status']=='no valid responses':continue
            results.append(dict(code=e['code'],year=int(year),**result))
        composite=estimate_composite(scored,abortion_codes)
        if composite['status']!='no valid responses':
            composites.append(dict(year=int(year),**composite))
    report=dict(status='offline pilot; not deployed; independent comparison is a separate report',
        method='With-replacement stratified PSU Taylor linearization of weighted response mean; full positive-weight year sample retains zero contributions for unanswered items.',
        sources={str(p):digest(p) for p in [source,manifest,mappings,protocol,Path(__file__)]},
        documentation=['https://gss.norc.org/content/dam/gss/get-documentation/pdf/reports/methodological-reports/GSS%20MR137%20Poststratification%20Weights.pdf'],
        limitations=['No adjustment for singleton strata yet; no standard error for those years.',
                    'Missing design identifiers prevent variance estimates.',
                    'Does not capture nonresponse bias, measurement differences, or uncertainty in weighting adjustments.',
                    'Abortion GSS composite retains shared-sample covariance; cross-source chart uncertainty is not estimated.'],
        estimates=results,abortion_composite=composites)
    artifact=Path('artifacts/wvs-pilot.sqlite')
    cohort_path=Path('artifacts/abortion-research-cohort.json')
    cohort=json.loads(cohort_path.read_text())
    db=connect(artifact)
    try:
        questions={q['code']:q for payload, in db.execute("SELECT payload FROM documents WHERE corpus='gss'")
                   for q in [json.loads(payload)]}
    finally:
        db.close()
    for row in results:
        if abs(row['mean']-questions[row['code']]['years'][str(row['year'])])>1e-10:
            raise ValueError('Point estimate differs from serving artifact')
    for row in composites:
        if abs(row['mean']-cohort['survey_series']['GSS'][str(row['year'])])>1e-10:
            raise ValueError('Composite estimate differs from research cohort')
    report['point_validation']=dict(item_years=len(results),composite_years=len(composites),
        hashes={str(p):digest(p) for p in [artifact,cohort_path]},tolerance=1e-10)
    Path('artifacts/gss-uncertainty.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    from collections import Counter
    print(dict(Counter(r['status'] for r in results)))


if __name__=='__main__':main()
