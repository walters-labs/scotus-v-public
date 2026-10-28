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
