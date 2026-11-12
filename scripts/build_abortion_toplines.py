"""Add pre-decision published toplines without pooling or altering raw surveys."""
import hashlib
import json
from pathlib import Path
from scripts.compare_policy import compare, report
ROOT=Path('data/research')

def build():
    spec=json.loads((ROOT/'abortion-published-toplines.json').read_text())
    for path,sha in spec['provenance'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha
    cases=json.loads((ROOT/'abortion-policy-components.json').read_text())['cases']
    mapping=json.loads((ROOT/'abortion-policy-mapping.json').read_text())
    base=json.loads((ROOT/'abortion-policy-surveys.json').read_text())
    for r in spec['survey_records']:
        policy=r['policy_id']
        mapping['policies'][policy]['questions'].append(dict(source=r['source'],variable=r['variable']))
        if policy!='retain_roe':
            mapping['policies'][policy]['support_definition']='Original favor/oppose categories concern the restriction; no access-oriented scalar is assigned.'
        for c in cases:
            for part in c['components']:
                if part['policy_id']==policy and c['case_id']==r['case_id']:
                    part['survey_fit']=r['survey_fit']
                    part['comparison_fit']=r['comparison_fit']
    result=compare(cases,base['survey_records']+spec['survey_records'],mapping)
    result['survey_provenance']={**base.get('provenance',{}),**spec['provenance']}
    result['input_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'abortion-published-toplines.json',ROOT/'abortion-policy-components.json',ROOT/'abortion-policy-mapping.json',ROOT/'abortion-policy-surveys.json',Path(__file__)]}
    (ROOT/'abortion-policy-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    Path('docs/ABORTION_POLICY_COMPARISON.md').write_text(report(result))
    print('Added four verified pre-decision toplines.')
if __name__=='__main__':build()
