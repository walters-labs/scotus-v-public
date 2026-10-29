import unittest
from scripts.audit_question_composition import audit, selected_items
from scvpublic.chart import chart
from scvpublic.store import series


class CompositionTests(unittest.TestCase):
    def test_unchanged_answers_but_new_question(self):
        row = audit({2000: {'a': 0.}, 2002: {'a': 0., 'b': 1.}})['transitions'][0]
        self.assertEqual(row['observed_change'], .5)
        self.assertEqual(row['common_item_change'], 0.)
        self.assertEqual(row['composition_contrast'], .5)
        self.assertEqual(row['gap'], 2)

    def test_no_overlap_does_not_invent_change(self):
        row = audit({2000: {'a': 0.}, 2001: {'b': 1.}})['transitions'][0]
        self.assertIsNone(row['common_item_change'])
        self.assertIsNone(row['composition_contrast'])

    def test_stable_items_have_zero_contrast(self):
        result = audit({2000: {'a': 0., 'b': 1.}, 2004: {'a': 1., 'b': 0.}})
        self.assertEqual(result['transitions'][0]['composition_contrast'], 0.)
        self.assertEqual(result['fixed_composition_groups'][0]['years'], [2000, 2004])

    def test_family_priority_retains_identity(self):
        selected = selected_items([
            dict(code='old', family='f', years={'2000': 0., '2002': 0.}),
            dict(code='new', family='f', priority=10, years={'2002': 1.})])
        self.assertEqual(selected, {2000: {'old': 0.}, 2002: {'new': 1.}})

    def test_chart_marks_question_change_with_same_source(self):
        ids = {'ANES': {2000: ['a'], 2002: ['b']}}
        for view in ['all', 'combined', 'anes']:
            svg = chart({}, {2000: 0., 2002: .2}, question_ids=ids, view=view)
            self.assertIn('ANES questions changed', svg)
            self.assertIn('stroke-dasharray="4 3"', svg)
        stable = chart({}, {2000: 0., 2002: .2},
                       question_ids={'ANES': {2000: ['a'], 2002: ['a']}})
        self.assertNotIn('stroke-dasharray', stable)

    def test_superseded_item_does_not_change_identities_or_mean(self):
        questions = [dict(code='a', family='old', years={'2000': -1}),
                     dict(code='b', family='new', supersedes=['a'], years={'2000': 1})]
        self.assertEqual(selected_items(questions), {2000: {'b': 1}})
        self.assertEqual(series([], questions)[1], {2000: 1})
