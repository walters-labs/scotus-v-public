import unittest
from scripts.evaluate_relevance import evaluate_hits, regressions


class RelevanceEvaluationTests(unittest.TestCase):
    def test_unknown_and_related_are_not_false_negatives(self):
        labels = {'a': {'label':'direct'}, 'b': {'label':'irrelevant'},
                  'c': {'label':'direct'}, 'd': {'label':'related'}}
        r = evaluate_hits([{'id':x} for x in ['a','b','d','unknown']], labels, lambda h:h['id'])
        self.assertEqual(r['labels'], dict(direct=1, irrelevant=1, related=1, unjudged=1))
        self.assertEqual(r['known_direct_missing'], ['c'])
        self.assertEqual(r['known_irrelevant_found'], ['b'])

    def test_regressions_detect_changed_members_not_just_counts(self):
        def report(ids):
            section = evaluate_hits([{'id':i} for i in ids],
                {i: {'label':label} for i,label in [('a','direct'),('b','direct'),('x','irrelevant'),('y','irrelevant')]},
                lambda h:h['id'])
            return {'queries':{'topic':dict(display=section,chart=section,surveys=section)}}
        before, after = report(['a','x']), report(['b','y'])
        self.assertEqual(len(regressions(after,before)),6)
        self.assertEqual(regressions(before,before),[])

    def test_empty_results_preserve_missing_positive(self):
        r=evaluate_hits([],{'a':{'label':'direct'}},lambda h:h['id'])
        self.assertEqual(r['known_direct_missing'],['a'])
        self.assertEqual(r['total'],0)
