"""Reproduce reviewed official-source repairs without overwriting serving inputs.

The checked-in manifest pins inputs and visually reviewed boundary-page spans.
It is a finite repair set, not a general footnote attribution classifier.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urldefrag

from scvpublic.build import digest
from scvpublic.modern import IndexParser, principal
from scripts.audit_opinion_structure import principal_spans

MANIFEST = Path('data/research/official-repair-validation.json')
SOURCE = Path('data/processed/modern/official.json')
OUTPUT = Path('data/processed/modern/official-repaired.json')
CACHE = Path('data/raw/official-scotus')


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def checked_span(page, span):
    start, end = span['start'], span['end']
    if not 0 <= start < end <= len(page):
        raise ValueError('Invalid reviewed span bounds')
    text = page[start:end]
    if sha(text) != span['sha256']:
        raise ValueError('Reviewed span checksum mismatch')
    return text


def repair_text(candidate, page, decision):
    if sha(candidate) != decision['candidate_text_sha256']:
        raise ValueError('Candidate text changed since review')
    if sha(page) != decision['boundary_page_sha256']:
        raise ValueError('Boundary page changed since review')
    result = candidate
    previous_end = decision['principal_prefix_end']
    for span in decision['additional_spans']:
        if span['start'] < previous_end:
            raise ValueError('Additional spans overlap principal text or each other')
        result += '\n' + checked_span(page, span)
        previous_end = span['end']
    if sha(result) != decision['repaired_text_sha256']:
        raise ValueError('Repaired output differs from reviewed text')
    return result


def unique_rows(rows):
    result = {row['case_id']: row for row in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate case IDs')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdftotext', default=shutil.which('pdftotext'))
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    if not args.pdftotext:
        parser.error('Pass --pdftotext /path/to/pdftotext')
    if args.output.resolve() == SOURCE.resolve():
        parser.error('Refusing to overwrite the original source')
    if args.output.exists():
        parser.error('Output already exists; use a new --output path')
    manifest = json.loads(MANIFEST.read_text())
    if digest(SOURCE) != manifest['source_sha256']:
        raise ValueError('Source changed since review')
    if digest(Path('scvpublic/modern.py')) != manifest['extractor_sha256']:
        raise ValueError('Extractor changed since review')
    source = json.loads(SOURCE.read_text())
    rows = unique_rows(source['records'])
    decisions = unique_rows(manifest['records'])
    if not decisions.keys() <= rows.keys():
        raise ValueError('Reviewed cases missing from source')
    index = []
    for path in sorted(CACHE.glob('index-*.html')):
        parsed = IndexParser()
        parsed.feed(path.read_text(encoding='utf-8-sig'))
        index.extend(parsed.rows)
    repaired = copy.deepcopy(source)
    repaired_rows = unique_rows(repaired['records'])
    details = []
    for key, decision in decisions.items():
        row = rows[key]
        if sha(row['opinion']) != decision['old_text_sha256']:
            raise ValueError('Original text mismatch: ' + key)
        url, fragment = urldefrag(row['source_url'])
        pdf = CACHE / url.rsplit('/', 1)[-1]
        if digest(pdf) != row['pdf_sha256'] or row['pdf_sha256'] != decision['pdf_sha256']:
            raise ValueError('PDF checksum mismatch: ' + key)
        raw = subprocess.check_output(
            [args.pdftotext, '-layout', str(pdf), '-'], timeout=60).decode('utf-8')
        pages = raw.split('\f')
        offset = int(fragment.split('=')[1]) - 1 if fragment else 0
        offsets = [int(urldefrag(i['url'])[1].split('=')[1]) - 1 for i in index
                   if urldefrag(i['url'])[0] == url and urldefrag(i['url'])[1]]
        end = min((n for n in offsets if n > offset), default=len(pages)) if fragment else len(pages)
        window = '\f'.join(pages[offset:end])
        candidate, numbers = principal(window)
        absolute_pages = [n + offset for n in numbers]
        if absolute_pages != decision['repaired_pages']:
            raise ValueError('Page selection changed since review: ' + key)
        spans = principal_spans(window, candidate, numbers)
        boundary = pages[absolute_pages[-1] - 1]
        last = next(s for s in spans if s['role'] == 'principal_candidate' and s['page'] == numbers[-1])
        if last['end'] != decision['principal_prefix_end']:
            raise ValueError('Principal boundary changed since review: ' + key)
        opinion = repair_text(candidate, boundary, decision)
        repaired_rows[key].update(opinion=opinion, pdf_pages=absolute_pages)
        details.append(dict(case_id=key, old_text_sha256=sha(row['opinion']),
                            repaired_text_sha256=sha(opinion), principal_spans=spans,
                            page_offset=offset, additional_spans=decision['additional_spans']))
    changed = {key for key in rows if rows[key] != repaired_rows[key]}
    if changed != set(decisions):
        raise ValueError('Changed record set differs from reviewed set')
    if digest(SOURCE) != manifest['source_sha256']:
        raise ValueError('Source changed during repair')
    repaired.update(revised_from_sha256=manifest['source_sha256'],
                    extractor_sha256=manifest['extractor_sha256'],
                    repair_manifest_sha256=digest(MANIFEST))
    payload = json.dumps(repaired, indent=2) + '\n'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects existing source/candidate files even on a race.
    with args.output.open('x') as stream:
        stream.write(payload)
    report_dir = Path('artifacts/official-repair-validation')
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / 'applied.json').write_text(json.dumps(dict(
        output=str(args.output), sha256=digest(args.output), changed=len(changed),
        unchanged=len(rows)-len(changed), records=details), indent=2)+'\n')
    print(f'Repaired {len(changed)} records; {len(rows)-len(changed)} unchanged. Output: {args.output}')


if __name__ == '__main__':
    main()
