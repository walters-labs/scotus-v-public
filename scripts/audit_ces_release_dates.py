"""Record release-vintage boundaries for exact downloaded annual CES files."""
import json
from pathlib import Path

from scvpublic.build import digest


records = []
sources = {}
for year, version in [(2022, 4), (2024, 9)]:
    manifest_path = Path(f'data/manifests/ces-{year}-v{version}.json')
    metadata_path = Path(f'data/raw/ces-{year}-v{version}/dataverse-metadata.json')
    manifest = json.loads(manifest_path.read_text())
    dataset = json.loads(metadata_path.read_text())['data']
    release = dataset['latestVersion']
    assert release['versionNumber'] == version and release['versionState'] == 'RELEASED'
    csv = next(f for f in manifest['files'] if f['path'].endswith('.csv'))
    file_id = int(csv['url'].rsplit('/', 1)[1])
    file = next(f['dataFile'] for f in release['files'] if f['dataFile']['id'] == file_id)
    assert file['checksum'] == csv['publisher_checksum']
    assert digest(Path(csv['path'])) == csv['sha256']
    records.append(dict(survey_year=year, doi=manifest['doi'], version=version,
        csv_id=file_id, csv_sha256=csv['sha256'],
        dataset_first_publication_date=dataset['publicationDate'],
        csv_publication_date=file['publicationDate'],
        version_release_time=release['releaseTime'],
        conservative_available_at=release['releaseTime'],
        forecasting_status='Not available before this version release; earlier versions require separate acquisition and review.'))
    sources.update({str(p): digest(p) for p in [manifest_path, metadata_path]})
manifest_path = Path('data/manifests/ces-policy-v3.json')
manifest = json.loads(manifest_path.read_text())
sources[str(manifest_path)] = digest(manifest_path)
for name, file_id, version in [('policy-v3', 6898233, 3), ('common-v12', 14076522, 12)]:
    metadata_path = Path('data/raw/ces-policy')/(name+'-metadata.json')
    release = json.loads(metadata_path.read_text())['data']
    assert release['versionNumber'] == version and release['versionState'] == 'RELEASED'
    local = next(f for f in manifest['files'] if f'/datafile/{file_id}' in f['url'])
    file = next(f['dataFile'] for f in release['files'] if f['dataFile']['id'] == file_id)
    assert file['checksum'] == local['publisher_checksum']
    assert digest(Path('data/raw')/local['path']) == local['sha256']
    records.append(dict(survey_year=None, input_role=name, doi=local['dataset_doi'], version=version,
        file_id=file_id, file_sha256=local['sha256'], file_publication_date=file['publicationDate'],
        version_release_time=release['releaseTime'], conservative_available_at=release['releaseTime'],
        forecasting_status='Retrospective cumulative input; earlier annual versions and weights need separate review.'))
    sources[str(metadata_path)] = digest(metadata_path)
report = dict(status='verified downloaded-version metadata; not a full historical vintage audit',
    records=records, sources=sources,
    limitations=['Dataset first publication is not availability of the exact downloaded CSV.',
        'Earlier releases may have usable observations but were not inspected here.',
        'Release time alone does not validate weight construction, interview timing, or predictive design.',
        'Existing retrospective evaluations are not retroactively certified by this audit.'])
Path('artifacts/ces-release-availability.json').write_text(json.dumps(report, indent=2)+'\n')
for record in records:
    print(record['survey_year'], record['version'], record['conservative_available_at'])
