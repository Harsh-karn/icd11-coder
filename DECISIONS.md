# Architectural and Technical Decision Log (`DECISIONS.md`)

This log records design decisions, options evaluated, empirical measurements, and trade-offs made throughout the development of the ICD-11 coding system.

---

### Decision 01: Two-Stage Hybrid Architecture (Retrieval + LLM Reranking with Offline Fallback)
* **Date & Time:** 2026-11-07 06:25 UTC+5:30
* **Commit:** `e1bad76` (Initial commit)
* **Decision:** Adopt a two-stage hybrid pipeline:
  1. **Stage 1 (Offline Candidate Retrieval):** Enriched ICD-11 metadata indexed with BM25 keyword search and dense semantic vector similarity to retrieve the top 20–25 candidate codes in <50ms on CPU.
  2. **Stage 2 (Online LLM Reranker & Selector):** If an API key (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`) is present, call a high-speed, cost-efficient model (`gpt-4o-mini` or `claude-3-5-haiku`) to select up to 3 ordered codes adhering to ICD-11 leaf and `.Z` residual rules.
  3. **Fallback:** If no API key is provided or if network fails, the Stage 1 candidate ranker with rule-based specificity tie-breaking acts as the complete standalone predictor.
* **Options Considered:**
  1. *Direct zero-shot LLM without retrieval:* Rejected immediately. The 18,375 ICD-11 codes cannot fit into a prompt context, and hallucination of invalid/legacy codes would result in 0 scores.
  2. *Pure offline BM25/Bi-encoder without LLM:* Highly efficient and free, but struggles with ambient clinical conversations where diagnoses are spoken colloquially or differentials are ruled out (e.g. "malaria excluded").
  3. *Two-stage Hybrid (Selected):* Delivers the accuracy of LLM clinical reasoning while strictly respecting the \$6 budget cap and 60-minute CPU runtime constraints.
* **Measurement / Rationale:**
  - Cost analysis: 600 notes $\times$ ~1,200 tokens (note + 20 candidates) $\approx$ 720k tokens $\approx$ \$0.11 total on `gpt-4o-mini`, using less than 2% of the \$6.00 budget.
  - Satisfies the hard constraint: *"With no key set, the system must still produce an answer for every note."*
* **What to Revisit with More Time:**
  - Fine-tune a lightweight local cross-encoder or biomedical bi-encoder (e.g. Bio_ClinicalBERT / SapBERT) to narrow the gap between the online and offline pipelines.


---

### Decision 02: ICD-11 Knowledge Base Enrichment via WHO 2026-01 Multilingual Tabulations
* **Date & Time:** 2026-11-07 06:35 UTC+5:30
* **Commit:** `7f45444` (Phase 2 commit)
* **Decision:** Build an enriched offline dataset (`data/enriched_mms.json`) joining the starter `mms-2026-01.json` with the official WHO 2026-01 SimpleTabulation datasets across English, Spanish, and French. Each code record is enriched with:
  - 5-level hierarchical ancestor taxonomy (`Grouping1` through `Grouping5` + Chapter)
  - Full translations for titles and block hierarchies in Spanish and French (for Slice B generalisation)
  - Verified leaf status and `.Z`/`.X` residual categorization
  - Official WHO coding notes and instructions
* **Options Considered:**
  1. *Titles only (starter `mms-2026-01.json`):* Rejected. Raw titles lack anatomical and pathophysiological context (e.g. "CA40.Z" says "Pneumonia, organism unspecified", but lacks "Respiratory system > Lung infections"). Furthermore, non-English notes in Slice B would fail completely.
  2. *Live runtime querying of WHO API:* Prohibited by grading rules (network access is strictly locked to OpenAI and Anthropic endpoints only).
  3. *Pre-compiled Multilingual Hierarchical Knowledge Base (Selected):* Matches 18,375 of 18,375 codes (100.0% coverage). Shipped directly in the image.
* **Measurement / Rationale:**
  - 100% of the 18,375 scoring categories were enriched with full taxonomic paths and multi-language mappings.
  - Directly addresses the Generalisation (Slice B, 25 points) requirement for non-English visits and rare chapters.
* **What to Revisit with More Time:**
  - Add clinical alias cross-walks (e.g., SNOMED CT to ICD-11 mapping tables and international brand-name medication dictionaries).


---

### Decision 03: Hybrid BM25 + Pre-computed MiniLM Dense Vector Retrieval Engine (Offline Path)
* **Date & Time:** 2026-11-07 06:48 UTC+5:30
* **Commit:** Upcoming Phase 3 commit
* **Decision:** Implement a high-speed hybrid retrieval engine combining:
  1. Native Python `BM25Okapi` with clinical abbreviation and colloquial synonym expansion (e.g., `chickenpox` $\leftrightarrow$ `varicella`, `jigger` $\leftrightarrow$ `tungiasis`, `bilharzia` $\leftrightarrow$ `schistosomiasis`, `URTI` $\leftrightarrow$ `acute nasopharyngitis`).
  2. Pre-computed dense embeddings (26.9 MB, 18,375 $\times$ 384 dimensions) using `all-MiniLM-L6-v2`, saved locally to `data/icd11_embeddings.npy` to eliminate all runtime network downloads.
  3. Query focus: extract diagnostic statements (`A:`, `Dx:`, and doctor conclusive statements in ambient transcripts) with double weighting.
  4. ICD-11 structural prior: 1.35$\times$ score boost for leaf categories and 0.35$\times$ penalty for non-leaf parent categories based on dev-set empirical finding (100% of gold codes are leaves).
* **Options Considered:**
  1. *Pure BM25:* Scored 8.3 / 75.0 (Top-1 recall: 10.0%, Top-25 recall: 25.0%). Failed on ambient transcripts and colloquial vocabulary.
  2. *Pure Dense Search:* Missed precise laboratory findings and specific acronyms like `mRDT`, `BS for MPS`, `TLD`.
  3. *Hybrid Dense + BM25 with Specificity Priors (Selected):* Jumped the offline score from 8.3 to **18.8 / 75.0**, and Top-25 candidate recall to **53.3%**.
* **Measurement / Rationale:**
  - Runtime: <60ms per note on CPU (0.06s), perfectly satisfying the 60-minute limit for 600 notes.
  - Satisfies the no-key constraint with a strong baseline score of 18.8 points out of 75.
* **What to Revisit with More Time:**
  - Fine-tune embedding weights with a larger synthetic clinical dataset or BM25 hyperparameter tuning ($k_1$, $b$).
