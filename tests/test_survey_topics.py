import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import numpy as np

from scvpublic.store import SCHEMA
from scvpublic.survey_topics import TopicSearch, topic_contains_query, is_parent_topic


class TopicRoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        self.artifact = folder/'search.sqlite'
        self.spec = folder/'topics.json'
        self.docs = [dict(code=code, title=title, question=question, family=code,
                          years={'2020':.25}) for code,title,question in [
            ('a','Forest rules','Support forest protection?'),
            ('b','Logging limits','Support limits on timber harvesting?'),
            ('c','Tax policy','Support raising income taxes?'),
            ('d','Unreviewed','Other question?')]]
        with sqlite3.connect(self.artifact) as db:
            db.executescript(SCHEMA)
            db.executemany('INSERT INTO documents VALUES (?,?,?)',
                [('ces',i,json.dumps(d)) for i,d in enumerate(self.docs)])
        self.entries = [dict(source='ces',code=d['code'],topic=topic,
            source_text_sha256=hashlib.sha256((d['title']+'\n'+d['question']).encode()).hexdigest())
            for d,topic in zip(self.docs, ['Forest protection and timber harvesting','Forest protection','Tax policy'])]
        self.write_spec()
        self.base = {'ces':[dict(self.docs[i],score=.8,semantic_score=.8,lexical_score=.8) for i in (0,2,3)]}
        self.baseline = SimpleNamespace(artifact=self.artifact,keys=[['ces',i] for i in range(4)],
            lock=threading.Lock(), vectors=np.array([[.5],[.4],[.3],[.2]]),
            encoder=SimpleNamespace(encode=lambda texts: np.array([[1.]])),
            lexical_weights=lambda *args: {},search=Mock(return_value=self.base))

    def write_spec(self):
        self.spec.write_text(json.dumps(dict(version=1,entries=self.entries)))

    def test_complete_phrase_with_spacing_variants(self):
        self.assertTrue(topic_contains_query('Healthcare and health insurance','health care'))
        self.assertTrue(topic_contains_query('Vehicle fuel-efficiency standards','fuel efficiency'))
        self.assertFalse(topic_contains_query('Healthcare and Medicaid eligibility','Medicaid expansion'))
        self.assertFalse(topic_contains_query('Healthcare and health insurance','care'))
        self.assertFalse(topic_contains_query('Climate change mitigation','climate change denial'))
        self.assertFalse(topic_contains_query('Tax policy','!!!'))

    def test_parent_topic_retains_baseline_evidence(self):
        self.assertTrue(is_parent_topic('Forest protection and timber harvesting','forest protection subsidies'))
        self.assertFalse(is_parent_topic('Labor unions and collective bargaining','health care'))
        self.assertFalse(is_parent_topic('Childcare funding','health care'))

    def test_broad_membership_preserves_unreviewed_and_scores(self):
        router = TopicSearch(self.baseline,self.spec)
        result = router.search(['forest protection'])['ces']
        self.assertEqual({d['code'] for d in result},{'a','b','d'})
        added = next(d for d in result if d['code']=='b')
        self.assertEqual(added['years'],{'2020':.25})
        self.assertEqual(added['question'],self.docs[1]['question'])
        self.assertEqual(added['topic_match'],'Forest protection')
        self.assertEqual([d['code'] for d in self.base['ces']],['a','c','d'])

    def test_qualifiers_multiple_inputs_and_single_word_fragments_fall_back(self):
        router = TopicSearch(self.baseline,self.spec)
        for terms in [['forest protection subsidies'],['forest'],['unknown'],['forest protection','tax']]:
            self.assertEqual(router.search(terms),self.base)

    def test_one_family_cannot_activate_route(self):
        with sqlite3.connect(self.artifact) as db:
            doc=dict(self.docs[1],family='a')
            db.execute('UPDATE documents SET payload=? WHERE id=1',(json.dumps(doc),))
        self.assertEqual(TopicSearch(self.baseline,self.spec).search(['forest protection']),self.base)

    def test_stale_duplicate_and_checksum_metadata_fail(self):
        with self.assertRaisesRegex(ValueError,'checksum'):
            TopicSearch(self.baseline,self.spec,'0'*64)
        self.entries.append(self.entries[0]);self.write_spec()
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            TopicSearch(self.baseline,self.spec)
        self.entries.pop();self.entries[0]['source_text_sha256']='0'*64;self.write_spec()
        with self.assertRaisesRegex(ValueError,'wording changed'):
            TopicSearch(self.baseline,self.spec)
