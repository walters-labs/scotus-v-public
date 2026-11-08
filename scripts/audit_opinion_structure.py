"""Read-only, bounded source-structure audit. No API or serving changes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urldefrag

from scvpublic.build import digest
from scvpublic.modern import IndexParser, principal

CASES = ['2018-010','2018-063','2020-007','2020-013','2020-015','2022-004','2023-049','2023-060']


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def principal_spans(text, extracted, numbers):
    """Map existing extractor output back to lossless page-prefix offsets.

    These spans still contain headers/footnotes. They are not certified speaker
    blocks. Unselected text is retained as unassigned, never silently deleted.
    """
    pages=text.split('\f');remaining=extracted;spans=[]
    for number in numbers:
        page=pages[number-1]
        prefix=0
        for a,b in zip(page,remaining):
            if a!=b:break
            prefix+=1
        if not prefix:raise ValueError('Cannot map extracted page prefix')
        spans.append(dict(page=number,start=0,end=prefix,role='principal_candidate',sha256=sha(page[:prefix])))
        remaining=remaining[prefix:]
        if number!=numbers[-1]:
            if not remaining.startswith('\n'):raise ValueError('Unexpected page separator')
            remaining=remaining[1:]
    if remaining:raise ValueError('Unmapped extraction tail')
    for number,page in enumerate(pages,1):
        end=next((s['end'] for s in spans if s['page']==number),0)
        if end<len(page):spans.append(dict(page=number,start=end,end=len(page),role='unassigned',sha256=sha(page[end:])))
    return sorted(spans,key=lambda s:(s['page'],s['start']))


def opening_notice(extracted):
    # Diagnostic only: never infer that an unflagged opinion is wholly controlling.
    text=re.sub(r'\s+',' ',extracted[:4500])
    match=re.search(r'(?:Chief )?Justice\b.{0,150}?\b(?:announced|delivered)\b.{0,650}',text,re.I)
    notice=match.group() if match else ''
    return dict(excerpt=notice,
        part_or_plurality_warning=bool(re.search(r'announced the judgment|except as to Part|with respect to Parts',notice,re.I)),
        authority='not_validated; principal does not mean wholly controlling')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdftotext',default=shutil.which('pdftotext'))
    args=parser.parse_args()
    if not args.pdftotext:parser.error('Pass --pdftotext /path/to/pdftotext')
    source=Path('data/processed/modern/official.json');before=digest(source)
    cache=Path('data/raw/official-scotus');out=Path('artifacts/opinion-structure-pilot');out.mkdir(exist_ok=True)
    index=[]
    for p in sorted(cache.glob('index-*.html')):
        parsed=IndexParser();parsed.feed(p.read_text(encoding='utf-8-sig'));index+=parsed.rows
    rows={r['case_id']:r for r in json.loads(source.read_text())['records']}
    results=[]
    for key in CASES:
        row=rows[key];url,fragment=urldefrag(row['source_url']);pdf=cache/url.rsplit('/',1)[-1]
        if digest(pdf)!=row['pdf_sha256']:raise ValueError('PDF hash mismatch')
        raw=subprocess.check_output([args.pdftotext,'-layout',str(pdf),'-'],timeout=60).decode()
        pages=raw.split('\f');start=int(fragment.split('=')[1])-1 if fragment else 0
        offsets=[int(urldefrag(i['url'])[1].split('=')[1])-1 for i in index
                 if urldefrag(i['url'])[0]==url and urldefrag(i['url'])[1]]
        end=min((n for n in offsets if n>start),default=len(pages)) if fragment else len(pages)
        text='\f'.join(pages[start:end]);extracted,numbers=principal(text)
        spans=principal_spans(text,extracted,numbers)
        (out/(key+'.txt')).write_text(text);(out/(key+'-principal.txt')).write_text(extracted)
        (out/(key+'-spans.json')).write_text(json.dumps(spans,indent=2)+'\n')
        headers=[]
        for n,page in enumerate(pages[start:end],start+1):
            lines=[x.strip() for x in page.splitlines() if x.strip()]
            if lines:headers.append(dict(page=n,lines=lines[:4]))
        record=dict(case_id=key,name=row['name'],pdf=str(pdf),source_url=row['source_url'],pdf_sha256=row['pdf_sha256'],
            start=start,end=end,principal_pages=[n+start for n in numbers],stored_pages=row['pdf_pages'],
            case_window_sha256=sha(text),same_as_stored=extracted==row['opinion'],stored_text_sha256=sha(row['opinion']),candidate_text_sha256=sha(extracted),
            opening=opening_notice(extracted),spans_path=str(out/(key+'-spans.json')),headers=headers)
        results.append(record)
    # Two unpaginated CaseSumm controls: expose source field structure without
    # applying a PDF page-header parser to a flat string.
    import pyarrow as pa
    from scvpublic.casesumm import FILES,citation_key
    controls=[];raw_controls=[]
    for name,expected in FILES.items():
        path=Path('data/raw/casesumm')/name
        if digest(path)!=expected:raise ValueError('CaseSumm hash mismatch')
        with pa.memory_map(str(path),'r') as stream:
            for batch in pa.ipc.open_stream(stream):
                for row in batch.to_pylist():
                    if citation_key(row['citation']) not in ['410 U.S. 113','505 U.S. 833']:continue
                    raw_controls.append(row);text=row['opinion']
                    markers=[dict(offset=m.start(),excerpt=text[m.start():m.start()+500]) for m in
                        re.finditer(r"Justice\b[^.]{0,140}\bannounced the judgment of the Court and delivered",text)]
                    controls.append(dict(citation=row['citation'],opinion_sha256=sha(text),characters=len(text),
                        start=text[:350],authored_opening_candidates=markers,
                        status='unpaginated; no automatic principal split or authority assignment'))
    (out/'casesumm-controls.json').write_text(json.dumps(raw_controls,indent=2)+'\n')
    (out/'inputs.json').write_text(json.dumps(results,indent=2)+'\n')
    compact=[{k:v for k,v in r.items() if k!='headers'} for r in results]
    report=dict(status='Source boundary audit only; no full-opinion interpretation or production changes',
        source_sha256=before,extractor_sha256=digest(Path('scvpublic/modern.py')),audit_sha256=digest(Path(__file__)),
        pdf_cases=len(results),changed_stored_texts=[r['case_id'] for r in results if not r['same_as_stored']],
        explicit_part_or_plurality_warnings=[r['case_id'] for r in results if r['opening']['part_or_plurality_warning']],
        records=compact,casesumm_controls=controls)
    Path('data/evaluation/opinion-structure-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    assert digest(source)==before
    print(json.dumps({k:v for k,v in report.items() if k not in ['records','casesumm_controls']},indent=2))


if __name__=='__main__':main()
