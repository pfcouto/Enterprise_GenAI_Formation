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
# Module 1 - From raw files to a knowledge base an agent can read

**The question of this notebook:** a company's knowledge sits in PDFs and web pages. What does it take to turn them into text a
retrieval system (or an agent) can use, *without losing the tables and the figures*?

We go through three stages, and look at what each one keeps:

```
Stage 1  data/raw_syone_corp/         79 pages scraped from syone.com (Markdown)      already done, committed
         data/raw_hardware_manuals/   8 PDF manuals of a fictional server rack        already done, committed
            |  Docling: finds the layout, rebuilds the tables, reads text in images
Stage 2  data/docling_output/         one JSON per document: text, tables, figures     this notebook, section 4
            |  OKF compiler: adds a YAML header (type, entities, links, figures)
Stage 3  data/okf_store/              the knowledge base: Markdown files + INDEX.md     this notebook, section 4
```

**This notebook runs the real pipeline, not a copy of it.** Section 4 calls the same two functions as the command-line scripts
`python -m backend.ingestion.run_docling` and `python -m backend.ingestion.run_okf`. A notebook is for *seeing* each stage;
the scripts run it in one line (that is what you would schedule in production).

Run the cells from top to bottom (Shift+Enter). Everything is local: no model API, no internet. About one minute in total.
"""),
    md("""
### Setup
Loads the project's code and points every path at the project folder. Nothing is parsed yet.
"""),
    code(SETUP + '''
import warnings
warnings.filterwarnings("ignore")                 # keep the outputs readable: library warnings are not the lesson here
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
from backend.ingestion.docling_parser import DoclingDocumentParser
logging.getLogger().setLevel(logging.WARNING)      # hide Docling's progress logs
try:
    from transformers.utils import logging as hf_logging
    hf_logging.disable_progress_bar(); hf_logging.set_verbosity_error()
except ImportError:
    pass
print("project root:", ROOT)
'''),
    md("""
## 1. Stage 1: what are the raw files?

Two knowledge bases, on purpose very different:
* **The Syone website**: 79 real pages, scraped once from syone.com and committed as a dated snapshot (a fresh scrape could
  change answers the evaluation expects). Web pages are already text, so they are the *easy* case.
* **The Aurora AOR-3 manuals**: 8 PDFs written for this course. Fictional, so every answer can be checked, and hard on
  purpose: big tables, codes that differ by one character, facts that exist only inside a figure.

**Look for:** how many pages were kept and skipped, and the 8 PDFs.
"""),
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
    md("""
## 2. Stage 2 on two documents: a web page, then a PDF

**Parsing** = turning a file into clean text *with its structure*: headings, tables, figures. It decides everything that
comes after: a fact the parser loses can never be found by any search or model.

First a web page. It is already Markdown, so no PDF engine is needed: the parser reads it and keeps its metadata.

**Look for:** `ENGINE: native-markdown`, and the page's title, source URL and section.
"""),
    code('''
parser = DoclingDocumentParser(ROOT / "data/extracted_images", ocr_engine="docling_standard")

page = parser.parse_document(ROOT / "data/raw_syone_corp/partners-zabbix-partner.md", corpus="syone_corp")
print("TITLE  :", page["title"]); print("SOURCE :", page["source_url"]); print("SECTION:", page["section"]); print("ENGINE :", page["ocr_engine_used"])
print(page["markdown_content"][:700])
'''),
    md("""
Now the hard case: a PDF. A PDF stores characters at positions on a page, not "a table with columns". **Docling**
(open source, IBM) rebuilds the structure with three models that run on this laptop:
* a **layout model** finds the blocks on each page (title, paragraph, table, picture, caption);
* **TableFormer** rebuilds each table: which cell belongs to which row and column;
* **OCR** (RapidOCR) reads text that is inside images.

We parse `aor3_06_fault_code_reference.pdf`: 30 fault codes in one big table that continues on the next page.

**Look for:** the number of tables and figures found, and one row of the fault table printed back as a Markdown row:
code, subsystem, severity, LED, cause, fix, each in its own column. If the table had been flattened into a paragraph,
"54.2 V" would no longer be attached to "0x4A7B".
"""),
    code('''
t0 = time.time()
doc = parser.parse_document(ROOT / "data/raw_hardware_manuals/aor3_06_fault_code_reference.pdf", corpus="hardware_manuals")
print(f"{doc['ocr_engine_used']}  |  {time.time()-t0:.0f}s  |  {len(doc['markdown_content']):,} chars  |  {len(doc['tables'])} tables  |  {len(doc['images'])} figures")
print()
row = next(l for l in doc["markdown_content"].splitlines() if "0x4A7B_VRM_OVERVOLT" in l and l.startswith("|"))
print("A fault-code table row, extracted from the PDF as a Markdown table row:\\n", row)
'''),
    md("""
### What the parser kept: tables and figures

Two things usually get lost when a PDF becomes text:
* **table structure**: rows become loose words. Here each table is also kept as data (below, as a table with its columns);
* **figures**: an image becomes `<!-- image -->` and its content is gone. Here every figure is bound to its file through
  its caption, and a **text description** is stored with it.

Why a description? The models that answer questions later are *text* models: **they never see pixels**. What is drawn
in a figure (an LED legend, a port map) becomes searchable only if it is written down. In this course the descriptions
were written by hand; in production a vision model writes them at ingestion time.

**Look for:** the first table with its columns; the two figures (F2, the LED legend, and F6, a flowchart) with their
captions and descriptions; then the F2 picture itself.
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
    md("""
## 4. Stages 2 and 3 for all 87 documents

This cell is the whole pipeline. It calls exactly what the two scripts call:

| This cell | The same as, in a terminal | Reads | Writes |
|---|---|---|---|
| `run_docling_parsing(...)` | `python -m backend.ingestion.run_docling` | `data/raw_*/` | `data/docling_output/*.json` (Stage 2) |
| `run_okf_compilation(...)` | `python -m backend.ingestion.run_okf` | `data/docling_output/` | `data/okf_store/<corpus>/*.md` + `INDEX.md` (Stage 3) |

Re-running it is safe: it overwrites the same files. About 30 seconds.

**Look for:** `parsed 87 documents, compiled 87 OKF files` (79 web pages + 8 manuals). Open `data/okf_store/` in the file
explorer and watch it fill.
"""),
    code('''
from backend.ingestion.run_docling import run_docling_parsing
from backend.ingestion.run_okf import run_okf_compilation
t0 = time.time()
n = run_docling_parsing("docling_standard", "all")
m = run_okf_compilation("docling_standard", "all")
print(f"parsed {n} documents, compiled {m} OKF files in {time.time()-t0:.0f}s")
'''),
    md("""
### Stage 2 output: what Docling hands to the compiler

One JSON file per document. **Look for:** the fields: the full text as Markdown, the tables as data, the figures with their
descriptions, and which engine parsed it and how long it took.
"""),
    code('''
stage2 = json.loads((ROOT / "data/docling_output/hardware_manuals__aor3_06_fault_code_reference__standard.json").read_text())
print(len(list((ROOT / "data/docling_output").glob("*.json"))), "JSON files in data/docling_output/\\n")
for k, v in stage2.items():
    shown = f"{len(v)} items" if isinstance(v, list) else (f"{len(v):,} characters" if isinstance(v, str) and len(v) > 80 else repr(v))
    print(f"  {k:18s} {shown}")
'''),
    md("""
### Stage 3 output: an OKF file

**OKF, the Open Knowledge Format** (Google Cloud, June 2026, v0.1, a proposal): a knowledge base is a **folder of Markdown
files**, each starting with a short **YAML header** ("frontmatter"); only `type` is required; links between files make the
folder a graph. A person can read it, git can diff it, an agent can navigate it.

The header our compiler writes, field by field:

| Field | What it is | Who uses it |
|---|---|---|
| `type` | the kind of document (`service_manual`, `corporate_overview`...) | the agent, to pick documents |
| `title`, `summary` | what the document is about, in a sentence | `INDEX.md`, the agent's first look |
| `entities` | the codes, products and names found in it | search; the graph in session 2 |
| `related` | links to the documents it refers to or shares entities with | the agent follows them (session 2) |
| `images` | each figure: file, caption, **description** | figures become searchable text |

Below the header is the document itself, as Markdown. Then **`INDEX.md`**: one line per document, the agent's entry point.

**Look for:** the header of the network switch manual (its entities are fault codes and products; its related documents;
its two figures), then the first lines of the index. Open the same file in the editor:
`data/okf_store/hardware_manuals/aor3_04_network_switch_manual.md`.
"""),
    code('''
okf = (ROOT / "data/okf_store/hardware_manuals/aor3_04_network_switch_manual.md").read_text()
print(okf.split("---")[1][:1800])           # the YAML frontmatter: type, entities, related links, figures
print("..."); print((ROOT / "data/okf_store/syone_corp/INDEX.md").read_text()[:900])   # the agent's entry point
'''),
    md("""
## 5. Test the data before you test the model

A pipeline can fail silently. Real example from building this course: Docling writes underscores escaped
(`0x4A7B\\_VRM_OVERVOLT`), so an exact search for the code finds nothing, and no error is raised anywhere. The parser now
undoes that, and `scripts/validate_dataset.py` checks the store every time:
1. all **30 fault codes** of the reference manual are intact in the OKF store;
2. all **34 golden questions** (the evaluation of session 3) can be answered from the store: their expected facts are there.

**Look for:** `30/30`, `34/34` and `OK`. Same as running `python scripts/validate_dataset.py` in a terminal.
"""),
    code('''
import subprocess
r = subprocess.run([sys.executable, "scripts/validate_dataset.py"], capture_output=True, text=True)
print(r.stdout)    # every fault code intact + every golden question answerable from this store
'''),
    md("""
## What we have now

* 87 documents, parsed with their tables and figures, compiled into an OKF knowledge base (`data/okf_store/`), and checked.
* Nothing has been indexed and no model has been called yet.

**Next (notebook 02):** two ways to search this store. Track A chunks it and indexes it (Qdrant for dense + BM25 search,
Neo4j for a knowledge graph). Track B uses the OKF folder *as it is*: an agent reads `INDEX.md`, greps and opens files.

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

**EN.** Session 1 turned the raw documents into OKF files (`data/okf_store/`). This notebook **indexes** them in two databases, the way Track A (GraphRAG + hybrid search) will use them:

```
data/okf_store/*.md ──► chunks ──┬──► Qdrant: 2 vectors per chunk (dense = meaning, BM25 = exact words)
                                 └──► Neo4j : entities + relationships (the graph)
```

Then it tests the three kinds of question below, **with the evidence printed**: which method finds the right chunk, and which one fails.

**PT.** Na sessão 1 transformámos os documentos em ficheiros OKF (`data/okf_store/`). Este notebook **indexa-os** em duas bases de dados, tal como o Track A (GraphRAG + hybrid search) as vai usar: cada chunk vai para o Qdrant com dois vetores (dense = significado, BM25 = palavras exatas) e as entidades e relações vão para o Neo4j (o grafo). Depois testamos os três tipos de pergunta da tabela, **com a prova impressa**: que método encontra o chunk certo e qual falha.

| Question type / Tipo de pergunta | Dense | BM25 | Graph | Shown in / Onde se vê |
|---|---|---|---|---|
| Paraphrase: "my fan stopped spinning" | good | weak | - | section 5b |
| Exact token: `FM4`, `0x4A7B_VRM_OVERVOLT` | unreliable | excellent | - | sections 5a, 5c |
| Relations: "which thermal codes light a solid red LED?" | weak | weak | excellent | section 4 |

Run it cell by cell (Shift+Enter). If the databases are already full, section 3 simply rebuilds them (it is idempotent).
*Corre célula a célula (Shift+Enter). Se as bases de dados já estiverem cheias, a secção 3 reconstrói-as (é idempotente).*
"""),
    code(SETUP + '''
import warnings; warnings.filterwarnings("ignore")
logging.getLogger("httpx").setLevel(logging.WARNING)          # hide one log line per Qdrant request
from backend.graph_rag.neo4j_client import Neo4jGraphClient
from backend.graph_rag.qdrant_hybrid import QdrantHybridStore
from backend.graph_rag.entity_extractor import EntityExtractor
from backend.graph_rag.chunker import chunk_okf_document, split_frontmatter
from backend.graph_rag.indexer import index_okf_store, build_chunks, okf_files
neo4j, qdrant = Neo4jGraphClient(), QdrantHybridStore()
print("Neo4j connected :", neo4j.driver is not None)
print("Qdrant ready    :", qdrant.ready, "(dense + BM25 models loaded)")
'''),
    md("""
**Result / Resultado.** Two `True`: the notebook talks to both databases running in Docker, and the two models that turn text into vectors are loaded locally (`bge-small-en-v1.5` for dense, a BM25 tokenizer for sparse).
*Dois `True`: o notebook fala com as duas bases de dados no Docker, e os dois modelos que transformam texto em vetores estão carregados localmente.*

## 1. Chunking that respects structure / Chunking que respeita a estrutura

**EN.** A model reads only a few chunks (we give it 5), so *how* we cut the documents decides what it can see. Tables are split **one row per chunk**, prefixed with the column names; prose is packed up to ~900 characters; each chunk keeps its heading path and the figures it mentions.

**PT.** O modelo só lê alguns chunks (damos-lhe 5), por isso *a forma como cortamos* os documentos decide o que ele consegue ver. As tabelas são cortadas **uma linha por chunk**, com o nome das colunas à frente; o texto corrido é agrupado até ~900 caracteres; cada chunk guarda o caminho de títulos e as figuras que menciona.
"""),
    code('''
chunks = build_chunks("hardware_manuals")
print(len(chunks), "chunks in the hardware corpus;", len(build_chunks("syone_corp")), "in the Syone corpus")
row = next(c for c in chunks if c["kind"] == "table_row" and "0x4A7B_VRM_OVERVOLT" in c["text"])
print("\\nA table-row chunk:\\n", row["text"])
fig = next(c for c in chunks if c["images"])
print("\\nA chunk that carries figures:", fig["section"], "->", [i["figure_id"] for i in fig["images"]])
'''),
    md("""
**Result / Resultado.**
* **EN.** 714 chunks for 8 manuals, 1,373 for 79 web pages. The table-row chunk reads `Quantity: Overvoltage protection cutoff | Threshold or value: 54.2 V | Related fault code: 0x4A7B_VRM_OVERVOLT`: the number **54.2** keeps its meaning because the column names travel with it. A splitter that cuts every 500 characters would separate the number from its header. The last line shows a chunk that carries its figures: when it is retrieved, the figure comes with it.
* **PT.** 714 chunks para 8 manuais, 1.373 para 79 páginas web. O chunk da linha de tabela diz `Quantity ... 54.2 V ... 0x4A7B_VRM_OVERVOLT`: o número **54.2** mantém o significado porque os nomes das colunas vão com ele. Um splitter que corta a cada 500 caracteres separava o número do cabeçalho. A última linha mostra um chunk que leva as suas figuras: quando é encontrado, a figura vem junto.

## 2. Entities and relationships for the graph / Entidades e relações para o grafo

**EN.** From the same OKF file we extract *things* (fault codes, LED states, parts, subsystems) and the *relations* between them. Rule-based and **data-driven**: the facts are read from the document's tables, not hard-coded. In production an LLM extractor is the usual next step; the graph model stays the same.

**PT.** Do mesmo ficheiro OKF extraímos *coisas* (códigos de erro, estados de LED, peças, subsistemas) e as *relações* entre elas. É por regras e **guiado pelos dados**: os factos são lidos das tabelas do documento, não estão escritos no código. Em produção, o passo seguinte habitual é um extrator com LLM; o modelo do grafo mantém-se.
"""),
    code('''
ex = EntityExtractor().extract_from_okf_file(ROOT / "data/okf_store/hardware_manuals/aor3_06_fault_code_reference.md")
print(len(ex["nodes"]), "nodes,", len(ex["relationships"]), "relationships from one document")
code_node = next(n for n in ex["nodes"] if n["id"] == "code:0x4A7B")
print(json.dumps(code_node, indent=1))
print([ (r["type"], r["target"]) for r in ex["relationships"] if r["source"] == "code:0x4A7B"])
'''),
    md("""
**Result / Resultado.**
* **EN.** 68 nodes and 271 relationships from **one** manual. The node `0x4A7B` carries its subsystem, severity, LED, root cause and remediation as properties, and the last line lists its arrows: `IN_SUBSYSTEM` Power VRM, `INDICATED_BY` Solid red PWR, ... Each arrow is one cell of the fault table.
* **PT.** 68 nós e 271 relações a partir de **um** manual. O nó `0x4A7B` guarda o subsistema, a severidade, o LED, a causa e a remediação como propriedades, e a última linha lista as setas: `IN_SUBSYSTEM` Power VRM, `INDICATED_BY` Solid red PWR, ... Cada seta é uma célula da tabela de códigos.

## 3. Index everything / Indexar tudo

**EN.** For every chunk: compute the dense vector and the BM25 vector, store both in Qdrant; write the entities and relations to Neo4j. Idempotent: running it twice gives the same result. **This cell is exactly `python -m backend.graph_rag.indexer`** in a terminal (about 40 s).

**PT.** Para cada chunk: calcula o vetor dense e o vetor BM25 e guarda os dois no Qdrant; escreve as entidades e relações no Neo4j. É idempotente: correr duas vezes dá o mesmo resultado. **Esta célula é exatamente `python -m backend.graph_rag.indexer`** num terminal (cerca de 40 s).
"""),
    code('''
t0 = time.time()
report = index_okf_store(neo4j, qdrant)
print(json.dumps(report, indent=1)); print(f"{time.time()-t0:.0f}s")
'''),
    md("""
**Result / Resultado.**
* **EN.** Hardware: 8 documents, 714 chunks, 90 nodes, 289 relationships. Syone: 79 documents, 1,373 chunks, 137 nodes, 796 relationships. In total 2,087 points in Qdrant and 227 nodes / 1,085 relationships in Neo4j: the numbers in the console header.
* **PT.** Hardware: 8 documentos, 714 chunks, 90 nós, 289 relações. Syone: 79 documentos, 1.373 chunks, 137 nós, 796 relações. No total, 2.087 pontos no Qdrant e 227 nós / 1.085 relações no Neo4j: os números do cabeçalho da consola.

## 4. The graph answers relation questions / O grafo responde a perguntas de relações

Row 3 of the table: *"which thermal codes light a solid red LED?"* (also open http://localhost:17474, login `neo4j` / `syone2026`).

**EN.** The answer needs **two columns of 30 rows at once** (subsystem = Thermal **and** LED = solid red). A vector search returns chunks that *look like* the question; a Cypher query returns exactly the rows that *satisfy* it. Cypher in one line: `MATCH` a drawn shape `(node)-[:RELATION]->(node)`, `WHERE` a filter, `RETURN` what to show.

**PT.** A resposta precisa de **duas colunas de 30 linhas ao mesmo tempo** (subsistema = Thermal **e** LED = vermelho fixo). Uma pesquisa vetorial devolve chunks que *se parecem* com a pergunta; uma query Cypher devolve exatamente as linhas que a *satisfazem*. Cypher numa linha: `MATCH` uma forma desenhada `(nó)-[:RELAÇÃO]->(nó)`, `WHERE` um filtro, `RETURN` o que mostrar.
"""),
    code('''
import pandas as pd
print("Node counts:"); display(pd.DataFrame(neo4j.stats()["nodes"]).T)
q = """MATCH (c:ErrorCode)-[:IN_SUBSYSTEM]->(:Subsystem {name:'Thermal'}), (c)-[:INDICATED_BY]->(l:LEDState)
       WHERE l.name CONTAINS 'Solid red' RETURN c.name AS code, c.severity AS severity, c.remediation AS remediation"""
display(pd.DataFrame(neo4j.run_cypher(q)))
'''),
    md("""
**Result / Resultado.**
* **EN.** The node counts: Document 87, ErrorCode 30, Technology 25, Part 18, ... Then exactly **two** codes: `0x8F11_TEMP_CRIT` and `0x8F02_FAN_ALL_FAIL`, both Critical, with their remediation. No ranking, no "top 5": the complete and exact answer.
* **PT.** As contagens de nós: Document 87, ErrorCode 30, Technology 25, Part 18, ... Depois exatamente **dois** códigos: `0x8F11_TEMP_CRIT` e `0x8F02_FAN_ALL_FAIL`, ambos Critical, com a remediação. Sem ranking, sem "top 5": a resposta completa e exata.

The same works on the website / *O mesmo funciona no site*: Syone's partners and their tier.
"""),
    code('''
q = """MATCH (o:Organization)-[:PARTNERS_WITH]->(p:Partner)<-[:DESCRIBES]-(d:Document) RETURN p.name AS partner, p.tier AS tier, d.doc_id AS page ORDER BY partner"""
display(pd.DataFrame(neo4j.run_cypher(q)))
'''),
    md("""
**Result / Resultado.** Six partners (Elastic, GitLab, Microsoft, Red Hat, Syntevo, Zabbix), each with its tier and the page it came from. *Seis parceiros, cada um com o nível e a página de onde veio.*

## 5. Dense vs BM25 vs hybrid, with the ranks visible / Dense vs BM25 vs hybrid, com os rankings à vista

**EN.** Each method returns its 20 best chunks. **Reciprocal Rank Fusion (RRF)** gives each chunk `1/(60 + rank)` from each list and adds them up; the 5 best go to the model. Every line below shows:

`RRF <fused score> | dense #<rank> | bm25 #<rank> | <document> | <start of the chunk>`

`None` = that method did not put the chunk in its top 20. Example: dense #2 and BM25 #12 give 1/62 + 1/72 = 0.0161 + 0.0139 = **0.0300**. A chunk found by only one method scores at most 1/61 = 0.0164, so **agreement between the two methods wins**. This is *debuggable retrieval*: you can always see why a chunk won.

**PT.** Cada método devolve os seus 20 melhores chunks. O **Reciprocal Rank Fusion (RRF)** dá a cada chunk `1/(60 + rank)` de cada lista e soma; os 5 melhores vão para o modelo. Cada linha abaixo mostra o score fundido, o rank no dense, o rank no BM25, o documento e o início do chunk. `None` = esse método não pôs o chunk no seu top 20. Exemplo: dense #2 e BM25 #12 dão 1/62 + 1/72 = **0.0300**. Um chunk encontrado só por um método tem no máximo 1/61 = 0.0164, por isso **o acordo entre os dois métodos ganha**. É *retrieval que se consegue depurar*: vê-se sempre porque é que um chunk ganhou.

### 5a. An exact fault code / Um código de erro exato
"""),
    code('''
def show(query, corpus="hardware_manuals", k=4):
    print(f"\\nQUERY: {query}")
    for h in qdrant.hybrid_search(query, corpus=corpus, top_k=k):
        print(f"  RRF {h['hybrid_score']:.4f} | dense #{str(h['dense_rank']):>4} | bm25 #{str(h['bm25_rank']):>4} | {h['title'][:34]:34s} | {h['text'].split(chr(10),1)[1][:70]}")

show("0x4A7B_VRM_OVERVOLT")   # the full code
show("0x4A7B")                # only the prefix: works because we also index the split form of every code
'''),
    md("""
**Result / Resultado.**
* **EN.** For the full code, the **definition row** (`Code: 0x4A7B_VRM_OVERVOLT | Subsystem: Power VRM | Severity: Critical ...`) is dense #2 but only **BM25 #12**: the code appears in about 15 chunks across the manuals, and BM25 prefers short chunks that repeat it. First place goes to a paragraph about the SEL export that also names the code (dense #4, BM25 #2). Fusion brings the definition row to **2nd**, inside the 5 chunks the model reads. Neither method alone is "the right one"; the fusion is robust. With the full question from the console ("What is the root cause ... for 0x4A7B_VRM_OVERVOLT?") the row is #1 for both methods. With only the prefix `0x4A7B`, BM25 #1 is the table that lists every Power VRM code: it still works because each code is also indexed in its split form.
* **PT.** Para o código completo, a **linha de definição** é dense #2 mas só **BM25 #12**: o código aparece em cerca de 15 chunks dos manuais, e o BM25 prefere chunks curtos que o repetem. O primeiro lugar vai para um parágrafo sobre o export do SEL que também cita o código (dense #4, BM25 #2). A fusão põe a linha de definição em **2.º**, dentro dos 5 chunks que o modelo lê. Nenhum método sozinho é "o certo"; a fusão é robusta. Com a pergunta completa da consola, a linha fica em #1 nos dois métodos. Só com o prefixo `0x4A7B`, o BM25 #1 é a tabela com todos os códigos Power VRM: funciona porque cada código também é indexado na forma partida.

### 5b. A paraphrase: no shared words / Uma paráfrase: nenhuma palavra em comum

Row 1 of the table. The manuals say "fan" and "tachometer"; we ask about a "cooling unit" that stopped "rotating". *Os manuais dizem "fan" e "tachometer"; nós perguntamos por uma "cooling unit" que deixou de "rotating".*
"""),
    code('''
show("the cooling unit stopped rotating")
'''),
    md("""
**Result / Resultado.**
* **EN.** Dense #1 (switch fan trays) and dense #2 (the procedure for `0x8F01_FAN_TACH_FAIL`, a fan that stopped) both have **BM25 `None`**: no word in common, so BM25 cannot see them. Only the *meaning* carries them. BM25's own #1 is a table row about the "Fan wall" that matched a word but not the problem. The fused #1 is the first step of the cooling procedure ("Read the SEL"), ranked by *both* methods (dense #6, BM25 #2): agreement wins. **Paraphrase → dense.**
* **PT.** O dense #1 (as gavetas de ventoinhas do switch) e o dense #2 (o procedimento para `0x8F01_FAN_TACH_FAIL`, uma ventoinha parada) têm os dois **BM25 `None`**: nenhuma palavra em comum, por isso o BM25 não os vê. Só o *significado* os encontra. O #1 do próprio BM25 é uma linha sobre o "Fan wall" que acertou numa palavra, mas não no problema. O #1 da fusão é o primeiro passo do procedimento de arrefecimento ("Read the SEL"), escolhido pelos *dois* métodos (dense #6, BM25 #2): o acordo ganha. **Paráfrase → dense.**

### 5c. A short exact identifier: where dense fails / Um identificador curto e exato: onde o dense falha

Row 2 of the table. `FM4` is one fan module (the manual calls them FM1 to FM6). Here we print the top 3 of **each method on its own**, before fusion, and mark with ✔ the chunks that really contain `FM4`.
*`FM4` é um módulo de ventoinha (o manual chama-lhes FM1 a FM6). Imprimimos o top 3 de **cada método sozinho**, antes da fusão, e marcamos com ✔ os chunks que contêm mesmo `FM4`.*
"""),
    code('''
def compare(query, must_contain, corpus="hardware_manuals", n=3):
    hits = qdrant.hybrid_search(query, corpus=corpus, top_k=40)
    print(f"QUERY: {query}")
    for method in ("dense", "bm25"):
        ranked = sorted((h for h in hits if h[f"{method}_rank"]), key=lambda h: h[f"{method}_rank"])[:n]
        print(f"\\n  {method} alone, top {n}:")
        for h in ranked:
            mark = "✔" if must_contain in h["text"] else "✘"
            print(f"    {mark} #{h[f'{method}_rank']} | {h['text'].split(chr(10),1)[1][:80]}")

compare("FM4", must_contain="FM4")
'''),
    md("""
**Result / Resultado.**
* **EN.** Dense alone: **no** chunk in its top 3 contains `FM4`. It returns figure *F4*, the line "FM1 to FM6" and an LED in *position 4*: to an embedding, `FM4`, `F4` and `4` *look alike*, and a 3-character code carries almost no meaning. BM25 alone: all three contain `FM4` (the rows of `0x8F01_FAN_TACH_FAIL`, the fault for that fan). **Exact token → BM25.** This is why we keep both: part numbers, error codes, VLAN names and product SKUs are everywhere in enterprise documents.
* **PT.** Dense sozinho: **nenhum** chunk do top 3 contém `FM4`. Devolve a figura *F4*, a linha "FM1 to FM6" e um LED na *posição 4*: para um embedding, `FM4`, `F4` e `4` *parecem-se*, e um código de 3 caracteres quase não tem significado. BM25 sozinho: os três contêm `FM4` (as linhas de `0x8F01_FAN_TACH_FAIL`, o erro dessa ventoinha). **Token exato → BM25.** É por isso que mantemos os dois: números de peça, códigos de erro, nomes de VLAN e SKUs estão por todo o lado nos documentos de uma empresa.

### 5d. Generic words add noise / Palavras genéricas fazem ruído
"""),
    code('''
show("error 0x8F01")
'''),
    md("""
**Result / Resultado.**
* **EN.** The top 4 are about **ECC memory errors**, not the fan code `0x8F01`. The word "error" is everywhere, and to the embedding "error 0x8F01" looks like "error 0x10E4". **BM25 is not magic**: one generic word drags both methods off. Remedies: a stop-word list, query rewriting, or the full question (the console asks "What does 0x8F01_FAN_TACH_FAIL mean?").
* **PT.** O top 4 é sobre **erros de memória ECC**, não sobre o código da ventoinha `0x8F01`. A palavra "error" está em todo o lado, e para o embedding "error 0x8F01" parece "error 0x10E4". **O BM25 não é magia**: uma palavra genérica desvia os dois métodos. Remédios: uma lista de stop-words, reescrever a pergunta, ou a pergunta completa.

### 5e. Near-duplicate codes: the hard case / Códigos quase iguais: o caso difícil

`0x4A7B_VRM_OVERVOLT` (above 54.2 V, critical) vs `0x4A7C_VRM_UNDERVOLT` (below 40.5 V, major): one character apart, opposite meaning.
*Um carácter de diferença, significado oposto.*
"""),
    code('''
show("0x4A7C_VRM_UNDERVOLT", k=3)
show("Which fault means the busbar dropped below 40.5 V?", k=3)
'''),
    md("""
**Result / Resultado.**
* **EN.** For `0x4A7C`, #1 is the paragraph that *contrasts* the two codes (BM25 #1), then the `0x4A7C` definition row: the right code, not its neighbour. Asked by meaning ("below 40.5 V"), #1 is the *Undervoltage cutoff 40.5 V* row (dense #1, BM25 #2) and then the `0x4A7C` rows: both methods agree, so fusion is confident.
* **PT.** Para `0x4A7C`, o #1 é o parágrafo que *compara* os dois códigos (BM25 #1), depois a linha de definição do `0x4A7C`: o código certo, não o vizinho. Perguntando pelo significado ("below 40.5 V"), o #1 é a linha *Undervoltage cutoff 40.5 V* (dense #1, BM25 #2) e depois as linhas do `0x4A7C`: os dois métodos concordam, por isso a fusão tem confiança.

## Recap / Resumo

| Question / Pergunta | What we saw / O que vimos |
|---|---|
| Paraphrase (5b) | dense finds the fan chunks; BM25 `None` |
| Exact token (5c) | BM25 3/3 with `FM4`; dense 0/3 |
| Exact code (5a) | BM25 alone puts the definition 12th; fusion brings it to 2nd |
| Relations (4) | Cypher returns exactly the 2 codes; no ranking |
| Noise (5d) | a generic word drags both methods off |

**EN.** No single method wins everywhere: hybrid search fuses dense and BM25, and the graph answers what no ranking can. This is Track A. Next, in the console: the same questions to Track A and to Track B (an agent that reads the OKF files directly, no index).

**PT.** Nenhum método ganha em todo o lado: a hybrid search junta dense e BM25, e o grafo responde ao que nenhum ranking consegue. Isto é o Track A. A seguir, na consola: as mesmas perguntas ao Track A e ao Track B (um agente que lê os ficheiros OKF diretamente, sem índice).

### Exercises / Exercícios
1. Query `show("0x4A7B_VRM_OVERVOLT")` after replacing the BM25 sparse vector with a zero vector (hint: comment out the `bm25` prefetch in `qdrant_hybrid.py`). Which queries break?
2. Try `compare("MGMT_VLAN_102", "MGMT_VLAN_102")` and `compare("SEL-0101", "SEL-0101")`: does dense fail on every identifier, or only on short ones?
3. Write a Cypher query that returns every code raised by the `AS-100G switch` component and the LED each one shows.
4. Add a new `Event` alias to `backend/ingestion/knowledge.py`, re-index, and find the new nodes in the Neo4j browser.
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
