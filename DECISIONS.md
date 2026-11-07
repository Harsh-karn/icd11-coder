# Architectural and Technical Decision Log (`DECISIONS.md`)

This log records design decisions, options evaluated, empirical measurements, and trade-offs made throughout the development of the ICD-11 coding system.

---

### Decision 01: Two-Stage Hybrid Architecture (Retrieval + LLM Reranking with Offline Fallback)
* **Date & Time:** 2026-11-07 06:25 UTC+5:30
* **Commit:** `e1bad76` (Initial commit)
* **Decision:** Adopt a two-stage hybrid pipeline:
  1. *Stage 1 (Offline Candidate Retrieval):* Enriched ICD-11 metadata indexed with BM25 keyword search and dense semantic vector similarity to retrieve the top 20–25 candidate codes in <50ms on CPU.
  2. *Stage 2 (Online LLM Reranker & Selector):* If an API key (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`) is present, call a high-speed, cost-efficient model (`gpt-4o-mini` or `claude-3-5-haiku`) to select up to 3 ordered codes adhering to ICD-11 leaf and `.Z` residual rules.
  3. *Fallback:* If no API key is provided or if network fails, the Stage 1 candidate ranker with rule-based specificity tie-breaking acts as the complete standalone predictor.
* **Options Considered:**
  1. *Direct zero-shot LLM without retrieval:* Rejected. 18,375 ICD-11 codes cannot fit into context, and hallucinations of legacy ICD-10 codes would score 0.
  2. *Pure offline BM25/Bi-encoder without LLM:* Free and fast, but struggles on conversational nuance and rule-outs.
  3. *Two-stage Hybrid (Selected):* Delivers high accuracy while strictly respecting the \$6 budget cap and 60-minute CPU runtime constraints.
* **Measurement / Rationale:** Token budget: 600 notes $\times$ ~1,200 tokens $\approx$ \$0.11 total on `gpt-4o-mini`, using less than 2% of the \$6.00 budget. Satisfies the mandatory no-key execution rule.
* **What to Revisit with More Time:** Train a local lightweight biomedical cross-encoder.

---

### Decision 02: Ingestion of Official WHO 2026-01 SimpleTabulation
* **Date & Time:** 2026-11-07 06:30 UTC+5:30
* **Commit:** `7f45444` (Phase 2 commit)
* **Decision:** Download and parse the official WHO 2026-01 SimpleTabulation dataset (`SimpleTabulation-ICD-11-MMS-en.zip`) from the WHO static release CDN.
* **Options Considered:**
  1. *Rely solely on provided titles in `mms-2026-01.json`:* Discarded. Lacked anatomical chapters, parent blocks, and coding notes.
  2. *Query live WHO API during runtime:* Prohibited by grading rules (network locked to OpenAI/Anthropic only).
  3. *Pre-compiled WHO Release Ingestion (Selected):* Extracted complete 5-level taxonomic hierarchies (`Grouping1` through `Grouping5`), parent URIs, and residual tags across 35,664 rows, matching 100% of MMS categories.
* **Measurement / Rationale:** 18,375 of 18,375 codes (100.0%) were enriched with complete taxonomic paths.
* **What to Revisit with More Time:** Ingest ICD-11 foundation definitions if full text dumps become available.

---

### Decision 03: Multilingual Knowledge Enrichment (Spanish & French) for Slice B
* **Date & Time:** 2026-11-07 06:35 UTC+5:30
* **Commit:** `7f45444` (Phase 2 commit)
* **Decision:** Ingest official WHO Spanish (`-es.zip`) and French (`-fr.zip`) SimpleTabulations into `data/enriched_mms.json`.
* **Options Considered:**
  1. *English-only index:* Risk of losing up to 25 points on Slice B if consultations are recorded in Spanish or French.
  2. *Runtime translation via external MT API:* Prohibited by sandbox firewall.
  3. *Pre-compiled Multilingual Index (Selected):* Built cross-lingual search documents embedding native Spanish and French titles and hierarchical block names.
* **Measurement / Rationale:** 18,375 / 18,375 categories mapped to Spanish and French equivalents with zero runtime translation latency.
* **What to Revisit with More Time:** Add Portuguese and Arabic tabulations.

---

### Decision 04: Native Python BM25Okapi over External C-Dependencies
* **Date & Time:** 2026-11-07 06:40 UTC+5:30
* **Commit:** `718b950` (Phase 3 commit)
* **Decision:** Implement a self-contained `BM25Okapi` in `src/bm25.py` rather than relying on external packages like `rank-bm25`.
* **Options Considered:**
  1. *External C/C++ packages:* Risk of compilation failures or wheel mismatches in Docker on the evaluation machine.
  2. *SQLite FTS5:* Good keyword search, but lacks direct tunable BM25 scoring parameters ($k_1$, $b$).
  3. *Native Python BM25Okapi (Selected):* 100% portable, builds in 0 seconds, and executes top-25 retrieval across 18,375 documents in <15ms.
* **Measurement / Rationale:** Guaranteed zero-build-failure reliability inside the Docker container.
* **What to Revisit with More Time:** Implement inverted index block compression.

---

### Decision 05: Clinical Abbreviation and Colloquial Synonym Lexicon
* **Date & Time:** 2026-11-07 06:42 UTC+5:30
* **Commit:** `718b950` (Phase 3 commit)
* **Decision:** Build a dedicated clinical abbreviation dictionary (`CLINICAL_ABBREVIATIONS` in `src/bm25.py`) bridging colloquial phrasing to medical nomenclature.
* **Options Considered:**
  1. *Raw tokenization:* Missed colloquial diseases (e.g. "chickenpox" $\leftrightarrow$ "varicella", "jigger" $\leftrightarrow$ "tungiasis", "bilharzia" $\leftrightarrow$ "schistosomiasis").
  2. *Comprehensive Lexicon (Selected):* Added 68 clinical mappings covering acronyms (`URTI`, `MPS`, `TLD`, `mRDT`) and colloquial synonyms.
* **Measurement / Rationale:** Increased BM25 candidate recall on conversational notes by >18%.
* **What to Revisit with More Time:** Auto-mine clinical synonym pairs from PubMed abstracts.

---

### Decision 06: Pre-computed Dense Semantic Embeddings via `all-MiniLM-L6-v2`
* **Date & Time:** 2026-11-07 06:44 UTC+5:30
* **Commit:** `718b950` (Phase 3 commit)
* **Decision:** Select `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions, 87 MB) and pre-compute embeddings for all 18,375 categories ahead of time into `data/icd11_embeddings.npy`.
* **Options Considered:**
  1. *Large LLM embeddings (e.g. text-embedding-3-large):* Prohibited by cost and runtime network barriers.
  2. *BERT-base / RoBERTa (768 dimensions):* Slower CPU matrix multiplication (~10ms) and 4x larger matrix.
  3. *all-MiniLM-L6-v2 (Selected):* Balanced semantic understanding with a lean 26.9 MB float32 matrix.
* **Measurement / Rationale:** Matrix fits completely in memory; CPU dot product takes only 2.8ms.
* **What to Revisit with More Time:** Fine-tune MiniLM with contrastive learning on clinical SOAP pairs.

---

### Decision 07: Diagnostic Section Weighting over Chief Complaints
* **Date & Time:** 2026-11-07 06:46 UTC+5:30
* **Commit:** `718b950` (Phase 3 commit)
* **Decision:** Implement `extract_diagnostic_query()` in `src/query_extractor.py` to heavily weight the assessment section (`A:`, `Dx:`, doctor conclusive statements) over past history and review of systems.
* **Options Considered:**
  1. *Flat full-text search:* Diluted the diagnostic signal with generic vitals (`BP 120/80`, `T 38.9C`) and non-specific symptoms.
  2. *Diagnostic Extraction (Selected):* Repeated the diagnostic line twice in the query string, prioritizing the true clinical impression.
* **Measurement / Rationale:** Top-1 recall jumped from 10.0% to 23.3% on `dev_notes.jsonl`.
* **What to Revisit with More Time:** Train a token classifier to segment notes into subjective, objective, and assessment spans.

---

### Decision 08: Specificity Priors (Leaf Promotion & Parent Demotion)
* **Date & Time:** 2026-11-07 06:48 UTC+5:30
* **Commit:** `718b950` (Phase 3 commit)
* **Decision:** Apply an empirical specificity re-weighting to candidate retrieval scores: $1.35\times$ boost to leaf categories, $0.35\times$ penalty to non-leaf categories, and $1.04\times$ boost to `.Z` residual codes.
* **Options Considered:**
  1. *Unweighted candidate scoring:* Surfaced high-level parent categories (e.g. `1F40` instead of `1F40.Z`), violating the brief's rule: *"A parent code does not count when a child fits"*.
  2. *Strict leaf filtering only:* Risked empty candidate sets on sparse queries.
  3. *Continuous Specificity Priors (Selected):* Promoted specific leaves while keeping parent candidates available as backup.
* **Measurement / Rationale:** Jumped offline baseline score on `dev_notes.jsonl` from **8.3 $\rightarrow$ 18.8 / 75.0**.
* **What to Revisit with More Time:** Hierarchical tree-traversal beam search.

---

### Decision 09: LLM Candidate-Constrained JSON Reranker (`gpt-4o-mini`)
* **Date & Time:** 2026-11-07 06:55 UTC+5:30
* **Commit:** `c834884` (Phase 4 & 5 commit)
* **Decision:** Design `LLMCoder` targeting `gpt-4o-mini` with structured JSON output constrained strictly to the top 20 candidate codes.
* **Options Considered:**
  1. *Open-ended generation:* High rate of hallucinations and legacy ICD-10 codes.
  2. *Candidate-Constrained JSON (Selected):* Restricts LLM choices to verified candidates with explicit leaf/residual labels and taxonomy context.
* **Measurement / Rationale:** Stays strictly within token budget (estimated \$0.11 for 600 notes vs \$6.00 limit).
* **What to Revisit with More Time:** Add dynamic in-context exemplars.

---

### Decision 10: Strict 5.0s Timeout and Automatic Candidate Substitution Guardrails
* **Date & Time:** 2026-11-07 07:00 UTC+5:30
* **Commit:** `aede701` (Phase 4 commit)
* **Decision:** Hardcode a 5.0-second timeout per LLM request and validate every predicted code against `mms-2026-01.json`. If an unlisted code is returned or if the call fails, fill slots from Stage 1 candidates.
* **Options Considered:**
  1. *Permit long timeouts (15s):* Risk exceeding the 60-minute cap on 600 notes if OpenAI encounters latency spikes.
  2. *5.0s Timeout with Dynamic Substitution (Selected):* Guarantees 0 invalid codes and prevents timeouts.
* **Measurement / Rationale:** Validated: `missing predictions 0, invalid codes 0`.
* **What to Revisit with More Time:** Exponential backoff retry for transient 503 errors.

---

### Decision 11: Async Concurrency (`asyncio.Semaphore(8)`) & Streaming Disk Flush
* **Date & Time:** 2026-11-07 07:05 UTC+5:30
* **Commit:** `b165e92` (Phase 4 commit)
* **Decision:** Implement `process_async()` in `src/pipeline.py` using `asyncio.Semaphore(8)` and immediately flush each prediction to disk (`flush=True`).
* **Options Considered:**
  1. *Batch writing at the end:* Risk of scoring 0 if container is stopped before finishing.
  2. *Streaming write per note (Selected):* Guarantees partial predictions score even under sudden process termination.
* **Measurement / Rationale:** 60 notes processed in 57.6s (projected ~10 minutes for 600 notes vs 60-minute limit).
* **What to Revisit with More Time:** Dynamic concurrency scaling based on API latency.

---

### Decision 12: Slim CPU-only PyTorch Docker Packaging
* **Date & Time:** 2026-11-07 07:08 UTC+5:30
* **Commit:** `c834884` (Phase 5 commit)
* **Decision:** Install PyTorch inside the Dockerfile using `--extra-index-url https://download.pytorch.org/whl/cpu` and set `HF_HUB_OFFLINE=1`.
* **Options Considered:**
  1. *Standard PyPI PyTorch:* Installs 2.5 GB of CUDA binaries, causing slow Docker builds.
  2. *CPU-only Wheel (Selected):* Reduces image size by over 2 GB, speeds up build time, and matches grading specs (8 CPUs, no GPU).
* **Measurement / Rationale:** Docker builds cleanly and runs 100% offline with zero network lookups.
* **What to Revisit with More Time:** Export model to ONNX runtime for even smaller footprint.

---

### Decision 13: Slice B Synthetic Generalisation Benchmark
* **Date & Time:** 2026-11-07 07:10 UTC+5:30
* **Commit:** `c17f1c1` (Phase 6 commit)
* **Decision:** Create `data/synthetic_generalisation.jsonl` with 10 multi-chapter, multilingual (Spanish/French) consults to evaluate Slice B.
* **Options Considered:**
  1. *Evaluate dev set only:* High risk of overfitting to Kenyan outpatient communicable diseases.
  2. *Synthetic Generalisation Suite (Selected):* Tested rare chapters (Cardiology, Ophthalmology, Urology, Endocrinology) and non-English dialogues.
* **Measurement / Rationale:** Achieved 5.0 / 25 points purely offline on Slice B with 0 crashes.
* **What to Revisit with More Time:** Expand synthetic benchmark to 150 notes.

---

### Decision 14: Negation and Rule-Out Clinical Logic
* **Date & Time:** 2026-11-07 07:12 UTC+5:30
* **Commit:** `c17f1c1` (Phase 6 commit)
* **Decision:** Add explicit negation rules in prompt and query extraction to downweight ruled-out conditions (e.g. "malaria excluded").
* **Options Considered:**
  1. *Allow LLM to infer negations without explicit rules:* Caused misclassification on `dev-002`.
  2. *Explicit Negation Guardrail (Selected):* Instructs the LLM to ignore differentials that tested negative.
* **Measurement / Rationale:** Successfully resolved the `dev-002` misclassification failure mode.
* **What to Revisit with More Time:** Integrate NegEx dependency parsing.
