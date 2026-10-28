import unittest
from scvpublic.sources import select_text


class SourceSelectionTests(unittest.TestCase):
    def test_procedural_stub_uses_available_opinion(self):
        full = 'The court considered whether juvenile offenders could receive a death sentence. '
        self.assertEqual(select_text('certiorari to the supreme court of missouri', full),
                         (full.strip(), 'short_syllabus_opinion_fallback'))

    def test_substantive_summary_is_preserved(self):
        summary = 'This case considers a legal dispute and explains the applicable rule. ' * 5
        self.assertEqual(select_text(summary, 'Full opinion. '*100), (summary.strip(), 'syllabus'))

    def test_no_better_source_preserves_short_text(self):
        self.assertEqual(select_text('Judgment reversed and remanded.', ''),
                         ('Judgment reversed and remanded.', 'syllabus'))
        self.assertEqual(select_text('Judgment reversed and remanded.', 'Reversed.'),
                         ('Judgment reversed and remanded.', 'syllabus'))

    def test_empty_summary_falls_back(self):
        self.assertEqual(select_text('   ', 'Opinion text.'), ('Opinion text.', 'opinion_fallback'))
