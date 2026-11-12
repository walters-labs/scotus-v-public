"""Publish the audited abortion survey history without changing case matching."""
import hashlib
import json
from pathlib import Path

SOURCE = Path('data/research/abortion-policy-surveys.json')
OUTPUT = Path('data/research/abortion-opinion-history.json')


def build():
    data = json.loads(SOURCE.read_text())
    records = data['survey_records']
    keys = [(r['source'], r['year'], r['variable']) for r in records]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate survey observation')
    result = {'survey_records': records, 'provenance': data['provenance'],
              'input_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              'limitations': data.get('limitations', [])}
    OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(f'Published {len(records)} observations to {OUTPUT}')


if __name__ == '__main__':
    build()
