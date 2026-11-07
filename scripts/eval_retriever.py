import json
import os
import sys
import subprocess

sys.path.insert(0, os.path.abspath("."))
from src.retriever import ICD11Retriever

print("Loading retriever...")
retriever = ICD11Retriever("data/enriched_mms.json")

with open("data/dev_notes.jsonl", encoding="utf-8") as f:
    dev_notes = [json.loads(line) for line in f]

print(f"Evaluating {len(dev_notes)} dev notes...")

top1_hits = 0
top3_hits = 0
top5_hits = 0
top10_hits = 0
top25_hits = 0

predictions = []

for n in dev_notes:
    gold_set = set(n["gold"])
    candidates = retriever.retrieve(n["text"], top_n=25)
    cand_codes = [c["code"] for c in candidates]
    
    top1 = bool(cand_codes) and cand_codes[0] in gold_set
    top3 = any(c in gold_set for c in cand_codes[:3])
    top5 = any(c in gold_set for c in cand_codes[:5])
    top10 = any(c in gold_set for c in cand_codes[:10])
    top25 = any(c in gold_set for c in cand_codes[:25])
    
    top1_hits += top1
    top3_hits += top3
    top5_hits += top5
    top10_hits += top10
    top25_hits += top25
    
    # Generate offline prediction (up to 3 codes)
    pred_codes = retriever.predict_offline(n["text"], max_codes=3)
    predictions.append({"id": n["id"], "codes": pred_codes})

n_total = len(dev_notes)
print("\n--- Retrieval Candidate Recall ---")
print(f"Top 1 Recall:  {top1_hits}/{n_total} ({top1_hits/n_total*100:.1f}%)")
print(f"Top 3 Recall:  {top3_hits}/{n_total} ({top3_hits/n_total*100:.1f}%)")
print(f"Top 5 Recall:  {top5_hits}/{n_total} ({top5_hits/n_total*100:.1f}%)")
print(f"Top 10 Recall: {top10_hits}/{n_total} ({top10_hits/n_total*100:.1f}%)")
print(f"Top 25 Recall: {top25_hits}/{n_total} ({top25_hits/n_total*100:.1f}%)")

os.makedirs("out", exist_ok=True)
pred_path = "out/pred_offline_bm25.jsonl"
with open(pred_path, "w", encoding="utf-8") as f:
    for p in predictions:
        f.write(json.dumps(p) + "\n")

print(f"\nWritten offline predictions to {pred_path}")
print("Running official score.py...")
cmd = f"python score.py --gold data/dev_notes.jsonl --pred {pred_path} --mms data/mms-2026-01.json"
subprocess.run(cmd, shell=True)
