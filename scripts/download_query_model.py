"""Download the pinned, checksum-verified local semantic model."""
import json
import argparse
from pathlib import Path
import shutil
import urllib.request
from scvpublic.build import digest

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--manifest',type=Path,default=Path('data/manifests/semantic-model.json'))
parser.add_argument('--output',type=Path,default=Path('artifacts/semantic-model'))
a=parser.parse_args()
spec = json.loads(a.manifest.read_text())
folder = a.output; folder.mkdir(parents=True, exist_ok=True)
for name, remote in spec['remote_files'].items():
    target = folder/name
    if target.exists():
        if digest(target) != spec['files'][name]: raise ValueError('Cached model checksum mismatch')
        continue
    url = f"https://huggingface.co/{spec['repository']}/resolve/{spec['revision']}/{remote}"
    temporary = target.with_suffix('.part')
    with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as stream:
        shutil.copyfileobj(response, stream)
    if digest(temporary) != spec['files'][name]: raise ValueError('Downloaded model checksum mismatch')
    temporary.replace(target)
print('Verified local semantic model')
