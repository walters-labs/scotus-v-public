"""Build explicit abortion-policy observations; no ideological-score conversion."""
import json
from pathlib import Path
import pandas as pd
import pyreadstat
from scvpublic.build import digest
from scripts.marriage_case_study import summarize

OUT=Path('data/research/abortion-policy-surveys.json')


def build():
    records=[]
    provenance={}
    def checked(path, expected=None):
        path=Path(path); sha=digest(path)
        if expected and sha!=expected: raise ValueError(f'Checksum mismatch: {path}')
        provenance[str(path)]=sha
        return path
    # ANES: preserve the multi-option policy categories instead of manufacturing
    # a binary support/oppose boundary. These are contextual observations only.
    root=Path('data/raw/rebuild/anes-20260205')
    manifest=json.loads(checked(root/'sources.json').read_text())
    raw=root/'anes_timeseries_cdf_stata_20260205.dta'
    checked(raw,manifest['files'][raw.name])
    mappings=json.loads(checked('data/anes/response_mappings.json').read_text())
    checked(root/'anes_timeseries_cdf_codebook_var_20260205.pdf',mappings['codebook_sha256'])
    frame=pd.read_stata(raw,columns=['VCF0004','VCF0009z','VCF0837','VCF0838'],convert_categoricals=False)
    for code in ['VCF0837','VCF0838']:
        entry=next(e for e in mappings['entries'] if e['code']==code)
        labels=({'1':'Never permit','2':'Only danger to life and health','3':'Personal difficulty caring for child','4':'Never forbid / unwanted child','9':'Do not know or other'} if code=='VCF0837' else
                {'1':'Never permit','2':'Only rape, incest, or danger to life','3':'Other reasons if need clearly established','4':'Always as personal choice','9':'Do not know or other'})
        for year,f in frame.groupby('VCF0004'):
            if not f[code].isin([1,2,3,4]).any(): continue
            # summarize validates weights/codes; five dummy groups are not used
            # in output. Each original response category remains independent.
            result=summarize(f,code,'VCF0009z',{str(k):'support' for k in [1,2,3,4,9]},excluded=['0','missing'])
            records.append(dict(source='ANES',year=int(year),variable=code,wording=entry['question'],weight='VCF0009z',
                denominator='Positive-weight coded answers 1–4 and DK/other (9); code 0 combines missing/not-administered and is excluded. Not a full-sample denominator.',
                category_definition=entry['valid_definition'],response_distribution=[dict(code=c['code'],label=labels[c['code']],percent=c['percent']) for c in result['categories']],
                n=result['n'],weight_sum=result['weight_sum'],excluded_positive_weight=result['excluded_positive_weight']))
    # GSS any-reason legality: not funding, gestational limits, or provider rules.
    m=json.loads(checked('data/manifests/gss-2024-r3a.json').read_text())
    raw=checked('data/raw/gss-2024-r3a/gss7224_r3a.dta',m['dta_sha256'])
    frame,meta=pyreadstat.read_dta(raw,usecols=['year','abany','wtssps','wtssnrps'],encoding='latin1',user_missing=True)
    if meta.variable_value_labels['abany'][1]!='yes' or meta.variable_value_labels['abany'][2]!='no': raise ValueError('Changed GSS labels')
    frame['w']=pd.to_numeric(frame.wtssps,errors='coerce').where(frame.year<2004,pd.to_numeric(frame.wtssnrps,errors='coerce'))
    for year,f in frame.groupby('year'):
        if not f.abany.isin([1,2]).any(): continue
        result=summarize(f,'abany','w',{'1':'support','2':'oppose','d':'unsure','n':'nonresponse','r':'nonresponse','s':'nonresponse'},excluded=['i','y','x','missing'])
        records.append(dict(source='GSS',year=int(year),variable='abany',wording='Whether it should be possible for a pregnant woman to obtain a legal abortion if she wants it for any reason (ABANY; item wording summarized).',
            weight='wtssps' if year<2004 else 'wtssnrps',denominator='Standard ABANY form only (ABANYG grid form is not merged). Positive-weight substantive, do-not-know and nonresponse item answers; inapplicable/unavailable/system missing excluded.',**result))
    # PRRI general legality; all/most legal versus most/all illegal, not a ban
    # on every abortion and not approval of any particular court holding.
    mappings=json.loads(checked('data/prri/policy-batch-mappings.json').read_text())
    entry=next(e for e in mappings['entries'] if e['code']=='prri_abortion')
    files={r['path']:r['sha256'] for r in json.loads(checked('data/manifests/prri-avs-acquisition.json').read_text())['files']}
    files.update({r['path']:r['sha256'] for r in json.loads(checked('data/manifests/prri-all-policy-documents.json').read_text())})
    for wave in entry['waves']:
        raw=Path(f"data/raw/prri-avs-{wave['year']}/responses.dta");checked(raw,files[str(raw)])
        code,weight=wave['source_code'],wave['weight']
        f,meta=pyreadstat.read_dta(raw,usecols=[code,weight])
        labels={str(int(k)):v for k,v in meta.variable_value_labels[code].items()}
        if labels!=wave['expected_labels'] or meta.column_names_to_labels[code]!=wave['expected_label']: raise ValueError('Changed PRRI labels')
        groups={k:'support' if k in ['1','2'] else 'oppose' if k in ['3','4'] else 'nonresponse' if 'skip' in v.lower() or v.lower()=='refused' else 'unsure' for k,v in labels.items()}
        result=summarize(f,code,weight,{**groups,'missing':'nonresponse'})
        for k,pct in wave['published_percentages'].items():
            actual=next(c['percent'] for c in result['categories'] if c['code']==k)
            if abs(actual-pct)>=1.1: raise ValueError('PRRI topline mismatch')
        records.append(dict(source='PRRI',year=wave['year'],variable=code,wording=wave['question'],weight=weight,
            denominator='All positive-weight wave respondents; support means legal all/most, opposition illegal most/all. Unsure/refused/skipped retained.',**result))
    # Reuse the previously validated named-Roe calculation, with hashes checked
    # against its raw inputs, reversing the question orientation explicitly.
    old=json.loads(checked('data/research/voter-roe-dobbs-comparison.json').read_text())
    for path,sha in old['provenance'].items(): checked(path,sha)
    s=old['survey']; responses={r['code']:r for r in s['responses']}
    if responses['9']['unweighted_count']: raise ValueError('Unaccounted not-asked VOTER answers')
    records.append(dict(source='VOTER',year=2020,variable=s['variable'],wording=s['question'],weight=s['weight'],denominator=s['denominator'],
        fieldwork_start=s['fieldwork_start'],fieldwork_end=s['fieldwork_end'],n=s['respondents'],
        percent=dict(support=responses['2']['weighted_percent'],oppose=responses['1']['weighted_percent'],neutral=0,unsure=responses['3']['weighted_percent'],nonresponse=responses['8']['weighted_percent']),
        orientation='Support = retain Roe; oppose = overturn Roe. Not general abortion legality.'))
    records.sort(key=lambda r:(r['source'],r['year'],r['variable']))
    checked(__file__)
    OUT.write_text(json.dumps(dict(survey_records=records,provenance=provenance),indent=2,allow_nan=False)+'\n')
    print('Saved',len(records),'observations to',OUT)


if __name__=='__main__': build()
