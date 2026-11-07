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
        """Predict top 1-3 codes for a single note."""
        # Step 1: Candidate retrieval
        candidates = self.retriever.retrieve(note_text, top_n=20)
        
        # Step 2: LLM reranking if key is available
        if self.llm.is_available:
            codes = self.llm.predict_sync(note_text, candidates)
            if codes:
                return codes

        # Step 3: High-speed offline fallback
        return self.retriever.predict_offline(note_text, max_codes=3)

    def process_file(self, input_path: str, output_path: str, concurrency: int = 5):
        """Process an input JSONL file and write streaming predictions to output_path."""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Ensure output directory exists
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        # Read input notes
        notes = []
        with open(input_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        notes.append(json.loads(line))
                    except Exception:
                        continue

        total_notes = len(notes)
        print(f"Processing {total_notes} notes -> {output_path}...")
        start_time = time.time()

        # Open output file in append mode and write streaming results
        with open(output_path, "w", encoding="utf-8") as out_f:
            for idx, note in enumerate(notes, 1):
                note_id = note.get("id", f"note-{idx}")
                note_text = note.get("text", "")

                try:
                    codes = self.predict_note(note_text)
                    if not codes:
                        codes = ["MG26"]  # Fallback
                except Exception as e:
                    print(f"Error on note {note_id}: {e}")
                    codes = ["MG26"]

                # Ensure only valid codes are output
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

        total_elapsed = time.time() - start_time
        print(f"Done. Processed {total_notes} notes in {total_elapsed:.2f}s ({total_elapsed/max(1, total_notes):.3f}s/note).")

