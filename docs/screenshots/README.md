# Screenshots

Captured from the running stack (Oct 2026) and used in the guides. The UI screenshots (`01`-`06`) use the Sunday League palette (navy neutrals, one blue accent, no gradients); `07`-`11` are the third-party tools.

| File | Shows | Model used |
|---|---|---|
| `01_home` | UI home, scenarios, header health pill | n/a |
| `02_bm25_exact`, `03_led_legend`, `04_footprint_map`, `04b_unanswerable` | both tracks answering | `deepseek-v4.1-flash` via the gateway (alias `formation-fast`, OpenCode Zen) |
| `05_eval_retrieval` | retrieval-only evaluation | none |
| `06_models` | free model explorer | none |
| `07_neo4j_graph`, `08_qdrant` | the two databases | none |
| `09_langfuse_traces` | Langfuse traces (gateway calls and `eval:` scores) | n/a |
| `10_grafana` | gateway operations and the failover panel | n/a |
| `11_prometheus_targets` | scrape targets | n/a |
| `05b_eval_judges` | full evaluation of the demo slice with the LLM judge panel | `deepseek-v4.1-flash`; judges DeepSeek, Haiku, Nemotron |
| `12_services`, `13_how_it_works` | the console's Services and How it works pages | none |
| `14_litellm_models` | LiteLLM admin UI, the aliases (note the red banner: the shared admin key is a static secret) | none |

`01`-`04` and `05b`, `12`-`14` were re-taken on 2026-10-25 after the navigation and judge panel were added.

Retake with `playwright-cli` (see the scripts pattern in the repository history) after UI changes.
