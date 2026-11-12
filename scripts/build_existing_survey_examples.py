"""Raw-data policy examples using existing GSS, CES and VOTER inputs only."""
import json
from pathlib import Path
import math
import sqlite3
import pandas as pd
import pyreadstat
from scvpublic.build import digest
from scvpublic.ces import join_weights
from scripts.marriage_case_study import summarize
from scripts.compare_policy import compare, report

ROOT=Path('data/research')


def build():
    records=[]; provenance={}
    def checked(path, expected=None):
        path=Path(path); sha=digest(path)
        if expected and sha!=expected:raise ValueError('Checksum mismatch: '+str(path))
        provenance[str(path)]=sha
        return path
    m=json.loads(checked('data/manifests/gss-2024-r3a.json').read_text())
    raw=checked('data/raw/gss-2024-r3a/gss7224_r3a.dta',m['dta_sha256'])
    f,meta=pyreadstat.read_dta(raw,usecols=['year','cappun','wtssps','wtssnrps'],encoding='latin1',user_missing=True)
    if meta.variable_value_labels['cappun'][1]!='favor' or meta.variable_value_labels['cappun'][2]!='oppose':raise ValueError('Changed GSS labels')
    for year in [1975,2000,2004]:
        frame=f.loc[f.year.eq(year)].copy();weight='wtssps' if year<2004 else 'wtssnrps'
        frame[weight]=pd.to_numeric(frame[weight],errors='coerce')
        values=summarize(frame,'cappun',weight,{'1':'support','2':'oppose','d':'unsure','n':'nonresponse','r':'nonresponse','s':'nonresponse'},excluded=['i','y','x','missing'])
        records.append(dict(source='GSS',year=year,variable='cappun',wording='Do you favor or oppose the death penalty for persons convicted of murder?',weight=weight,
            orientation='Support means favoring the death penalty for murder; it is not the liberal endpoint.',
            denominator='Positive-weight substantive, do-not-know and item nonresponse answers; inapplicable/unavailable/system missing excluded.',**values))
    m=json.loads(checked('data/manifests/ces-policy-v3.json').read_text())
    for source in m['files']:checked(Path('data/raw')/source['path'],source['sha256'])
    mappings=json.loads(checked('data/ces/affirmative-action-mappings.json').read_text())
    f,meta=pyreadstat.read_dta('data/raw/ces-policy/responses.dta',usecols=['year','case_id','affirmativeaction'])
    weights=pd.read_feather('data/raw/ces-policy/common.feather',columns=['year','case_id','weight'])
    f=join_weights(f,weights)
    for entry in mappings['entries']:
        labels={str(int(k)):v for k,v in meta.variable_value_labels['affirmativeaction'].items()}
        if labels!=entry['expected_labels']:raise ValueError('Changed CES labels')
        for year in entry['years']:
            frame=f.loc[f.year.eq(year)]
            counts={str(int(k)):int(v) for k,v in frame.affirmativeaction.dropna().value_counts().items()}
            if counts!=entry['published_counts'][str(year)]:raise ValueError('CES published count mismatch')
            if not frame['_merge'].eq('both').all():raise ValueError('Unmatched CES weights')
            values=summarize(frame,'affirmativeaction','weight',{'1':'support','2':'support','3':'oppose','4':'oppose'},excluded=['missing'])
            records.append(dict(source='CES',year=year,variable=entry['code'],wording=entry['question'],weight='weight',
                denominator='Conditional on the four support/oppose answers in the harmonized file; original reasons for missing answers unavailable. Employment and college admissions are combined in the question.',**values))
    m=json.loads(checked('data/manifests/voter-policy-batch.json').read_text())
    for path,sha in m['sources'].items():checked(path,sha)
    entry=next(e for e in m['entries'] if e['code']=='voter_affirmativeaction')
    for wave in entry['waves']:
        code,weight=wave['code'],wave['weight']
        f,meta=pyreadstat.read_dta(m['raw_path'],encoding=m['encoding'],usecols=[code,weight])
        labels={str(int(k)):v for k,v in meta.variable_value_labels[code].items()}
        if labels!=wave['expected_labels'] or meta.column_names_to_labels[code]!=wave['expected_label']:raise ValueError('Changed VOTER labels')
        groups={k:'support' if k=='1' else 'oppose' if k=='2' else 'nonresponse' if 'skip' in v.lower() else 'unsure' for k,v in labels.items() if 'not asked' not in v.lower()}
        excluded=[k for k,v in labels.items() if 'not asked' in v.lower()]+['missing']
        values=summarize(f,code,weight,groups,excluded)
        records.append(dict(source='VOTER',year=int(wave['year']),variable=code,wording=wave['question'],weight=weight,
            denominator='Positive-weight administered-wave answers, including unsure/skipped; not-asked/system missing excluded. The question combines women and racial minorities and does not isolate college admissions.',**values))
    # Independent parity check: recover serving scores from response categories,
    # not by converting the serving mean into a prevalence percentage.
    with sqlite3.connect('file:artifacts/court-details.sqlite?mode=ro',uri=True) as db:
        docs={(c,json.loads(p)['code']):json.loads(p) for c,p in db.execute("SELECT corpus,payload FROM documents WHERE corpus != 'court'")}
    for r in records:
        key='voter_affirmativeaction' if r['source']=='VOTER' else r['variable']
        d=docs[(r['source'].lower(),key)]
        valid=[c for c in r['categories'] if c['code'] in d['scores']]
        mean=sum(c['weight_sum']*d['scores'][c['code']] for c in valid)/sum(c['weight_sum'] for c in valid)
        if not math.isclose(mean,d['years'][str(r['year'])],abs_tol=1e-8):raise ValueError('Serving score mismatch')
    checked('artifacts/court-details.sqlite');checked(__file__)
    for topic, sources in [('capital-punishment',{'GSS'}),('affirmative-action',{'CES','VOTER'})]:
        case_path=ROOT/f'{topic}-policy-components.json';mapping_path=ROOT/f'{topic}-policy-mapping.json'
        cases=json.loads(checked(case_path).read_text())['cases'];mapping=json.loads(checked(mapping_path).read_text())
        observations=[r for r in records if r['source'] in sources]
        data=dict(survey_records=observations,provenance=provenance.copy())
        (ROOT/f'{topic}-policy-surveys.json').write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
        result=compare(cases,observations,mapping)
        result['survey_provenance']=data['provenance']
        result['limitations'].append('Selected cases are not a representative sample. Broad attitudes do not establish agreement with narrower offender categories or admissions programs.')
        (ROOT/f'{topic}-policy-comparison.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        Path('docs/'+topic.upper().replace('-','_')+'_POLICY_COMPARISON.md').write_text(report(result))
        print(topic,len(cases),'cases;',len(observations),'raw-derived observations')


if __name__=='__main__':build()
