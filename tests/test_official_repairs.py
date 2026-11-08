import copy
import json
from pathlib import Path
import unittest

from scripts.validate_official_repairs import repair_text, sha, unique_rows


class RepairGuardTests(unittest.TestCase):
    def setUp(self):
        self.candidate = 'Court disposition.\n'
        self.page = self.candidate + 'Justice X, dissenting.\nSeparate reasoning.\n5\nCourt footnote.\n'
        start = self.page.index('5\n')
        self.decision = dict(candidate_text_sha256=sha(self.candidate),
                             boundary_page_sha256=sha(self.page),
                             principal_prefix_end=len(self.candidate),
                             additional_spans=[dict(start=start, end=len(self.page),
                                                    sha256=sha(self.page[start:]))],
                             repaired_text_sha256=sha(self.candidate+'\n'+self.page[start:]))

    def test_recovers_reviewed_footnote_without_separate_reasoning(self):
        repaired = repair_text(self.candidate, self.page, self.decision)
        self.assertIn('Court footnote.', repaired)
        self.assertNotIn('Separate reasoning', repaired)

    def test_changed_pdf_text_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'Boundary page'):
            repair_text(self.candidate, self.page+'extra', self.decision)

    def test_changed_candidate_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'Candidate text'):
            repair_text(self.candidate+'extra', self.page, self.decision)

    def test_wrong_span_hash_rejected(self):
        decision = copy.deepcopy(self.decision)
        decision['additional_spans'][0]['sha256'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'span checksum'):
            repair_text(self.candidate, self.page, decision)

    def test_overlapping_span_rejected(self):
        decision = copy.deepcopy(self.decision)
        decision['additional_spans'][0]['start'] = 0
        with self.assertRaisesRegex(ValueError, 'overlap'):
            repair_text(self.candidate, self.page, decision)

    def test_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            unique_rows([{'case_id':'x'}, {'case_id':'x'}])


@unittest.skipUnless(Path('data/processed/modern/official-repaired.json').exists(),
                     'Local repaired source not built')
class LocalRepairIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = unique_rows(json.loads(Path('data/processed/modern/official.json').read_text())['records'])
        cls.new = unique_rows(json.loads(Path('data/processed/modern/official-repaired.json').read_text())['records'])
        cls.manifest = json.loads(Path('data/research/official-repair-validation.json').read_text())

    def test_only_reviewed_text_and_pages_change(self):
        self.assertEqual(self.old.keys(), self.new.keys())
        changed = {k for k in self.old if self.old[k] != self.new[k]}
        self.assertEqual(changed, {r['case_id'] for r in self.manifest['records']})
        self.assertEqual(len(changed), 65)
        for key in changed:
            for field, value in self.old[key].items():
                if field not in ('opinion', 'pdf_pages'):
                    self.assertEqual(value, self.new[key][field], (key, field))

    def test_moyle_has_disposition_not_concurrence_fragment(self):
        text = self.new['2023-060']['opinion']
        self.assertIn('improvidently granted', text)
        self.assertNotIn('abortion enclaves', text)
        self.assertEqual(self.new['2023-060']['pdf_pages'], [3])

    def test_companion_disposition_footnote_preserved(self):
        text = self.new['2022-043']['opinion']
        self.assertIn('Suski', text)
        self.assertIn('improvidently granted', text)
        self.assertNotIn('Justice Jackson, with whom', text)

    def test_all_reviewed_output_hashes_match(self):
        for record in self.manifest['records']:
            self.assertEqual(sha(self.new[record['case_id']]['opinion']), record['repaired_text_sha256'])

    def test_footnote_continuations_recovered(self):
        self.assertIn('dissent posits, only nationwide', self.new['2023-034']['opinion'])
        self.assertIn('ample, how long an', self.new['2024-014']['opinion'])
