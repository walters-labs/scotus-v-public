"""Cache official SCOTUS indexes/PDFs and extract principal opinions for SCDB gaps."""
import argparse
from datetime import datetime
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import time
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urldefrag
from .build import digest

BASE = 'https://www.supremecourt.gov'


class IndexParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.cells=None; self.cell=None; self.url=None
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='tr': self.cells=[]; self.url=None
        if tag=='td' and self.cells is not None: self.cell=[]
        if tag=='a' and self.cells is not None and re.match(r'/opinions/(?:\d+pdf|preliminaryprint|boundvolumes)/.*\.pdf(?:#page=\d+)?$',attrs.get('href',''),re.I):
            self.url=urljoin(BASE,attrs['href'])
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag=='td' and self.cell is not None:
            self.cells.append(' '.join(''.join(self.cell).split())); self.cell=None
        if tag=='tr' and self.cells is not None:
            if self.url and len(self.cells)>=4:
                date=None
                for fmt in ('%m/%d/%y','%m/%d/%Y'):
                    try: date=datetime.strptime(self.cells[1],fmt).date().isoformat(); break
                    except ValueError: pass
                if date:self.rows.append(dict(date=date,docket=self.cells[2],name=self.cells[3],url=self.url))
            self.cells=None; self.cell=None


def principal(text):
    """Use running headers, never body mentions of dissents, as boundaries."""
    pages=text.split('\f'); chosen=[]; started=False
    for number,page in enumerate(pages,1):
        lines=[line.strip() for line in page.splitlines() if line.strip()]
        if not lines:
            continue
        running_header = lines[1] if len(lines)>1 else ''
        separate=bool(re.search(r'\b(concurring|dissenting)\b', running_header, re.I))
        main=bool(re.search(r'Opinion of the Court|Per Curiam', ' '.join(lines[:3])))
        # Pluralities have an authored header; require an explicit judgment
        # announcement at the opening, not just any justice's opinion header.
        if re.search(r'Opinion of [A-Z]', running_header):
            opening = ' '.join(lines[2:8])
            main = main or bool(re.match(
                r'(?:Chief )?Justice [A-Za-z]+ announced the judgment of the Court', opening))
        # In edited Reports, a separate opinion can begin midway down the last
        # majority page. Keep the majority prefix rather than the separate text.
        boundary=re.search(r'(?m)^\s*(?:Justice|Chief Justice) [A-Za-z]+(?: and Justice [A-Za-z]+)?,[A-Za-z ,.’]*(?:\n[A-Za-z ,.’]+){0,3}\b(?:concurring|dissenting)\b', page)
        if not started:
            if not main:
                continue
            started=True
        elif 'Syllabus' in running_header:
            break
        if separate and not main:
            # Watermarks can split an author's name. On a mixed page, the
            # Court's formal closing still identifies the end of its text.
            closing = re.search(r'(?m)^\s*It is so ordered\.\s*$', page)
            separate_opening = page[closing.end():closing.end()+500] if closing else ''
            watermark_boundary = (re.search(r'Justice', separate_opening) and
                                  re.search(r'\b(?:concurring|dissenting)\b', separate_opening))
            if closing and not boundary and watermark_boundary:
                chosen.append((number, page[:closing.end()]))
                break
            if boundary and len(page[:boundary.start()].split())>30:
                chosen.append((number,page[:boundary.start()]))
            break
        if boundary:
            chosen.append((number,page[:boundary.start()]))
            break
        chosen.append((number,page))
    if not chosen or len(' '.join(p for _,p in chosen).split())<20:
        raise ValueError('no_confident_principal_opinion')
    return '\n'.join(p for _,p in chosen), [n for n,_ in chosen]


def fetch(url, path):
    if not path.exists():
        # Official robots.txt specifies a one-second crawl delay.
        time.sleep(1)
        req=Request(url,headers={'User-Agent':'scvpublic-research/1.0'})
        with urlopen(req,timeout=45) as response: data=response.read()
        temp=path.with_suffix(path.suffix+'.part');temp.write_bytes(data);temp.replace(path)
    return path.read_bytes()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--missing',type=Path,default=Path('data/processed/modern/missing-scdb.json'))
    p.add_argument('--cache',type=Path,default=Path('data/raw/official-scotus'))
    p.add_argument('--output',type=Path,default=Path('data/processed/modern/official.json'))
    p.add_argument('--include-unscored-after',help='ISO date of the last covered SCDB decision')
    p.add_argument('--pdftotext',default='pdftotext')
    args=p.parse_args()
    if args.include_unscored_after:
        datetime.fromisoformat(args.include_unscored_after)
    args.cache.mkdir(parents=True,exist_ok=True)
    missing=json.loads(args.missing.read_text()); index=[];sources={};errors=[]; records=[]
    converter=subprocess.run([args.pdftotext,'-v'],capture_output=True,text=True,check=True).stderr.splitlines()[0]
    def snapshot():
        args.output.parent.mkdir(parents=True,exist_ok=True)
        result=dict(format_version=1,converter=converter,extractor_sha256=digest(Path(__file__)),
                    records=records,errors=errors,sources=sources)
        stage=args.output.with_suffix('.part')
        stage.write_text(json.dumps(result,indent=2)+'\n')
        stage.replace(args.output)
    for year in range(2016,2027):
        url=f'{BASE}/opinions/slipopinion/{year%100:02}'
        path=args.cache/f'index-{year}.html'
        try:
            parser=IndexParser();parser.feed(fetch(url,path).decode('utf-8-sig'))
            index.extend(parser.rows);sources[str(path.resolve())]=dict(url=url,sha256=digest(path))
            print('index',year,len(parser.rows),flush=True)
        except Exception as e:errors.append(dict(url=url,reason=str(e)))
    if args.include_unscored_after:
        seen = set()
        for item in index:
            key=(item['date'],item['docket'])
            if item['date'] <= args.include_unscored_after or key in seen:
                continue
            seen.add(key)
            date=datetime.fromisoformat(item['date'])
            missing.append(dict(caseId='official:'+':'.join(key),docket=item['docket'],
                                dateDecision=date.strftime('%m/%d/%Y'),caseName=item['name'],
                                term=str(date.year if date.month>=10 else date.year-1),unscored=True))
    for i,row in enumerate(missing):
        date=datetime.strptime(row['dateDecision'],'%m/%d/%Y').date().isoformat()
        matches={item['url']:item for item in index if item['date']==date and
                 row['docket'] in re.findall(r'\d{2}-\d+|\d{2}A\d+|\d+,?\s*Orig\.?',item['docket'])}
        if len(matches)!=1:
            errors.append(dict(case_id=row['caseId'],reason='ambiguous_or_missing_index_match'));continue
        url=next(iter(matches)); download_url, fragment = urldefrag(url)
        path=args.cache/download_url.rsplit('/',1)[1]
        try:
            data=fetch(download_url,path)
            if not data.startswith(b'%PDF'):raise ValueError('not_pdf')
            text=subprocess.check_output([args.pdftotext,'-layout',str(path),'-'],timeout=60).decode('utf-8')
            offset = int(fragment.split('=')[1])-1 if fragment else 0
            if fragment:
                next_pages = [int(urldefrag(item['url'])[1].split('=')[1])-1 for item in index
                              if urldefrag(item['url'])[0] == download_url and urldefrag(item['url'])[1]]
                end = min((n for n in next_pages if n > offset), default=len(text.split('\f')))
                text = '\f'.join(text.split('\f')[offset:end])
            opinion,pages=principal(text)
            pages=[n+offset for n in pages]
            # Require the actual PDF to contain the matched docket, too.
            normalized=text.replace('–','-').replace('—','-')
            if row['docket'] not in normalized[:12000]:raise ValueError('pdf_docket_not_verified')
            records.append(dict(citation=f"0.US.{row['term']}_{row['docket']}",opinion=opinion,
                                case_id=row['caseId'],source_url=url,pdf_pages=pages,pdf_sha256=digest(path),
                                name=row['caseName'],date=date,unscored=row.get('unscored',False)))
            sources[str(path.resolve())]=dict(url=url,sha256=digest(path))
        except Exception as e:errors.append(dict(case_id=row['caseId'],url=url,reason=str(e)))
        if i%20==0:print('progress',i+1,'of',len(missing),'accepted',len(records),flush=True)
        snapshot()
    snapshot()
    print('accepted',len(records),'errors',len(errors),flush=True)


if __name__=='__main__':main()
