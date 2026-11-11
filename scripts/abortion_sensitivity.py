"""Fixed-search, descriptive annual sensitivity analysis; no model fitting."""
import argparse
from collections import defaultdict
from copy import deepcopy
import csv
import json
from math import fsum, sqrt, isclose
from pathlib import Path
from scvpublic.build import digest
from scvpublic.chart import combine_sources
from scvpublic.hybrid import HybridSearch, chart_matches, CHART_CUTOFF
from scvpublic.store import series, court_counts, survey_items
from scvpublic.survey_search import SurveySearch

NAMES={'public':'ANES','gss':'GSS','ces':'CES','pew':'Pew','wvs':'WVS',
       'prri':'PRRI','nationscape':'Nationscape','voter':'VOTER'}


def correlation(x,y):
    if len(x)<3:return None
    mx,my=fsum(x)/len(x),fsum(y)/len(y)
    dx,dy=[v-mx for v in x],[v-my for v in y]
    denominator=sqrt(fsum(v*v for v in dx)*fsum(v*v for v in dy))
    return fsum(a*b for a,b in zip(dx,dy))/denominator if denominator else None


def compare(court,public,years):
    x,y=[court[t] for t in years],[public[t] for t in years]
    pairs=[(a,b) for a,b in zip(x,y) if abs(a)>1e-12 and abs(b)>1e-12]
    return dict(years=years,n=len(years),pearson_r=correlation(x,y),
                same_sign=sum((a>0)==(b>0) for a,b in pairs),sign_denominator=len(pairs))


def variants(court,directions):
    result={'current':series(court,[])[0]}
    for key,unit,remove_margin in [('no_vote_margin',False,True),('equal_cases',True,False),('equal_cases_direction',True,True)]:
        hits=deepcopy(court)
        for hit in hits:
            if unit:hit['score']=1.
            for case in hit['cases']:
                if case['polarity'] is not None and remove_margin:
                    case['polarity']=directions[case.get('case_id',hit['case_id'])]
        result[key]=series(hits,[])[0]
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',type=Path,default=Path('artifacts/court-details.sqlite'))
    p.add_argument('--bundle',type=Path,default=Path('artifacts/semantic-court-details'))
    p.add_argument('--output',type=Path,default=Path('data/evaluation/abortion-sensitivity.json'))
    a=p.parse_args()
    engine=HybridSearch(a.bundle,a.artifact)
    hits=engine.search(['abortion','',''])
    court=chart_matches(hits)
    surveys=SurveySearch(a.bundle,a.artifact,engine.encoder).search(['abortion','',''])
    sources={NAMES[k]:series([],v)[1] for k,v in surveys.items() if k in NAMES}
    sources={k:v for k,v in sources.items() if v}
    scdb=Path('data/raw/scdb-2026/SCDB_2026_01_caseCentered_Citation.csv')
    assert digest(scdb)=='b3cc84bd73a7a0325856cca52ae6fc5bd6a39433113f83fef248556ad4488528'
    with scdb.open(encoding='utf-8-sig') as f:rows={r['caseId']:r for r in csv.DictReader(f)}
    directions={}
    for hit in court:
        for case in hit['cases']:
            if case['polarity'] is None:continue
            key=case.get('case_id',hit['case_id']);r=rows[key]
            direction={'1':-1.,'2':1.,'3':0.}[r['decisionDirection']]
            maj,minv=float(r['majVotes']),float(r['minVotes'])
            assert isclose(case['polarity'],direction*abs(maj-minv)/(maj+minv),abs_tol=1e-12)
            directions[key]=direction
    courts=variants(court,directions)
    public,contributors=combine_sources(sources)
    overlap=sorted(courts['current'].keys() & public.keys())
    drops={name:combine_sources({k:v for k,v in sources.items() if k!=name})[0] for name in sources}
    common=sorted(set(overlap).intersection(*(set(v) for v in drops.values())))
    weight_metrics={key:compare(v,public,overlap) for key,v in courts.items()}
    loo={}
    for name,pub in drops.items():
        years=sorted(set(overlap)&pub.keys())
        delta=[abs(pub[t]-public[t]) for t in years]
        loo[name]=dict(matched_years=compare(courts['current'],pub,years),
                       fixed_years=compare(courts['current'],pub,common),
                       years_lost=sorted(set(overlap)-set(years)),
                       max_public_change=max(delta,default=0),
                       mean_public_change=fsum(delta)/len(delta) if delta else None,
                       sign_changes=[t for t in years if (pub[t]>1e-12)-(pub[t]<-1e-12)!=(public[t]>1e-12)-(public[t]<-1e-12)])
    # Frozen selections make the analysis reviewable without rerunning retrieval.
    result=dict(query='abortion',artifact_sha256=digest(a.artifact),
        bundle_manifest_sha256=digest(a.bundle/'manifest.json'),scdb_sha256=digest(scdb),
        chart_cutoff=CHART_CUTOFF,selected_court_documents=len(court),
        court_counts=court_counts(court),court_series=courts,survey_series=sources,
        public_series=public,contributors=contributors,overlap_years=overlap,
        fixed_leave_one_out_years=common,weight_metrics=weight_metrics,
        fixed_baseline=compare(courts['current'],public,common),leave_one_out=loo,
        leave_one_out_series=drops,
        questions={NAMES[k]:dict(selected=len(v),codes=[q['code'] for q in v],
                     yearly_used={y:[c for c,_ in items] for y,items in survey_items(v).items()})
                   for k,v in surveys.items() if k in NAMES},
        frozen_court=court,frozen_surveys=surveys,
        limitations=['Descriptive association only; no causal or predictive inference.',
          'Same-year observed values only; no interpolation, smoothing or lag search.',
          'Search selections are held fixed, not newly certified as topic-relevant.',
          'Source/question mix changes over time; leave-one-source-out is not a sampling confidence interval.',
          'SCDB direction is outcome coding, not necessarily support for abortion rights.',
          'Same-sign compares coded scales, not substantive legal-policy agreement.'])
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k in ['selected_court_documents','overlap_years','fixed_leave_one_out_years','weight_metrics','fixed_baseline','leave_one_out','questions']},indent=2))


if __name__=='__main__':main()
