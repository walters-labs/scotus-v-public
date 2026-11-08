"""Apply reviewed CaseSumm prefix boundaries to a separate, lossless repair file.

No heuristic chooses the cut during application. Each decision pins original
text, offset and retained text; changed inputs fail closed. Not a serving index.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

from scvpublic.build import digest
from scvpublic.casesumm import FILES, citation_key, resolve

MANIFEST = Path('data/research/casesumm-prefix-review.json')
OUTPUT = Path('data/processed/casesumm/opinion-repairs.json')
STATUSES = {'preface_separated', 'unchanged_no_justified_prefix', 'unresolved_summary_only'}


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def apply_decision(raw, decision):
    text, syllabus = raw['opinion'] or '', raw['syllabus'] or ''
    if raw['citation'] != decision['citation']:
        raise ValueError('Citation mismatch')
    if sha(text) != decision['opinion_sha256'] or sha(syllabus) != decision['syllabus_sha256']:
        raise ValueError('Source text changed since review')
    cut = decision['split_offset']
    status = decision['status']
    if status not in STATUSES or type(cut) is not int or not 0 <= cut < len(text):
        raise ValueError('Invalid repair decision')
    if (status == 'preface_separated') != (cut > 0):
        raise ValueError('Status and prefix boundary disagree')
    prefix, retained = text[:cut], text[cut:]
    if sha(prefix) != decision['prefix_sha256'] or sha(retained) != decision['retained_sha256']:
        raise ValueError('Reviewed boundary checksum mismatch')
    sections = []
    if cut:
        sections.append(dict(start=0, end=cut, role='prefatory_material', sha256=sha(prefix)))
    sections.append(dict(start=cut, end=len(text),
                         role='post_preface_text_not_authority_certified' if cut else 'unsegmented_source_field',
                         sha256=sha(retained)))
    # The excluded prefix is retained verbatim, so the original is reconstructible.
    return dict(case_id=decision['case_id'], citation=raw['citation'],
                status=status, original_opinion_sha256=sha(text),
                syllabus=syllabus, opinion=retained, prefatory_material=prefix,
                sections=sections, controlling_opinion_certified=False)


def load_sources(manifest):
    import pyarrow as pa

    if manifest['casesumm_files'] != FILES:
        raise ValueError('CaseSumm source version differs from review')
    scdb = Path(manifest['scdb_path'])
    if digest(scdb) != manifest['scdb_sha256']:
        raise ValueError('SCDB identity data changed since review')
    citations, dockets = defaultdict(list), defaultdict(list)
    with scdb.open(encoding='utf-8-sig') as stream:
        for row in csv.DictReader(stream):
            citations[citation_key(row['usCite'])].append(row)
            dockets[(row['term'], row['docket'])].append(row)
    decisions = {r['case_id']: r for r in manifest['records']}
    if len(decisions) != len(manifest['records']):
        raise ValueError('Duplicate review identity')
    wanted_citations = {r['citation'] for r in decisions.values()}
    found = {}
    for name, expected in FILES.items():
        path = Path('data/raw/casesumm') / name
        if digest(path) != expected:
            raise ValueError('CaseSumm checksum mismatch: ' + name)
        with pa.memory_map(str(path), 'r') as stream:
            for batch in pa.ipc.open_stream(stream):
                for row in batch.to_pylist():
                    if row['citation'] not in wanted_citations:
                        continue
                    doc, _ = resolve(row['citation'], citations, dockets)
                    if not doc or doc['case_id'] not in decisions:
                        raise ValueError('Case identity mismatch')
                    key = doc['case_id']
                    if key in found and found[key] != row:
                        raise ValueError('Conflicting duplicate raw source')
                    found[key] = row
    if set(found) != set(decisions):
        raise ValueError('Incomplete reviewed source coverage')
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; choose a new --output path')
    manifest = json.loads(MANIFEST.read_text())
    sources = load_sources(manifest)
    records = [apply_decision(sources[r['case_id']], r) for r in manifest['records']]
    counts = dict(Counter(r['status'] for r in records))
    if counts != manifest['summary']:
        raise ValueError('Repair counts differ from review')
    output = dict(format_version=1, status='offline_source_overlay_not_deployed',
                  manifest_sha256=digest(MANIFEST), casesumm_files=FILES,
                  summary=counts, limitations=manifest['limitations'], records=records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        stream.write(json.dumps(output, indent=2)+'\n')
    report = dict(status=output['status'], output=str(args.output),
                  output_sha256=digest(args.output), manifest_sha256=digest(MANIFEST),
                  summary=counts, lossless_partitions_verified=len(records),
                  separated_characters=sum(len(r['prefatory_material']) for r in records),
                  limitations=manifest['limitations'])
    Path('data/evaluation/casesumm-prefix-repairs.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('output','summary','lossless_partitions_verified')}, indent=2))


if __name__ == '__main__':
    main()
