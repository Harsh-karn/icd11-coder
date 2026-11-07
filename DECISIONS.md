# Architectural and Technical Decision Log (`DECISIONS.md`)

This log records design decisions, options evaluated, empirical measurements, and trade-offs made throughout the development of the ICD-11 coding system.

---

### Decision 01: Two-Stage Hybrid Architecture (Retrieval + LLM Reranking with Offline Fallback)
* **Date & Time:** 2026-11-07 06:25 UTC+5:30
* **Commit:** Initial commit
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
