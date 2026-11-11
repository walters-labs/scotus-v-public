"""Offline marriage-policy case study: explicit questions, response shares, no pooled ideology."""
import json
from pathlib import Path
import math
import sqlite3
import pandas as pd
import pyreadstat
from scvpublic.build import digest
from scvpublic.ces import join_weights

CASE_SPEC=Path('data/research/marriage-case-components.json')

OUT=Path('data/research/marriage-case-study.json')
PROVENANCE={}


def verify(path,sha):
    path=Path(path)
    if digest(path)!=sha:raise ValueError('Source checksum mismatch: '+str(path))
    PROVENANCE[str(path)]=sha


def summarize(frame,code,weight,groups,excluded=()):
    def canonical(x):
        if pd.isna(x):return 'missing'
        return str(int(x)) if isinstance(x,(int,float)) else str(x)
    answers=frame[code].map(canonical)
    w=pd.to_numeric(frame[weight],errors='raise')
    if ((w.dropna()<0)|~w.dropna().map(math.isfinite)).any():raise ValueError('Invalid weight')
    positive=w.notna() & w.gt(0)
    unexpected=set(answers[positive])-set(groups)-set(excluded)
    if unexpected:raise ValueError(f'Unmapped {code} responses: {unexpected}')
    eligible=positive & ~answers.isin(excluded)
    denominator=math.fsum(w[eligible])
    if denominator<=0:raise ValueError('Empty survey denominator')
    categories=[]
    for val,label in groups.items():
        selected=eligible & answers.eq(val)
        amount=math.fsum(w[selected])
        categories.append(dict(code=val,group=label,n=int(selected.sum()),weight_sum=amount,
                               percent=100*amount/denominator))
    percentages={label:math.fsum(c['percent'] for c in categories if c['group']==label)
                 for label in ['support','oppose','neutral','unsure','nonresponse']}
    assert math.isclose(sum(percentages.values()),100,abs_tol=1e-8)
    # Independent grouped-sum check of response totals.
    check=pd.DataFrame({'answer':answers[eligible],'weight':w[eligible]}).groupby('answer').weight.sum()
    for c in categories:assert math.isclose(float(check.get(c['code'],0)),c['weight_sum'],abs_tol=1e-8)
    return dict(n=int(eligible.sum()),weight_sum=denominator,percent=percentages,categories=categories,
                excluded_positive_weight=int((positive & ~eligible).sum()),
                missing_or_zero_weight=int((~positive).sum()))


def build():
    records=[]
    # GSS: distinguish substantive neutral, can't choose and nonresponse.
    manifest=Path('data/manifests/gss-2024-r3a.json');m=json.loads(manifest.read_text())
    raw=Path('data/raw/gss-2024-r3a/gss7224_r3a.dta');verify(raw,m['dta_sha256'])
    f,meta=pyreadstat.read_dta(raw,usecols=['year','marsame','marsame1','wtssps','wtssnrps'],user_missing=True,encoding='latin1')
    f['study_weight']=pd.to_numeric(f.wtssps,errors='coerce').where(f.year<2004,pd.to_numeric(f.wtssnrps,errors='coerce'))
    for code in ['marsame','marsame1']:
        assert [meta.variable_value_labels[code][i] for i in range(1,6)]==['strongly agree','agree','neither agree nor disagree','disagree','strongly disagree']
        for year,frame in f.groupby('year'):
            if not frame[code].isin([1,2,3,4,5]).any():continue
            result=summarize(frame,code,'study_weight',{'1':'support','2':'support','3':'neutral','4':'oppose','5':'oppose','d':'unsure','n':'nonresponse','s':'nonresponse','r':'nonresponse'},excluded=['i','y','missing'])
            records.append(dict(source='GSS',year=int(year),variable=code,
                wording=meta.column_names_to_labels[code],weight='wtssps' if year<2004 else 'wtssnrps',
                denominator='Positive-weight respondents with substantive, cannot-choose or nonresponse item codes; inapplicable/year-unavailable/system-missing excluded.',
                wording_note='Two wording variants kept distinct; Stata variable label is not full questionnaire context.',**result))
    # PRRI: full sample, including DK/refused/skipped, from reviewed wave mappings.
    mappings=Path('data/prri/policy-batch-mappings.json');mapping=json.loads(mappings.read_text())
    entry=next(e for e in mapping['entries'] if e['code']=='prri_marriage')
    files={r['path']:r['sha256'] for r in json.loads(Path('data/manifests/prri-avs-acquisition.json').read_text())['files']}
    files.update({r['path']:r['sha256'] for r in json.loads(Path('data/manifests/prri-all-policy-documents.json').read_text())})
    for wave in entry['waves']:
        year=wave['year'];raw=Path(f'data/raw/prri-avs-{year}/responses.dta')
        verify(raw,files[str(raw)])
        pdf=raw.with_name('questionnaire.pdf');verify(pdf,files[str(pdf)])
        code,weight=wave['source_code'],wave['weight']
        f,meta=pyreadstat.read_dta(raw,usecols=[code,weight])
        labels={str(int(k)):v for k,v in meta.variable_value_labels[code].items()}
        assert labels==wave['expected_labels'] and meta.column_names_to_labels[code]==wave['expected_label']
        groups={k:('support' if k in ['1','2'] else 'oppose' if k in ['3','4'] else 'nonresponse' if 'skip' in v.lower() or v.lower()=='refused' else 'unsure') for k,v in labels.items()}
        result=summarize(f,code,weight,{**groups,'missing':'nonresponse'})
        for k,pct in wave['published_percentages'].items():
            got=next(r['percent'] for r in result['categories'] if r['code']==k)
            assert abs(got-pct)<1.1,(year,k,got,pct)
        records.append(dict(source='PRRI',year=year,variable=code,wording=wave['question'],weight=weight,
            doi=wave['doi'],denominator='All positive-weight wave respondents, including unsure/refused/skipped and missing.',**result))
    # CES harmonized source records only support/oppose. Unknown original missing
    # semantics cannot be reconstructed; report a conditional denominator explicitly.
    m=json.loads(Path('data/manifests/ces-policy-v3.json').read_text())
    for r in m['files']:verify(Path('data/raw')/r['path'],r['sha256'])
    code='gaymarriage_legalize'
    f,meta=pyreadstat.read_dta('data/raw/ces-policy/responses.dta',usecols=['year','case_id',code])
    assert meta.variable_value_labels[code]=={1:'Support',2:'Oppose'}
    w=pd.read_feather('data/raw/ces-policy/common.feather',columns=['year','case_id','weight'])
    f=join_weights(f,w)
    for year in range(2012,2017):
        frame=f.loc[f.year.eq(year)]
        assert (frame['_merge']=='both').all()
        result=summarize(frame,code,'weight',{'1':'support','2':'oppose'},excluded=['missing'])
        records.append(dict(source='CES',year=year,variable=code,
            wording='Do you favor or oppose allowing gays and lesbians to marry legally?',weight='weight',
            denominator='Support/oppose respondents only; harmonized missing answers excluded, original unsure/nonresponse categories unavailable here.',**result))
    # VOTER: all positive-weight administered wave responses, including unsure.
    manifest=Path('data/manifests/voter-policy-batch.json');m=json.loads(manifest.read_text())
    for path,sha in m['sources'].items():verify(path,sha)
    entry=next(e for e in m['entries'] if e['code']=='voter_marriage')
    for wave in entry['waves']:
        code,weight=wave['code'],wave['weight']
        f,meta=pyreadstat.read_dta(m['raw_path'],encoding=m['encoding'],usecols=[code,weight])
        labels={str(int(k)):v for k,v in meta.variable_value_labels[code].items()}
        assert labels==wave['expected_labels'] and meta.column_names_to_labels[code]==wave['expected_label']
        groups={k:('support' if k=='1' else 'oppose' if k=='2' else 'nonresponse' if 'skip' in v.lower() else 'unsure') for k,v in labels.items() if 'not asked' not in v.lower()}
        excluded=[k for k,v in labels.items() if 'not asked' in v.lower()]+['missing']
        result=summarize(f,code,weight,groups,excluded)
        records.append(dict(source='VOTER',year=int(wave['year']),variable=code,wording=wave['question'],weight=weight,
            denominator='Positive-weight administered wave respondents, including unsure/skipped; not-asked and system missing excluded.',**result))
    # Reproduce existing valid-response scores without using them as support shares.
    with sqlite3.connect('file:artifacts/court-details.sqlite?mode=ro',uri=True) as db:
        docs={(corpus,json.loads(p)['code']):json.loads(p) for corpus,p in db.execute("SELECT corpus,payload FROM documents WHERE corpus != 'court'")}
    for r in records:
        corpus=r['source'].lower();key=r['variable'] if corpus=='gss' else {'prri':'prri_marriage','ces':'gaymarriage_legalize','voter':'voter_marriage'}[corpus]
        doc=docs[(corpus,key)];scores=doc['scores']
        valid=[c for c in r['categories'] if c['code'] in scores]
        avg=sum(c['weight_sum']*scores[c['code']] for c in valid)/sum(c['weight_sum'] for c in valid)
        assert math.isclose(avg,doc['years'][str(r['year'])],abs_tol=1e-8),(corpus,r['year'],avg)
    records.sort(key=lambda r:(r['source'],r['year'],r['variable']))
    prior={}
    for decision_year in [2013,2015]:
        prior[str(decision_year)]={}
        for source in ['GSS','PRRI','CES','VOTER']:
            candidates=[r for r in records if r['source']==source and decision_year-3<=r['year']<decision_year]
            prior[str(decision_year)][source]=max(candidates,key=lambda r:r['year']) if candidates else None
    for path in [CASE_SPEC,Path(__file__),Path('data/prri/policy-batch-mappings.json'),Path('data/manifests/gss-2024-r3a.json'),Path('data/manifests/ces-policy-v3.json'),Path('data/manifests/voter-policy-batch.json')]:PROVENANCE[str(path)]=digest(path)
    result=dict(case_review=json.loads(CASE_SPEC.read_text()),scope='Support for legal same-sex marriage; three deliberately selected case events, not complete legal history.',
        timing_rule='Latest earlier-calendar-year wave per source within three years; same-year waves excluded to avoid uncertain before/after ordering.',
        survey_records=records,prior_observations=prior,provenance=PROVENANCE,
        limitations=['No pooled percentage: wording, denominator, target population and mode differ.',
          'Retrospective current data vintages, not a historically available forecasting dataset.',
          'No survey-design uncertainty or confidence intervals estimated.',
          'Broad legality preferences compare outcome direction, not approval of constitutional reasoning or federal-recognition details.'])
    OUT.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    for year,sources in prior.items():
        for source,r in sources.items():print(year,source, None if r is None else (r['year'],r['percent']))
    print('Validated',len(records),'source/question-years against deployed scores; saved',OUT)


if __name__=='__main__':build()
