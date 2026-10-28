import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from scvpublic.build import digest
from scvpublic.hybrid import HybridSearch, chart_matches
from scvpublic.store import SCHEMA


class HybridTests(unittest.TestCase):
    def test_independent_candidates_threshold_cache_and_checksums(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);artifact=folder/'search.sqlite'
            with sqlite3.connect(artifact) as db:
                db.executescript(SCHEMA)
                for i in range(102):
                    db.execute('INSERT INTO documents VALUES (?,?,?)',('court',i,json.dumps({'case_id':str(i),'name':str(i),'cases':[]})))
                db.executemany('INSERT INTO postings VALUES (?,?,?,?)',[('court','topic',0,.01),('court','topic',101,1.)])
            vectors=np.zeros((102,384),dtype=np.float32);vectors[:,0]=.1
            vectors[0,0]=.6;vectors[101,0]=.01
            np.save(folder/'vectors.npy',vectors)
            (folder/'ids.json').write_text(json.dumps(list(range(102))))
            for name in ('model.onnx','tokenizer.json'):(folder/name).write_text('fixture')
            files={n:digest(folder/n) for n in ['model.onnx','tokenizer.json','vectors.npy','ids.json']}
            (folder/'manifest.json').write_text(json.dumps(dict(artifact_sha256=digest(artifact),document_count=102,files=files)))
            with patch('scvpublic.hybrid.Encoder') as encoder:
                query=np.zeros((1,384),dtype=np.float32);query[0,0]=1.
                encoder.return_value.encode.return_value=query
                engine=HybridSearch(folder,artifact);hits=engine.search(['topic'])
                self.assertEqual(hits[0]['case_id'],'0')
                self.assertIn('101',[h['case_id'] for h in hits])  # outside semantic top 100
                self.assertEqual([h['case_id'] for h in chart_matches(hits)],['0'])
                self.assertEqual(engine.search(['topic']),hits)
                encoder.return_value.encode.assert_called_once()
                self.assertEqual(engine.search(['!!!']),[])
                self.assertTrue(engine.search(['unseen but meaningful']))  # semantic-only retrieval
                encoder.return_value.encode.return_value=query*.1
                self.assertEqual(engine.search(['unfamiliar weak query']),[])
            (folder/'ids.json').write_text('[]')
            with self.assertRaisesRegex(ValueError,'checksum'):HybridSearch(folder,artifact)
