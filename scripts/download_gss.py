"""Download and verify the reviewed GSS release; fail if NORC replaces the URL."""
import json
from pathlib import Path
import shutil
import urllib.request
import zipfile

from scvpublic.build import digest


def main():
    spec = json.loads(Path('data/manifests/gss-2024-r3a.json').read_text())
    directory = Path('data/raw/gss-2024-r3a')
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / Path(spec['dta_member']).name
    if target.exists():
        if digest(target) != spec['dta_sha256']:
            raise ValueError('Existing GSS source has an unexpected checksum')
        print(f'Verified cached {target}')
        return
    archive = directory / 'download.zip.part'
    request = urllib.request.Request(spec['url'], headers={'User-Agent': 'scotus-v-public research importer'})
    with urllib.request.urlopen(request, timeout=120) as response, archive.open('wb') as stream:
        shutil.copyfileobj(response, stream)
    if digest(archive) != spec['zip_sha256']:
        raise ValueError('NORC archive changed: review the new release before updating the manifest')
    temporary = target.with_suffix('.part')
    with zipfile.ZipFile(archive) as zipped:
        with zipped.open(spec['dta_member']) as source, temporary.open('wb') as stream:
            shutil.copyfileobj(source, stream)
    if digest(temporary) != spec['dta_sha256']:
        raise ValueError('Extracted GSS source checksum mismatch')
    temporary.replace(target)
    archive.unlink()
    print(f'Downloaded and verified {target}')


if __name__ == '__main__':
    main()
