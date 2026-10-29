"""Audit actual chart inputs; coverage is not evidence of alignment or causality."""
import argparse
from contextlib import closing
import json
from pathlib import Path
from scvpublic.build import digest
from scvpublic.hybrid import HybridSearch, chart_matches, CHART_CUTOFF
from scvpublic.store import connect, survey_search, series, court_counts
from scvpublic.chart import combine_sources

TOPICS = ['abortion', 'gun control', 'gay marriage', 'death penalty', 'immigration', 'environmental regulation']
CORPORA = {'public':'ANES', 'gss':'GSS', 'ces':'CES', 'pew':'Pew', 'wvs':'WVS'}


def audit(artifact, bundle):
    engine = HybridSearch(bundle, artifact)
    results = {}
    with closing(connect(artifact)) as db:
        available = {c for c, in db.execute('SELECT DISTINCT corpus FROM documents')}
        for topic in TOPICS:
            courts = chart_matches(engine.search([topic]))
            court_series = series(courts, [])[0]
            sources, details = {}, {}
            for corpus, name in CORPORA.items():
                if corpus not in available:
                    continue
                hits = survey_search(db, corpus, [topic])
                sources[name] = series([], hits)[1]
                details[name] = dict(matched_variables=len(hits),
                    matched_families=len({h.get('family',h['code']) for h in hits}),
                    years=list(sources[name]), scores=sources[name],
                    questions=[{k:h[k] for k in ('code','family','question','measurement_type','years','respondents','weight','rationale','priority','supersedes') if k in h} for h in hits])
            combined, contributors = combine_sources(sources)
            years = sorted(combined)
            results[topic] = dict(court_years=list(court_series), court_scores=court_series,
                court_counts=court_counts(courts), scored_cases=sum(court_counts(courts).values()),
                court_matches=[{k:h.get(k) for k in ('case_id','name','score','cases')} for h in courts],
                sources=details, combined_scores=combined, contributors=contributors,
                same_year_overlap=sorted(set(court_series)&set(combined)),
                years_with_multiple_sources=[y for y,n in contributors.items() if len(n)>1],
                source_changes=[dict(previous=a,year=b,before=contributors[a],after=contributors[b])
                    for a,b in zip(years,years[1:]) if set(contributors[a])!=set(contributors[b])],
                gaps_over_five_years=[[a,b] for a,b in zip(years,years[1:]) if b-a>5])
    return dict(artifact_sha256=digest(artifact), bundle_manifest_sha256=digest(bundle/'manifest.json'),
        court_threshold=CHART_CUTOFF, survey_limit_per_source=10, topics=results,
        limitations=['Counts are search-conditioned, not a complete topic census.',
            'Question respondent counts are not independent samples and must not be summed across items.',
            'Court polarity includes vote margin and is not a binary liberal/conservative outcome.',
            'Survey aggregates lack sampling-design uncertainty; no significance or prediction claim is made.',
            'Same-year overlap does not establish sentiment preceded the court decision.'])


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',type=Path,default=Path('artifacts/wvs-pilot.sqlite'))
    p.add_argument('--bundle',type=Path,default=Path('artifacts/semantic-wvs-pilot'))
    p.add_argument('--output',type=Path,default=Path('artifacts/topic-coverage.json'))
    a=p.parse_args(); report=audit(a.artifact,a.bundle)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    for topic,r in report['topics'].items():
        print(topic,json.dumps(dict(cases=r['scored_cases'],public_years=len(r['combined_scores']),
            overlapping_years=len(r['same_year_overlap']),multi_source_years=len(r['years_with_multiple_sources']),
            questions={s:v['matched_variables'] for s,v in r['sources'].items()})))
