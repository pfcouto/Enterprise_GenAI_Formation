#!/usr/bin/env python3
"""
Runs the golden evaluation from the command line and saves one JSON line per question (safe to interrupt and resume).

  python scripts/run_eval.py --mode retrieval                      # no LLM, seconds
  python scripts/run_eval.py --mode full --model formation-local   # retrieval + generated answers
  python scripts/run_eval.py --mode full --track graph_rag --ids hw_001 hw_003
  python scripts/run_eval.py --mode full --track graph_rag --demo --judge   # the 8-question live slice + judge panel
  python scripts/run_eval.py --mode judge                          # grade the STORED full-run answers with the judge panel
Results: docs/eval_results/<mode>_<track>_<model>.jsonl and a summary table on stdout.

Cost (deepseek-v4.1-flash on OpenCode Zen): a full run of both tracks is about $0.28 (Track B, the agent, is about 7x
Track A); --mode judge re-uses stored answers, so it only pays the judges (they are reasoning models: about $0.12 for all 68).
"""

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.evaluation.golden_dataset import DEMO_SLICE, GOLDEN_EVALUATION_DATASET  # noqa: E402
from backend.evaluation.langfuse_evals import JUDGE_PANEL, LLMJudgeEvaluator  # noqa: E402
from backend.graph_rag.neo4j_client import Neo4jGraphClient  # noqa: E402
from backend.graph_rag.pipeline import GraphRAGPipeline  # noqa: E402
from backend.graph_rag.qdrant_hybrid import QdrantHybridStore  # noqa: E402
from backend.okf_agents.deep_agent_harness import OKFDeepAgentHarness  # noqa: E402
from backend.okf_agents.pipeline import OKFAgentPipeline  # noqa: E402

OUT = ROOT / "docs" / "eval_results"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["retrieval", "full", "judge"], default="retrieval",
                    help="judge: grade the answers stored by a previous full run (no new answers are generated)")
    ap.add_argument("--track", choices=["graph_rag", "okf_agent", "both"], default="both")
    ap.add_argument("--model", default="formation-fast")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--demo", action="store_true", help="only the 8 questions of DEMO_SLICE")
    ap.add_argument("--judge", action="store_true", help="full mode: also grade each answer with the judge panel")
    ap.add_argument("--judges", nargs="*", default=JUDGE_PANEL, help="gateway aliases of the judges")
    ap.add_argument("--add-judges", action="store_true",
                    help="judge mode: grade items already judged again with --judges and merge the verdicts (e.g. --judges formation-judge-nemotron)")
    ap.add_argument("--fresh", action="store_true", help="ignore previous results and start over")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    neo4j, qdrant = Neo4jGraphClient(), QdrantHybridStore()
    pipes = {"graph_rag": GraphRAGPipeline(neo4j, qdrant), "okf_agent": OKFAgentPipeline()}
    ev = LLMJudgeEvaluator()
    items = [i for i in GOLDEN_EVALUATION_DATASET if (not args.ids or i["id"] in args.ids) and (not args.demo or i["id"] in DEMO_SLICE)]
    tracks = ["graph_rag", "okf_agent"] if args.track == "both" else [args.track]

    summary = {}
    for track in tracks:
        path = OUT / f"{args.mode}_{track}_{args.model.replace('/', '_')}.jsonl"
        done = {}
        if path.exists() and not args.fresh:
            done = {json.loads(l)["id"]: json.loads(l) for l in path.read_text().splitlines() if l.strip()}
        else:
            path.write_text("")
        stored, previous = {}, {}
        if args.mode == "judge":
            # --fresh re-grades everything; --add-judges re-grades judged items with --judges and merges the verdicts.
            # The answers come from the reference full run of this track and model.
            previous, done = done, ({} if args.add_judges else done)
            source = OUT / f"full_{track}_{args.model.replace('/', '_')}.jsonl"
            stored = {json.loads(l)["id"]: json.loads(l) for l in source.read_text().splitlines() if l.strip()} if source.exists() else {}
        for item in items:
            if item["id"] in done:
                continue
            if args.mode == "judge":
                if item["id"] not in stored or stored[item["id"]]["score"]["answer_mode"] != "generated":
                    continue
                rec = stored[item["id"]]
                rec["score"].update(await ev.judge_panel(item, rec["answer"], args.judges))
                if item["id"] in previous:  # keep the verdicts of judges not asked this time (e.g. a free judge added on another day)
                    rec["score"]["judges"] = {**(previous[item["id"]]["score"].get("judges") or {}),
                                              **{j: v for j, v in rec["score"]["judges"].items() if v}}
                    scores = [v["score"] for v in rec["score"]["judges"].values() if v]
                    rec["score"]["judge_mean"] = round(sum(scores) / len(scores), 2) if scores else None
                    rec["score"]["judge_spread"] = round(max(scores) - min(scores), 2) if len(scores) > 1 else None
            elif args.mode == "retrieval":
                if track == "okf_agent":
                    nav = OKFDeepAgentHarness(item["corpus"]).scripted_navigation(item["question"])
                    docs, ctx = [d["doc_id"] for d in nav["collected_documents"]], "\n".join(d["content"] for d in nav["collected_documents"])
                else:
                    ch = qdrant.hybrid_search(item["question"], corpus=item["corpus"], top_k=5)
                    g = neo4j.query_graph_neighborhood(neo4j.extract_keywords(item["question"]), corpus=item["corpus"])
                    docs, ctx = list(dict.fromkeys(c["doc_id"] for c in ch)), "\n".join(c["text"] for c in ch) + g["formatted_context"]
                score = ev.evaluate_response(item, "", docs, ctx, "retrieval_only")
                score["passed"] = bool(score["retrieval_any_expected_doc"] if item["expected_docs"] else True) and \
                    (score["context_keyword_recall"] is None or score["context_keyword_recall"] >= 0.6)
                rec = {"id": item["id"], "category": item["category"], "corpus": item["corpus"], "score": score, "retrieved_docs": docs, "seconds": 0}
            else:
                res = await pipes[track].execute_query(item["question"], corpus=item["corpus"], model_name=args.model, include_context=True)
                score = ev.evaluate_response(item, res["answer"], res.get("retrieved_doc_ids"), res.get("context_text", ""), res["answer_mode"])
                if args.judge and res["answer_mode"] == "generated":
                    score.update(await ev.judge_panel(item, res["answer"], args.judges))
                rec = {"id": item["id"], "category": item["category"], "corpus": item["corpus"], "score": score, "answer": res["answer"],
                       "retrieved_docs": res.get("retrieved_doc_ids"), "agent_trajectory": res.get("agent_trajectory"),
                       "llm_error": res.get("llm_error"), "seconds": res["latency_seconds"]}
            done[item["id"]] = rec
            with path.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            score = rec["score"]
            verdicts = "  ".join(f"{j.replace('formation-judge-', '')}={v['score'] if v else '-'}" for j, v in (score.get("judges") or {}).items())
            print(f"[{track}] {item['id']:10s} {'PASS' if score['passed'] else 'FAIL'}  {item['category']:22s} {verdicts}", flush=True)

        rows = [done[i["id"]] for i in items if i["id"] in done]
        summary[track] = rows

    print("\n" + "=" * 70)
    for track, rows in summary.items():
        by = defaultdict(lambda: [0, 0])
        for r in rows:
            by[r["category"]][1] += 1
            by[r["category"]][0] += 1 if r["score"]["passed"] else 0
        total = sum(1 for r in rows if r["score"]["passed"])
        print(f"{track}: {total}/{len(rows)} passed on keywords ({args.mode}, model={args.model})")
        for cat, (p, n) in sorted(by.items()):
            print(f"   {cat:24s} {p}/{n}")
        judged = [r for r in rows if r["score"].get("judges")]
        if judged:
            print(f"   judge panel on {len(judged)} answers (mean score; agreement with the keyword verdict at 0.5):")
            for j in args.judges:
                got = [(r["score"]["judges"][j]["score"], r["score"]["passed"]) for r in judged if r["score"]["judges"].get(j)]
                if got:
                    agree = sum(1 for s, k in got if (s >= 0.5) == k)
                    print(f"     {j:28s} mean {sum(s for s, _ in got) / len(got):.2f}   agrees with keywords {agree}/{len(got)}")
                else:
                    print(f"     {j:28s} no usable verdicts (unreachable or not JSON)")
            split = [r["id"] for r in judged if (r["score"].get("judge_spread") or 0) >= 0.5]
            print(f"   judges disagree (spread >= 0.5) on: {', '.join(split) or 'none'}")


if __name__ == "__main__":
    asyncio.run(main())
