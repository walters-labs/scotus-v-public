"""Acquire full annual PRRI AVS files from ARDA's public catalog (no scoring)."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urljoin
from urllib.request import urlopen


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.href=None; self.label=''
    def handle_starttag(self, tag, attrs):
        if tag=='a': self.href=dict(attrs).get('href'); self.label=''
    def handle_data(self, data):
        if self.href: self.label+=data
    def handle_endtag(self, tag):
        if tag=='a' and self.href:
            self.links.append((self.href,' '.join(self.label.split())))
            self.href=None


def links(data):
    parser=Links(); parser.feed(data.decode()); return parser.links


def fetch(url):
    with urlopen(url,timeout=60) as response: return response.read()


def restore():
    """Restore reviewed raw files from pinned manifests without recrawling."""
    records = json.loads(Path('data/manifests/prri-avs-acquisition.json').read_text())['files']
    records += json.loads(Path('data/manifests/prri-policy-documents.json').read_text())
    for record in records:
        path = Path(record['path'])
        if path.exists():
            content = path.read_bytes()
        else:
            content = fetch(record['url'])
        if hashlib.sha256(content).hexdigest() != record['sha256']:
            raise ValueError('Source changed; review required: '+str(path))
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore', action='store_true', help='Restore pinned acquisition and questionnaire files')
    if parser.parse_args().restore:
        restore()
        return
    import pyreadstat
    catalog_url='https://www.thearda.com/data-archive/browse-alphabetically'
    catalog=fetch(catalog_url)
    studies=[]
    for href,label in links(catalog):
        match=re.fullmatch(r'PRRI American Values Survey, (20\d\d)(, Pre-Election)?',label)
        if match: studies.append((int(match[1]),urljoin(catalog_url,href),label))
    assert len(studies)==len({year for year,_,_ in studies}), 'Ambiguous annual studies'
    manifest=dict(source='PRRI American Values Survey via ARDA',catalog_url=catalog_url,
        status='acquisition only; not mapped or integrated',
        selection='Main annual study, pre-election when separate pre/post releases exist; supplements excluded.',
        attribution='Credit PRRI as original collector and ARDA as distributor in resulting publications/presentations.',
        files=[],studies=[])
    destination=Path('data/manifests/prri-avs-acquisition.json')
    for year,page,label in sorted(studies):
        folder=Path(f'data/raw/prri-avs-{year}');folder.mkdir(parents=True,exist_ok=True)
        summary=fetch(page)
        download_page=page+'&tab=3'
        downloads=fetch(download_page)
        choices=[urljoin(page,url) for url,text in links(downloads) if 'Completely labeled Stata' in text]
        assert len(choices)==1, (year,choices)
        path=folder/'responses.dta'
        if not path.exists():
            data=fetch(choices[0]); temp=path.with_suffix('.tmp');temp.write_bytes(data);temp.replace(path)
        _,meta=pyreadstat.read_dta(str(path),metadataonly=True)
        for name,data in [('summary.html',summary),('downloads.html',downloads)]: (folder/name).write_bytes(data)
        for name,url in [('responses.dta',choices[0]),('summary.html',page),('downloads.html',download_page)]:
            file=folder/name
            manifest['files'].append(dict(path=str(file),url=url,bytes=file.stat().st_size,sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
        doi=re.search(r'10\.17605/OSF\.IO/[A-Za-z0-9]+',summary.decode())
        manifest['studies'].append(dict(year=year,title=label,summary_url=page,doi=doi[0] if doi else None,
            rows=meta.number_rows,columns=meta.number_columns,
            weight_candidates=[v for v in meta.column_names if 'weight' in v.lower()]))
        destination.write_text(json.dumps(manifest,indent=2)+'\n')
        print(year,meta.number_rows,meta.number_columns,flush=True)


if __name__=='__main__':main()
