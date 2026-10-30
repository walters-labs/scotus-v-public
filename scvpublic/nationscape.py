"""Offline Nationscape weekly policy import with pinned published-table checks."""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path

from .build import digest
from .survey_schema import prepare


def summarize(frame, expected, validation_weights=None, code='gov_insurance', score_map=None):
    score_map = {1:1.,2:-1.} if score_map is None else score_map
    if set(score_map) != {1,2} or set(score_map.values()) != {-1,1}:
        raise ValueError('Invalid Nationscape response mapping')
    answer, weight = frame[code], frame.weight
    if set(answer.dropna()) - {1, 2, 999}:
        raise ValueError('Unknown Nationscape answer')
    if not (weight.notna() & weight.gt(0) & weight.lt(float('inf'))).all():
        raise ValueError('Invalid Nationscape weight')
    answered = answer.notna()
    if int(answered.sum()) != expected['published_n']:
        raise ValueError('Nationscape published count mismatch')
    sums = {str(int(k)):float(v) for k,v in frame.loc[answered].groupby(code).weight.sum().items()}
    check_sums = sums
    if validation_weights is not None:
        if not (validation_weights.notna() & validation_weights.gt(0) & validation_weights.lt(float('inf'))).all():
            raise ValueError('Invalid published-table weights')
        check_frame = frame.loc[answered].copy()
        check_frame['weight'] = validation_weights[answered]
        check_sums = {str(int(k)):float(v) for k,v in check_frame.groupby(code).weight.sum().items()}
    total = math.fsum(check_sums.values())
    percentages = {k:100*check_sums.get(k,0)/total for k in ('1','2','999')}
    if any(abs(percentages[k]-p) > .51 for k,p in expected['published_percentages'].items()):
        raise ValueError('Nationscape published percentage mismatch')
    scores = answer.map(score_map)
    valid = scores.notna()
    denominator = math.fsum(weight[valid])
    if denominator <= 0:
        raise ValueError('No substantive answers')
    mean = math.fsum(scores[valid]*weight[valid])/denominator
    grouped = (sums.get('1',0)*score_map[1]+sums.get('2',0)*score_map[2])/(sums.get('1',0)+sums.get('2',0))
    if abs(mean-grouped)>1e-10:
        raise ValueError('Nationscape independent aggregate mismatch')
    return dict(score=mean, respondents=int(valid.sum()), weight_sum=denominator, percentages=percentages)


def annualize(observations):
    groups = defaultdict(list)
    seen=set()
    for item in observations:
        if item['date'] in seen:
            raise ValueError('Duplicate Nationscape weekly wave')
        seen.add(item['date'])
        groups[item['date'][:4]].append(item)
    # A survey-weighted mean within each wave, then equal weight per observed wave.
    return {year:math.fsum(w['score'] for w in waves)/len(waves) for year,waves in groups.items()}


def healthcare_entry(source_url):
    return dict(code='nationscape_gov_insurance',family='nationscape_gov_insurance',title='Government-run health insurance',question='Provide government-run health insurance to all Americans.',scores={'1':1,'2':-1},weight='weight (2016 vote calibration) within each weekly wave; equal weight per observed wave within year',source_url=source_url,question_note='Agree = +1; disagree = −1; not sure and skipped excluded. Annual points average observed weekly estimates equally, grouped by wave start year. 2019 and 2021 cover only part of the year; 2021 contains one wave. This item does not specify eliminating private insurance.')

def build(manifest, output):
    import pyreadstat
    if output.exists():
        raise FileExistsError(output)
    spec=json.loads(manifest.read_text())
    entries=spec.get('entries') or [dict(healthcare_entry(spec['source_url']), source_code='gov_insurance')]
    sources={str(manifest):digest(manifest)}
    documents=[]
    verified=set()
    for entry in entries:
        observations=[]
        code=entry['source_code']
        score_map={int(k):v for k,v in entry['scores'].items()}
        for wave in spec['waves']:
            if 'parallel' in wave['path']:
                raise ValueError('Parallel samples are not part of this import')
            for file,checksum in wave['files'].items():
                if file not in verified:
                    if digest(Path(file)) != checksum:
                        raise ValueError('Nationscape checksum mismatch: '+file)
                    verified.add(file)
                elif sources[file] != checksum:
                    raise ValueError('Conflicting Nationscape checksum')
                sources[file]=checksum
            expected=wave['questions'][code] if 'questions' in wave else wave
            columns=list(dict.fromkeys([code,'weight','start_date',wave['validation_weight']]))
            frame,meta=pyreadstat.read_dta(wave['path'],usecols=columns)
            values={str(int(k)):v for k,v in meta.variable_value_labels[code].items()}
            if meta.column_names_to_labels[code] != expected['expected_label'] or values != expected['expected_labels']:
                raise ValueError('Nationscape labels changed: '+code)
            if len(frame)!=wave['rows'] or frame.start_date.isna().any():
                raise ValueError('Nationscape rows/dates changed')
            result=summarize(frame,expected,frame[wave['validation_weight']],code,score_map)
            observations.append(dict(wave=wave['wave'],date=wave['date'],first_response=frame.start_date.min().isoformat(),last_response=frame.start_date.max().isoformat(),weight='weight',validation_weight=wave['validation_weight'],**result))
        years=annualize(observations)
        doc={k:v for k,v in entry.items() if k!='source_code'}
        doc.update(years=years,respondents={y:sum(w['respondents'] for w in observations if w['date'].startswith(y)) for y in years},weekly_observations=observations,weekly_counts={y:sum(w['date'].startswith(y) for w in observations) for y in years},dataset='Nationscape')
        documents.append(doc)
    notes=spec.get('notes','Democracy Fund + UCLA Nationscape. One reviewed health-insurance question; 77 weekly surveys, July 2019–January 2021. Three parallel surveys excluded. Annual estimates describe observed weeks, not full calendar years. Counts are responses, not necessarily unique people.')
    payload=prepare(dict(methodology='explicit-nationscape-v1',release='Nationscape weekly December 2021 release',notes=notes,sources=sources,documents=documents))
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix('.tmp');temporary.write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n');temporary.replace(output)
    print(json.dumps(dict(questions=len(documents),question_weeks=sum(len(d['weekly_observations']) for d in documents),years={d['code']:d['years'] for d in documents})))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,default=Path('data/manifests/nationscape-healthcare.json'))
    p.add_argument('--output',type=Path,default=Path('data/processed/nationscape-healthcare/public.json'))
    p.add_argument('--base-artifact',type=Path)
    p.add_argument('--artifact',type=Path,default=Path('artifacts/nationscape-healthcare.sqlite'))
    a=p.parse_args();build(a.manifest,a.output)
    if a.base_artifact:
        from .gss import attach
        attach(a.base_artifact,a.output,a.artifact,corpus='nationscape')


if __name__=='__main__':
    main()
