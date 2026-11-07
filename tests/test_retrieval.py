import json
import unittest
from pathlib import Path
from src.retriever import ICD11Retriever

class Retrieval(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.retriever=ICD11Retriever()

    def test_dev_negation_regression(self):
        note=next(json.loads(l) for l in Path('data/dev_notes.jsonl').read_text().splitlines() if json.loads(l)['id']=='dev-002')
        candidates=self.retriever.retrieve(note['text'],20)
        self.assertFalse(any('malaria' in c['title'].lower() for c in candidates))
        self.assertTrue(set(note['gold']).intersection(self.retriever.select_offline(candidates)))

    def test_positive_malaria_not_suppressed(self):
        candidates=self.retriever.retrieve('Dx: Malaria confirmed.',20)
        self.assertTrue(any('malaria' in c['title'].lower() for c in candidates))

    def test_empty_note(self):
        self.assertEqual([],self.retriever.predict_offline(''))

    def test_artifact_shape(self):
        self.assertIsNotNone(self.retriever.embed_model)
        self.assertEqual((len(self.retriever.categories),384),self.retriever.dense_embeddings.shape)
