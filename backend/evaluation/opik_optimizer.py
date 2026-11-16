"""
Prompt-optimization loop (the idea behind Opik's MetaPrompt / GEPA optimizers, in ~60 readable lines).

Loop:  candidate prompt -> run the REAL pipeline on a slice of the golden set -> score with the evaluator -> keep the best.
Candidates here are three hand-written variants (naive -> precise -> precise + figure rules) so the effect is easy to see
in a live session. Opik's optimizers do the same but ask an LLM to propose and mutate the candidates automatically
(`pip install opik-optimizer`; see notebook 05, last cell).

Nothing is simulated: if the LLM gateway is unreachable the loop raises GatewayError instead of inventing scores.
"""

import logging
from typing import Any, Dict, List, Optional

from backend.evaluation.golden_dataset import GOLDEN_EVALUATION_DATASET
from backend.evaluation.langfuse_evals import LLMJudgeEvaluator
from backend.llm import GatewayError

logger = logging.getLogger(__name__)

CONTEXT = "\n\n=== PASSAGES ===\n{text_context}\n\n=== GRAPH FACTS ===\n{graph_context}\n\n=== AVAILABLE FIGURES ===\n{figures}\n"

PROMPT_VARIANTS = [
    ("v0 naive", "Answer the question using the context below." + CONTEXT),
    ("v1 precise", "You are a technical specialist. Answer ONLY from the context. Quote codes, ports, names and values exactly as written; "
                   "if the context does not contain the answer, say so." + CONTEXT),
    ("v2 precise + figure rules", "You are a technical specialist. Answer ONLY from the context. Quote codes, ports, names and values exactly as written; "
                                  "if the context does not contain the answer, say so. {figure_rules} Always include the exact markdown image line of a figure "
                                  "when the question is about something a figure shows (LED legend, map, diagram, flowchart, chart)." + CONTEXT),
]
DEFAULT_SLICE = ["hw_001", "hw_003", "hw_007", "hw_010", "hw_012", "hw_020", "syone_002", "syone_007"]


class OpikPromptOptimizer:
    def __init__(self, evaluator: LLMJudgeEvaluator):
        self.evaluator = evaluator

    async def run_optimization_loop(self, pipeline, model_name: str = "formation-fast", ids: Optional[List[str]] = None) -> Dict[str, Any]:
        wanted = ids or DEFAULT_SLICE
        items = [i for i in GOLDEN_EVALUATION_DATASET if i["id"] in wanted]
        history: List[Dict[str, Any]] = []
        for name, template in PROMPT_VARIANTS:
            per_item = []
            for item in items:
                res = await pipeline.execute_query(item["question"], corpus=item["corpus"], model_name=model_name,
                                                   system_prompt=template, include_context=True)
                if res["answer_mode"] != "generated":
                    raise GatewayError(res.get("llm_error") or "LLM unavailable")
                sc = self.evaluator.evaluate_response(item, res["answer"], res.get("retrieved_doc_ids"), res.get("context_text", ""), res["answer_mode"])
                per_item.append({"id": item["id"], "passed": sc["passed"], "keyword_recall": sc["keyword_recall"],
                                 "visual_grounding": sc["visual_grounding_score"]})
            passed = sum(1 for r in per_item if r["passed"])
            history.append({"variant": name, "prompt": template.split("\n\n=== PASSAGES")[0], "pass_rate": round(passed / len(items), 3),
                            "passed": f"{passed}/{len(items)}", "details": per_item})
            logger.info(f"{name}: {passed}/{len(items)} passed")
        best = max(history, key=lambda h: h["pass_rate"])
        return {"optimizer": "manual-candidates loop (concept of Opik MetaPrompt/GEPA)", "dataset_slice": [i["id"] for i in items],
                "history": history, "best_variant": best["variant"], "best_prompt": best["prompt"], "best_pass_rate": best["pass_rate"]}
