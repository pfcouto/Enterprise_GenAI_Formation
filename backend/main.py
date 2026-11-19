"""
Syone Enterprise GenAI backend (FastAPI).

Two retrieval tracks over the same OKF knowledge base, side by side:
  * graph_rag  - Qdrant (dense + BM25) + Neo4j graph facts
  * okf_agent  - an agent that navigates the OKF Markdown files with tools
plus ingestion, evaluation (retrieval + answer metrics) and prompt optimization.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Histogram, make_asgi_app
from pydantic import BaseModel

from backend.evaluation.golden_dataset import DEMO_SLICE, get_dataset_by_corpus
from backend.evaluation.langfuse_evals import JUDGE_PANEL, LLMJudgeEvaluator
from backend.evaluation.opik_optimizer import OpikPromptOptimizer
from backend.graph_rag.indexer import index_okf_store, okf_files
from backend.graph_rag.neo4j_client import Neo4jGraphClient
from backend.graph_rag.pipeline import GraphRAGPipeline
from backend.graph_rag.qdrant_hybrid import QdrantHybridStore
from backend.llm import GatewayError
from backend.okf_agents.deep_agent_harness import OKFDeepAgentHarness
from backend.okf_agents.pipeline import OKFAgentPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).parent.parent
EXTRACTED_IMAGES_DIR = WORKSPACE_ROOT / "data" / "extracted_images"
CORPORA = ["syone_corp", "hardware_manuals"]

REQUEST_COUNTER = Counter("syone_requests_total", "Total requests processed", ["endpoint", "pipeline"])
LATENCY_HISTOGRAM = Histogram("syone_request_latency_seconds", "Request latency", ["pipeline"])

app = FastAPI(title="Syone Enterprise GenAI API",
              description="GraphRAG + BM25 versus Google OKF agentic navigation, with evaluation", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
EXTRACTED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static/images", StaticFiles(directory=str(EXTRACTED_IMAGES_DIR)), name="static_images")
app.mount("/metrics", make_asgi_app())

neo4j_client = Neo4jGraphClient()
qdrant_store = QdrantHybridStore()
graph_rag_pipeline = GraphRAGPipeline(neo4j_client, qdrant_store)
okf_agent_pipeline = OKFAgentPipeline()
evaluator = LLMJudgeEvaluator()
prompt_optimizer = OpikPromptOptimizer(evaluator)
ingestion_status: Dict[str, Any] = {"state": "idle"}


class QueryRequest(BaseModel):
    query: str
    corpus: str = "syone_corp"
    pipeline: str = "graph_rag"  # "graph_rag" | "okf_agent"
    model_name: str = "formation-fast"


class EvalRunRequest(BaseModel):
    corpus: str = "all"
    pipeline: str = "graph_rag"
    model_name: str = "formation-fast"
    mode: str = "full"  # "full" (retrieval + LLM answer) | "retrieval" (no LLM needed)
    ids: Optional[List[str]] = None
    limit: Optional[int] = None
    demo_slice: bool = False  # the 8 questions of DEMO_SLICE (cheap enough to run live)
    judge: bool = False  # grade every generated answer with the judge panel (LLM-as-a-judge)
    judges: Optional[List[str]] = None  # gateway aliases; default JUDGE_PANEL


# --------------------------------------------------------------------------- status
@app.get("/api/health")
def health_check():
    qdrant_ok = qdrant_store.reconnect()
    neo4j_ok = neo4j_client.reconnect()
    return {
        "status": "healthy", "version": app.version,
        "neo4j_connected": neo4j_ok, "qdrant_connected": qdrant_ok, "embeddings_ready": qdrant_store.ready,
        "qdrant_points": {c: qdrant_store.count(c) for c in CORPORA} if qdrant_ok else {},
        "graph": {k: v for k, v in neo4j_client.stats().items() if k.startswith("total")} if neo4j_ok else {},
        "okf_documents": {c: len(okf_files(c)) for c in CORPORA},
        "litellm_url": os.getenv("LITELLM_URL", "http://litellm:4000/v1"),
        "langfuse_host": os.getenv("LANGFUSE_HOST", "http://langfuse-server:3000"),
        "ingestion": ingestion_status,
    }


@app.get("/api/models/free")
async def get_dynamic_free_models():
    """Live discovery of free OpenRouter models, sorted by context window (free lists change every few weeks)."""
    models: List[Dict[str, Any]] = []
    source = "openrouter-live"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get("https://openrouter.ai/api/v1/models")
        resp.raise_for_status()
        for m in resp.json().get("data", []):
            if str(m.get("pricing", {}).get("prompt", "")).strip() not in ("0", "0.0", "0.00"):
                continue
            arch = m.get("architecture", {})
            inputs = arch.get("input_modalities") or []
            models.append({
                "id": f"openrouter/{m['id']}", "name": m.get("name", m["id"]), "provider": "openrouter",
                "context_length": m.get("context_length", 0),
                "modality": "multimodal / vision" if "image" in inputs else "text->text",
                "supports_vision": "image" in inputs,
                "supports_tools": "tools" in (m.get("supported_parameters") or []),
                "description": (m.get("description") or "")[:140],
            })
    except Exception as e:  # noqa: BLE001
        logger.warning(f"OpenRouter discovery failed: {e}")
        source = "offline-fallback"
        models = [
            {"id": "openrouter/openrouter/free", "name": "OpenRouter Free Router", "provider": "openrouter", "context_length": 200000,
             "modality": "multimodal / vision", "supports_vision": True, "supports_tools": True,
             "description": "Auto-router that picks an available free model for each request."},
            {"id": "openrouter/nvidia/nemotron-3.5-lightning:free", "name": "NVIDIA Nemotron 3.5 Lightning (free)", "provider": "openrouter",
             "context_length": 1000000, "modality": "text->text", "supports_vision": False, "supports_tools": True,
             "description": "Fast 1M-context text model (example; verify availability)."},
        ]
    models.sort(key=lambda x: x["context_length"], reverse=True)

    aliases = [  # stable gateway names (see config/litellm_config.yaml): these survive free-model churn
        {"id": "formation-fast", "name": "formation-fast (gateway alias, fallback ladder)", "provider": "litellm", "context_length": 1000000,
         "modality": "text->text", "supports_vision": False, "supports_tools": True,
         "description": "Default. Provider A, then B... (failover ladder), then formation-reasoning, then formation-local."},
        {"id": "formation-opencode", "name": "formation-opencode (pinned: OpenCode Zen deepseek-v4.1-flash, paid)", "provider": "litellm", "context_length": 1000000,
         "modality": "text->text", "supports_vision": False, "supports_tools": True,
         "description": "One provider, one model, no failover. Needs OPENCODE_API_KEY with balance."},
        {"id": "formation-qwen", "name": "formation-qwen (pinned: OpenCode Zen qwen3.8-flash, thinking off, paid)", "provider": "litellm", "context_length": 1000000,
         "modality": "multimodal / vision", "supports_vision": True, "supports_tools": True,
         "description": "The cheaper candidate: Track A measured against DeepSeek (comparable quality, 2.4x cheaper, slower). Track B not tested yet."},
        {"id": "formation-openrouter-free", "name": "formation-openrouter-free (pinned: gemma-4-31b-it:free)", "provider": "litellm", "context_length": 262144,
         "modality": "multimodal / vision", "supports_vision": True, "supports_tools": True,
         "description": "One provider, one free model, no failover. Free account, 50 requests/day (1,000 with $10 credit)."},
        {"id": "formation-reasoning", "name": "formation-reasoning (gateway alias)", "provider": "litellm", "context_length": 262144,
         "modality": "text->text", "supports_vision": False, "supports_tools": True, "description": "Larger free model for harder questions."},
        {"id": "formation-vision", "name": "formation-vision (gateway alias)", "provider": "litellm", "context_length": 262144,
         "modality": "multimodal / vision", "supports_vision": True, "supports_tools": True, "description": "Free vision-capable model."},
        {"id": "formation-local", "name": "formation-local (LM Studio / Ollama on your machine)", "provider": "local", "context_length": 32768,
         "modality": "text->text", "supports_vision": False, "supports_tools": True, "description": "Optional offline model, no key needed."},
    ]
    return {"count": len(models) + len(aliases), "source": source, "models": aliases + models}


@app.get("/api/corpora")
def corpora_overview():
    """What is in each knowledge base (documents, figures) - shown on the frontend corpus selector."""
    out = {}
    for c in CORPORA:
        files = okf_files(c)
        out[c] = {"documents": len(files), "figures": len(list((EXTRACTED_IMAGES_DIR / c).glob("*.png")) + list((EXTRACTED_IMAGES_DIR / c).glob("*.jpg")))
                  if (EXTRACTED_IMAGES_DIR / c).exists() else 0,
                  "doc_ids": [f.stem for f in files]}
    return out


@app.get("/api/graph/stats")
def graph_stats():
    return neo4j_client.stats()


# Health URLs as seen from INSIDE the Docker network (service names, container ports); Jupyter and LM Studio run on the host.
SERVICE_PROBES = {
    "neo4j": "http://neo4j:7474",
    "qdrant": "http://qdrant:6333/healthz",
    "litellm": "http://litellm:4000/health/liveliness",
    "langfuse": "http://langfuse-server:3000/api/public/health",
    "prometheus": "http://prometheus:9090/-/healthy",
    "grafana": "http://grafana:3000/api/health",
    "jupyter": "http://host.docker.internal:18888/api",
    "lmstudio": "http://host.docker.internal:1234/v1/models",
}


@app.get("/api/services/status")
async def services_status():
    """Is each tool of the stack up? Shown on the frontend's Services page (any HTTP answer counts as up)."""
    async def probe(url: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                await client.get(url)
            return True
        except Exception:  # noqa: BLE001
            return False

    names = list(SERVICE_PROBES)
    results = await asyncio.gather(*(probe(SERVICE_PROBES[n]) for n in names))
    return {"backend": True, **dict(zip(names, results))}


# --------------------------------------------------------------------------- query
@app.post("/api/query")
async def execute_query(req: QueryRequest):
    REQUEST_COUNTER.labels(endpoint="/api/query", pipeline=req.pipeline).inc()
    start = time.time()
    try:
        pipe = okf_agent_pipeline if req.pipeline == "okf_agent" else graph_rag_pipeline
        result = await pipe.execute_query(query=req.query, corpus=req.corpus, model_name=req.model_name)
        LATENCY_HISTOGRAM.labels(pipeline=req.pipeline).observe(time.time() - start)
        return result
    except Exception as e:  # noqa: BLE001
        logger.error(f"Query execution error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------- ingestion
@app.post("/api/ingestion/run")
def trigger_ingestion(background_tasks: BackgroundTasks):
    """(Re)indexes the OKF store into Neo4j + Qdrant in the background (same code as notebook 02)."""
    def _job():
        ingestion_status.update({"state": "running", "started": time.time()})
        try:
            report = index_okf_store(neo4j_client, qdrant_store)
            ingestion_status.update({"state": "done", "report": report, "seconds": round(time.time() - ingestion_status["started"], 1)})
        except Exception as e:  # noqa: BLE001
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            ingestion_status.update({"state": "failed", "error": str(e)})

    background_tasks.add_task(_job)
    return {"message": "Indexing started. Poll GET /api/health for ingestion status."}


# --------------------------------------------------------------------------- evaluation
@app.get("/api/eval/dataset")
def get_eval_dataset(corpus: str = "all"):
    return {"dataset": get_dataset_by_corpus(corpus), "demo_slice": DEMO_SLICE, "judge_panel": JUDGE_PANEL}


async def _retrieval_only(item: Dict[str, Any], pipeline: str) -> Dict[str, Any]:
    """Retrieval stage only (no LLM): which documents / how much of the needed facts reach the generator?"""
    if pipeline == "okf_agent":
        nav = OKFDeepAgentHarness(item["corpus"]).scripted_navigation(item["question"])
        docs = [d["doc_id"] for d in nav["collected_documents"]]
        ctx = "\n".join(d["content"] for d in nav["collected_documents"])
    else:
        qdrant_store.reconnect()
        chunks = qdrant_store.hybrid_search(item["question"], corpus=item["corpus"], top_k=5)
        graph = neo4j_client.query_graph_neighborhood(neo4j_client.extract_keywords(item["question"]), corpus=item["corpus"])
        docs = list(dict.fromkeys(c["doc_id"] for c in chunks))
        ctx = "\n".join(c["text"] for c in chunks) + "\n" + graph["formatted_context"]
    return {"docs": docs, "context": ctx}


# Every run is saved to data/eval_runs/ so the page can show it again after a reload (no need to re-run and spend quota),
# and runs keep going server-side if the browser leaves the page. GET /api/eval/status reports the run in progress.
EVAL_RUNS_DIR = Path("data/eval_runs")
eval_progress: Dict[str, Any] = {"state": "idle"}


def _questions_label(req: EvalRunRequest) -> str:
    if req.demo_slice:
        return "demo slice"
    if req.ids:
        return "selected"
    return f"first {req.limit}" if req.limit else "all"


def _golden_comparison(item: Dict[str, Any], answer: str, docs: List[str], context: str, score: Dict[str, Any], mode: str) -> Dict[str, Any]:
    """Side by side with the golden set: which expected facts, documents and figures were found, and the rule that decided."""
    c = evaluator._contains
    kws, exp_docs, imgs = item.get("expected_keywords", []), item.get("expected_docs", []), item.get("expected_images", [])
    keywords = [{"keyword": k, "in_context": bool(context) and c(context, k), "in_answer": bool(answer) and c(answer, k)} for k in kws]
    documents = [{"doc_id": d, "retrieved": d in (docs or [])} for d in exp_docs]
    figures = [{"figure": i, "cited": bool(answer) and i.lower() in answer.lower()} for i in imgs]
    if mode == "retrieval":
        n_ctx = sum(1 for k in keywords if k["in_context"])
        rule = [
            f"expected document retrieved: {'yes' if score.get('retrieval_any_expected_doc') else 'no'} (needs one of: {', '.join(exp_docs)})"
            if exp_docs else "no expected document (refusal question): document check skipped",
            f"facts in context: {n_ctx}/{len(kws)} (needs 60% or more)" if kws else "no expected facts",
        ]
    elif item.get("should_refuse"):
        rule = ["the knowledge base does not contain the answer: passes only if the answer refuses",
                f"refused: {'yes' if score.get('refusal_ok') else 'no'}", f"answer generated by the LLM: {'yes' if score.get('answer_mode') == 'generated' else 'no (extractive fallback)'}"]
    else:
        n_ans = sum(1 for k in keywords if k["in_answer"])
        rule = [f"facts in answer: {n_ans}/{len(kws)} (needs 60% or more)" if kws else "no expected facts"]
        if item.get("category") == "visual_grounding" and imgs:
            rule.append(f"figure cited: {sum(1 for f in figures if f['cited'])}/{len(imgs)} (required: the question is about a figure)")
        rule.append(f"answer generated by the LLM: {'yes' if score.get('answer_mode') == 'generated' else 'no (extractive fallback)'}")
    return {"expected_answer": item["expected_answer"], "keywords": keywords, "documents": documents, "figures": figures,
            "should_refuse": item.get("should_refuse", False), "rule": rule, "retrieved_docs": docs or []}


async def _run_evaluation(req: EvalRunRequest) -> Dict[str, Any]:
    dataset = get_dataset_by_corpus(req.corpus)
    if req.demo_slice:
        dataset = [d for d in dataset if d["id"] in DEMO_SLICE]
    if req.ids:
        dataset = [d for d in dataset if d["id"] in req.ids]
    if req.limit:
        dataset = dataset[: req.limit]
    pipe = okf_agent_pipeline if req.pipeline == "okf_agent" else graph_rag_pipeline
    results = []
    started = time.time()
    eval_progress.update({"state": "running", "done": 0, "total": len(dataset), "started_at": started,
                          "pipeline": req.pipeline, "mode": req.mode, "corpus": req.corpus, "questions": _questions_label(req),
                          "judge": bool(req.judge or req.judges) and req.mode == "full"})

    for item in dataset:
        if req.mode == "retrieval":
            r = await _retrieval_only(item, req.pipeline)
            score = evaluator.evaluate_response(item, "", r["docs"], r["context"], answer_mode="retrieval_only")
            score["passed"] = bool(score["retrieval_any_expected_doc"] if item["expected_docs"] else True) and \
                (score["context_keyword_recall"] is None or score["context_keyword_recall"] >= 0.6)
            results.append({"id": item["id"], "question": item["question"], "corpus": item["corpus"], "category": item["category"],
                            "actual_response": "(retrieval only)", "expected_answer": item["expected_answer"],
                            "retrieved_docs": r["docs"], "score": score, "latency_seconds": 0,
                            "golden": _golden_comparison(item, "", r["docs"], r["context"], score, "retrieval")})
            eval_progress["done"] = len(results)
            continue
        res = await pipe.execute_query(item["question"], corpus=item["corpus"], model_name=req.model_name, include_context=True)
        score = evaluator.evaluate_response(item, res["answer"], res.get("retrieved_doc_ids"), res.get("context_text", ""), res["answer_mode"])
        if (req.judge or req.judges) and res["answer_mode"] == "generated":
            score.update(await evaluator.judge_panel(item, res["answer"], req.judges))
        evaluator.log_to_langfuse(score, req.pipeline, item["question"])
        results.append({"id": item["id"], "question": item["question"], "corpus": item["corpus"], "category": item["category"],
                        "actual_response": res["answer"], "expected_answer": item["expected_answer"], "answer_mode": res["answer_mode"],
                        "retrieved_docs": res.get("retrieved_doc_ids"), "score": score, "latency_seconds": res["latency_seconds"],
                        "golden": _golden_comparison(item, res["answer"], res.get("retrieved_doc_ids") or [], res.get("context_text", "") or "", score, "full")})
        eval_progress["done"] = len(results)

    def avg(key):
        vals = [r["score"][key] for r in results if r["score"].get(key) is not None]
        return round(sum(vals) / len(vals), 3) if vals else None

    passed = sum(1 for r in results if r["score"]["passed"])
    judge_avgs = {}
    for judge in (req.judges or JUDGE_PANEL) if (req.judge or req.judges) else []:
        vals = [r["score"]["judges"][judge]["score"] for r in results if (r["score"].get("judges") or {}).get(judge)]
        judge_avgs[judge] = round(sum(vals) / len(vals), 3) if vals else None
    run_id = time.strftime("%Y%m%d-%H%M%S") + f"_{req.pipeline}_{req.mode}"
    out = {
        "run_id": run_id, "run_at": time.strftime("%Y-%m-%d %H:%M:%S"), "seconds": round(time.time() - started, 1),
        "questions": _questions_label(req), "judge": bool(judge_avgs),
        "pipeline": req.pipeline, "corpus": req.corpus, "mode": req.mode, "model_used": req.model_name,
        "total_tests": len(results), "passed_tests": passed,
        "pass_rate": f"{round(passed / len(results) * 100, 1)}%" if results else "n/a",
        "avg_retrieval_doc_hit": avg("retrieval_doc_hit"), "avg_context_keyword_recall": avg("context_keyword_recall"),
        "avg_keyword_recall": avg("keyword_recall"), "avg_visual_grounding_score": avg("visual_grounding_score"),
        "extractive_fallbacks": sum(1 for r in results if r.get("answer_mode") == "extractive"),
        "avg_judge_scores": judge_avgs,
        "judge_disagreements": sum(1 for r in results if (r["score"].get("judge_spread") or 0) >= 0.5),
        "details": results,
    }
    try:
        EVAL_RUNS_DIR.mkdir(parents=True, exist_ok=True)
        (EVAL_RUNS_DIR / f"{run_id}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as e:
        logger.warning(f"Could not save the evaluation run: {e}")
    return out


@app.post("/api/eval/run")
async def run_evaluation_benchmark(req: EvalRunRequest):
    if eval_progress.get("state") == "running":
        raise HTTPException(status_code=409, detail="An evaluation is already running: wait for it (GET /api/eval/status), it will appear under Saved runs.")
    task = asyncio.create_task(_run_evaluation(req))
    task.add_done_callback(lambda _t: eval_progress.update({"state": "idle"}))
    # shield: if the browser leaves the page, the run continues and is saved
    return await asyncio.shield(task)


@app.get("/api/eval/status")
def eval_status():
    return eval_progress


@app.get("/api/eval/runs")
def list_eval_runs(limit: int = 30):
    runs = []
    for f in sorted(EVAL_RUNS_DIR.glob("*.json"), reverse=True)[:limit] if EVAL_RUNS_DIR.exists() else []:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        runs.append({k: d.get(k) for k in ("run_id", "run_at", "seconds", "questions", "judge", "pipeline", "corpus", "mode",
                                           "model_used", "total_tests", "passed_tests", "pass_rate")})
    return {"runs": runs}


@app.get("/api/eval/runs/{run_id}")
def get_eval_run(run_id: str):
    f = EVAL_RUNS_DIR / f"{Path(run_id).name}.json"
    if not f.exists():
        raise HTTPException(status_code=404, detail="Unknown run")
    return json.loads(f.read_text(encoding="utf-8"))


@app.post("/api/eval/optimize-prompts")
async def run_prompt_optimization(model_name: str = "formation-fast"):
    try:
        return await prompt_optimizer.run_optimization_loop(graph_rag_pipeline, model_name)
    except GatewayError as e:
        raise HTTPException(status_code=503, detail=f"Prompt optimization needs a working LLM gateway: {e}")
