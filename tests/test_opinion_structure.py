import unittest
from scvpublic.modern import principal
from scripts.audit_opinion_structure import principal_spans,opening_notice


class StructureAuditTests(unittest.TestCase):
    def test_mixed_page_partition_preserves_every_character(self):
        text=('Cite as: 600 U.S. 1\nOpinion of the Court\n'+('reasoning '*60)+
              '\f2 Case\nSmith, J., concurring\n'+('closing reasoning '*20)+
              '\nIt is so ordered.\nJustice Smith, concurring.\nSeparate reasoning.')
        extracted,numbers=principal(text)
        spans=principal_spans(text,extracted,numbers)
        for n,page in enumerate(text.split('\f'),1):
            ranges=[r for r in spans if r['page']==n]
            self.assertEqual(''.join(page[r['start']:r['end']] for r in ranges),page)
            self.assertEqual(sum(r['end']-r['start'] for r in ranges),len(page))
        self.assertNotIn('Separate reasoning',extracted)
        self.assertIn('It is so ordered.',extracted)
        self.assertTrue(any(r['role']=='unassigned' and r['page']==2 for r in spans))

    def test_unmapped_text_rejected(self):
        with self.assertRaises(ValueError):principal_spans('source','different',[1])

    def test_part_warning_not_whole_case_authority(self):
        for text in ['Justice Kagan announced the judgment of the Court and delivered an opinion.',
                     'Chief Justice Roberts delivered the opinion of the Court, except as to Part III.']:
            notice=opening_notice(text)
            self.assertTrue(notice['part_or_plurality_warning'])
            self.assertIn('not_validated',notice['authority'])
        notice=opening_notice('Justice Smith delivered the opinion of the Court.')
        self.assertFalse(notice['part_or_plurality_warning'])
        self.assertIn('not_validated',notice['authority'])
