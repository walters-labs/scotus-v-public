import unittest
from scripts.audit_court_corpus import inspect,queue


class CorpusAuditTests(unittest.TestCase):
    def row(self,syllabus,opinion,**extra):
        return dict(source='casesumm',**inspect(syllabus,opinion),**extra)

    def test_empty_opinion_is_gap_even_with_summary(self):
        row=self.row('Available summary','')
        self.assertEqual(queue(row),'source_gap_or_conflict')

    def test_summary_overlap_is_candidate_not_clean(self):
        text=' '.join('word'+str(i) for i in range(110))
        row=self.row(text,text)
        self.assertIn('opening_shared_with_syllabus',row['signals'])
        self.assertEqual(queue(row),'possible_summary_or_prefatory_material')

    def test_late_author_after_held(self):
        text='Held: '+('summary material '*100)+'Justice Smith announced the judgment of the Court.'
        row=self.row('',text)
        self.assertIn('held_before_late_author_cue',row['signals'])

    def test_short_order_is_review_not_assumed_missing(self):
        row=self.row('','The writ is dismissed as improvidently granted.')
        self.assertEqual(queue(row),'short_opinion_review')
        self.assertNotIn('empty_opinion',row['signals'])

    def test_cached_official_difference_has_own_priority(self):
        row=self.row('','Short disposition.',official_extraction_status='changed')
        self.assertEqual(queue(row),'existing_official_extraction_difference')
        row['conflicting_source_records']=True
        self.assertEqual(queue(row),'source_gap_or_conflict')

    def test_no_trigger_does_not_certify_clean(self):
        row=self.row('', 'Ordinary reasoning. '*110)
        self.assertEqual(queue(row),'no_priority_trigger_not_verified_clean')
        self.assertEqual(row['author_cue_count'],0)

    def test_mid_summary_style_is_review_candidate(self):
        row=self.row('', '(b) '+('Summary-style text. '*110))
        self.assertEqual(queue(row),'possible_summary_or_prefatory_material')
