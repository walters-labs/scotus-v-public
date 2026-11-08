"""Reproduce the reviewed Woodson source sections from the pinned official PDF."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from scvpublic.build import digest
from scripts.repair_casesumm_prefixes import sha

MANIFEST = Path('data/research/woodson-source-recovery.json')


def sections(text, manifest):
    if sha(text) != manifest['extracted_sha256']:
        raise ValueError('PDF extraction differs from reviewed text')
    pages = text.split('\f')
    result = []
    occupied = {}
    for span in manifest['spans']:
        n, a, b = span['page'], span['start'], span['end']
        if not 1 <= n <= len(pages) or not 0 <= a < b <= len(pages[n-1]):
            raise ValueError('Invalid reviewed span')
        if any(a < y and x < b for x, y in occupied.get(n, [])):
            raise ValueError('Overlapping source spans')
        occupied.setdefault(n, []).append((a, b))
        part = pages[n-1][a:b]
        if sha(part) != span['sha256']:
            raise ValueError('Reviewed span checksum mismatch')
        result.append(dict(span, text=part))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pdftotext', default=shutil.which('pdftotext'))
    p.add_argument('--output', type=Path, default=Path('data/processed/casesumm/woodson-recovered.json'))
    args = p.parse_args()
    if not args.pdftotext: p.error('Pass --pdftotext /path/to/pdftotext')
    if args.output.exists(): p.error('Output exists; use a new --output path')
    manifest = json.loads(MANIFEST.read_text())
    if digest(Path(manifest['pdf_path'])) != manifest['pdf_sha256']:
        raise ValueError('Official PDF checksum mismatch')
    text = subprocess.check_output([args.pdftotext, '-layout', manifest['pdf_path'], '-'], timeout=60).decode()
    extracted = sections(text, manifest)
    result = dict(case_id=manifest['case_id'], citation=manifest['citation'],
                  source_url=manifest['source_url'], source_sha256=manifest['pdf_sha256'],
                  manifest_sha256=digest(MANIFEST), original_pdf_text=text, sections=extracted,
                  authority=manifest['authority'], limitations=manifest['limitations'],
                  status='recovered_local_source_not_deployed')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream: stream.write(json.dumps(result, indent=2)+'\n')
    print('Recovered',len(extracted),'source spans; original full extraction preserved')


if __name__ == '__main__': main()
