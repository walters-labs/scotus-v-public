"""Shared processed-survey contract; no database or scientific dependencies."""
import argparse
import json
import math
from pathlib import Path
import re

VERSION = 'survey-documents-v1'
METHODOLOGIES = {f'explicit-{source}-v1' for source in ('anes', 'gss', 'ces', 'pew', 'wvs', 'prri', 'nationscape')}


def validate(payload):
    """Validate without mutating. Unversioned existing files remain readable."""
    def require(condition, message):
        if not condition:
            raise ValueError('Survey schema: '+message)

    def number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

    def text(value):
        return isinstance(value, str) and bool(value.strip())

    require(isinstance(payload, dict), 'payload must be an object')
    require(payload.get('schema_version', VERSION) == VERSION, 'unsupported schema version')
    require(payload.get('methodology') in METHODOLOGIES, 'unknown methodology/source')
    sources = payload.get('sources')
    require(isinstance(sources, dict) and bool(sources), 'source checksums required')
    for path, checksum in sources.items():
        require(text(path) and isinstance(checksum, str) and re.fullmatch(r'[0-9a-f]{64}', checksum), 'invalid source checksum')
    documents = payload.get('documents')
    require(isinstance(documents, list), 'documents must be a list')
    seen = set()
    for d in documents:
        require(isinstance(d, dict), 'document must be an object')
        for field in ('code', 'family', 'title', 'question', 'weight'):
            require(text(d.get(field)), 'missing/invalid '+field)
        code = d['code']
        require(code not in seen, 'duplicate question '+code)
        seen.add(code)
        if 'search_text' in d:
            require(text(d['search_text']), code+': invalid search_text')
        years, counts = d.get('years'), d.get('respondents')
        require(isinstance(years, dict) and isinstance(counts, dict), code+': years/respondents required')
        require(years.keys() == counts.keys(), code+': respondent years differ from score years')
        for year, score in years.items():
            require(isinstance(year, str) and re.fullmatch(r'[12][0-9]{3}', year), code+': invalid year')
            require(number(score) and -1 <= score <= 1, code+': score outside [-1,1]')
            require(type(counts[year]) is int and counts[year] > 0, code+': invalid respondent count')
        if 'scores' in d:
            require(isinstance(d['scores'], dict) and bool(d['scores']), code+': invalid response map')
            for answer, score in d['scores'].items():
                require(text(answer) and number(score) and -1 <= score <= 1, code+': invalid response mapping')
        for field in ('weight_sums', 'year_provenance'):
            if field not in d:
                continue
            values = d[field]
            require(isinstance(values, dict) and values.keys() <= years.keys(), code+': invalid '+field+' years')
            for year, value in values.items():
                if field == 'weight_sums':
                    require(number(value) and value > 0, code+': invalid weight sum')
                else:
                    require(isinstance(value, dict), code+': invalid annual provenance')
                    for key in ('source_code', 'weight', 'question', 'doi'):
                        require(text(value.get(key)), code+': missing annual provenance '+key)
                    if 'wave' in value:
                        require(text(value['wave']), code+': invalid wave')
    return dict(questions=len(documents), question_years=sum(len(d['years']) for d in documents))


def prepare(payload):
    """Tag newly built outputs only after successful validation."""
    validate(payload)
    payload['schema_version'] = VERSION
    return payload


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('files', type=Path, nargs='+')
    args = p.parse_args()
    for path in args.files:
        payload = json.loads(path.read_text())
        print(json.dumps(dict(file=str(path), version=payload.get('schema_version', 'unversioned'), **validate(payload))))


if __name__ == '__main__':
    main()
