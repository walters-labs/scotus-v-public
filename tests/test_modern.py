import unittest
from scvpublic.modern import IndexParser, principal


class ModernTests(unittest.TestCase):
    def test_index_matches_date_docket_and_volume_page(self):
        parser=IndexParser()
        parser.feed('''<table><tr><td>1</td><td>6/24/22</td><td>19-1392</td>
            <td><a href="/opinions/preliminaryprint/597US.pdf#page=10">A v. B</a></td></tr>
            <tr><td>2</td><td>6/25/22</td><td>20-1</td>
            <td><a href="/opinions/21pdf/20-1_abcd.pdf">C v. D</a></td></tr></table>''')
        self.assertEqual(len(parser.rows),2)
        self.assertEqual(parser.rows[0]['date'],'2022-06-24')
        self.assertTrue(parser.rows[0]['url'].endswith('#page=10'))
        self.assertEqual(parser.rows[1]['docket'],'20-1')

    def test_principal_boundaries_and_body_mentions(self):
        body='The dissenting opinion argues otherwise. '+('majority reasoning '*100)
        text='Slip opinion\n\nSyllabus\n\nnot indexed\fCite as: 600 U.S. 1\n\nOpinion of the Court\n\n'+body
        text+='\f2 A v. B\n\nOpinion of the Court\n\n'+body
        text+='\fCite as: 600 U.S. 1\n\nTHOMAS, J., concurring\n\nseparate opinion'
        result,pages=principal(text)
        self.assertEqual(pages,[2,3])
        self.assertIn('dissenting opinion argues',result)
        self.assertNotIn('separate opinion',result)
        self.assertNotIn('not indexed',result)

    def test_unrecognized_document_is_not_silently_indexed(self):
        with self.assertRaises(ValueError):principal('unknown layout '*100)

    def test_edited_reports_mixed_case_boundary_preserves_majority_prefix(self):
        main='Cite as: 600 U.S. 1\n\nOpinion of the Court\n\n'+('majority '*120)
        ending='2 A v B\n\nAlito, J., concurring in judgment\n\n'+('majority conclusion '*30)
        ending+='\nJustice Alito, concurring in the judgment.\nseparate argument'
        text,pages=principal(main+'\f'+ending)
        self.assertEqual(pages,[1,2])
        self.assertIn('majority conclusion',text)
        self.assertNotIn('separate argument',text)

    def test_four_digit_index_year(self):
        parser=IndexParser()
        parser.feed('<tr><td>1</td><td>10/14/2026</td><td>26A476</td><td><a href="/opinions/26pdf/26a476.pdf">Case</a></td></tr>')
        self.assertEqual(parser.rows[0]['date'],'2026-10-14')

    def test_short_per_curiam_under_concurrence_header(self):
        text=('Cite as: 603 U.S. 324\nKagan, J., concurring\nPer Curiam.\n'
              'The writs of certiorari before judgment are dismissed as improvidently granted, '
              'and the stays entered by the Court on January 5, 2024, are vacated.\nIt is so ordered.\n'
              'Justice Kagan, with whom Justice Sotomayor joins, and\n'
              'with whom Justice Jackson joins as to Part II, concurring.\nseparate argument')
        result,pages=principal(text)
        self.assertEqual(pages,[1])
        self.assertIn('It is so ordered.',result)
        self.assertNotIn('separate argument',result)
        self.assertNotIn('with whom',result)

    def test_authored_separate_opinion_is_not_principal(self):
        with self.assertRaises(ValueError):
            principal('338 MOYLE v. UNITED STATES\nOpinion of Jackson, J.\n'+('argument '*120))

    def test_plurality_requires_judgment_announcement(self):
        first=('Cite as: 593 U.S. 420\nOpinion of Kagan, J.\n'
               'Justice Kagan announced the judgment of the Court and\n'
               'delivered an opinion, in which other Justices join.\n'+('plurality reasoning '*100))
        second='424 BORDEN\nOpinion of Kagan, J.\n'+('continued reasoning '*100)
        separate='Cite as: 593 U.S. 420\nThomas, J., concurring\nseparate reasoning'
        result,pages=principal(first+'\f'+second+'\f'+separate)
        self.assertEqual(pages,[1,2])
        self.assertIn('continued reasoning',result)
        self.assertNotIn('separate reasoning',result)

    def test_nonparticipation_notice_before_multiline_dissent(self):
        text=('Cite as: 600 U.S. 1\nOpinion of the Court\n'+('majority '*100)+
              '\nJustice Barrett took no part in the consideration or\ndecision of this case.\n'
              'Justice Breyer, with whom Justice Sotomayor and\nJustice Kagan join, dissenting.\nseparate argument')
        result,_=principal(text)
        self.assertIn('decision of this case.',result)
        self.assertNotIn('separate argument',result)
        self.assertNotIn('with whom',result)

    def test_joint_dissent_and_watermark_on_mixed_final_page(self):
        first='Cite as: 600 U.S. 1\nOpinion of the Court\n'+('majority '*100)
        for heading in ['Justice Sotomayor and Justice Kagan, dissenting.',
                        'Page\n Justice Proof Pending Publication\n Barrett, concurring.']:
            last=('2 Case\nBarrett, J., concurring\n'+('majority conclusion '*35)+
                  '\nIt is so ordered.\n'+heading+'\nseparate argument')
            result,pages=principal(first+'\f'+last)
            self.assertEqual(pages,[1,2])
            self.assertIn('majority conclusion',result)
            self.assertNotIn('separate argument',result)

    def test_separate_opinion_closing_does_not_make_it_majority(self):
        first='Cite as: 600 U.S. 1\nOpinion of the Court\n'+('majority '*100)
        separate='2 Case\nJustice Smith, concurring\n'+('separate argument '*100)+'\nIt is so ordered.\n'
        result,pages=principal(first+'\f'+separate)
        self.assertEqual(pages,[1])
        self.assertNotIn('separate argument',result)
