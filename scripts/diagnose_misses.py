import json
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from src.retriever import ICD11Retriever

retriever = ICD11Retriever("data/enriched_mms.json")

with open("data/dev_notes.jsonl", encoding="utf-8") as f:
    dev_notes = [json.loads(line) for line in f]

misses = []
for n in dev_notes:
    gold_set = set(n["gold"])
    candidates = retriever.retrieve(n["text"], top_n=25)
    cand_codes = [c["code"] for c in candidates]
    if not any(c in gold_set for c in cand_codes):
        misses.append((n, candidates[:5]))

print(f"Total misses in Top 25: {len(misses)} / {len(dev_notes)}")
for n, top5 in misses[:5]:
    print(f"\n[{n['id']}] style={n['style']}")
    print(f"Text snippet: {n['text'][:140]}...")
    print(f"Gold: {n['gold']}")
    print("Top 5 retrieved:")
    for c in top5:
        print(f"  {c['code']} ({c['title']}): score={c['score']:.3f}, bm25={c['raw_bm25']:.1f}")

