"""Six-request development comparison: fixed model/prompt, old vs repaired inputs."""
import argparse
import json
from pathlib import Path
from scvpublic.build import digest
from scripts import pilot_case_findings as api
from scripts import pilot_case_findings_v2 as v2

ROOT=Path('artifacts/repaired-input-comparison')
CASES=['2023-060','2020-015','1991-117']


def packet(key,syllabus,opinion,kind):
    sections=[];summary=api.normalized(syllabus);text=api.normalized(opinion)
    if summary:sections.append(dict(id='syllabus',type='syllabus',excerpted=len(summary)>7000,text=summary[:7000]))
    budget=16000-sum(len(s['text']) for s in sections)
    if len(text)<=budget:sections.append(dict(id='opinion',type=kind,excerpted=False,text=text))
    else:
        half=budget//2
        sections.extend([dict(id='opinion_start',type=kind,excerpted=True,text=text[:half]),dict(id='opinion_end',type=kind,excerpted=True,text=text[-half:])])
    for s in sections:
        s['passages']=[dict(id=p['id'],text=p['text']) for p in v2.passages(s)]
        del s['text']
    return dict(case_id=key,sections=sections)


def prepare():
    if (ROOT/'cohort.json').exists():raise FileExistsError('Preserve existing comparison inputs')
    source=Path('data/processed/modern/official.json')
    manifest=json.loads(Path('artifacts/prepared-opinion-sections/manifest.json').read_text())
    if digest(source)!=manifest['official_source_sha256']:raise ValueError('Source changed')
    official={r['case_id']:r for r in json.loads(source.read_text())['records']}
    prepared={r['case_id']:r for r in manifest['records']}
    packets=[];cohort=[];provenance=[]
    for key in CASES:
        ref=prepared['505.US.833' if key=='1991-117' else key];path=Path(ref['path'])
        if digest(path)!=ref['sha256']:raise ValueError('Candidate changed')
        doc=json.loads(path.read_text())
        if key=='1991-117':
            summary=doc['originals']['syllabus_field'];old=doc['originals']['opinion_field'];role='authored_text_candidate'
        else:summary='';old=official[key]['opinion'];role='principal_text_candidate'
        new='\n'.join(s['text'] for s in doc['sections'] if s['role']==role)
        if not new:raise ValueError('Missing candidate')
        for variant,text,kind in [('old',old,'opinion'),('repaired',new,role)]:
            item=f'{key}-{variant}'
            packets.append(packet(item,summary,text,kind));cohort.append(dict(case_id=item,split='comparison'))
        provenance.append(dict(case_id=key,candidate_sha256=ref['sha256'],old_text_sha256=api.sha(old),
            repaired_text_sha256=api.sha(new),old_chars=len(old),repaired_chars=len(new),
            authority_warning=doc['authority'],controlling_opinion_certified=False))
    ROOT.mkdir(parents=True,exist_ok=True)
    for name,value in [('packets.json',packets),('cohort.json',dict(cases=cohort)),('provenance.json',provenance)]:
        (ROOT/name).write_text(json.dumps(value,indent=2)+'\n')
    print('Prepared six fixed-budget packets; no interpretation expectations sent to model.')


def report():
    contract=json.loads((ROOT/'contract.json').read_text());packets={p['case_id']:p for p in json.loads((ROOT/'packets.json').read_text())}
    records=[]
    for key in packets:
        p=ROOT/(key+'.json')
        if not p.exists():continue
        r=json.loads(p.read_text())
        assert r['contract_sha256']==contract['sha256']
        assert r['packet_sha256']==api.sha(json.dumps(packets[key],sort_keys=True))
        assert r['validation_errors']==v2.validate(r['result'],packets[key])[0]
        records.append(r)
    output=dict(status='Paired development observations, one draw per condition; not causal accuracy proof',
        contract=contract,provenance=json.loads((ROOT/'provenance.json').read_text()),records=records,
        limitations=['Same 16000-character head/tail budget; repaired does not mean full opinion.',
            'Source labels and text change together; contribution of each is not isolated.',
            'One response per condition; temperature zero does not ensure deterministic replication.',
            'This tests input preparation, not prediction, policy scoring or whole-corpus accuracy.'])
    Path('data/evaluation/repaired-input-comparison.json').write_text(json.dumps(output,indent=2)+'\n')
    for r in records:
        print(r['case_id'],r['validation_errors'])
        for f in (r['result'] or {}).get('findings',[]):print(' ',f['nature'],f['decision_status'],f['actor'],f['outcome'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','run','report']);a=p.parse_args()
    if a.action=='prepare':prepare()
    elif a.action=='run':
        api.run('comparison',6,root=ROOT,prompt=v2.PROMPT,schema=v2.SCHEMA,validator=v2.validate,cohort_path=ROOT/'cohort.json')
    else:report()
