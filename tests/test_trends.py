import sqlite3
import unittest
from scipy.sparse import csr_matrix
from scvpublic.build import write_index
from scvpublic.store import SCHEMA, search, court_counts, series
from scvpublic.chart import chart


class TrendTests(unittest.TestCase):
    def test_threshold_expands_beyond_display_limit_and_keeps_boundary(self):
        with sqlite3.connect(':memory:') as db:
            db.executescript(SCHEMA)
            write_index(db, 'court', csr_matrix([[1.]]*11+[[.2],[.19]]), ['topic'],
                        [{'id': i} for i in range(13)])
            self.assertEqual(len(search(db, 'court', ['topic'])), 10)
            self.assertEqual(len(search(db, 'court', ['topic'], limit=None, relative_cutoff=.2)), 12)
            self.assertEqual(search(db, 'court', ['absent'], limit=None), [])
            self.assertEqual(len(search(db, 'court', ['topic', 'topic'], limit=None, relative_cutoff=.2)), 12)

    def test_counts_and_best_fit(self):
        self.assertEqual(court_counts([{'cases': [{'year': 2000, 'polarity': 0},
                                                   {'year': 2000, 'polarity': 1},
                                                   {'year': 2001, 'polarity': None}]}]), {2000: 2})
        self.assertIn('Court connected observations', chart({2000: 0, 2002: 1}, {}))
        self.assertNotIn('connected observations', chart({2000: 0}, {}))
        self.assertEqual(chart({2000: 0, 2002: 1}, {2000: 1, 2004: 0}).count('connected observations'), 2)
        self.assertIn('stroke-width="2"', chart({2000: 0, 2001: 1}, {}))
        self.assertIn('2 cases', chart({2000: 0}, {}, counts={2000: 2}))

    def test_relevance_weighted_obergefell_year(self):
        court = [dict(score=.5327193737030029, cases=[dict(year=2015, polarity=1/9)]),
                 dict(score=.12659239768981934, cases=[dict(year=2015, polarity=-1/9)])]
        score = series(court, [dict(years={'2015': .5})])[0][2015]
        self.assertAlmostEqual(score, .068443, places=6)
        self.assertEqual(series(court, [dict(years={'2015': .5})])[1], {2015: .5})
        self.assertEqual(series(court[::-1], [])[0][2015], score)
        scaled = [dict(d, score=d['score']*3) for d in court]
        self.assertAlmostEqual(series(scaled, [])[0][2015], score)
        self.assertAlmostEqual(series(court[:1], [])[0][2015], 1/9)
        court.append(dict(score=100, cases=[dict(year=2015, polarity=None)]))
        court.append(dict(score=0, cases=[dict(year=2015, polarity=-1)]))
        self.assertAlmostEqual(series(court, [])[0][2015], score)
        self.assertEqual(court_counts(court), {2015: 2})
