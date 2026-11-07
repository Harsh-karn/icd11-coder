import json
import os
import re
import hashlib
from pathlib import Path
import numpy as np
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
from src.bm25 import BM25Okapi, tokenize
from src.query_extractor import extract_diagnostic_query, excluded_terms

class ICD11Retriever:
    def __init__(
        self,
        enriched_path: str = "data/enriched_mms.json",
        emb_path: str = "data/icd11_embeddings.npy",
        model_path: str = "data/minilm_model"
    ):
        if not os.path.exists(enriched_path):
            raise FileNotFoundError(f"Enriched database not found at {enriched_path}")
        
        with open(enriched_path, encoding="utf-8") as f:
            self.categories: List[Dict[str, Any]] = json.load(f)
            
        self.code_to_idx = {cat["code"]: idx for idx, cat in enumerate(self.categories)}
        self.valid_codes = set(self.code_to_idx.keys())
        
        # 1. BM25 Index
        corpus = [tokenize(cat["search_text"], expand_abbreviations=False) for cat in self.categories]
        self.bm25 = BM25Okapi(corpus)
        
        # 2. Dense Embeddings
        self.dense_embeddings = None
        self.embed_model = None
        if os.path.exists(emb_path) and os.path.exists(model_path):
            try:
                manifest_path = Path(emb_path).with_suffix(".manifest.json")
                manifest = json.loads(manifest_path.read_text())
                for file, expected in manifest.items():
                    raw = (Path(enriched_path).parent / file).read_bytes()
                    if file.endswith((".json", ".md", ".txt")):
                        raw = raw.replace(b"\r\n", b"\n")
                    actual = hashlib.sha256(raw).hexdigest()
                    if actual != expected:
                        raise ValueError("artifact checksum mismatch: " + file)
                self.dense_embeddings = np.load(emb_path, allow_pickle=False)
                if self.dense_embeddings.shape != (len(self.categories), 384):
                    raise ValueError("embedding shape mismatch")
                os.environ["HF_HUB_OFFLINE"] = "1"
                os.environ["TRANSFORMERS_OFFLINE"] = "1"
                self.embed_model = SentenceTransformer(model_path)
            except Exception as e:
                print(f"Warning: Dense model failed to load ({e}), falling back to pure BM25.")

    def retrieve(self, note_text: str, top_n: int = 25) -> List[Dict[str, Any]]:
        """Retrieve top candidate ICD-11 categories using hybrid BM25 + Dense similarity."""
        if not isinstance(note_text, str) or not note_text.strip() or top_n <= 0:
            return []
        excluded = excluded_terms(note_text)
        diag_query = extract_diagnostic_query(note_text)
        query_tokens = tokenize(diag_query, expand_abbreviations=True)
        
        # 1. BM25 scoring
        bm25_scores = np.array(self.bm25.get_scores(query_tokens), dtype=np.float32)
        max_bm25 = np.max(bm25_scores) if len(bm25_scores) > 0 else 0.0
        if max_bm25 > 0:
            bm25_norm = bm25_scores / max_bm25
        else:
            bm25_norm = np.zeros_like(bm25_scores)

        # 2. Dense semantic scoring
        if self.embed_model is not None and self.dense_embeddings is not None:
            # Encode the diagnostic query with the packaged model.
            q_emb = self.embed_model.encode([diag_query], normalize_embeddings=True)
            dense_scores = np.dot(self.dense_embeddings, q_emb[0])
            # Dense cosine similarities typically range from 0.2 to 0.9, normalize to [0, 1]
            dense_norm = np.clip((dense_scores - 0.2) / 0.7, 0.0, 1.0)
            # Hybrid combination
            combined = 0.45 * bm25_norm + 0.55 * dense_norm
        else:
            combined = bm25_norm

        # 3. Apply ICD-11 specificity adjustments
        # Dev set data showed 100% of gold codes are leaves!
        # Leaf codes get a 1.35x boost, non-leaf codes get 0.35x penalty
        adjusted_scores = combined.copy()
        for idx, cat in enumerate(self.categories):
            is_leaf = cat.get("leaf", False)
            is_residual = cat.get("residual", False)
            
            if is_leaf:
                adjusted_scores[idx] *= 1.35
            else:
                adjusted_scores[idx] *= 0.35
                
            if is_leaf and is_residual and "unspecified" in cat["title"].lower():
                # Slight bump for .Z unspecified codes when exact subtype is omitted
                adjusted_scores[idx] *= 1.04

        # Rank candidates
        top_indices = np.argsort(adjusted_scores)[::-1]
        
        candidates = []
        for idx in top_indices:
            cat = self.categories[idx]
            if any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)",
                             cat["title"], re.I) for term in excluded):
                continue
            candidates.append({
                "code": cat["code"],
                "title": cat["title"],
                "chapter": cat["chapter"],
                "chapter_title": cat["chapter_title"],
                "hierarchy": cat["hierarchy"],
                "leaf": cat["leaf"],
                "residual": cat["residual"],
                "coding_note": cat.get("coding_note", ""),
                "raw_bm25": float(bm25_scores[idx]),
                "score": float(adjusted_scores[idx])
            })
            if len(candidates) >= top_n:
                break
                
        return candidates

    def predict_offline(self, note_text: str, max_codes: int = 3) -> List[str]:
        """Offline prediction using hybrid ranker with leaf-first priority."""
        candidates = self.retrieve(note_text, top_n=20)
        return self.select_offline(candidates, max_codes)

    def select_offline(self, candidates, max_codes=3):
        if not candidates:
            return []

        # Prioritize leaves
        leaf_cands = [c for c in candidates if c["leaf"]]
        pool = leaf_cands if leaf_cands else candidates

        chosen = []
        for c in pool:
            code = c["code"]
            if code not in chosen and code in self.valid_codes:
                chosen.append(code)
            if len(chosen) >= max_codes:
                break
        return chosen
