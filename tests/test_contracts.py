import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src.bm25 import tokenize
from src.query_extractor import excluded_terms, extract_diagnostic_query
from src.llm_coder import LLMCoder
from src.pipeline import ICD11Pipeline

class Contracts(unittest.TestCase):
    def test_abbreviations(self):
        for text, wrong in [('normal','antimalarial'),('administration','diabetes'),('age 45','gastroenteritis'),('BP 120/80','hypertension')]:
            self.assertNotIn(wrong, tokenize(text))
        self.assertIn('tuberculosis', tokenize('PTB'))
        self.assertIn('hipertensión', tokenize('hipertensión'))

    def test_negation_scope(self):
        self.assertEqual({'heart disease'}, excluded_terms('No history of heart disease.'))
        self.assertIn('malaria', excluded_terms('malaria excluded. Viral URTI.'))
        self.assertNotIn('malaria', excluded_terms('Malaria confirmed.'))
        self.assertNotIn('asthma', excluded_terms('Known asthma. No fever. Acute asthma exacerbation.'))
        self.assertNotIn('malaria', extract_diagnostic_query('Dx: Viral URTI; malaria excluded.').lower())

    def test_response_schema(self):
        coder = LLMCoder.__new__(LLMCoder)
        coder.valid_codes = {'CA00','CA07.0','MG26'}
        candidates = [{'code':'CA00'},{'code':'CA07.0'}]
        for raw in ['null','[]','{}','{"codes":null}','{"codes":[123]}','{"codes":["MG26"]}','garbage']:
            self.assertEqual([], coder._parse_and_validate(raw,candidates))
        self.assertEqual(['CA00'],coder._parse_and_validate('{"codes":["CA00","CA00"]}',candidates))

    def test_budget_no_dispatch(self):
        sys_keys = {"SYSTEMROOT", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA", "PATH", "TEMP", "TMP", "SystemDrive"}
        base_env = {k: v for k, v in os.environ.items() if k in sys_keys}
        with patch.dict(os.environ, {**base_env, 'ICD_BUDGET_USD':'0'}, clear=True):
            coder=LLMCoder({'CA00'})
        coder.async_openai=object()
        self.assertEqual([],asyncio.run(coder.predict_async('cold',[{'code':'CA00','title':'Cold'}])))
        self.assertEqual(0,coder.calls)

    def test_batch_failure_and_concurrency(self):
        class Retriever:
            valid_codes={'CA00'}
            def retrieve(self,text,top_n): return [{'code':'CA00'}]
            def select_offline(self,candidates): return ['CA00']
        class Provider:
            is_available=True; calls=0; reserved=0; active=0; peak=0
            async def predict_async(self,text,candidates):
                self.active+=1; self.peak=max(self.peak,self.active)
                await asyncio.sleep(.02)
                self.active-=1
                return []
            async def close(self): pass
        p=ICD11Pipeline.__new__(ICD11Pipeline);p.retriever=Retriever();p.llm=Provider()
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'output'
            notes=[{'id':str(i),'text':'cold'} for i in range(8)]+[{'id':'empty','text':None}]
            asyncio.run(p.process_async(notes,str(output),4))
            rows=[json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual(9,len(rows));self.assertGreater(p.llm.peak,1);self.assertLessEqual(p.llm.peak,4)
            self.assertEqual([],next(r['codes'] for r in rows if r['id']=='empty'))
            self.assertTrue(all(r['codes']==['CA00'] for r in rows if r['id']!='empty'))

    def test_synthetic_gold(self):
        valid={c['code'] for c in json.loads(Path('data/mms-2026-01.json').read_text())}
        for line in Path('data/synthetic_generalisation.jsonl').read_text().splitlines():
            if line.strip(): self.assertTrue(set(json.loads(line)['gold']) <= valid)

if __name__=='__main__': unittest.main()
