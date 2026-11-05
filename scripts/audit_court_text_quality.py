"""Read-only source-quality signals and cached official syllabus availability."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urldefrag

from scvpublic.build import digest
from scvpublic.sources import source_texts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, default=Path('artifacts/affirmative-action.sqlite'))
    parser.add_argument('--pdftotext', default='pdftotext')
    parser.add_argument('--output', type=Path, default=Path('artifacts/court-text-quality-signals.json'))
    args = parser.parse_args()
    official = Path('data/processed/modern/official.json')
    _, texts, origins = source_texts(args.artifact, official)
    signals = {}
    for origin in sorted(set(origins.values())):
        group = [text for key, text in texts.items() if origins[key] == origin]
        signals[origin] = dict(
            documents=len(group),
            watermark=sum('Page Proof Pending Publication' in text for text in group),
            line_end_hyphen=sum(bool(re.search(r'[A-Za-z]-\s*\n\s*[a-z]', text)) for text in group),
            opening_amicus=sum(bool(re.search(r'amicus|amici', text[:1800], re.I)) for text in group))
    rows = []
    for record in json.loads(official.read_text())['records']:
        url, fragment = urldefrag(record['source_url'])
        start = int(fragment.split('=')[1]) if fragment else 1
        pdf = Path('data/raw/official-scotus') / url.rsplit('/', 1)[-1]
        if digest(pdf) != record['pdf_sha256']:
            raise ValueError(f'PDF checksum mismatch: {pdf}')
        text = subprocess.check_output([
            args.pdftotext, '-f', str(start), '-l', str(start + 1),
            '-layout', str(pdf), '-'], timeout=60).decode('utf-8')
        rows.append(dict(case_id=record['case_id'],
            indexed=record['case_id'] in texts,
            syllabus_header_in_first_two_pages=bool(re.search(r'(?m)^\s*Syllabus\s*$', text))))
    report = dict(
        provenance={str(p): digest(p) for p in (args.artifact, official, Path(__file__))},
        counts=dict(Counter(origins.values())), signals=signals,
        limitations='Signals are not confirmed error rates. Amicus mentions can be substantive. '
                     'Syllabus header presence is not validated extraction; absence in two pages does not prove absence.',
        official_pdf_probe=dict(records=rows,
            indexed_syllabus_headers=sum(r['indexed'] and r['syllabus_header_in_first_two_pages'] for r in rows)))
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(signals=signals, indexed_syllabus_headers=report['official_pdf_probe']['indexed_syllabus_headers'])))


if __name__ == '__main__':
    main()
