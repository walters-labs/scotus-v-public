"""Regression checks for partial-label, frozen-ranking evaluation."""
import unittest
from scripts.evaluate_frozen_court import compare, gates



class FrozenCourtEvaluationTests(unittest.TestCase):
    def test_new_irrelevant_fails_without_treating_unjudged_as_irrelevant(self):
        labels={'good': {'label':'direct'}, 'bad': {'label':'irrelevant'}}
        before=[{'case_id':'good','score':.7}]
        after=before+[{'case_id':'bad','score':.4}, {'case_id':'unknown','score':.4}]
        result=compare(before,after,labels)
        assert result['new_irrelevant']==['bad']
        assert result['added_unjudged']==['unknown']
        assert not gates({'query':result})['no_new_irrelevant']


    def test_existing_negative_is_not_new_and_cutoff_is_inclusive(self):
        labels={'bad':{'label':'irrelevant'},'good':{'label':'direct'}}
        before=[{'case_id':'good','score':.30},{'case_id':'bad','score':.4}]
        result=compare(before,[{'case_id':'good','score':.30}],labels)
        assert result['lost_direct']==[]
        assert result['removed_irrelevant']==['bad']
        assert all(gates({'query':result}).values())


    def test_top_ten_regression_is_independent_of_chart_retention(self):
        before=[{'case_id':'good','score':.6}]
        after=[{'case_id':str(i),'score':.7} for i in range(10)]+before
        result=compare(before,after,{'good':{'label':'direct'}})
        assert result['lost_direct']==[]
        assert result['lost_direct_top10']==['good']
