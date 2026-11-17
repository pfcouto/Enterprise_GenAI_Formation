#!/usr/bin/env python3
"""
Generates the five formation notebooks into notebooks/.
Edit the cell lists below, run `python scripts/generate_notebooks.py`, commit the .ipynb files.
Validate end to end with: scripts/run_notebooks.sh   (executes every notebook headless).
"""

import json
from pathlib import Path

OUT = Path(__file__).parent.parent / "notebooks"
OUT.mkdir(parents=True, exist_ok=True)


_n = [0]


def _id():
    _n[0] += 1
    return f"cell{_n[0]:04d}"


def md(text):
    return {"id": _id(), "cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(keepends=True)}


def code(text):
    return {"id": _id(), "cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": text.strip("\n").splitlines(keepends=True)}


def write(name, cells):
    nb = {"cells": cells, "nbformat": 4, "nbformat_minor": 5,
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                       "language_info": {"name": "python"}}}
    (OUT / name).write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", name)


SETUP = '''
import os, sys, json, asyncio, time, logging
from pathlib import Path
ROOT = Path("..").resolve()
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)                                   # every path below is relative to the project root
os.environ.setdefault("HF_HOME", str(ROOT / "models" / "huggingface"))
logging.getLogger("neo4j").setLevel(logging.ERROR)
MODEL = os.getenv("FORMATION_MODEL", "formation-fast")   # use "formation-local" if you run LM Studio / Ollama
'''

# ------------------------------------------------------------------------------------------------ 01
write("01_docling_to_google_okf.ipynb", [
    md("""
# Module 1 - From raw files to a Google OKF knowledge base

```
data/raw_syone_corp/        <- scraped web pages (Markdown)         \\
data/raw_hardware_manuals/  <- 8 PDF manuals with tables + figures   /  Stage 1: acquisition
        |  Docling  (layout model + TableFormer tables + OCR)
data/docling_output/        <- Stage 2: structured JSON (markdown, tables, figures)
        |  OKF compiler (frontmatter, entities, related links, INDEX.md)
data/okf_store/             <- Stage 3: the knowledge base both retrieval tracks use
```
Run the cells in order and **read the outputs**: the point of this module is to see what each stage keeps and what it loses.
"""),
    code(SETUP + '''
from backend.ingestion.docling_parser import DoclingDocumentParser
print("project root:", ROOT)
'''),
    md("## 1. What did the acquisition scripts produce?"),
    code('''
manifest = json.loads((ROOT / "data/raw_syone_corp/_manifest.json").read_text())
print(f"Syone website: scraped {manifest['scraped_at'][:10]} from {manifest['source']}")
print(f"  {manifest['pages_ok']} pages kept, {manifest.get('pages_skipped', 0)} skipped (index/duplicates), "
      f"{manifest['pages_failed']} failed, {manifest['images']} informative images")
import collections
print("  pages per section:", dict(collections.Counter(p["section"] for p in manifest["pages"] if p["status"] == "ok").most_common(8)))
print()
for pdf in sorted((ROOT / "data/raw_hardware_manuals").glob("*.pdf")):
    print(f"  {pdf.name:45s} {pdf.stat().st_size/1024:6.0f} KB")
'''),
    md("## 2. Parse a scraped page (no OCR needed) and a PDF (needs Docling)"),
    code('''
parser = DoclingDocumentParser(ROOT / "data/extracted_images", ocr_engine="docling_standard")

page = parser.parse_document(ROOT / "data/raw_syone_corp/partners-zabbix-partner.md", corpus="syone_corp")
print("TITLE  :", page["title"]); print("SOURCE :", page["source_url"]); print("SECTION:", page["section"]); print("ENGINE :", page["ocr_engine_used"])
print(page["markdown_content"][:700])
'''),
    code('''
t0 = time.time()
doc = parser.parse_document(ROOT / "data/raw_hardware_manuals/aor3_06_fault_code_reference.pdf", corpus="hardware_manuals")
print(f"{doc['ocr_engine_used']}  |  {time.time()-t0:.0f}s  |  {len(doc['markdown_content']):,} chars  |  {len(doc['tables'])} tables  |  {len(doc['images'])} figures")
print()
row = next(l for l in doc["markdown_content"].splitlines() if "0x4A7B_VRM_OVERVOLT" in l and l.startswith("|"))
print("A fault-code table row, extracted from the PDF as a Markdown table row:\\n", row)
'''),
    md("""
### Check what the parser kept: tables and figures
Two things commonly get lost in PDF extraction: **table structure** (rows become loose text) and **figures** (images become `<!-- image -->`).
Here every figure is bound to its file through the caption line, and its *description* is stored next to it, so the words drawn **inside** the picture become searchable text.
"""),
    code('''
import pandas as pd
print("First extracted table as a DataFrame:")
display(pd.DataFrame(doc["tables"][0]).head(4))
for im in doc["images"]:
    print(f"\\n{im['figure_id']}: {im['caption']}\\n   path: {im['path']}\\n   description: {im['description'][:200]}...")
from IPython.display import Image, display
display(Image(filename=str(ROOT / "data/extracted_images/hardware_manuals" / doc["images"][0]["file"]), width=620))
'''),
    md("""
## 3. Why Docling standard, and not a vision model?

A newer option is a **vision-language model** that reads a page *image* and writes Markdown. We measured one, GLM-OCR (0.9B), through Docling's VLM pipeline on the 8 Aurora manuals (Apple M4 Max), then removed it from this repository:

| | Docling standard (used here) | GLM-OCR, served on the GPU by LM Studio |
|---|---|---|
| What it is | Layout model + TableFormer (tables) + RapidOCR | 0.9B vision-language model: page image in, Markdown out |
| Time, 8 manuals | **31 s** | **569 s** (18 times slower; about 6 min/page on the CPU) |
| Table rows recovered | 427 | 368 |
| Fault-code manual | 6 tables | 4: the continuation of the fault table on the next page is lost |
| Document titles | the real titles | the file name |

**Newer is not better by default: measure on your own documents.** Vision models earn their place on scans, formulas and hard layouts; for born-digital PDFs with tables, the classic pipeline wins here.
"""),
    md("## 4. Run the full pipeline: Docling -> JSON -> OKF\nThis cell calls exactly what the two pipeline scripts call: `python -m backend.ingestion.run_docling`, then `python -m backend.ingestion.run_okf`. The notebook is for seeing each stage; the scripts run it in one line."),
    code('''
from backend.ingestion.run_docling import run_docling_parsing
from backend.ingestion.run_okf import run_okf_compilation
logging.getLogger().setLevel(logging.WARNING)
n = run_docling_parsing("docling_standard", "all")
m = run_okf_compilation("docling_standard", "all")
print(f"parsed {n} documents, compiled {m} OKF files")
'''),
    code('''
okf = (ROOT / "data/okf_store/hardware_manuals/aor3_04_network_switch_manual.md").read_text()
print(okf.split("---")[1][:1800])           # the YAML frontmatter: type, entities, related links, figures
print("..."); print((ROOT / "data/okf_store/syone_corp/INDEX.md").read_text()[:900])   # the agent's entry point
'''),
    code('''
import subprocess
r = subprocess.run([sys.executable, "scripts/validate_dataset.py"], capture_output=True, text=True)
print(r.stdout)    # every fault code intact + every golden question answerable from this store
'''),
    md("""
### Exercises
1. Open `data/okf_store/hardware_manuals/aor3_06_fault_code_reference.md`. Find a code whose cell text was wrapped across lines in the PDF. Did the parser keep it in one piece? (`validate_dataset.py` checks all 30.)
2. Add a ninth PDF of your own to `data/raw_hardware_manuals/`, re-run section 4 and look at its `entities:` list.
3. Change `okf_compiler._related()` so that same-section documents score higher. How do the `related:` lists change?
"""),
])

# ------------------------------------------------------------------------------------------------ 02
write("02_graphrag_hybrid_neo4j_qdrant.ipynb", [
    md("""
# Module 2 - Index the OKF store: Qdrant (dense + BM25) and Neo4j (graph)

Start the stack first: `docker compose up --build -d`. The databases start **empty**: this notebook fills them.

| Question type | Dense vectors | BM25 | Graph |
|---|---|---|---|
| "my fan stopped spinning" (paraphrase) | good | weak | - |
| `0x4A7B_VRM_OVERVOLT` (exact token) | unreliable | excellent | - |
| "which codes light a solid red LED in the thermal subsystem?" (relations) | weak | weak | excellent |
"""),
    code(SETUP + '''
from backend.graph_rag.neo4j_client import Neo4jGraphClient
from backend.graph_rag.qdrant_hybrid import QdrantHybridStore
from backend.graph_rag.entity_extractor import EntityExtractor
from backend.graph_rag.chunker import chunk_okf_document, split_frontmatter
from backend.graph_rag.indexer import index_okf_store, build_chunks, okf_files
neo4j, qdrant = Neo4jGraphClient(), QdrantHybridStore()
print("Neo4j connected :", neo4j.driver is not None)
print("Qdrant ready    :", qdrant.ready, "(dense + BM25 models loaded)")
'''),
    md("## 1. Chunking that respects structure\nTables are split **one row per chunk** (prefixed by the column names), prose is packed up to ~900 characters, and each chunk keeps its heading path and the figures it mentions."),
    code('''
chunks = build_chunks("hardware_manuals")
print(len(chunks), "chunks in the hardware corpus;", len(build_chunks("syone_corp")), "in the Syone corpus")
row = next(c for c in chunks if c["kind"] == "table_row" and "0x4A7B_VRM_OVERVOLT" in c["text"])
print("\\nA table-row chunk:\\n", row["text"])
fig = next(c for c in chunks if c["images"])
print("\\nA chunk that carries figures:", fig["section"], "->", [i["figure_id"] for i in fig["images"]])
'''),
    md("## 2. Entities and relationships for the graph\nRule-based and **data-driven**: the facts (cause, remediation, LED state) are read from the document tables, not hard-coded."),
    code('''
ex = EntityExtractor().extract_from_okf_file(ROOT / "data/okf_store/hardware_manuals/aor3_06_fault_code_reference.md")
print(len(ex["nodes"]), "nodes,", len(ex["relationships"]), "relationships from one document")
code_node = next(n for n in ex["nodes"] if n["id"] == "code:0x4A7B")
print(json.dumps(code_node, indent=1))
print([ (r["type"], r["target"]) for r in ex["relationships"] if r["source"] == "code:0x4A7B"])
'''),
    md("## 3. Index everything (idempotent: safe to re-run)\nThe same as `python -m backend.graph_rag.indexer` in a terminal."),
    code('''
t0 = time.time()
report = index_okf_store(neo4j, qdrant)
print(json.dumps(report, indent=1)); print(f"{time.time()-t0:.0f}s")
'''),
    md("## 4. Explore the graph with Cypher  (also open http://localhost:17474, login neo4j / syone2026)"),
    code('''
import pandas as pd
print("Node counts:"); display(pd.DataFrame(neo4j.stats()["nodes"]).T)
q = """MATCH (c:ErrorCode)-[:IN_SUBSYSTEM]->(:Subsystem {name:'Thermal'}), (c)-[:INDICATED_BY]->(l:LEDState)
       WHERE l.name CONTAINS 'Solid red' RETURN c.name AS code, c.severity AS severity, c.remediation AS remediation"""
display(pd.DataFrame(neo4j.run_cypher(q)))
'''),
    code('''
q = """MATCH (o:Organization)-[:PARTNERS_WITH]->(p:Partner)<-[:DESCRIBES]-(d:Document) RETURN p.name AS partner, p.tier AS tier, d.doc_id AS page ORDER BY partner"""
display(pd.DataFrame(neo4j.run_cypher(q)))
'''),
    md("""
## 5. Dense vs BM25 vs hybrid, with the ranks visible
`hybrid_search` returns the rank each method gave every chunk and the fused RRF score, so you can see *why* a chunk won.
"""),
    code('''
def show(query, corpus, k=4):
    print(f"\\nQUERY: {query}")
    for h in qdrant.hybrid_search(query, corpus=corpus, top_k=k):
        print(f"  RRF {h['hybrid_score']:.4f} | dense #{str(h['dense_rank']):>4} | bm25 #{str(h['bm25_rank']):>4} | {h['title'][:34]:34s} | {h['text'].split(chr(10),1)[1][:70]}")

show("0x4A7B_VRM_OVERVOLT", "hardware_manuals")             # the code appears in ~15 chunks: BM25 alone ranks the definition row ~12th; fusion lifts it into the top 5
show("the cooling unit stopped rotating", "hardware_manuals")  # no shared words with the manual ("fan", "tachometer"): dense carries it, BM25 is weak
show("error 0x8F01", "hardware_manuals")                      # a generic word ("error") drags BM25 towards unrelated chunks: noise is real
show("0x4A7B", "hardware_manuals")                            # prefix only: works because we also index the split form of every code
'''),
    md("""
### What the ranks tell you
* **Exact identifier** (`0x4A7B_VRM_OVERVOLT`): the code is mentioned in about 15 chunks across 8 manuals, so BM25 returns *all of them* (the definition row is not necessarily first by BM25 alone). Dense vectors know which chunk is the *definition*. Reciprocal Rank Fusion lets each method vote: the table row (BM25 #12, dense #2 when this was written) comes out 2nd, inside the 5 chunks the model reads. With the full question ("What is the root cause ... for 0x4A7B_VRM_OVERVOLT?", as in the web UI) the table row is rank 1 for both methods.
* **Paraphrase** with no shared words: BM25 has nothing to match; dense finds the fan chunks.
* **Generic words hurt BM25**: `error 0x8F01` also matches every chunk containing "error". Stop-word lists and query rewriting exist for this reason.

### Near-duplicate codes: the hard case
`0x4A7B_VRM_OVERVOLT` (54.2 V, critical) vs `0x4A7C_VRM_UNDERVOLT` (40.5 V, major). Embeddings see them as almost the same text.
"""),
    code('''
show("0x4A7C_VRM_UNDERVOLT", "hardware_manuals", k=3)
show("Which fault means the busbar dropped below 40.5 V?", "hardware_manuals", k=3)
'''),
    md("""
### Exercises
1. Query `show("0x4A7B_VRM_OVERVOLT", ...)` after replacing the BM25 sparse vector with a zero vector (hint: comment out the `bm25` prefetch in `qdrant_hybrid.py`). Which queries break?
2. Write a Cypher query that returns every code raised by the `AS-100G switch` component and the LED each one shows.
3. Add a new `Event` alias to `backend/ingestion/knowledge.py`, re-index, and find the new nodes in the Neo4j browser.
"""),
])

# ------------------------------------------------------------------------------------------------ 03
write("03_langchain_deep_agents_okf.ipynb", [
    md("""
# Module 3 - Google OKF: let an agent navigate the knowledge base

No chunking, no embeddings, no index. The knowledge base is a folder of Markdown files with YAML frontmatter, and the
model gets four tools - the same verbs you would use in a terminal:

| Tool | Terminal analogue |
|---|---|
| `list_okf_topics` | `ls` + reading the frontmatter summaries |
| `grep_okf` | `grep -rn` |
| `read_okf_document` | `cat` (the **whole** file) |
| `follow_related_links` | opening the cross-links in the frontmatter |

You need a tool-calling LLM for the real agent (free OpenRouter key, or LM Studio with `FORMATION_MODEL=formation-local`).
Without one, the scripted navigator below still shows the same tools in action.
"""),
    code(SETUP + '''
from backend.okf_agents import tools
from backend.okf_agents.deep_agent_harness import OKFDeepAgentHarness
from backend.okf_agents.pipeline import OKFAgentPipeline
from backend.graph_rag.pipeline import GraphRAGPipeline
from backend.graph_rag.neo4j_client import Neo4jGraphClient
from backend.graph_rag.qdrant_hybrid import QdrantHybridStore
print("tools:", [t["function"]["name"] for t in tools.TOOL_SCHEMAS])
'''),
    md("## 1. The tools by hand"),
    code('''
topics = tools.list_okf_topics("hardware_manuals")
for t in topics[:3]: print(f"{t['doc_id']:36s} {t['type']:18s} {t['summary'][:70]}")
print()
for h in tools.grep_okf("hardware_manuals", "0x4A7B_VRM_OVERVOLT"): print(h["doc_id"], h["match_count"], "matches; first:", h["matches"][0]["text"][:90])
doc = tools.read_okf_document("hardware_manuals", "aor3_02_power_shelf_manual")
print("\\nread whole document:", len(doc["content"]), "chars;", len(doc["images"]), "figures; related:", doc["related"])
'''),
    md("## 2. Scripted navigation (no LLM): same tools, fixed plan"),
    code('''
nav = OKFDeepAgentHarness("hardware_manuals").scripted_navigation("What does fault code 0x8F11_TEMP_CRIT mean?")
for s in nav["trajectory"]: print(f"{s['step']}. {s['action']}({s['args']}) -> {s['observation']}")
'''),
    md("## 3. The real agent: an LLM chooses the next tool call"),
    code('''
async def ask(q, corpus):
    r = await OKFAgentPipeline().execute_query(q, corpus=corpus, model_name=MODEL)
    print("agent_mode:", r["agent_mode"], "| answer_mode:", r["answer_mode"], "| latency:", r["latency_seconds"], "s")
    if r["llm_error"]: print("LLM problem:", r["llm_error"][:160])
    for s in r["agent_trajectory"]: print(f"  {s['step']}. {s['action']}({s['args']}) -> {s['observation']}")
    print("\\n" + r["answer"][:900]); return r

r = await ask("Which fault codes are critical and show a solid red PWR LED in the Thermal subsystem?", "hardware_manuals")
'''),
    md("## 4. Same question, both tracks"),
    code('''
graph = GraphRAGPipeline(Neo4jGraphClient(), QdrantHybridStore())
q = "Which monitoring and observability tools does Syone use, and which of them does it hold official partnerships for?"
a = await graph.execute_query(q, corpus="syone_corp", model_name=MODEL)
b = await OKFAgentPipeline().execute_query(q, corpus="syone_corp", model_name=MODEL)
for name, r in (("GraphRAG", a), ("OKF agent", b)):
    print(f"=== {name}: {r['latency_seconds']}s, {r['context_chars']:,} context chars, mode={r['answer_mode']}")
    print(r["answer"][:600], "\\n")
'''),
    md("""
## 5. Optional: the same idea with LangChain Deep Agents
`deepagents` adds planning, a virtual filesystem and sub-agents on top of the same tool-calling loop. Here we hand it our OKF tools.
(Needs a tool-calling model reachable through the gateway.)
"""),
    code('''
RUN_DEEPAGENTS = False
if RUN_DEEPAGENTS:
    from deepagents import create_deep_agent
    from langchain_openai import ChatOpenAI

    def list_okf_topics(corpus: str) -> list:
        """List all documents of an OKF corpus ('syone_corp' or 'hardware_manuals') with summaries."""
        return tools.run_tool(corpus, "list_okf_topics", {})
    def grep_okf(corpus: str, pattern: str) -> list:
        """Exact text search across all documents of the corpus."""
        return tools.grep_okf(corpus, pattern)
    def read_okf_document(corpus: str, doc_id: str) -> dict:
        """Read one whole document (frontmatter + body)."""
        return tools.read_okf_document(corpus, doc_id)

    from backend.llm import LITELLM_URL, LITELLM_MASTER_KEY          # gateway URL + key from .env
    llm = ChatOpenAI(model=MODEL, base_url=LITELLM_URL, api_key=LITELLM_MASTER_KEY)
    agent = create_deep_agent(model=llm, tools=[list_okf_topics, grep_okf, read_okf_document],
                              system_prompt="Answer only from the OKF documents; quote codes exactly.")
    out = agent.invoke({"messages": [{"role": "user", "content": "What does fault 0x10E4_ECC_MULTI_BIT require the technician to do? Corpus: hardware_manuals"}]})
    print(out["messages"][-1].content)
else:
    print("Set RUN_DEEPAGENTS = True to run it.")
'''),
    md("""
## When to use which

| | GraphRAG + BM25 | OKF agent |
|---|---|---|
| Setup | Chunk, embed, extract entities, index | None: Markdown files are the index |
| Exact codes | Excellent (BM25) | Excellent (`grep`) |
| Multi-document questions | Needs the graph or luck in top-k | Natural: follow links, read whole documents |
| Cost per question | Low (a few chunks) | Higher (whole documents, several LLM calls) |
| Scales to | Millions of documents | Limited by context window and tool-call budget |
| Fails when | The needed chunk is not in top-k | The model does not find the right document |

Notebook 5 measures both on the same 34 questions.
"""),
])

# ------------------------------------------------------------------------------------------------ 04
write("04_litellm_langfuse_telemetry.ipynb", [
    md("""
# Module 4 - One AI gateway, free models, and tracing

**Anti-pattern:** every service calls a provider SDK with its own key and model name. When a free model disappears (it will) you edit five codebases.
**Gateway pattern:** every service calls `http://litellm:4000/v1` with an alias (`formation-fast`); the gateway holds keys, routes, retries, falls back and reports.

Open the gateway config next to this notebook: `config/litellm_config.yaml`.
"""),
    code(SETUP + '''
import httpx, base64
from backend.llm import chat, GatewayError
GATEWAY = os.getenv("LITELLM_URL", "http://localhost:14000/v1")
KEY = os.getenv("LITELLM_MASTER_KEY", "sk-syone-formation-master-key")
print("gateway:", GATEWAY)
'''),
    md("## 1. Which free models exist *right now*?\nThe list changes every few weeks, which is exactly why services use aliases."),
    code('''
import pandas as pd
r = httpx.get("http://localhost:18000/api/models/free", timeout=20).json()
print("source:", r["source"], "|", r["count"], "models")
df = pd.DataFrame(r["models"])[["id", "context_length", "supports_vision", "supports_tools"]]
display(df.head(12))
'''),
    md("## 2. Call every alias through the gateway"),
    code('''
async def probe(alias):
    t0 = time.time()
    try:
        m = await chat([{"role": "user", "content": "Reply with exactly: ready"}], alias, max_tokens=200, timeout=120)
        return alias, "OK", f"{time.time()-t0:.1f}s", (m.get("content") or "").strip()[:30]
    except GatewayError as e:
        return alias, "FAIL", f"{time.time()-t0:.1f}s", str(e)[:90]

rows = [await probe(a) for a in ("formation-fast", "formation-reasoning", "formation-vision", "formation-local")]
display(pd.DataFrame(rows, columns=["alias", "status", "time", "reply / error"]))
'''),
    md("""
### Reading the table
* `OK`: the alias works. `FAIL` with *User not found* = the OpenRouter key in `.env` is still the placeholder; `free-models-per-day` = the daily cap (see section 3).
* `formation-local` works only if LM Studio / Ollama is running on your machine.
* An alias can `FAIL` here only after **all** its failover layers (section 3) have failed.
"""),
    md("""
## 3. Failover: what a gateway is *for*
Free tiers hit limits (20 requests/minute and 50/day on OpenRouter without credit), providers have outages, models disappear. The gateway absorbs that so your application never notices. Three layers, all in `config/litellm_config.yaml`:

| Layer | Setting | What happens |
|---|---|---|
| 1. Deployments in order | several `model_name: formation-fast` entries with `order: 1, 2, 3...` | a failed call is retried on the next provider |
| 2. Cooldown | `allowed_fails: 1`, `cooldown_time: 30` | a deployment that returned 429/5xx is skipped for 30 s: later calls do not even try it |
| 3. Alias fallbacks | `fallbacks: formation-fast -> formation-reasoning -> formation-local` | the whole alias failed: try another model family, then a local model |

Proof without spending quota: the alias `formation-failover-drill` has a primary deployment pointing at a **closed port** (a simulated outage) and a secondary that answers. Call it three times and read the response headers.
"""),
    code('''
def drill():
    r = httpx.post(f"{GATEWAY}/chat/completions", headers={"Authorization": f"Bearer {KEY}"}, timeout=60,
                   json={"model": "formation-failover-drill", "messages": [{"role": "user", "content": "hi"}]})
    h = r.headers
    return {"status": r.status_code, "answer": r.json()["choices"][0]["message"]["content"][:48],
            "fallbacks": h.get("x-litellm-attempted-fallbacks"), "retries": h.get("x-litellm-attempted-retries"),
            "ms": round(float(h.get("x-litellm-response-duration-ms", 0)), 1)}
display(pd.DataFrame([drill() for _ in range(3)]))
'''),
    md("""
Read it: the **first** call tried the dead primary, failed and was served by the secondary (`fallbacks = 1`, slower). The **next** calls are fast because the dead deployment is in **cooldown** and was not even tried. After 30 seconds the gateway tries it again (self-healing).
Now the real chain: the default alias with every provider failing ends in the application's own safety net.
"""),
    code('''
try:
    await chat([{"role": "user", "content": "hi"}], "alias-that-does-not-exist", max_tokens=5, timeout=30)
except GatewayError as e:
    print("GatewayError ->", str(e)[:160])
print("\\nWhen EVERY layer fails, the pipelines return an EXTRACTIVE answer (retrieved passages, clearly labelled) instead of inventing text.")
'''),
    md("""
## 3b. Virtual keys: hand out access, not provider keys
A gateway issues its **own** keys, limited to chosen model aliases, with a budget, a rate limit and an expiry. The provider key (OpenCode, OpenRouter...) stays inside the gateway. This cell mints a throw-away key (needs the **admin** key in `LITELLM_MASTER_KEY`), uses it the way a trainee would, and deletes it.
"""),
    code('''
BASE = GATEWAY.rsplit("/v1", 1)[0]
admin = {"Authorization": f"Bearer {KEY}"}
g = httpx.post(f"{BASE}/key/generate", headers=admin, timeout=30,
               json={"key_alias": "nb4-demo", "models": ["formation-fast"], "max_budget": 0.02, "rpm_limit": 3, "duration": "1h"})
if g.status_code != 200:
    print("Needs the gateway ADMIN key in LITELLM_MASTER_KEY (a trainee virtual key cannot mint keys):", g.status_code)
else:
    vkey = g.json()["key"]
    def as_trainee(model):
        r = httpx.post(f"{GATEWAY}/chat/completions", headers={"Authorization": f"Bearer {vkey}"}, timeout=90,
                       json={"model": model, "messages": [{"role": "user", "content": "Reply: ok"}], "max_tokens": 20})
        return {"requested model": model, "HTTP": r.status_code, "meaning": {200: "answered", 403: "not allowed for this key", 429: "rate limit (3/min)", 422: "budget exceeded"}.get(r.status_code, "")}
    rows = [as_trainee(m) for m in ("formation-fast", "formation-reasoning", "openrouter/openai/gpt-4o")]
    rows += [as_trainee("formation-fast") for _ in range(3)]            # 1 + 3 requests in a minute: the limit is 3
    display(pd.DataFrame(rows))
    httpx.post(f"{BASE}/key/delete", headers=admin, json={"keys": [vkey]}, timeout=30)
    print("key deleted")
'''),
    md("## 4. Tracing: every call is a Langfuse trace\nOpen http://localhost:13000 - login `syone@syone.com` / `syone2026`, project *Enterprise GenAI Formation*."),
    code('''
auth = base64.b64encode(f"{os.getenv('LANGFUSE_PUBLIC_KEY','pk-lf-syone-public-key')}:{os.getenv('LANGFUSE_SECRET_KEY','sk-lf-syone-secret-key')}".encode()).decode()
resp = httpx.get("http://localhost:13000/api/public/traces?limit=5", headers={"Authorization": f"Basic {auth}"}, timeout=20)
print("Langfuse API status:", resp.status_code)
for t in resp.json().get("data", [])[:5]:
    print(f"  {t['timestamp'][:19]}  {t.get('name')}  latency={t.get('latency')}s  cost={t.get('totalCost')}")
'''),
    md("## 5. Metrics: Prometheus scrapes the gateway and the API\nGrafana (http://localhost:13001, syone / syone2026) draws them."),
    code('''
for metric in ("litellm_requests_metric_total", "syone_requests_total"):
    q = httpx.get("http://localhost:19090/api/v1/query", params={"query": f"sum({metric})"}, timeout=10).json()
    print(metric, "=", q["data"]["result"][0]["value"][1] if q["data"]["result"] else "no data yet (send some requests first)")
'''),
    md("""
### Exercises
1. Add a **second provider** to `formation-fast` (uncomment the Groq or Gemini block, put its free key in `.env`, `docker compose up -d --force-recreate litellm`). Then break the first deployment on purpose (wrong key) and watch the alias keep answering.
2. Edit the drill: put `cooldown_time: 5` and call it every 2 seconds for 20 seconds. Explain the pattern of `ms` and `fallbacks`.
3. Find your last chat in Langfuse. How many tokens did the OKF agent use compared to GraphRAG?
"""),
])

# ------------------------------------------------------------------------------------------------ 05
write("05_opik_prompt_optimizer_lab.ipynb", [
    md("""
# Module 5 - Evaluate, then optimize

You cannot improve what you do not measure. The golden set has **34 questions** (14 Syone, 20 Aurora) with expected keywords, expected documents and expected figures,
verified against the sources by `scripts/validate_dataset.py`.

Two evaluation modes:
* **retrieval** - no LLM: did the right documents and facts reach the generator? (instant, free, deterministic)
* **full** - generate the answer too; score facts, figure citation, refusals.
"""),
    code(SETUP + '''
import pandas as pd
from backend.evaluation.golden_dataset import GOLDEN_EVALUATION_DATASET as GOLD
from backend.evaluation.langfuse_evals import LLMJudgeEvaluator
from backend.evaluation.opik_optimizer import OpikPromptOptimizer
from backend.graph_rag.pipeline import GraphRAGPipeline
from backend.graph_rag.neo4j_client import Neo4jGraphClient
from backend.graph_rag.qdrant_hybrid import QdrantHybridStore
from backend.okf_agents.deep_agent_harness import OKFDeepAgentHarness
from backend.okf_agents.pipeline import OKFAgentPipeline
neo4j, qdrant = Neo4jGraphClient(), QdrantHybridStore()
graph, okf, ev = GraphRAGPipeline(neo4j, qdrant), OKFAgentPipeline(), LLMJudgeEvaluator()
df = pd.DataFrame(GOLD)
display(df.groupby(["corpus", "category"]).size().unstack(0).fillna(0).astype(int))
display(df[["id", "category", "question"]].head(6))
'''),
    md("## 1. Retrieval-only evaluation (no LLM, runs in seconds)"),
    code('''
def retrieval_eval(track):
    rows = []
    for item in GOLD:
        if track == "A: GraphRAG":
            ch = qdrant.hybrid_search(item["question"], corpus=item["corpus"], top_k=5)
            g = neo4j.query_graph_neighborhood(neo4j.extract_keywords(item["question"]), corpus=item["corpus"])
            docs, ctx = list(dict.fromkeys(c["doc_id"] for c in ch)), "\\n".join(c["text"] for c in ch) + g["formatted_context"]
        else:
            nav = OKFDeepAgentHarness(item["corpus"]).scripted_navigation(item["question"])
            docs, ctx = [d["doc_id"] for d in nav["collected_documents"]], "\\n".join(d["content"] for d in nav["collected_documents"])
        s = ev.evaluate_response(item, "", docs, ctx, "retrieval_only")
        rows.append({"id": item["id"], "category": item["category"], "track": track, "doc_found": s["retrieval_any_expected_doc"], "facts_in_context": s["context_keyword_recall"]})
    return pd.DataFrame(rows)

res = pd.concat([retrieval_eval("A: GraphRAG"), retrieval_eval("B: OKF scripted")])
res["ok"] = (res["doc_found"].fillna(True)) & (res["facts_in_context"].fillna(1) >= 0.6)
display(res.pivot_table(index="category", columns="track", values="ok", aggfunc="mean").round(2))
print("Overall:", res.groupby("track")["ok"].mean().round(3).to_dict())
'''),
    md("Which questions does each track miss? (Read the failures: that is where the learning is.)"),
    code('''
display(res[~res["ok"]][["id", "track", "category", "doc_found", "facts_in_context"]].sort_values("id"))
'''),
    md("## 2. Full evaluation (needs an LLM). Start small: 8 questions"),
    code('''
SUBSET = ["hw_001", "hw_002", "hw_003", "hw_007", "hw_010", "hw_020", "syone_002", "syone_014"]
async def full_eval(pipe, track):
    rows = []
    for item in [g for g in GOLD if g["id"] in SUBSET]:
        r = await pipe.execute_query(item["question"], corpus=item["corpus"], model_name=MODEL, include_context=True)
        s = ev.evaluate_response(item, r["answer"], r.get("retrieved_doc_ids"), r.get("context_text", ""), r["answer_mode"])
        rows.append({"id": item["id"], "track": track, "mode": r["answer_mode"], "passed": s["passed"], "keywords": s["found_keywords"],
                     "figure": s["visual_grounding_score"], "refusal_ok": s["refusal_ok"], "sec": r["latency_seconds"], "answer": r["answer"]})
    return pd.DataFrame(rows)

full = pd.concat([await full_eval(graph, "A: GraphRAG"), await full_eval(okf, "B: OKF agent")])
display(full.pivot(index="id", columns="track", values="passed"))
print(full.groupby("track")[["passed", "sec"]].agg({"passed": "mean", "sec": "mean"}).round(2))
if (full["mode"] == "extractive").any():
    print("\\nSome answers were extractive: the LLM gateway was not reachable (see notebook 4). They count as failed.")
'''),
    md("""
## 2b. LLM-as-a-judge: a panel of three
Keywords cannot tell a paraphrase from an error. A **judge** model reads the question, the reference answer and the candidate and returns a grade (0-1)
and a reason. One judge is just another model with its own biases, so three families grade the same Track A answers from section 2:
`formation-judge-deepseek` (the model that wrote the answers: watch for self-preference), `formation-judge-haiku` (Claude Haiku 5.5) and
`formation-judge-nemotron` (free, 50 requests/day). The judges are reasoning models: they think before they grade, so each grade takes a few seconds.
"""),
    code('''
from backend.evaluation.langfuse_evals import JUDGE_PANEL
rows = []
for _, r in full[(full["track"] == "A: GraphRAG") & (full["mode"] == "generated")].iterrows():
    item = next(g for g in GOLD if g["id"] == r["id"])
    panel = await ev.judge_panel(item, r["answer"])
    rows.append({"id": r["id"], "keywords_pass": r["passed"],
                 **{j.replace("formation-judge-", ""): (v["score"] if v else None) for j, v in panel["judges"].items()},
                 "spread": panel["judge_spread"]})
    for j, v in panel["judges"].items():
        print(f"{r['id']:10s} {j.replace('formation-judge-', ''):9s} {v['score'] if v else '-':>5}  {v['reason'][:110] if v else 'no verdict'}")
judged = pd.DataFrame(rows)
display(judged)
'''),
    md("Read the rows where a judge and the keyword verdict disagree, and where the judges disagree with each other (`spread` 0.5 or more): sometimes the judge is right, sometimes the keyword list, and sometimes the judge is simply wrong. That is why you calibrate judges against a few answers graded by a human."),
    md("""
## 3. Optimize the prompt (a minimal version of what Opik's MetaPrompt / GEPA optimizers do)
Three prompt candidates are scored on the **real pipeline**; the best one wins. Opik's optimizers add an LLM that proposes and mutates candidates for you.
"""),
    code('''
opt = OpikPromptOptimizer(ev)
try:
    out = await opt.run_optimization_loop(graph, MODEL, ids=["hw_001", "hw_003", "hw_007", "hw_012", "syone_002", "syone_007"])
    for h in out["history"]: print(f"{h['variant']:28s} passed {h['passed']}")
    print("\\nbest:", out["best_variant"])
except Exception as e:
    print("Needs a working LLM:", e)
'''),
    md("""
### Going further with Opik itself (optional)
```python
pip install opik-optimizer           # then, with an Opik workspace key in .env (OPIK_API_KEY):
from opik_optimizer import MetaPromptOptimizer, ChatPrompt
```
Wrap `GraphRAGPipeline.execute_query` as the task function and `LLMJudgeEvaluator.evaluate_response` as the metric; see Opik's docs for the exact signatures of the release you installed.

### Exercises
1. Which category does Track A fail most in the retrieval table? Which does Track B? Why?
1. In section 2b, find an answer where the judges disagree. Read it yourself: who is right?
2. Add two golden questions of your own to `backend/evaluation/golden_dataset.py`; run `python scripts/validate_dataset.py` to confirm they are answerable.
3. Add a fourth prompt variant that asks for a one-sentence answer. Does the pass rate change?
"""),
])
