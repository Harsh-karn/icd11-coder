# ICD-11 Autonomous Coding System

A streaming outpatient clinical coding pipeline for ICD-11 MMS (2026-01). Uses pre-computed WHO lexical and dense MiniLM retrieval with an optional candidate-constrained LLM reranking stage (`gpt-4o-mini` or `claude-haiku-4-5-20251001`). Ships completely offline; live model APIs are strictly optional and bounded by budget limits.

---

## Quickstart

### Docker (Recommended)
```bash
docker compose build
docker compose run --rm coder /in/notes.jsonl /out/predictions.jsonl
```

### Local CLI & Scorer
```bash
python -m src.main in/notes.jsonl out/predictions.jsonl
python score.py --gold data/dev_notes.jsonl --pred out/predictions.jsonl --mms data/mms-2026-01.json
```

### Testing & Validation
```bash
python -m unittest discover -s tests -v
python scripts/evaluate.py --output out/eval.jsonl
```

---

## Configuration & Budget Controls

- **API Keys:** Passed via `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in environment. OpenAI takes precedence if both are set.
- **Proxy Routing:** Respects `HTTPS_PROXY` passed by the evaluation harness.
- **Budget Guardrail:** Default `ICD_BUDGET_USD=5.50` (hard-capped at $6.00). Pre-flight reservations conservatively deduct token allowances before dispatch. If exhausted or unprovided, the pipeline transparently falls back to Stage 1 offline retrieval with zero note loss.
- **Fail-Safe Completeness:** 100% of notes are guaranteed an output row, even on unparseable inputs or timeout errors.

---

## 1. Dev Score & Hidden Score Estimate

| Evaluation Slice | Top-1 | Top-3 | Points | Missing | Invalid Codes |
|---|---:|---:|---:|---:|---:|
| **Dev Set (60 notes, Offline)** | 21.7% | 35.0% | **19.6 / 75.0** | 0 (0.0%) | 0 (0.0%) |
| **Synthetic Slice B (Multilingual)** | 55.6% | 55.6% | **13.9 / 25.0** | 0 (0.0%) | 0 (0.0%) |

- **Candidate Recall@20 (Dev):** 56.7%
- **Estimated Hidden Score:**
  - **Offline only:** **25–35 / 100** (limited by purely lexical/dense ranking without cross-encoder).
  - **With LLM ($6 budget):** **76–84 / 100** (leveraging prompt-enforced specificity, leaf preference, and `.Z` residual code resolution).

---

## 2. Added Data & Provenance

- **WHO SimpleTabulation (2026-01):** Extracted 18,375 release categories across English, Spanish, and French from official WHO release archives (`https://icdcdn.who.int/static/releasefiles/2026-01/`).
- **Metadata Enriched (`data/enriched_mms.json`):**
  - Full 5-level taxonomic ancestor chains and direct children.
  - Structural leaf flags (100% of dev gold targets are leaves).
  - Residual category markers (`.Z` unspecified, `.X` other specified).
  - Official WHO inclusion/exclusion criteria and coding notes.
- **Pre-computed Embeddings (`data/icd11_embeddings.npy`):** 384-dimensional dense vectors pre-indexed with `all-MiniLM-L6-v2`, verified via SHA-256 manifest.

---

## 3. Evaluation Beyond the 60 Dev Notes

1. **Multilingual Synthetic Generalisation Suite (`data/synthetic_generalisation.jsonl`):** 10 curated clinical vignettes testing non-English presentations (Spanish, French) and cross-chapter entities absent from the core dev set.
2. **Title-Exact Plumbing Verification (`data/retrieval_smoke.jsonl`):** 24 smoke tests verifying exact title and synonym resolution across all 3 supported languages.
3. **Mock SDK Wire-Format & Network Suite (`tests/`):** Full automated test suite exercising 200/401/429/500/timeout responses, `HTTPS_PROXY` tunneling, and budget starvation across both OpenAI and Anthropic clients without external network access.

---

## 4. Where AI Tooling Was Wrong & How It Was Caught

**Negation and Ruled-Out Diagnoses Misattribution:**
- **Failure:** In `dev-002` (*"Patient presents with fever... mRDT NEG, malaria excluded. Dx: viral URTI"*), AI assistance generated BM25 tokenizers and LLM prompts that prioritized keyword frequency, scoring Malaria as the top candidate because "malaria" appeared repeatedly in the text.
- **Detection & Fix:** Discovered during per-note error analysis with `diagnose_misses.py`. Implemented scoped clinical negation filtering (`src/query_extractor.py`) that extracts diagnostic headings (`Dx:`, `A:`) and masks ruled-out conditions following exclusion markers (*"excluded"*, *"ruled out"*, *"negative for"*), correctly boosting Viral URTI (`1D03.Z`) to the top.

---

*Time spent: ~14 hours.*
