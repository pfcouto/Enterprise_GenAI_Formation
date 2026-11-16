# Three sessions of one hour: plan and slide map

Each session is one hour; the first 5 minutes are kept for late arrivals (attendance QR code, "is your stack up?"), so the content is **55 minutes**. Each session ends on something that works on its own, so a missed session does not break the next. The minute-by-minute script, the agenda and the goals are the speaker's own notes (Syone-internal, not in this repository).

| Session | Theme | Content (minutes) | Live part |
|---|---|---|---|
| **1. From RAG to navigable knowledge** | Why RAG evolved; parsing decides what a system can ever know | How we got here (15), the two tracks and the toolbox (5), parsing (5), notebook 01 live (25), wrap-up (5) | Notebook 01, an OKF file, `validate_dataset.py` |
| **2. Two ways to find the answer** | GraphRAG + BM25 against the OKF agent | Recap (3), dense vs BM25 vs graph (5), notebook 02 and the databases (14), the console scenarios (25), which track wins (8) | Notebook 02, Neo4j, Qdrant, the console |
| **3. Can we trust and run it?** | The enterprise layer | Gateway (7), failover and virtual keys live (12), tracing (5), evaluation (7), the LLM judge panel (6), prompt optimisation (4), monitoring (4), take-home and Q&A (8) | `litellm_config.yaml`, failover drill, Langfuse, `/eval` with the judges, Grafana |

Run every full evaluation **before** the session; live, use retrieval-only (free) and the 8-question demo slice with the judge panel (about 3 minutes, under 3 cents).

## The deck: `Documents/Enterprise AI Engineering - UP Skill 2026.pptx`

Built on the UP Skill 2026 Light template; 35 slides plus 7 hidden backup slides (a screenshot of every live demo, in case it fails). Every content slide has speaker notes pointing to the guide. Curiosities (Obsidian/Notion vaults, the context-window timeline, GraphRAG's origin, GLM-OCR on CPU vs GPU) are in the notes, not on the slides.

| Slides | Session | Content |
|---|---|---|
| 1-3 | all | Title, agenda, what you take away |
| 4-11 | 1 | Section; LLM limits; fine-tuning vs RAG; how RAG works (last year's slide 10); where classic RAG breaks; BM25 + GraphRAG; context windows; OKF |
| 12-16 | 1 | Two tracks; the toolbox (one screenshot per tool); parsing; two engines; live notebook 01 |
| 17-21 | 2 | Section; three ways to match; live notebook 02; live console; which track wins |
| 22-30 | 3 | Section; the gateway; live failover and keys; tracing; evaluation; judge panel; prompt optimisation; monitoring; take it home |
| 31-35 | all | Questions, attendance QR (shown at the start of every session), survey, privacy, thank you |
| 36-42 (hidden) | backup | Console scenarios, evaluation with judges, Neo4j, Qdrant, LiteLLM |

The screenshots used are in `docs/screenshots/` (see its README); re-take them after any UI change.
