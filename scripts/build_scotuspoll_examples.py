"""Convert reviewed, published toplines to two bounded policy examples."""
import hashlib
import json
from pathlib import Path
from scripts.compare_policy import compare, report

ROOT=Path('data/research')
INPUT=Path('data/scotuspoll/policy-toplines.json')

def build():
    spec=json.loads(INPUT.read_text())
    records=[]
    for row in spec['rows']:
        source=spec['sources'][str(row['year'])]
        if not 0 < row['item_n'] <= source['sample_n']:
            raise ValueError('Invalid published sample count')
        records.append(dict(source='SCOTUSPoll',year=row['year'],variable=row['variable'],wording=row['wording'],
            response_distribution=[dict(code=c,label=l,percent=v) for c,l,v in row['answers']],
            denominator=f"Published two-option percentages; item N={row['item_n']:,} of {source['sample_n']:,} survey respondents. No reconstruction of omitted answers or new weighting. Rounded publisher estimates, not raw counts.",
            weight='Published topline; respondent weights not loaded',n=row['item_n'],
            fieldwork_start=source['fieldwork_start'],fieldwork_end=source['fieldwork_end'],fieldwork_source=source['fieldwork_source'],
            source_url=source['url'],source_page=row['page'],attribution=spec['attribution'],
            wording_note='Question and answer labels paraphrased; consult the linked PDF for exact wording and randomized option order.'))
    provenance={str(INPUT):hashlib.sha256(INPUT.read_bytes()).hexdigest(),str(Path(__file__)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    for topic in ['firearms','religion']:
        case_path=ROOT/f'{topic}-policy-components.json'
        mapping_path=ROOT/f'{topic}-policy-mapping.json'
        mapping=json.loads(mapping_path.read_text())
        codes={q['variable'] for p in mapping['policies'].values() for q in p['questions']}
        observations=[r for r in records if r['variable'] in codes]
        result=compare(json.loads(case_path.read_text())['cases'],observations,mapping)
        result['survey_provenance']=provenance
        result['input_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [INPUT,case_path,mapping_path,Path(__file__)]}
        result['limitations'] += ['Published toplines, not independently reweighted microdata; exact question wording is in the source PDF.',
                                 'These deliberately chosen examples are not a representative sample. Narrow percentage leads are not significance claims.',
                                 'Direct match denotes the stated policy component, not endorsement of every rationale or factual qualification.']
        (ROOT/f'{topic}-policy-comparison.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        Path(f'docs/{topic.upper()}_POLICY_COMPARISON.md').write_text(report(result))
        print(topic,len(result['cases']),'cases')

if __name__=='__main__':build()
