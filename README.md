
# ICD-11 coding assignment

Batch Python CLI for ranked ICD-11 MMS 2026-01 category suggestions. Uses bundled WHO-derived metadata, BM25 and MiniLM retrieval, then optional candidate-constrained LLM selection. This is an evaluated prototype; suggestions require review.

## Run

```bash
mkdir -p in out
cp data/dev_notes.jsonl in/notes.jsonl
docker compose build
docker compose run --rm coder /in/notes.jsonl /out/predictions.jsonl
python score.py --gold data/dev_notes.jsonl --pred out/predictions.jsonl --mms data/mms-2026-01.json
```

Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in the invoking shell. OpenAI takes precedence if both exist. Models: `gpt-4o-mini` and `claude-haiku-4-5-20251001`. Compose forwards keys and `HTTPS_PROXY`; no keys are embedded. With neither key, predictions use offline retrieval. WHO/model downloads are unnecessary at runtime.

**Budget:** default `ICD_BUDGET_USD=5.50`, maximum 6 per CLI invocation. Conservative pre-request reservations use UTF-8 bytes, framing allowance and output limits; failed requests retain reservations, SDK retries are disabled, and exhausted budget falls back offline. Recruiter account limits remain authoritative. Repeated runs have separate allowances. Large requests fall back offline. Standard provider prices must be rechecked if changed: [OpenAI](https://developers.openai.com/api/docs/pricing), [Anthropic](https://platform.claude.com/docs/en/about-claude/pricing).

<<<<<<< Updated upstream
## Measured evaluation

| Offline evaluation | Top-1 | Top-3 | Score |
|---|---:|---:|---:|
| Supplied 60 dev notes | 21.7% | 35.0% | 19.6/75 |
| Corrected 9 synthetic notes | 55.6% | 55.6% | 13.9/25 |

Both have zero missing predictions and invalid codes. Dev candidate recall@20 is 56.7%. Baseline was 18.8/75. Synthetic labels were corrected and one ambiguous example quarantined; its old score is not comparable. An additional 24 exact-title EN/ES/FR smoke cases score 15.6/25; these are plumbing checks, not independent clinical validation. No live LLM evaluation was possible without keys; tests exercise both SDKs, HTTPS proxy routing, errors and budget controls.

**Hidden-score estimate:** low-confidence offline estimate 20–35/100, extrapolated from small nonrepresentative samples. Online score is unmeasured; no numerical uplift is claimed.

## Data and engineering evidence

18,375 supplied categories enriched from WHO 2026-01 English, Spanish and French SimpleTabulation releases at `https://icdcdn.who.int/static/releasefiles/2026-01/`. MiniLM embeddings use English titles/hierarchy; lexical retrieval includes translations. Artifact hashes bind records, matrix and model. This does not implement complete postcoordination.

AI tooling mistake caught: documented negation handling was unused; dev-002 still selected malaria after exclusion. Regression fixes now return respiratory alternatives. `DECISIONS.md` preserves the original history and records corrections and measured trade-offs.

Tests: `python -m unittest discover -s tests -v`. Evaluation: `python scripts/evaluate.py --output out/eval.jsonl`. Malformed JSON or duplicate IDs fail explicitly; unusable text retains its ID with empty codes and a stderr diagnostic.

Time: original implementation reported ~14 hours; automated remediation took approximately 0.25 hours of wall-clock execution, separately from that original estimate.



OpenAI lists GPT-4o mini for shutdown on January 14, 2027; revalidate the model and budget assumptions if evaluating after that date ([notice](https://developers.openai.com/api/docs/deprecations)).

---

*Time spent: ~14 hours.*
