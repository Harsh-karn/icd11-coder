import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

print("Exporting MiniLM model locally and generating ICD-11 embeddings...")

model_save_dir = "data/minilm_model"
if not os.path.exists(model_save_dir):
    print("Loading all-MiniLM-L6-v2...")
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    model.save(model_save_dir)
    print(f"Model saved to {model_save_dir}")
else:
    print(f"Loading model from local directory {model_save_dir}...")
    model = SentenceTransformer(model_save_dir)

with open("data/enriched_mms.json", encoding="utf-8") as f:
    categories = json.load(f)

print(f"Encoding {len(categories)} categories...")
# Use concise representation for embedding: code, title, and direct hierarchy
texts_to_embed = [
    f"{c['title']}. Chapter: {c['chapter_title']}. {', '.join(c['hierarchy'])}"
    for c in categories
]

embeddings = model.encode(texts_to_embed, batch_size=128, show_progress_bar=True, normalize_embeddings=True)
embeddings = np.array(embeddings, dtype=np.float32)

emb_path = "data/icd11_embeddings.npy"
np.save(emb_path, embeddings)
print(f"Embeddings saved to {emb_path} with shape {embeddings.shape} ({os.path.getsize(emb_path) / 1024 / 1024:.2f} MB)")


# Bind the saved matrix to the exact ordered records and local model files.
import hashlib
from pathlib import Path
files = [Path("data/enriched_mms.json"), Path(emb_path)] + [p for p in Path(model_save_dir).rglob("*") if p.is_file()]
manifest = {str(p.relative_to("data")): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
Path(emb_path).with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
