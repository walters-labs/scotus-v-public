import copy
import unittest
from scripts.pilot_case_findings import validate


class EvidenceValidationTest(unittest.TestCase):
    def setUp(self):
        self.packet={'sections':[dict(id='syllabus',type='syllabus',excerpted=True,
            text='The plaintiffs lack standing to bring this action.') ]}
        self.result=dict(findings=[dict(issue='standing',challenged_action='agency decision',
            disposition='dismissal',kind='procedural',attribution='syllabus',source_id='syllabus',
            evidence='The plaintiffs lack standing to bring this action.')],
            completeness='limited',limitations=['Excerpt only'])

    def test_exact_evidence(self):
        errors,evidence=validate(self.result,self.packet)
        self.assertEqual(errors,[])
        self.assertEqual(evidence[0]['offset'],0)

    def test_stitched_or_paraphrased_quote_fails(self):
        for quote in ['The plaintiffs lack standing ... bring this action.',
                      'The petitioners lack standing to bring this action.']:
            result=copy.deepcopy(self.result);result['findings'][0]['evidence']=quote
            self.assertIn('0:unverified_quote',validate(result,self.packet)[0])

    def test_wrong_section_and_attribution(self):
        result=copy.deepcopy(self.result);result['findings'][0]['source_id']='opinion'
        self.assertIn('0:unverified_quote',validate(result,self.packet)[0])
        result=copy.deepcopy(self.result);result['findings'][0]['attribution']='court'
        self.assertIn('0:syllabus_misattributed',validate(result,self.packet)[0])

    def test_partial_source_cannot_be_complete(self):
        self.result['completeness']='complete'
        self.assertIn('overclaims_completeness',validate(self.result,self.packet)[0])

    def test_invalid_structure_and_invented_kind(self):
        self.assertEqual(validate([],self.packet)[0],['invalid_top_level'])
        self.result['findings'][0]['kind']='liberal'
        self.assertIn('0:invalid_kind',validate(self.result,self.packet)[0])
