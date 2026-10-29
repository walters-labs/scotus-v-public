"""Dry-run revised extraction against cached PDFs; never replace serving inputs."""
import argparse
import json
from pathlib import Path
import subprocess
from urllib.parse import urldefrag
from scvpublic.modern import principal,IndexParser
from scvpublic.build import digest


def main():
    source=Path('data/processed/modern/official.json')
    cache=Path('data/raw/official-scotus')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdftotext',default='pdftotext')
    parser.add_argument('--candidate-output',type=Path,help='Write a separate corrected source file only if every record extracts successfully')
    args=parser.parse_args()
    converter=args.pdftotext
    if args.candidate_output and args.candidate_output.exists():
        raise FileExistsError(args.candidate_output)
    index=[]
    for p in cache.glob('index-*.html'):
        parser=IndexParser();parser.feed(p.read_text(encoding='utf-8-sig'));index.extend(parser.rows)
    original=json.loads(source.read_text())
    texts={};result=[];corrected=[]
    for row in original['records']:
        url,fragment=urldefrag(row['source_url']);path=cache/url.rsplit('/',1)[1]
        if digest(path)!=row['pdf_sha256']:
            raise ValueError('PDF checksum mismatch: '+str(path))
        if url not in texts:
            texts[url]=subprocess.check_output([converter,'-layout',str(path),'-'],timeout=60).decode('utf-8')
        text=texts[url];offset=int(fragment.split('=')[1])-1 if fragment else 0
        if fragment:
            offsets=[int(urldefrag(i['url'])[1].split('=')[1])-1 for i in index if urldefrag(i['url'])[0]==url and urldefrag(i['url'])[1]]
            end=min((n for n in offsets if n>offset),default=len(text.split('\f')))
            text='\f'.join(text.split('\f')[offset:end])
        try:
            new,pages=principal(text);pages=[n+offset for n in pages]
            corrected.append(dict(row,opinion=new,pdf_pages=pages))
            status='unchanged' if new==row['opinion'] else 'changed'
            result.append(dict(case_id=row['case_id'],status=status,old_pages=row['pdf_pages'],new_pages=pages,old_words=len(row['opinion'].split()),new_words=len(new.split())))
        except ValueError as e:result.append(dict(case_id=row['case_id'],status='rejected',reason=str(e)))
    report=dict(source_sha256=digest(source),extractor_sha256=digest(Path('scvpublic/modern.py')),records=result)
    Path('artifacts/official-extraction-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    if args.candidate_output:
        if len(corrected)!=len(original['records']):
            raise ValueError('Candidate not written: unresolved extraction errors')
        original.update(records=corrected,extractor_sha256=report['extractor_sha256'],
                        revised_from_sha256=report['source_sha256'])
        args.candidate_output.parent.mkdir(parents=True,exist_ok=True)
        args.candidate_output.write_text(json.dumps(original,indent=2)+'\n')
    from collections import Counter
    print(dict(Counter(r['status'] for r in result)))


if __name__=='__main__':main()
