"""Integrate sourced published toplines into explicit marriage policy components."""
import json
import hashlib
from pathlib import Path
from copy import deepcopy
from scripts.compare_policy import compare

ROOT=Path('data/research')

def build():
    path=ROOT/'marriage-targeted-poll-candidates.json'
    candidates=json.loads(path.read_text())
    for source in candidates['sources']:
        assert hashlib.sha256(Path(source['path']).read_bytes()).hexdigest()==source['sha256']
    base=json.loads((ROOT/'marriage-case-study.json').read_text())
    cases=json.loads((ROOT/'marriage-case-components.json').read_text())['cases']
    mapping=json.loads((ROOT/'marriage-policy-mapping.json').read_text())
    records=[]
    for i,r in enumerate(candidates['records']):
        source=candidates['sources'][0 if r['source']=='Gallup' else 1]
        record=dict(source=r['source'],year=int(r['field_end'][:4]),variable=f'marriage_topline_{i+1}',
            field_start=r['field_start'],field_end=r['field_end'],data_kind='published_topline',
            wording=r['question_summary'],wording_note='Question summary (paraphrased). See the original report for exact wording and questionnaire context.',
            denominator='Published weighted percentages; includes no opinion. Rounded totals may equal 101%; values are not renormalized.',
            weight='Publisher-weighted topline; respondent-level weights unavailable',source_url=source['url'],
            source_page=r['page'],source_item=r['item'],sample_n=r['sample_n'],
            response_distribution=[dict(code=k,label=k.replace('_',' ').capitalize(),percent=v) for k,v in r['percent'].items()])
        if i==1:record['wording_note']+=' Report gives full-survey n and split forms; item-level sample size is not established.'
        if i==3:record['orientation']='Opposing this ban aligns with marriage access; support here means support for allowing bans.'
        records.append(record)
        policy=f'marriage_targeted_{i+1}'
        mapping['policies'][policy]=dict(support_definition=r['question_summary'],questions=[dict(source=r['source'],variable=record['variable'])])
        case=next(c for c in cases if c['case_id']==('2012-079' if i<2 else '2014-070'))
        original=case['components'][0 if i!=2 else 1]
        component=deepcopy(original)
        component.update(component_id=policy,policy_id=policy,issue=original['issue']+' — targeted polling',
            comparison_fit='contextual' if i==1 else 'direct',survey_fit=r['fit'])
        case['components'].append(component)
    result=compare(cases,base['survey_records']+records,mapping)
    result['survey_provenance']={**base['provenance'],**{s['path']:s['sha256'] for s in candidates['sources']}}
    result['input_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [path,ROOT/'marriage-case-study.json',ROOT/'marriage-case-components.json',ROOT/'marriage-policy-mapping.json',Path(__file__)]}
    (ROOT/'marriage-policy-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    (ROOT/'marriage-published-toplines.json').write_text(json.dumps(dict(survey_records=records,provenance=candidates['sources']),indent=2)+'\n')
    print('Integrated four organization-labeled toplines; original case comparisons retained.')

if __name__=='__main__':build()
