import json
from pathlib import Path
import unittest
from scripts.recover_woodson import sections
from scripts.repair_casesumm_prefixes import sha


class RecoveryGuards(unittest.TestCase):
    def test_changed_extraction_rejected(self):
        with self.assertRaisesRegex(ValueError, 'extraction differs'):
            sections('changed', dict(extracted_sha256=sha('original'),spans=[]))

    def test_overlap_rejected(self):
        span=dict(page=1,start=0,end=4,role='opinion',sha256=sha('text'))
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            sections('text',dict(extracted_sha256=sha('text'),spans=[span,span]))


@unittest.skipUnless(Path('data/processed/casesumm/woodson-recovered.json').exists(),'Local PDF recovery absent')
class WoodsonRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc=json.loads(Path('data/processed/casesumm/woodson-recovered.json').read_text())
        cls.manifest=json.loads(Path('data/research/woodson-source-recovery.json').read_text())

    def test_all_spans_match_pinned_source(self):
        self.assertEqual(sections(self.doc['original_pdf_text'],self.manifest),self.doc['sections'])

    def test_plurality_includes_disposition_and_footnote40(self):
        text='\n'.join(s['text'] for s in self.doc['sections'] if s['role'].startswith('principal_plurality'))
        self.assertIn('It is so ordered.',text)
        self.assertIn('unnecessary to reach the question',text)
        self.assertNotIn('Arthur M. Michaelson',text)
        self.assertNotIn('concurring in the judgment.',text)
        self.assertTrue(text.startswith('Judgment of the Court,'))

    def test_separate_concurrences_do_not_include_dissent(self):
        for role in ['brennan_concurrence_in_judgment','marshall_concurrence_in_judgment']:
            text='\n'.join(s['text'] for s in self.doc['sections'] if s['role']==role)
            self.assertIn('judgment',text)
            self.assertNotIn('dissenting.',text)
            self.assertNotIn('39 MR.',text)

    def test_original_full_pdf_retained(self):
        self.assertIn('REHNQUIST',self.doc['original_pdf_text'])
        self.assertEqual(sha(self.doc['original_pdf_text']),self.manifest['extracted_sha256'])
