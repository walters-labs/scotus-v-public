"""Measure repaired-source exposure in search without rebuilding or changing scores."""
import argparse
import hashlib
import json
from pathlib import Path

from scvpublic.build import digest
from scvpublic.sources import source_texts, select_text


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def verified(summary_path):
    summary = json.loads(Path(summary_path).read_text())
    path = Path(summary['output'])
    if digest(path) != summary['output_sha256']:
        raise ValueError(f'Repaired output checksum mismatch: {path}')
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, default=Path('artifacts/scdb-issues.sqlite'))
    parser.add_argument('--output', type=Path, default=Path('data/evaluation/repair-search-impact.json'))
    args = parser.parse_args()
    docs, texts, origins = source_texts(args.artifact)
    wanted = {d['case_id'] for d in docs}
    prefixes = verified('data/evaluation/casesumm-prefix-repairs.json')
    official = verified('data/evaluation/official-repair-summary.json')
    original = json.loads(Path('data/processed/modern/official.json').read_text())
    before = {r['case_id']: r['opinion'] for r in original['records']}
    prefix_rows = []
    for r in prefixes['records']:
        key = r['case_id']
        if key not in wanted:
            continue
        old = r['prefatory_material'] + r['opinion']
        if sha(old) != r['original_opinion_sha256']:
            raise ValueError(f'Lossless partition mismatch: {key}')
        selected, _ = select_text(r['syllabus'], old)
        if selected != texts[key]:
            raise ValueError(f'Unexpected baseline source: {key}')
        new, _ = select_text(r['syllabus'], r['opinion'])
        prefix_rows.append(dict(case_id=key, status=r['status'],
            embedding_input_changed_if_prefix_removed=new != selected,
            tfidf_input_changed_if_prefix_removed=' '.join(old.split()) != ' '.join(r['opinion'].split())))
    official_rows = []
    for r in official['records']:
        key = r['case_id']
        if r['opinion'] == before[key]:
            continue
        official_rows.append(dict(case_id=key, indexed=key in wanted,
            selected_official_source=origins.get(key) == 'official_opinion_fallback'))
    recovered = verified('data/evaluation/woodson-source-recovery.json')
    woodson = next(r for r in prefixes['records'] if r['case_id'] == recovered['case_id'])
    full = '\n'.join(s['text'] for s in recovered['sections'] if s['role'].startswith('principal_plurality'))
    selected, origin = select_text(woodson['syllabus'], full)
    result = dict(status='input_impact_only_not_relevance_validation',
        artifact_sha256=digest(args.artifact), indexed_cases=len(docs),
        prefix_repairs=dict(indexed_records=len(prefix_rows),
            tfidf_changes_if_trimmed=sum(r['tfidf_input_changed_if_prefix_removed'] for r in prefix_rows),
            embedding_changes_if_trimmed=sum(r['embedding_input_changed_if_prefix_removed'] for r in prefix_rows),
            recommendation='Retain prefatory text for retrieval; use boundaries only for attribution experiments.', records=prefix_rows),
        official_repairs=dict(changed_records=len(official_rows),
            selected_changed_records=sum(r['selected_official_source'] for r in official_rows), records=official_rows),
        woodson=dict(case_id=recovered['case_id'], baseline_embedding_origin=origins[recovered['case_id']],
            candidate_embedding_origin=origin, embedding_input_changed=selected != texts[recovered['case_id']],
            recovered_principal_words=len(full.split()),
            limitation='Recovered principal is a plurality; source length is not authority or relevance.'),
        limitations=['No candidate index built; no evidence of ranking improvement yet.',
                    'Changing TF-IDF documents also changes corpus IDF and can affect unrepaired cases.',
                    'Source repairs do not change SCDB direction, votes, or policy interpretation.'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: {a:b for a,b in v.items() if a != 'records'} if isinstance(v,dict) else v
                      for k,v in result.items()}, indent=2))


if __name__ == '__main__':
    main()
