import json
from pathlib import Path
import unittest

from scripts.repair_casesumm_prefixes import apply_decision, sha


class PrefixRepairTests(unittest.TestCase):
    def setUp(self):
        # A summary imitates an opening; the reviewed cut must skip it.
        self.prefix = 'Justice A delivered the opinion, concluding that: summary. Counsel. '
        self.body = 'Justice A delivered the opinion of the Court. Reasoning. Later separate opinion.'
        self.raw = dict(citation='1.US.1', syllabus='Summary', opinion=self.prefix+self.body)
        self.decision = dict(case_id='test', citation='1.US.1', status='preface_separated',
                             split_offset=len(self.prefix), opinion_sha256=sha(self.raw['opinion']),
                             syllabus_sha256=sha('Summary'), prefix_sha256=sha(self.prefix),
                             retained_sha256=sha(self.body))

    def test_reviewed_cut_not_first_author_mention(self):
        result = apply_decision(self.raw, self.decision)
        self.assertEqual(result['opinion'], self.body)
        self.assertEqual(result['prefatory_material']+result['opinion'], self.raw['opinion'])
        self.assertIn('Later separate opinion.', result['opinion'])
        self.assertFalse(result['controlling_opinion_certified'])

    def test_changed_opinion_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Source text'):
            apply_decision(dict(self.raw, opinion=self.raw['opinion']+'extra'), self.decision)

    def test_changed_syllabus_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Source text'):
            apply_decision(dict(self.raw, syllabus='other'), self.decision)

    def test_wrong_citation_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Citation'):
            apply_decision(dict(self.raw, citation='2.US.2'), self.decision)

    def test_wrong_cut_rejected(self):
        with self.assertRaisesRegex(ValueError, 'boundary checksum'):
            apply_decision(self.raw, dict(self.decision, split_offset=5))

    def test_empty_retained_field_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Invalid repair'):
            apply_decision(self.raw, dict(self.decision, split_offset=len(self.raw['opinion'])))

    def test_unchanged_status_cannot_trim(self):
        with self.assertRaisesRegex(ValueError, 'Status and prefix'):
            apply_decision(self.raw, dict(self.decision, status='unchanged_no_justified_prefix'))

    def test_unresolved_source_is_preserved(self):
        decision = dict(self.decision, status='unresolved_summary_only', split_offset=0,
                        prefix_sha256=sha(''), retained_sha256=sha(self.raw['opinion']))
        self.assertEqual(apply_decision(self.raw, decision)['opinion'], self.raw['opinion'])


@unittest.skipUnless(Path('data/processed/casesumm/opinion-repairs.json').exists(),
                     'Local CaseSumm repairs not generated')
class LocalPrefixRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = json.loads(Path('data/processed/casesumm/opinion-repairs.json').read_text())
        cls.rows = {r['case_id']:r for r in cls.result['records']}
        cls.review = json.loads(Path('data/research/casesumm-prefix-review.json').read_text())

    def test_all_fields_reconstruct_with_exact_hashes(self):
        self.assertEqual(len(self.rows), 106)
        for d in self.review['records']:
            r = self.rows[d['case_id']]
            self.assertEqual(sha(r['prefatory_material']+r['opinion']), d['opinion_sha256'])
            self.assertEqual(sha(r['syllabus']), d['syllabus_sha256'])
            self.assertEqual(sha(r['opinion']), d['retained_sha256'])
            cursor = 0
            for section in r['sections']:
                self.assertEqual(section['start'], cursor)
                self.assertGreater(section['end'], cursor)
                cursor = section['end']
            self.assertEqual(cursor, d['original_characters'])

    def test_casey_skips_summary_opening(self):
        row = self.rows['1991-117']
        self.assertEqual(len(row['prefatory_material']), 23218)
        self.assertIn('Liberty finds no refuge', row['opinion'][:600])
        self.assertIn('concluding that', row['prefatory_material'])

    def test_hartford_keeps_second_authored_opinion(self):
        text = self.rows['1992-119']['opinion']
        self.assertTrue(text.startswith('Justice SOUTER announced'))
        self.assertIn('Justice SCALIA delivered the opinion of the Court', text)

    def test_mcconnell_keeps_multiple_authors(self):
        text = self.rows['2003-006']['opinion']
        self.assertTrue(text.startswith("JUSTICE STEVENS and JUSTICE O'CONNOR"))
        self.assertIn('CHIEF JUSTICE REHNQUIST delivered', text)
        self.assertIn('JUSTICE BREYER delivered', text)

    def test_no_justified_prefix_means_no_deletion(self):
        rows = [r for r in self.rows.values() if r['status']=='unchanged_no_justified_prefix']
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(not r['prefatory_material'] for r in rows))

    def test_woodson_flagged_not_repaired(self):
        r = self.rows['1975-176']
        self.assertEqual(r['status'], 'unresolved_summary_only')
        self.assertEqual(r['prefatory_material'], '')
        self.assertEqual(len(r['opinion'].split()), 472)
