"""Verify CES inputs, join respondent weights, and inventory observed policy coverage."""
import json
from pathlib import Path
import pandas as pd
from scvpublic.build import digest


from scvpublic.ces import respondent_ids


def main():
    spec=json.loads(Path('data/manifests/ces-policy-v3.json').read_text())
    for f in spec['files']:
        if digest(Path('data/raw')/f['path'])!=f['sha256']:
            raise ValueError('CES source checksum mismatch: '+f['path'])
    p=pd.read_stata('data/raw/ces-policy/responses.dta',convert_categoricals=False)
    w=pd.read_feather('data/raw/ces-policy/common.feather',columns=['year','case_id','weight','weight_post'])
    p['case_id']=respondent_ids(p['case_id']);w['case_id']=respondent_ids(w['case_id'])
    joined=p.merge(w,on=['year','case_id'],how='left',validate='one_to_one',indicator=True)
    by_year=[]
    for year,group in joined.groupby('year'):
        by_year.append(dict(year=int(year),respondents=len(group),unmatched_weights=int((group['_merge']!='both').sum()),positive_pre_weights=int((group.weight>0).sum()),
                            positive_post_weights=int((group.weight_post>0).sum())))
    items={code:dict(observed_years=sorted(int(y) for y in p.loc[p[code].notna(),'year'].unique()),
                    observed_codes=sorted(float(v) for v in p[code].dropna().unique()),
                    nonmissing_responses=int(p[code].notna().sum()))
           for code in p.columns if code not in ('year','case_id')}
    report=dict(status='acquired and joined; response mappings and wave-specific weighting still require review',
                policy_respondents=len(p),policy_items=len(items),matched_weight_records=int((joined['_merge']=='both').sum()),
                unmatched_weight_records=int((joined['_merge']!='both').sum()),
                years=by_year,items=items,source_hashes={f['path']:f['sha256'] for f in spec['files']})
    Path('data/ces/acquisition_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','policy_respondents','policy_items','matched_weight_records','unmatched_weight_records','years')},indent=2))


if __name__=='__main__':main()
