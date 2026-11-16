# Participant guide: build and run the whole pipeline yourself

You will run every stage of a GenAI system on your own laptop: acquire data, parse it, build two knowledge bases, query them side by side, route model calls through a gateway, trace them, and measure quality. Each step below says **what to run, what you should see, and what to look at**. If your output differs, jump to [Troubleshooting](#7-troubleshooting).

**Time:** about 15 minutes of setup (mostly downloads), then follow along with the session.

**The three sessions and where they are in this guide**

| Session | Theme | Sections |
|---|---|---|
| 1. From RAG to navigable knowledge | why RAG evolved; parsing PDFs and web pages; Google's Open Knowledge Format | 2, 3 (notebook 1) |
| 2. Two ways to find the answer | indexing into Qdrant and Neo4j; GraphRAG + BM25 against the OKF agent | 4, 5 (notebooks 2, 3) |
| 3. Can we trust and run it? | the AI gateway and failover, virtual keys, tracing, evaluation with an LLM judge panel, monitoring | 6 (notebooks 4, 5) |

**Logins** (public demo defaults, also on the console's **Services** page, <http://localhost:13002/services>):

| Tool | URL | Login |
|---|---|---|
| Formation console | <http://localhost:13002> | none |
| Neo4j Browser | <http://localhost:17474> | `neo4j` / `syone2026` |
| Qdrant dashboard | <http://localhost:16333/dashboard> | none |
| LiteLLM admin UI | <http://localhost:14000/ui> | `syone` / `syone2026` |
| Langfuse | <http://localhost:13000> | `syone@syone.com` / `syone2026` |
| Grafana | <http://localhost:13001> | `syone` / `syone2026` |
| Prometheus | <http://localhost:19090> | none |
| FastAPI docs | <http://localhost:18000/docs> | none |

New to the console? Its **How it works** page (<http://localhost:13002/how-it-works>) explains the two tracks and the path of one question through the stack.
**Needs:** Docker Desktop (8 GB RAM for Docker), Python 3.11 to 3.14 (or [uv](https://docs.astral.sh/uv/), which fetches it for you), 10 GB free disk, internet for the first setup. Node.js is **not** needed.

![Diagram: see source in docs/diagrams/participant_guide_1.mmd](docs/diagrams/participant_guide_1.png)

*Diagram source: `docs/diagrams/participant_guide_1.mmd` (Mermaid). Re-render with `npx @mermaid-js/mermaid-cli -i docs/diagrams/participant_guide_1.mmd -o docs/diagrams/participant_guide_1.png -c docs/diagrams/mermaid.json -b "#141B23" -s 2`.*

---

## 1. Setup

```bash
git clone https://github.com/pfcouto/Enterprise_GenAI_Formation.git
cd Enterprise_GenAI_Formation
cp .env.example .env                       # then put your key in it (next section)

# Python 3.11 to 3.14. Python 3.15 is too new: onnxruntime (used for the embeddings) has no build for it yet.
# Easiest: uv (https://docs.astral.sh/uv/) fetches the right Python for you, whatever is installed.
uv venv --python 3.13 .venv
source .venv/bin/activate                  # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt         # a few minutes
#   without uv: python3.13 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

python scripts/download_models.py --download
python scripts/download_models.py --check
```

Expected from `--check`:

```
Local model cache (./models/)
  OK       fastembed dense (bge-small-en-v1.5)
  OK       fastembed BM25 sparse (Qdrant/bm25)
  OK       Docling layout model
  OK       Docling TableFormer
  missing  GLM-OCR 0.9B (optional)

Status: READY for offline use
```

(GLM-OCR is optional, 2.5 GB; add `--glm` only if you want to try it.)

### Choose how the LLM will answer

You need **at least one** of these. Add more than one and the AI gateway **fails over** between them when one hits a limit (section 6). Change `.env`, then `docker compose up -d`.

| Option | Setup | Notes |
|---|---|---|
| **A. OpenRouter (recommended to start)** | Create a free account and a key at <https://openrouter.ai/keys> (no credit card), then `OPENROUTER_API_KEY=sk-or-v1-...` in `.env` | **Free models: 20 requests/minute and 50 requests/day** (1,000/day once the account holds $10 of credit). One question in the console uses about 5-9 requests (Track A one, the agent of Track B one per step), so 50/day is enough to try a handful of questions, not to run the evaluation with an LLM. The judge panel needs OpenCode Zen for two of its three judges |
| **B. OpenCode Zen** | `OPENCODE_API_KEY=` in `.env` (pay-as-you-go balance; default model `deepseek-v4.1-flash`) | What the speaker uses. The full 34-question evaluation of both tracks costs about $0.28. OpenCode's *free* models and the *Go* plan cannot be used through an API |
| **C. A speaker's shared gateway** | Only when a speaker runs one for the room: they give you a **virtual key**. In `.env` set `LITELLM_URL=http://<speaker-ip>:14000/v1` and `LITELLM_MASTER_KEY=<your virtual key>` | No provider account. The key works for **one model alias only** (`formation-fast`), with a small budget, a rate limit and an expiry. Other models answer *403*, too many requests *429*, an exhausted budget *422* |
| **D. Another free-tier provider** | Groq, Google AI Studio (Gemini) or Mistral: free key in `.env` (`GROQ_API_KEY`, `GEMINI_API_KEY`, `MISTRAL_API_KEY`), uncomment its block in `config/litellm_config.yaml` | One more rung of the failover ladder. Check the model id against the provider's list. See `docs/AI_GATEWAY_FAILOVER.md` |
| **E. Local model** | [LM Studio](https://lmstudio.ai) or Ollama, load a chat model, start its server; choose `formation-local` | No key, no limits; speed depends on your machine (a 27B model took 1-4 minutes per answer). It is also the last fallback of the default alias |
| **F. Nothing** | Leave `.env` as is | **Extractive mode**: instead of a generated answer you get the best retrieved passages, clearly labelled. The retrieval evaluation needs no LLM at all |


---

## 2. Stage 1: acquire the data

```bash
python scripts/scrape_syone.py
python scripts/download_hardware_manuals.py
```

**What you should see (scraper):** about two minutes of one line per page, then

```
Done: 79 pages kept (13 skipped as index/duplicate), 0 failed, 7 content images kept (28 sitewide images dropped)
```

**What to look at**

* `data/raw_syone_corp/about.md`: a real page converted to clean Markdown. Open `data/raw_syone_corp/_manifest.json` to see exactly what was scraped and what was skipped.
* `data/raw_syone_corp/partners-red-hat-premier-partner.md`: find the `## Frequently asked questions` section (the website's accordion FAQ turned into text).
* `data/extracted_images/syone_corp/`: only **4 informative images** survive out of 215 on the site. Open `syone-footprint-map.png` (the footprint map): a fact that exists only in the picture.
* `data/raw_hardware_manuals/`: 8 PDFs of a **fictional** product (Aurora AOR-3). Open `aor3_06_fault_code_reference.pdf`: one table with 30 fault codes.

If you are offline, skip the scraper: the repository already contains a dated snapshot. The golden questions were checked against that snapshot; if the website has changed since, `git checkout data/raw_syone_corp` restores it.

---

## 3. Stages 2 and 3: parse with Docling, compile to OKF

```bash
export HF_HOME=$PWD/models/huggingface       # Windows PowerShell: $env:HF_HOME="$PWD/models/huggingface"
python -m backend.ingestion.run_docling      # about 40 seconds
python -m backend.ingestion.run_okf
python scripts/validate_dataset.py
```

**What you should see**

```
✓ Docling parsing complete: 87 documents → data/docling_output
✓ OKF compilation complete: 87 OKF documents generated.
OKF store: 79 Syone documents, 8 hardware documents
[1] fault codes intact in the reference manual: 30/30
[2/3] golden questions verifiable against the store: 34/34
OK
```

**What to look at**

* `data/docling_output/hardware_manuals__aor3_06_fault_code_reference__standard.json`: the parser result: Markdown, `tables`, `images` (each figure with a caption and a **description**).
* `data/okf_store/hardware_manuals/aor3_04_network_switch_manual.md`: the YAML frontmatter at the top (type, entities, `related:` links, figures) followed by the document body.
* `data/okf_store/hardware_manuals/INDEX.md`: the entry point an agent reads first.

> **Why the description of a figure matters:** a language model never sees pixels. The description (what is *drawn* in the figure) is stored with it, so a question such as "which port carries the management VLAN?" can be answered from a diagram.

**Optional: the GLM-OCR engine** (a 0.9B vision-language model that reads a page image and writes Markdown). Two ways to run it:

| Backend | Command | Speed |
|---|---|---|
| **GPU via LM Studio (recommended)** | In LM Studio download `ggml-org/GLM-OCR-GGUF` (Q8_0 is fine), load it (identifier `glm-ocr`) and start the server (port 1234). Then `python -m backend.ingestion.run_docling --engine glm-ocr --glm-backend lmstudio --corpus hardware_manuals` | about **7 s per page**; all 8 manuals in about 9.5 minutes (Apple M4 Max) |
| CPU inside Docling | `... --engine glm-ocr --max-pages 1 --corpus hardware_manuals` (after `download_models.py --glm`) | about **6 minutes per page**: try one page only. Docling's Transformers engine cannot use the Apple GPU |

The output goes to `data/okf_store_glm_ocr/` (compile with `python -m backend.ingestion.run_okf --engine glm-ocr`); compare it with `data/okf_store/` (all 30 fault codes survive in both). Ollama works the same way with `--glm-backend ollama`.

---

## 4. Start the stack and index

```bash
docker compose up --build -d
docker compose ps
```

The first build takes a few minutes. When everything is up you should see 14 containers, with `neo4j`, `qdrant`, `backend` and the Langfuse databases `healthy`.

```bash
curl -s localhost:18000/api/health | python -m json.tool
```

The databases start **empty**: `qdrant_points` and `graph` are 0 and the UI header says *Not indexed yet*. Fill them:

```bash
python -m backend.graph_rag.indexer
```

```
Indexed corpus 'hardware_manuals': {'documents': 8,  'chunks': 720,  'qdrant_points': 720,  'graph': {'nodes': 90, 'relationships': 289}}
Indexed corpus 'syone_corp':       {'documents': 79, 'chunks': 1373, 'qdrant_points': 1373, 'graph': {'nodes': 140, 'relationships': 796}}
```

(About 40 seconds. Safe to re-run.) Refresh <http://localhost:13002>: the header now reads *Ready · 2093 chunks indexed*.

### Look inside the databases

| What | Where | Try |
|---|---|---|
| **Neo4j graph** | <http://localhost:17474> (login `neo4j` / `syone2026`) | `MATCH p=(c:ErrorCode)-[:IN_SUBSYSTEM\|INDICATED_BY\|AFFECTS]->(x) WHERE c.code IN ['0x4A7B','0x4A7C','0x8F11','0x8F02'] RETURN p` |
| **Qdrant vectors** | <http://localhost:16333/dashboard> → *Collections* → `syone_knowledge_hybrid` | open one point: its payload plus **two vectors**, `dense` (384 numbers) and `bm25` (sparse) |

![Neo4j graph of four fault codes, their subsystems and LED states](docs/screenshots/07_neo4j_graph.png)

Each blue node is a fault code read from the manual's table; beige nodes are subsystems; yellow nodes are the LED state each code produces. Note that two codes share `Solid red PWR`.

![Qdrant: one chunk with a dense and a BM25 vector](docs/screenshots/08_qdrant.png)

---

## 5. Ask questions: the two tracks side by side

Open <http://localhost:13002>. Pick a knowledge base, a model, and click one of the **featured scenarios**. Both tracks run at the same time.

The default model alias `formation-fast` follows the gateway's failover ladder; choose `formation-local` in the model selector only if you run a local model (option E).

![Home screen](docs/screenshots/01_home.png)

**How to read the two panels**

* **Track A (left):** how many chunks were retrieved; for **each chunk** its *dense rank*, *BM25 rank* and fused score (that tells you why it won); the graph entities used as facts; the answer.
* **Track B (right):** the agent's **trajectory**: each tool call and what it returned, the documents it opened in full, then the answer. The small badge says `llm_tool_calling` (a model chose the tools) or `scripted_navigation` (fallback when no tool-calling model is reachable).
* An amber banner means the answer is **extractive**: the LLM could not be reached and you are seeing retrieved passages.
* Figures cited in an answer are shown inline; click one to enlarge it.

### Scenarios to run (all have verified answers in the golden set)

| Scenario | Knowledge base | What to observe |
|---|---|---|
| **BM25 exact match**: *root cause and remediation for `0x4A7B_VRM_OVERVOLT`* | Aurora | Track A: the fault-table row is the top chunk (dense rank 1 and BM25 rank 1 for this question; with a bare code the ranks are more mixed, see notebook 2). Track B: `grep_okf("0x4A7B_VRM_OVERVOLT")` finds it in two documents |
| **Near-duplicate codes**: `0x4A7C` vs `0x4A7B` | Aurora | The two codes differ by one character. Compare the dense and BM25 ranks of their chunks |
| **Visual: LED legend**: *what does a blinking amber PWR LED mean?* | Aurora | The answer should cite figure F2. Read the nuance: ten codes share that LED, so the SEL code decides |
| **Text inside a diagram**: *which port carries out-of-band management?* | Aurora | `MGMT0` / `MGMT_VLAN_102` appear in the port-map figure's description |
| **Real website: footprint map** | Syone | The answer comes from the map's description; the map is shown |
| **Real website: FAQ** | Syone | Zabbix partner status from the partner page |
| **Multi-hop graph**: *which monitoring tools and which official partnerships?* | Syone | Compare how each track gathers evidence from several pages |
| **Unanswerable**: *Syone's revenue in 2030* | Syone | A good answer says it does not know. Watch for invented numbers |

![BM25 exact match scenario](docs/screenshots/02_bm25_exact.png)

![LED legend scenario with the figure cited](docs/screenshots/03_led_legend.png)

![Footprint map scenario](docs/screenshots/04_footprint_map.png)

### Free model explorer
<http://localhost:13002/models> lists the free OpenRouter models available **right now**, by context window, with vision and tool-calling flags. The four `formation-*` aliases at the top are stable names that the gateway maps to real models (`config/litellm_config.yaml`).

![Free model explorer](docs/screenshots/06_models.png)

---

## 6. Notebooks, evaluation, and observability

### Notebooks
```bash
jupyter lab --notebook-dir=notebooks --port 18888 --IdentityProvider.token=syone2026
```
Run them in order. Set `FORMATION_MODEL=formation-local` in the environment before starting Jupyter if you use option B.

| # | Notebook | Do this |
|---|---|---|
| 1 | Docling → OKF | See what each stage keeps; find a table row and a figure binding |
| 2 | Indexing | Compare dense, BM25 and hybrid rank for the same query; write a Cypher query |
| 3 | OKF agent | Call the four tools by hand, then let a model drive them |
| 4 | Gateway + tracing | Probe every model alias; read the Langfuse trace of your own question |
| 5 | Evaluation | Score both tracks on the 34 golden questions; run the prompt-optimization loop |

### Evaluation
Open <http://localhost:13002/eval>. Choose **retrieval only (no LLM)**, track A, click *Run benchmark*:

![Retrieval evaluation](docs/screenshots/05_eval_retrieval.png)

*Expected doc retrieved* and *Facts in context* tell you whether the right evidence reached the generator **before** any LLM is involved. Try track B and compare: which categories does each track miss? Then try *full* mode on the **demo slice (8)** (needs an LLM) and tick **Judge panel (3 LLMs)**: three models of different families grade each answer against the reference and give a reason. Find a question where a judge disagrees with the keyword verdict, or with another judge, and read the answer yourself: who is right? (The judges are gateway aliases of their own: on the speaker's shared gateway your virtual key must include them, otherwise a judge shows *no verdict*.) From a terminal: `python scripts/run_eval.py --mode retrieval` or `--mode full --model formation-local`.

### Observability
| What | Where | Look for |
|---|---|---|
| **Traces** | <http://localhost:13000> (`syone@syone.com` / `syone2026`) → project *Enterprise GenAI Formation* → *Traces* | One trace per gateway call: prompt, answer, tokens, latency. Evaluation scores appear as traces named `eval:...` |
| **Metrics** | <http://localhost:13001> (`syone` / `syone2026`) → Dashboards → *GenAI Formation* | Request rate, p95 latency, tokens, fallbacks; questions per minute by track |
| **Targets** | <http://localhost:19090/targets> | `litellm-gateway` and `syone-backend` both `UP` |

![Langfuse traces](docs/screenshots/09_langfuse_traces.png)

### Failover: what the gateway does when a provider hits its limit

This is the main reason to run an AI gateway. Free tiers are capped, providers have outages: the gateway absorbs it so your application never notices. Three layers, all in `config/litellm_config.yaml`:

1. **Deployments in order:** several entries named `formation-fast` with `order: 1, 2, 3...`; a failed call is retried on the next one.
2. **Cooldown:** a deployment that returned 429/5xx is skipped for 30 s, so later calls do not waste time on it.
3. **Alias fallbacks:** if the whole alias fails, try another alias: `formation-fast` → `formation-reasoning` → `formation-local`.

**Try it safely** (no quota used): the alias `formation-failover-drill` has a primary deployment pointing at a closed port and a secondary that answers.

```bash
for i in 1 2 3; do
  curl -s -i localhost:14000/v1/chat/completions \
    -H 'Authorization: Bearer sk-syone-formation-master-key' -H 'content-type: application/json' \
    -d '{"model":"formation-failover-drill","messages":[{"role":"user","content":"hi"}]}' \
  | grep -iE 'x-litellm-attempted|x-litellm-response-duration|SERVED'
done
```

You should see: call 1 `attempted-fallbacks: 1` (tried the dead primary, then the secondary served it); calls 2 and 3 much faster (the primary is in **cooldown** and is not even tried). Notebook 4, section 3, prints this as a table. Then watch the **Failover** panel in Grafana count provider failures and successful fallbacks, and check in Langfuse which underlying model answered each call.

![Grafana: gateway operations and failover counters](docs/screenshots/10_grafana.png)

**Your turn:** add a second provider to `formation-fast` (see `docs/AI_GATEWAY_FAILOVER.md`), break the first one on purpose with a wrong key, and keep asking questions in the UI: the answers keep coming.

**Virtual keys (try it on your own gateway):** `python scripts/create_trainee_key.py --budget 0.02 --rpm 3` mints a restricted key. Call the gateway with it: `formation-fast` answers; `formation-reasoning` returns *403*; the 4th request within a minute returns *429*; once the $0.02 is spent you get *422 Budget has been exceeded*. Notebook 4, section 3b, runs exactly this.



---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| UI header says *Databases not reachable* | Containers still starting | `docker compose ps`; wait for `neo4j` to be healthy (about 30 s) |
| Header says *Not indexed yet* | The databases start empty | `python -m backend.graph_rag.indexer` |
| Amber banner: *No LLM answer: gateway HTTP 401 ... User not found* | `.env` still has the placeholder key | Add a real OpenRouter key, then `docker compose up -d`; or use `formation-local` |
| Amber banner: *HTTP 429* | Per-minute limit, or **`free-models-per-day`** (the 50 requests/day cap of a free OpenRouter account) on **every** configured provider | The gateway already retries and fails over; if the banner still shows, all rungs are exhausted: add a second provider (option B), use a local model (C), use *retrieval only* in the evaluation page, or add $10 of credit to lift the OpenRouter cap |
| Amber banner: *gateway unreachable* | LiteLLM container not running | `docker compose logs litellm` |
| `formation-local` fails | Local server not running | Start LM Studio's server (port 1234) or Ollama; Ollama needs `api_base: http://host.docker.internal:11434/v1` in the gateway config |
| Agent track shows `scripted_navigation` | The model does not support tool calling | Pick a model with `supports_tools` in the model explorer |
| `docker compose up` fails on a port | Another service uses 13000, 13001, 13002, 14000, 16333, 17474, 17687, 18000 or 19090 | Stop it or edit the port mapping in `docker-compose.yml` |
| `AttributeError: 'NoneType' object has no attribute 'warning'` printed after a GLM-OCR run | Docling's cleanup message at interpreter exit | Harmless: the parse already finished (measured: about 6 minutes for one page on a laptop CPU) |
| Parsing is slow the first time | Models loading from disk | Run `scripts/download_models.py --download` beforehand |
| `ModuleNotFoundError: backend` | Wrong directory | Run commands from the repository root |
| Scraper cannot reach syone.com | Offline / blocked | Use the committed snapshot and skip the scraper |
| Langfuse login page loops | Containers still initialising | `docker compose logs langfuse-server`; wait until it prints `Ready` |
| Qdrant `Failed to obtain server version` warning | Harmless version-check message | Ignore |

Reset everything (deletes the databases): `docker compose down -v`.

## 8. Challenges (after the session)

1. Add a **ninth manual** of your own and a golden question about it; run `scripts/validate_dataset.py`.
2. Make Track A answer *"which codes does the AS-100G switch raise?"* correctly: inspect the graph with Cypher first.
3. Add a new gateway alias `formation-cheap` pointing at another free model and watch the fallback ladder in the Langfuse traces.
4. Replace the rule-based entity extractor with an LLM-based one for the Syone corpus and compare the graphs.
5. Re-scrape syone.com with `--max-blog 60`; which golden questions break, and why?
