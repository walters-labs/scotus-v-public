"""Package an explicit allowlist; never ship raw data or local credentials."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import shutil
from contextlib import closing, nullcontext
from scvpublic.store import connect, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifact', type=Path)
    parser.add_argument('--output', type=Path, default=Path('artifacts/scvpublic-release.tar.gz'))
    parser.add_argument('--directory', type=Path, help='Write an unpacked release for rsync instead of a tarball')
    parser.add_argument('--hybrid', type=Path, help='Validated embedding bundle to include')
    args = parser.parse_args()
    with closing(connect(args.artifact)) as db:
        assert metadata(db)['schema_version'] == 1
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    paths = [Path('requirements.txt'), Path('LICENSE')]
    # Keep acquisition, mapping, and research code on the build workstation.
    paths += [Path('scvpublic')/name for name in
              ('__init__.py', 'web.py', 'store.py', 'chart.py', 'build.py',
               'hybrid.py', 'encoding.py', 'survey_search.py')]
    paths += [p for folder in ('scvpublic/templates', 'scvpublic/static')
              for p in Path(folder).rglob('*') if p.is_file()]
    paths += [Path('deploy')/name for name in
              ('install-release.sh', 'scvpublic.service', 'activate-public.sh',
               'svp.walterslabs.dev.conf', 'prune-releases.sh')]
    paths += [Path('scripts/check_serving.py')]
    extra = []
    if args.hybrid:
        from scvpublic.hybrid import HybridSearch
        engine = HybridSearch(args.hybrid, args.artifact)
        paths += [Path('requirements-hybrid.txt'), Path('scripts/check_hybrid_http.py')]
        extra = [(args.hybrid/name, Path('artifacts/hybrid')/name) for name in
                 ('manifest.json', 'model.onnx', 'tokenizer.json', 'vectors.npy', 'ids.json', 'README.md')]
    if args.hybrid and (args.hybrid/'sources.json').exists():
        extra.append((args.hybrid/'sources.json', Path('artifacts/hybrid/sources.json')))
    if args.hybrid and 'survey_documents' in json.loads((args.hybrid/'manifest.json').read_text()):
        from scvpublic.survey_search import SurveySearch, SURVEY_FILES
        SurveySearch(args.hybrid, args.artifact, engine.encoder)
        extra.extend((args.hybrid/name, Path('artifacts/hybrid')/name) for name in SURVEY_FILES)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.directory:
        args.directory.mkdir(parents=True, exist_ok=False)
    with (nullcontext(args.directory) if args.directory else tempfile.TemporaryDirectory()) as temp:
        root = Path(temp)
        hashes = {}
        for source, relative in [(p, p) for p in paths] + [(args.artifact, Path('artifacts/search.sqlite'))] + extra:
            dest = root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            dest.chmod(0o644)
            with dest.open('rb') as stream:
                hashes[str(relative)] = hashlib.file_digest(stream, 'sha256').hexdigest()
        (root / 'SHA256SUMS').write_text(''.join(f'{digest}  {name}\n' for name, digest in sorted(hashes.items())))
        if args.directory:
            print(json.dumps({'release': str(root), 'files': len(hashes)}))
            return
        with tarfile.open(args.output, 'w:gz', compresslevel=1) as archive:
            for item in sorted(root.rglob('*')):
                if item.is_file():
                    archive.add(item, arcname=str(item.relative_to(root)), recursive=False)
    print(json.dumps({'release': str(args.output), 'bytes': args.output.stat().st_size, 'files': len(hashes)}))


if __name__ == '__main__':
    main()
