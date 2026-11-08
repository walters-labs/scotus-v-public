"""Four-request development check of Woodson recovery and Coinbase footnote repair."""
import argparse
import json
from pathlib import Path
from scvpublic.build import digest
from scripts import pilot_case_findings as api
from scripts import pilot_case_findings_v2 as v2
from scripts.compare_repaired_inputs import packet
from scripts.recover_woodson import sections as recovered_sections

ROOT = Path('artifacts/source-repair-comparison')


def prepare():
    if ROOT.exists(): raise FileExistsError('Preserve earlier comparison')
    prior_contract = json.loads(Path('artifacts/repaired-input-comparison/contract.json').read_text())
    if api.config().get('GROQ_MODEL', 'openai/gpt-oss-120b') != prior_contract['model']:
        raise ValueError('Model changed; comparison requires previous fixed model')
    cohort = json.loads(api.COHORT.read_text())['cases']
    if any(r['case_id'] in ['1975-176','2022-043'] and r['split']=='evaluation' for r in cohort):
        raise ValueError('Do not consume reserved evaluation cases')
    prefix = Path('data/processed/casesumm/opinion-repairs.json')
    expected = json.loads(Path('data/evaluation/casesumm-prefix-repairs.json').read_text())
    if digest(prefix) != expected['output_sha256']: raise ValueError('Prefix source changed')
    woodson_old = next(r for r in json.loads(prefix.read_text())['records'] if r['case_id']=='1975-176')
    recovery_path = Path('data/processed/casesumm/woodson-recovered.json')
    recovered = json.loads(recovery_path.read_text())
    if recovered['manifest_sha256'] != digest(Path('data/research/woodson-source-recovery.json')):
        raise ValueError('Recovery manifest mismatch')
    recovery_manifest = json.loads(Path('data/research/woodson-source-recovery.json').read_text())
    if recovered_sections(recovered['original_pdf_text'], recovery_manifest) != recovered['sections']:
        raise ValueError('Recovered sections differ from pinned source')
    woodson_new = '\n'.join(s['text'] for s in recovered['sections'] if s['role'].startswith('principal_plurality'))
    old_path = Path('data/processed/modern/official.json')
    new_path = Path('data/processed/modern/official-repaired.json')
    official_summary = json.loads(Path('data/evaluation/official-repair-summary.json').read_text())
    if digest(old_path)!=official_summary['source_sha256'] or digest(new_path)!=official_summary['output_sha256']:
        raise ValueError('Official source hash mismatch')
    old = next(r for r in json.loads(old_path.read_text())['records'] if r['case_id']=='2022-043')['opinion']
    new = next(r for r in json.loads(new_path.read_text())['records'] if r['case_id']=='2022-043')['opinion']
    pairs = [('1975-176', woodson_old['syllabus'], woodson_old['opinion'], woodson_new, 'three_justice_plurality_not_majority_reasoning'),
             ('2022-043', '', old, new, 'principal_opinion_source')]
    packets, provenance = [], []
    for key, summary, before, after, role in pairs:
        for variant, text, kind in [('old',before,'opinion'),('repaired',after,role)]:
            packets.append(packet(key+'-'+variant, summary, text, kind))
        provenance.append(dict(case_id=key,old_sha256=api.sha(before),repaired_sha256=api.sha(after),
                               old_characters=len(before),repaired_characters=len(after)))
    expectations = dict(status='Frozen before model calls; assistant assessment, not independent ground truth',
        woodson=['Recognize the case concerns North Carolina mandatory capital sentencing, not a categorical ban on capital punishment.',
                 'Recover the separate proportionality question expressly not reached in footnote 40.',
                 'Do not describe three-justice plurality reasoning as unanimously or wholly majority-endorsed.'],
        coinbase=['Distinguish interlocutory arbitration-appeal stay procedure from substantive enforceability of arbitration.',
                  'Recover the Suski companion writ dismissal as improvidently granted from footnote 7.'],
        limitations=['One draw per condition; no corpus-level accuracy estimate.',
                     'Same prompt, schema, model and 16000-character head/tail budget; source text and labels change together.',
                     'Woodson old source is summary-only; repaired packet still excerpts the recovered plurality.',
                     'Woodson concurrences are preserved locally but not included in these fixed-budget comparison packets.'])
    ROOT.mkdir()
    for name, obj in [('packets.json',packets),('cohort.json',dict(cases=[dict(case_id=p['case_id'],split='comparison') for p in packets])),('provenance.json',provenance),('expectations.json',expectations)]:
        (ROOT/name).write_text(json.dumps(obj,indent=2)+'\n')
    print('Prepared four packets; no rubric expectations included in model inputs.')


def report():
    packets={p['case_id']:p for p in json.loads((ROOT/'packets.json').read_text())}
    contract=json.loads((ROOT/'contract.json').read_text());records=[]
    for key,p in packets.items():
        path=ROOT/(key+'.json')
        if not path.exists():continue
        r=json.loads(path.read_text())
        if r['contract_sha256']!=contract['sha256'] or r['packet_sha256']!=api.sha(json.dumps(p,sort_keys=True)):
            raise ValueError('Result/contract mismatch')
        if r['validation_errors']!=v2.validate(r['result'],p)[0]:raise ValueError('Validation changed')
        records.append(r)
    result=dict(status='Development comparison, not held-out accuracy',contract=contract,
                expectations=json.loads((ROOT/'expectations.json').read_text()),
                provenance=json.loads((ROOT/'provenance.json').read_text()),records=records)
    Path('data/evaluation/source-repair-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    for r in records:
        print(r['case_id'],r['validation_errors'])
        print(json.dumps(r['result'],indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','run','report']);args=p.parse_args()
    if args.action=='prepare':prepare()
    elif args.action=='report':report()
    else:api.run('comparison',4,root=ROOT,prompt=v2.PROMPT,schema=v2.SCHEMA,validator=v2.validate,cohort_path=ROOT/'cohort.json')
