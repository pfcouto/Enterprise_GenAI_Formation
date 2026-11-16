# Evaluation results

Raw results (one JSON line per question) of `scripts/run_eval.py`; interpretation in the speaker guide, section C.1.

- `full_*_formation-fast.jsonl`: **reference run**: `deepseek-v4.1-flash` on OpenCode Zen through the gateway; Track A 32/34, Track B 34/34 (about 840k tokens, about $0.28 for both tracks).
- `judge_*_formation-fast.jsonl`: the same stored answers graded by the **LLM judge panel** (DeepSeek V4.1 Flash, Claude Haiku 5.5, Nemotron free) on 2026-10-25 with `python scripts/run_eval.py --mode judge` (no answer regenerated; about $0.12). Nemotron's free quota (50 requests/day) ran out after a few answers: add its votes another day with `--mode judge --add-judges --judges formation-judge-nemotron`.
- `prompt_optimization_formation-fast.json`: the three-variant prompt loop on 8 questions (naive 3/8, precise 3/8, precise + figure rules 7/8).
- `retrieval_*`: retrieval-only runs (no LLM): Track A 33/34, Track B (scripted navigation) 30/34.
- `v1_full_*_formation-local.jsonl`, `full_*_formation-local.jsonl`: earlier runs with a slow local 27B model (before the chunking fixes: Track A 24/34; the `full_*` local files are Track A after the fixes 31/34 and Track B 34/34 with two questions re-run after fixing bugs in our code).

### Evaluation results on the 34-question golden set

Model: **`deepseek-v4.1-flash` on OpenCode Zen** through the gateway (alias `formation-fast`), one clean run of both tracks on 2026-10-23. Raw per-question results: `docs/eval_results/*.jsonl` (reproduce with `python scripts/run_eval.py --mode full --model formation-fast`).

| Category | Retrieval only: A | Retrieval only: B (scripted) | **Full: A (GraphRAG)** | **Full: B (OKF agent)** | A before the chunking fixes* |
|---|---:|---:|---:|---:|---:|
| bm25_exact_match | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| factual | 7/8 | 5/8 | 7/8 | 8/8 | 5/8 |
| faq | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| multi_hop_graph | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| near_duplicate_codes | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| no_answer | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| table_lookup | 4/4 | 4/4 | 4/4 | 4/4 | 3/4 |
| text_in_diagram | 5/5 | 5/5 | 5/5 | 5/5 | 2/5 |
| visual_grounding | 5/5 | 4/5 | 4/5 | 5/5 | 2/5 |
| **total** | **33/34** | **30/34** | **32/34** | **34/34** | **24/34** |

\* The last column is the first full run, made with a slow local 27B model **before** two chunking fixes (see below); it is the "before" of the before/after story, not a like-for-like comparison.

| Run | Questions | Avg seconds per question | Cost |
|---|---:|---:|---|
| Track A (GraphRAG + BM25) | 34 | 2.6 | about 3k tokens per question |
| Track B (OKF agent) | 34 | 5.5 | about 20k tokens per question |
| **Both tracks** | 68 | | **about $0.28 in total** (840k tokens at $0.30 / $1.20 per 1M) |

**How to read this (and the story to tell):**

* **Retrieval vs generation.** With *no LLM at all*, Track A already puts the right document in front of the model for 33 of 34 questions. Questions that fail in "Full" but not in "Retrieval" are generation problems; the others are retrieval problems.
* **Measure, read the failures, change one thing, measure again.** The first full run (local model) scored **24/34** for Track A. Reading the failures showed two retrieval gaps: facts that exist only in a page's meta description (frontmatter, never chunked) and figure descriptions that could not be retrieved on their own. Two chunking changes (a summary "card" per document, one chunk per figure) raised retrieval to 33/34 and flipped every `text_in_diagram` question to pass; the later full run on the hosted model scored **32/34**.
* **Track B scored 34/34**, the agent finds everything, at about twice Track A's latency and about 7 times its tokens. Along the way it exposed two bugs in *our* code that the evaluation caught: an accent mismatch in the scorer ("Vitor" vs "Vítor") and the agent looping on one tool call then leaking a raw tool call as its answer (fixed with a loop guard).
* **What still fails in Track A (2 questions)**, both instructive: `syone_013` (*where are the offices?*: the contact page says "Lisboa ... Porto ..." and never "offices" or "located": a vocabulary mismatch that dense retrieval did not bridge; query rewriting or enriching the chunk would fix it) and `hw_009` (needs the *neighbouring* rack unit, which the retrieved chunks did not include).
* **Caveat:** keyword-based scoring, one model, one run. Treat the numbers as a demonstration of the method, not a benchmark.

#### Prompt optimization (notebook 05, section 3): measured

Three prompt candidates scored on the real Track A pipeline over 8 questions (`docs/eval_results/prompt_optimization_formation-fast.json`):

| Prompt variant | Questions passed (of 8) |
|---|---:|
| v0 naive | 3/8 |
| v1 precise | 3/8 |
| v2 precise + figure rules | 7/8 |

Adding the figure rule (`include the exact markdown image line when a figure shows the answer`) is what moves the score: the naive and "precise" prompts answer the facts but never cite the figures the questions ask for. This is the loop that Opik's MetaPrompt/GEPA optimizers automate by letting an LLM propose and mutate the candidates.

#### LLM judge panel on the reference answers (2026-10-25)

| | Keyword verdict | DeepSeek: mean grade, agrees with keywords | Haiku (thinking off) | Nemotron (free) |
|---|---:|---|---|---|
| Track A | 32/34 | 0.90, 31 of 33 | 0.85, 34 of 34 | 1.00, 6 of 6 |
| Track B | 34/34 | 0.97, 32 of 33 | 0.89, 34 of 34 | none (quota) |

Haiku was re-graded with its thinking switched off (`thinking: {type: disabled}` in the gateway config; before: 0.81 / 0.89, agreeing 32 and 33 times). Cases worth reading (details in the speaker guide, section 5.1b): `syone_014` (a correct refusal the keyword regex missed: scorer fixed), `hw_012` Track B (wrong order of steps and wrong command: keywords pass, DeepSeek 0.3), `syone_011` Track A (both judges see the same missing fact, grades 0.4 and 0.8), and judge noise (the DeepSeek judge gave the same answer 0.1 to 0.8 over 12 calls at temperature 0).

**Data drift note.** The reference full run was made on 2026-10-23, before the Syone figures were renamed (`about-1.png` became `syone-footprint-map.png`). Re-scoring the stored `syone_002` answers today fails the figure check because they cite the old name; a live run passes. Re-run the evaluation after every data change: this is exactly the drift it exists to catch.
