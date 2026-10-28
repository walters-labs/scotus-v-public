import sqlite3
import unittest
from scipy.sparse import csr_matrix
from scvpublic.build import write_index
from scvpublic.store import SCHEMA,search,survey_search


class PhraseTests(unittest.TestCase):
    def test_common_legal_words_survive_court_indexing(self):
        from scvpublic.casesumm import court_vectorizer
        vectorizer = court_vectorizer()
        matrix = vectorizer.fit_transform([
            'civil rights voting discrimination', 'civil rights equal protection',
            'civil procedure jurisdiction', 'contract rights damages'])
        vocabulary = vectorizer.get_feature_names_out()
        self.assertIn('civil', vocabulary)
        self.assertIn('rights', vocabulary)
        with sqlite3.connect(':memory:') as db:
            db.executescript(SCHEMA)
            write_index(db, 'court', matrix, vocabulary, [{'id':i} for i in range(4)])
            hits = search(db, 'court', ['civil rights'])
            self.assertEqual({d['id'] for d in hits[:2]}, {0, 1})

    def test_survey_cutoff_removes_weaker_partial_match(self):
        with sqlite3.connect(':memory:') as db:
            db.executescript(SCHEMA)
            docs = [{'id':0,'question':'gun permits'},
                    {'id':1,'question':'birth control'}]
            for corpus in ['public','gss']:
                write_index(db,corpus,csr_matrix([[.423,0],[0,.359]]),
                            ['gun','control'],docs)
                self.assertEqual([d['id'] for d in survey_search(db,corpus,['gun control'])],[0])
                self.assertEqual([d['id'] for d in survey_search(db,corpus,['birth control'])],[1])
                self.assertEqual([d['id'] for d in survey_search(db,corpus,['unknown gun'])],[0])

    def test_survey_coverage_rewards_both_words_without_phrase_requirement(self):
        with sqlite3.connect(':memory:') as db:
            db.executescript(SCHEMA)
            write_index(db,'gss',csr_matrix([[.3,.3],[.8,0]]),['climate','policy'],
                        [{'id':0,'question':'policy on climate'}, {'id':1,'question':'climate'}])
            self.assertEqual([d['id'] for d in survey_search(db,'gss',['climate policy'])],[0])
            self.assertEqual([d['id'] for d in survey_search(db,'gss',['policy climate'])],[0])

    def test_multiword_queries_find_unigrams_and_boost_bigrams(self):
        with sqlite3.connect(':memory:') as db:
            db.executescript(SCHEMA)
            for corpus in ['court','public']:
                write_index(db,corpus,csr_matrix([[.4,.4,.8],[.7,0,0]]),
                            ['climate','policy','climate policy'],[{'id':0},{'id':1}])
            self.assertEqual([d['id'] for d in search(db,'court',['Climate policy!'])],[0,1])
            self.assertAlmostEqual(search(db,'court',['climate policy'])[0]['score'],1.6)
            self.assertAlmostEqual(search(db,'public',['climate policy'])[0]['score'],1.6)
            self.assertEqual(search(db,'court',['!!!']),[])

    def test_all_topics_use_only_query_vocabulary_without_required_terms(self):
        with sqlite3.connect(':memory:') as db:
            db.executescript(SCHEMA)
            vocab = ['marriage', 'homosexual', 'gun', 'firearms']
            docs = [{'id': i} for i in range(4)]
            for corpus in ['court', 'public']:
                write_index(db, corpus, csr_matrix([[.8,.2,0,0],[.8,0,0,0],
                                                   [0,0,.5,0],[0,0,0,.6]]), vocab, docs)
                for term in ['gay marriage','same-sex marriage','marriage equality']:
                    hits = search(db,corpus,[term])
                    self.assertEqual([d['id'] for d in hits], [0,1])
                    self.assertEqual([d['score'] for d in hits], [.8,.8])
                self.assertEqual([d['id'] for d in search(db,corpus,['gun control'])], [2])
                self.assertEqual(search(db,corpus,['second amendment']), [])
                self.assertEqual(len(search(db,corpus,['gay marriage','gun control'])), 3)
