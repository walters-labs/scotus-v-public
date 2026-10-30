import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock

import numpy as np
from scvpublic.build import digest
from scvpublic.store import SCHEMA
from scvpublic.survey_search import SurveySearch, SURVEY_FILES


class SurveyHybridTests(unittest.TestCase):
    def test_abstention_synonyms_cache_and_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            artifact = folder/'search.sqlite'
            keys = [['ces', 0], ['gss', 0], ['public', 0], ['wvs', 0]]
            with sqlite3.connect(artifact) as db:
                db.executescript(SCHEMA)
                for corpus, id in keys:
                    db.execute('INSERT INTO documents VALUES (?,?,?)',
                               (corpus, id, json.dumps(dict(code=corpus, question='Question', years={}))))
                # A high lexical score cannot rescue an unrelated semantic match.
                db.execute('INSERT INTO postings VALUES (?,?,?,?)', ('public', 'topic', 0, 1.))
            vectors = np.zeros((4, 384), dtype=np.float32)
            vectors[:, 0] = [.8, .6, .2, .35]
            np.save(folder/SURVEY_FILES[0], vectors)
            (folder/SURVEY_FILES[1]).write_text(json.dumps(keys))
            manifest = dict(artifact_sha256=digest(artifact),
                            files={name: digest(folder/name) for name in SURVEY_FILES})
            (folder/'manifest.json').write_text(json.dumps(manifest))
            encoder = Mock()
            query = np.zeros((1,384), dtype=np.float32); query[0,0] = 1.
            encoder.encode.return_value = query
            engine = SurveySearch(folder, artifact, encoder)
            hits = engine.search(['topic'])
            self.assertEqual([h['code'] for h in hits['gss']], ['gss'])  # semantic-only synonym
            self.assertEqual(hits['public'], [])
            self.assertEqual(hits['wvs'], [])
            self.assertEqual(engine.search(['topic']), hits)
            encoder.encode.assert_called_once()
            self.assertFalse(any(engine.search(['!!!']).values()))
            encoder.encode.return_value = query*.1
            self.assertFalse(any(engine.search(['gibberish']).values()))
            (folder/SURVEY_FILES[1]).write_text('[]')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                SurveySearch(folder, artifact, encoder)
            manifest['files'][SURVEY_FILES[1]] = digest(folder/SURVEY_FILES[1])
            (folder/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'coverage'):
                SurveySearch(folder, artifact, encoder)
