import copy
import unittest
from scripts.pilot_case_findings_v2 import passages,validate


class SpanEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.packet=dict(sections=[dict(id='syllabus',type='syllabus',excerpted=True,
            passages=[dict(id='syllabus:p001',text='The Court decides intervention, not policy validity.')])])
        self.result=dict(findings=[dict(issue='intervention',challenged_action='motion',
            outcome='motion granted',nature='procedure',decision_status='decided',
            actor='controlling_court',evidence_ids=['syllabus:p001'])],completeness='limited',limitations=[])

    def test_resolves_exact_source_without_model_quote(self):
        errors,checks=validate(self.result,self.packet)
        self.assertEqual(errors,[])
        self.assertEqual(checks[0]['resolved'][0]['text'],self.packet['sections'][0]['passages'][0]['text'])
        self.assertEqual(checks[0]['resolved'][0]['source_type'],'syllabus')
        # A syllabus can report a Court holding; source type and actor differ.
        self.assertEqual(self.result['findings'][0]['actor'],'controlling_court')

    def test_unknown_and_duplicate_ids(self):
        self.result['findings'][0]['evidence_ids']=['absent']
        errors,checks=validate(self.result,self.packet)
        self.assertIn('0:unknown_evidence_id',errors)
        self.assertFalse(checks[0]['all_ids_resolved'])
        self.result['findings'][0]['evidence_ids']=['syllabus:p001']*2
        self.assertIn('0:duplicate_evidence',validate(self.result,self.packet)[0])

    def test_unresolved_policy_question_is_not_rejected_as_malformed(self):
        self.result['findings'][0].update(nature='policy_merits',decision_status='not_reached')
        self.assertEqual(validate(self.result,self.packet)[0],[])

    def test_no_complete_claim_on_excerpts(self):
        self.result['completeness']='complete'
        self.assertIn('overclaims_completeness',validate(self.result,self.packet)[0])

    def test_invalid_status_and_extra_quote(self):
        self.result['findings'][0]['decision_status']='probably'
        self.assertIn('0:invalid_decision_status',validate(self.result,self.packet)[0])
        self.result['findings'][0]['quote']='invented'
        self.assertIn('0:invalid_fields',validate(self.result,self.packet)[0])

    def test_lossless_chunks_and_offsets(self):
        section=dict(id='opinion',text='One sentence. Another sentence with a citation. '*100)
        original=copy.deepcopy(section);chunks=passages(section)
        self.assertEqual(''.join(c['text'] for c in chunks),section['text'])
        self.assertEqual(len({c['id'] for c in chunks}),len(chunks))
        for chunk in chunks:
            self.assertEqual(section['text'][chunk['start']:chunk['end']],chunk['text'])
        self.assertEqual(section,original)

    def test_empty_results_are_abstention_not_policy_merits(self):
        self.result['findings']=[]
        self.assertEqual(validate(self.result,self.packet),([],[]))
