import json
import os
import sys
import time
import asyncio
from typing import List, Dict, Any, Optional

from src.retriever import ICD11Retriever
from src.llm_coder import LLMCoder

class ICD11Pipeline:
    def __init__(
        self,
        enriched_path: str = "data/enriched_mms.json",
        emb_path: str = "data/icd11_embeddings.npy",
        model_path: str = "data/minilm_model"
    ):
        print("Initializing ICD-11 Hybrid Pipeline...")
        self.retriever = ICD11Retriever(
            enriched_path=enriched_path,
            emb_path=emb_path,
            model_path=model_path
        )
        self.llm = LLMCoder(valid_codes=self.retriever.valid_codes)
        print(f"Pipeline ready. LLM available: {self.llm.is_available}")

    def predict_note(self, note_text: str) -> List[str]:
        """Synchronous prediction for a single note."""
        candidates = self.retriever.retrieve(note_text, top_n=20)
        if self.llm.is_available:
            codes = self.llm.predict_sync(note_text, candidates)
            if codes:
                return codes
        return self.retriever.predict_offline(note_text, max_codes=3)

    async def predict_note_async(self, note_text: str, sem: asyncio.Semaphore) -> List[str]:
        """Asynchronous prediction with concurrency rate-limiting semaphore."""
        candidates = self.retriever.retrieve(note_text, top_n=20)
        if self.llm.is_available:
            async with sem:
                codes = await self.llm.predict_async(note_text, candidates)
                if codes:
                    return codes
        return self.retriever.predict_offline(note_text, max_codes=3)

    async def process_async(self, notes: List[Dict[str, Any]], output_path: str, concurrency: int = 8):
        """Process notes asynchronously with an asyncio.Semaphore(limit=8)."""
        sem = asyncio.Semaphore(concurrency)
        total_notes = len(notes)
        start_time = time.time()

        with open(output_path, "w", encoding="utf-8") as out_f:
            for idx, note in enumerate(notes, 1):
                note_id = note.get("id", f"note-{idx}")
                note_text = note.get("text", "")

                try:
                    codes = await self.predict_note_async(note_text, sem)
                except Exception as e:
                    codes = ["MG26"]

                valid_preds = [c for c in codes if c in self.retriever.valid_codes][:3]
                if not valid_preds:
                    valid_preds = ["MG26"]

                res_row = {"id": note_id, "codes": valid_preds}
                out_f.write(json.dumps(res_row, ensure_ascii=False) + "\n")
                out_f.flush()

                if idx % 10 == 0 or idx == total_notes:
                    elapsed = time.time() - start_time
                    rate = idx / max(0.1, elapsed)
                    print(f"[{idx}/{total_notes}] completed ({elapsed:.1f}s, {rate:.1f} notes/sec)")

    def process_file(self, input_path: str, output_path: str, concurrency: int = 8):
        """Process an input JSONL file and write streaming predictions to output_path."""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        notes = []
        with open(input_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        notes.append(json.loads(line))
                    except Exception:
                        continue

        if self.llm.is_available:
            asyncio.run(self.process_async(notes, output_path, concurrency=concurrency))
        else:
            # High-speed synchronous offline runner
            start_time = time.time()
            total_notes = len(notes)
            with open(output_path, "w", encoding="utf-8") as out_f:
                for idx, note in enumerate(notes, 1):
                    note_id = note.get("id", f"note-{idx}")
                    note_text = note.get("text", "")
                    codes = self.retriever.predict_offline(note_text, max_codes=3)
                    valid_preds = [c for c in codes if c in self.retriever.valid_codes][:3]
                    if not valid_preds:
                        valid_preds = ["MG26"]
                    out_f.write(json.dumps({"id": note_id, "codes": valid_preds}, ensure_ascii=False) + "\n")
                    out_f.flush()
                    if idx % 10 == 0 or idx == total_notes:
                        elapsed = time.time() - start_time
                        print(f"[{idx}/{total_notes}] completed ({elapsed:.1f}s, {idx/max(0.1, elapsed):.1f} notes/sec)")
