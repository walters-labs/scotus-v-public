"""Attach SCDB issue records offline without changing retrieval or case scoring."""
import argparse
from collections import defaultdict
import csv
import io
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import zipfile
import hashlib
from .build import digest

MEMBER='SCDB_2026_01_caseCentered_Vote.csv'
CSV_SHA256='113e64b3f7729f4063ab01d766532ff2920e88cfce8fe097689caff3d4cf1a1b'
FIELDS=['docketId','caseIssuesId','voteId','issue','issueArea','lawType','lawSupp','caseDisposition','decisionDirection','majVotes','minVotes']


def signal(issue):
    """Describe the coded issue, never infer merits from absence of a code."""
    try:code=int(issue)
    except (ValueError,TypeError):return 'missing_issue'
    if code in range(90150,90201,10):return 'explicit_no_merits_issue'
    if code in range(90210,90311,10):return 'standing_issue'
    if code in range(90010,90091,10):return 'comity_issue'
    if code in (90130,90140):return 'mootness_or_venue_issue'
    if code==90480:return 'timeliness_issue'
    if code in range(90320,90521,10):return 'judicial_administration_issue'
    return 'no_selected_signal_not_a_merits_label'


def group_rows(rows):
    groups=defaultdict(list);seen=set()
    for row in rows:
        if not row.get('caseId') or not row.get('voteId') or row['voteId'] in seen:
            raise ValueError('Missing or duplicate SCDB identity')
        seen.add(row['voteId'])
        groups[row['caseId']].append({k:row[k] for k in FIELDS})
    return {k:sorted(v,key=lambda r:r['voteId']) for k,v in groups.items()}


def enriched(doc,groups):
    if 'scdb_issues' in doc:raise ValueError('SCDB issue metadata already attached')
    key=doc.get('case_id');rows=groups.get(key,[])
    codes=sorted({r['issue'] for r in rows if r['issue']})
    signals=sorted({signal(c) for c in codes}-{'no_selected_signal_not_a_merits_label','missing_issue'})
    # Top-level metadata only: never expand doc['cases'] or change its polarity.
    return dict(doc,scdb_issues=dict(release='SCDB_2026_01',status='matched' if rows else 'not_in_release',
        issue_codes=codes,signals=signals,records=rows))


def attach(artifact,archive,output,bundle=None,output_bundle=None):
    if output.exists():raise FileExistsError(output)
    if bool(bundle)!=bool(output_bundle):raise ValueError('Specify both bundle paths or neither')
    if output_bundle and output_bundle.exists():raise FileExistsError(output_bundle)
    with zipfile.ZipFile(archive) as z:raw=z.read(MEMBER)
    if hashlib.sha256(raw).hexdigest()!=CSV_SHA256:raise ValueError('SCDB release checksum mismatch')
    groups=group_rows(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    manifest=None
    if bundle:
        manifest=json.loads((bundle/'manifest.json').read_text())
        if manifest['artifact_sha256']!=digest(artifact):raise ValueError('Bundle does not match input artifact')
        for name,expected in manifest['files'].items():
            if Path(name).name!=name or digest(bundle/name)!=expected:raise ValueError('Invalid bundle file')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        candidate=Path(tmp)/'artifact.sqlite'
        with sqlite3.connect(artifact.resolve().as_uri()+'?mode=ro',uri=True) as source, sqlite3.connect(candidate) as db:
            source.backup(db)
            rows=db.execute("SELECT id,payload FROM documents WHERE corpus='court' ORDER BY id").fetchall()
            count=0
            for id,payload in rows:
                doc=enriched(json.loads(payload),groups)
                count+=doc['scdb_issues']['status']=='matched'
                db.execute("UPDATE documents SET payload=? WHERE corpus='court' AND id=?",(json.dumps(doc,allow_nan=False),id))
            provenance=dict(release='SCDB_2026_01',archive_sha256=digest(archive),csv_sha256=CSV_SHA256,
                source_url='https://scdb.la.psu.edu/data/2026-release-01/',matched_documents=count,unmatched_documents=len(rows)-count,
                semantics='Descriptive issue metadata; no change to scores, weights, search or chart eligibility.')
            db.execute('INSERT INTO meta VALUES (?,?)',('scdb_issue_metadata',json.dumps(provenance)))
            db.commit()
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Invalid artifact')
        if manifest:
            output_bundle.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory(dir=output_bundle.parent) as bt:
                target=Path(bt)/'bundle';target.mkdir()
                for name in manifest['files']:shutil.copyfile(bundle/name,target/name)
                # Packaging expects the model README; preserve optional source
                # provenance even when it is not in the runtime file allowlist.
                for name in ('README.md','sources.json'):
                    if name not in manifest['files'] and (bundle/name).is_file():
                        shutil.copyfile(bundle/name,target/name)
                manifest['metadata_enriched_from_artifact_sha256']=manifest['artifact_sha256']
                manifest['artifact_sha256']=digest(candidate)
                (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
                target.rename(output_bundle)
        candidate.rename(output)
    print(json.dumps(provenance))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--archive',type=Path,default=Path('data/raw/scdb-2026/issues-split.zip'))
    p.add_argument('--bundle',type=Path);p.add_argument('--output-bundle',type=Path)
    a=p.parse_args();attach(a.artifact,a.archive,a.output,a.bundle,a.output_bundle)

if __name__=='__main__':main()
