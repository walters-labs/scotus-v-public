import copy
import unittest
from scripts.prepare_opinion_sections import casesumm_sections,pdf_sections,verify_partition,header_end


class PreparedSectionsTests(unittest.TestCase):
    def test_mixed_page_header_is_not_body_or_speaker(self):
        text=('Cite as: 603 U.S. 324\nKagan, J., concurring\nPer Curiam.\n'
              'The writs of certiorari before judgment are dismissed as improvidently granted, '
              'and the stays entered by the Court on January 5, 2024, are vacated.\nIt is so ordered.\n'
              'Justice Kagan, concurring.\nSeparate opinion text.')
        originals,sections,_=pdf_sections(text,2)
        verify_partition(originals,sections)
        body=''.join(s['text'] for s in sections if s['role']=='principal_text_candidate')
        self.assertIn('Per Curiam.',body)
        self.assertIn('It is so ordered.',body)
        self.assertNotIn('concurring',body)
        self.assertNotIn('Separate opinion text.',body)
        self.assertTrue(any('Separate opinion text.' in s['text'] for s in sections if s['role']=='unassigned_material'))
        self.assertEqual(list(originals),['pdf_page_3'])

    def test_unique_authored_opening_separates_prefatory_text(self):
        prefix='Summary discussing the rulings below. '
        row=dict(syllabus='Separate syllabus.',opinion=prefix+
            'Justice Smith announced the judgment of the Court and delivered an opinion. Reasoning.')
        before=copy.deepcopy(row)
        originals,sections,notice,status=casesumm_sections(row)
        verify_partition(originals,sections)
        authored=next(s for s in sections if s['role']=='authored_text_candidate')
        self.assertEqual(authored['start'],len(prefix))
        self.assertTrue(notice['part_or_plurality_warning'])
        self.assertEqual(status,'opening_candidate_requires_source_review')
        self.assertEqual(row,before)

    def test_missing_or_ambiguous_opening_stays_unsegmented(self):
        cue='Justice Smith announced the judgment of the Court and delivered an opinion. '
        for text in ['Body discussing a dissenting opinion.', 'Summary. '+cue+cue]:
            originals,sections,_,status=casesumm_sections(dict(syllabus='',opinion=text))
            verify_partition(originals,sections)
            self.assertEqual(status,'unsegmented_not_promoted')
            self.assertEqual(sections[0]['role'],'unsegmented_opinion_field')

    def test_partition_rejects_modified_and_missing_text(self):
        originals,sections,_,_=casesumm_sections(dict(syllabus='',opinion='Some source text.'))
        bad=copy.deepcopy(sections);bad[0]['text']='Modified source.'
        with self.assertRaises(ValueError):verify_partition(originals,bad)
        with self.assertRaises(ValueError):verify_partition(originals,[])
        bad=copy.deepcopy(sections);bad[0]['start']=1
        with self.assertRaises(ValueError):verify_partition(originals,bad)

    def test_header_detection_does_not_scan_body_mentions(self):
        self.assertEqual(header_end('Body prose\nThe dissenting opinion disagrees.'),0)
        self.assertEqual(header_end('Cite as: 603 U.S. 1\nBody prose\nJustice Smith, dissenting.'),0)
