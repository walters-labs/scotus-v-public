import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import patch
import zipfile
from scvpublic.scdb_metadata import attach, MEMBER
from scvpublic.store import SCHEMA
import unittest
from scvpublic.scdb_metadata import FIELDS,enriched,group_rows


def row(case,vote,issue,direction='2'):
    r={k:'' for k in FIELDS};r.update(caseId=case,voteId=vote,issue=issue,decisionDirection=direction)
    return r

class MetadataTests(unittest.TestCase):
    def test_multiple_issues_never_expand_cases_or_average_direction(self):
        groups=group_rows([row('a','v1','50020'),row('a','v2','90310','1')])
        doc=dict(case_id='a',cases=[dict(year=2024,polarity=1)],name='Example')
        original=copy.deepcopy(doc);out=enriched(doc,groups)
        self.assertEqual(doc,original)
        self.assertEqual(out['cases'],original['cases'])
        self.assertEqual(out['scdb_issues']['issue_codes'],['50020','90310'])
        self.assertEqual(out['scdb_issues']['signals'],['standing_issue'])
        self.assertEqual([r['decisionDirection'] for r in out['scdb_issues']['records']],['2','1'])

    def test_supplemental_case_is_explicitly_unmatched(self):
        doc=enriched(dict(case_id='official:new',cases=[]),{})
        self.assertEqual(doc['scdb_issues']['status'],'not_in_release')
        self.assertEqual(doc['scdb_issues']['records'],[])

    def test_duplicate_rows_fail_instead_of_multiplying_weight(self):
        with self.assertRaises(ValueError):group_rows([row('a','v','50020'),row('a','v','50020')])

    def test_no_signal_is_not_merits_and_repeat_attachment_fails(self):
        doc=enriched(dict(case_id='a',cases=[]),group_rows([row('a','v','50020')]))
        self.assertEqual(doc['scdb_issues']['signals'],[])
        with self.assertRaises(ValueError):enriched(doc,{})

    def test_enrichment_preserves_packaging_assets_and_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);base=root/'old.sqlite';archive=root/'issues.zip'
            with sqlite3.connect(base) as db:
                db.executescript(SCHEMA)
                db.execute('INSERT INTO documents VALUES (?,?,?)',('court',0,json.dumps(dict(case_id='a',cases=[dict(polarity=1,year=2024)]))))
                db.execute('INSERT INTO postings VALUES (?,?,?,?)',('court','example',0,.5));db.commit()
            original=base.read_bytes();out=io.StringIO();writer=csv.DictWriter(out,fieldnames=['caseId']+FIELDS);writer.writeheader();writer.writerow(row('a','v1','50020'))
            raw=out.getvalue().encode()
            with zipfile.ZipFile(archive,'w') as z:z.writestr(MEMBER,raw)
            bundle=root/'bundle';bundle.mkdir();(bundle/'vectors.npy').write_bytes(b'unchanged')
            (bundle/'README.md').write_text('Model license');(bundle/'sources.json').write_text('{}')
            (bundle/'manifest.json').write_text(json.dumps(dict(artifact_sha256=hashlib.sha256(original).hexdigest(),files={'vectors.npy':hashlib.sha256(b'unchanged').hexdigest()})))
            candidate=root/'new.sqlite';target=root/'new-bundle'
            with patch('scvpublic.scdb_metadata.CSV_SHA256',hashlib.sha256(raw).hexdigest()):attach(base,archive,candidate,bundle,target)
            self.assertEqual(base.read_bytes(),original)
            self.assertEqual((target/'README.md').read_text(),'Model license')
            self.assertEqual((target/'sources.json').read_text(),'{}')
            self.assertEqual((target/'vectors.npy').read_bytes(),b'unchanged')
            self.assertEqual(json.loads((target/'manifest.json').read_text())['artifact_sha256'],hashlib.sha256(candidate.read_bytes()).hexdigest())
            with sqlite3.connect(candidate) as db:
                doc=json.loads(db.execute('SELECT payload FROM documents').fetchone()[0])
                self.assertEqual(doc['cases'],[dict(polarity=1,year=2024)])
                self.assertEqual(db.execute('SELECT weight FROM postings').fetchone()[0],.5)
