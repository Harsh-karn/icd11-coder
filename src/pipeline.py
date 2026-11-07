import asyncio
import json
import logging
import os
from src.retriever import ICD11Retriever
from src.llm_coder import LLMCoder


class ICD11Pipeline:
    def __init__(self, enriched_path="data/enriched_mms.json",
                 emb_path="data/icd11_embeddings.npy", model_path="data/minilm_model"):
        self.retriever = ICD11Retriever(enriched_path, emb_path, model_path)
        self.llm = LLMCoder(self.retriever.valid_codes)

    def predict_note(self, note_text):
        candidates = self.retriever.retrieve(note_text, top_n=20)
        codes = self.llm.predict_sync(note_text, candidates) if self.llm.is_available else []
        return codes or self.retriever.select_offline(candidates)

    async def process_async(self, notes, output_path, concurrency=4):
        if concurrency < 1:
            raise ValueError("concurrency must be positive")
        queue = asyncio.Queue(maxsize=concurrency * 2)
        # One retrieval thread at a time protects the shared model and bounds CPU use.
        retrieval_lock = asyncio.Lock()
        async def produce():
            for note in notes:
                await queue.put(note)
            for _ in range(concurrency):
                await queue.put(None)

        with open(output_path, "w", encoding="utf-8") as output:
            async def worker():
                while True:
                    note = await queue.get()
                    if note is None:
                        return
                    codes = []
                    try:
                        text = note["text"]
                        if not isinstance(text, str) or not text.strip():
                            raise ValueError("empty or non-string text")
                        async with retrieval_lock:
                            candidates = await asyncio.to_thread(self.retriever.retrieve, text, 20)
                        if self.llm.is_available:
                            codes = await self.llm.predict_async(text, candidates)
                        codes = codes or self.retriever.select_offline(candidates)
                    except Exception as exc:
                        logging.warning("Note processing failed: %s", type(exc).__name__)
                    codes = list(dict.fromkeys(c for c in codes if c in self.retriever.valid_codes))[:3]
                    # No await between write and flush; workers cannot interleave a row.
                    output.write(json.dumps({"id": note["id"], "codes": codes}, ensure_ascii=False) + "\n")
                    output.flush()
            try:
                async with asyncio.TaskGroup() as tasks:
                    tasks.create_task(produce())
                    for _ in range(concurrency):
                        tasks.create_task(worker())
            finally:
                await self.llm.close()
                logging.warning("LLM requests=%d reserved_usd=%.4f", self.llm.calls, self.llm.reserved)

    def process_file(self, input_path, output_path, concurrency=4):
        notes = []
        ids = set()
        with open(input_path, encoding="utf-8") as source:
            for number, line in enumerate(source, 1):
                if not line.strip():
                    continue
                try:
                    note = json.loads(line)
                except ValueError as exc:
                    raise ValueError(f"Invalid JSON on line {number}") from exc
                if not isinstance(note, dict) or not isinstance(note.get("id"), str):
                    raise ValueError(f"Expected object with string id on line {number}")
                if note["id"] in ids:
                    raise ValueError(f"Duplicate id on line {number}")
                ids.add(note["id"])
                note.setdefault("text", "")
                notes.append(note)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        asyncio.run(self.process_async(notes, output_path, concurrency))
