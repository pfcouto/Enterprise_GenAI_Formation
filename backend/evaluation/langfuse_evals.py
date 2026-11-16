"""
Evaluation engine: retrieval metrics (no LLM needed) + answer metrics + optional LLM-as-a-judge, scores pushed to Langfuse.

Why separate retrieval from answer quality? When an answer is wrong you need to know WHICH stage failed:
  retrieval_doc_hit      did the pipeline fetch/open the document(s) that contain the answer?      (retrieval)
  context_keyword_recall are the required facts present in the context handed to the LLM?          (retrieval)
  keyword_recall         does the generated answer contain the required facts?                     (generation)
  visual_grounding       did the answer cite the expected figure(s)?                               (multimodal)
  refusal_ok             for unanswerable questions: did it say so instead of inventing?          (honesty)
  judges                 optional 0-1 grades from a PANEL of LLM judges of different families      (LLM-as-a-judge)

Why a panel? A judge is just another model: it has its own biases (a model tends to prefer answers written by itself)
and its own blind spots. Three families grading the same answer show where they agree, and where you must not trust one.
"""

import asyncio
import json
import logging
import os
import re
import unicodedata
from typing import Any, Dict, List, Optional

from backend.llm import GatewayError, chat

logger = logging.getLogger(__name__)

REFUSAL_RE = re.compile(r"(not (?:contain|mention|state|provide|specif|found|available|covered)|no (?:information|mention|data|details)|"
                        r"cannot (?:find|answer)|can't (?:find|answer)|does not (?:say|include|list|contain)|unable to find|out of scope|"
                        r"isn't (?:stated|mentioned)|is not (?:stated|mentioned|specified)|"
                        # found by the judge panel: a correct refusal ("I don't have that information... contains no revenue
                        # figures") that the keyword scorer marked as failed
                        r"(?:don't|do not) have (?:that|this|any|the) information|contains? no |can(?:no|')t guess)", re.I)

# Gateway aliases (config/litellm_config.yaml): the answer model itself, another family, and a free model.
JUDGE_PANEL = ["formation-judge-deepseek", "formation-judge-haiku", "formation-judge-nemotron"]
JUDGE_PROMPT = (
    "You grade answers of a question-answering system against a reference answer written by a human.\n\n"
    "Question: {question}\nReference answer: {reference}\nCandidate answer: {answer}\n\n"
    "Does the candidate state the same key facts as the reference, without contradicting it or inventing facts? "
    "If the reference says the information is not available, the candidate must say so too. Ignore style, length and "
    "extra correct detail; image links in the candidate are fine.\n"
    'Reply with JSON only: {{"score": <0.0-1.0>, "reason": "<one short sentence>"}}'
)


class LLMJudgeEvaluator:
    """Scores one answer against a golden item."""

    @staticmethod
    def _norm(s: str) -> str:
        """Case, spacing, underscores/hyphens and accents are ignored (Vitor == Vítor)."""
        s = unicodedata.normalize("NFKD", s)
        return re.sub(r"[\s_\-]+", "", "".join(c for c in s if not unicodedata.combining(c))).lower()

    def _contains(self, text: str, needle: str) -> bool:
        return self._norm(needle) in self._norm(text)

    def evaluate_response(self, item: Dict[str, Any], answer: str, retrieved_doc_ids: Optional[List[str]] = None,
                          context_text: str = "", answer_mode: str = "generated") -> Dict[str, Any]:
        kws, imgs, docs = item.get("expected_keywords", []), item.get("expected_images", []), item.get("expected_docs", [])
        retrieved_doc_ids = retrieved_doc_ids or []

        doc_hit = round(sum(1 for d in docs if d in retrieved_doc_ids) / len(docs), 2) if docs else None
        # one expected document is enough for a pass (several docs often hold the same fact)
        doc_any = (any(d in retrieved_doc_ids for d in docs)) if docs else None
        ctx_recall = round(sum(1 for k in kws if self._contains(context_text, k)) / len(kws), 2) if kws and context_text else None
        kw_recall = round(sum(1 for k in kws if self._contains(answer, k)) / len(kws), 2) if kws else None
        vis = round(sum(1 for i in imgs if i.lower() in answer.lower()) / len(imgs), 2) if imgs else None

        refused = bool(REFUSAL_RE.search(answer))
        if item.get("should_refuse"):
            passed = refused and answer_mode == "generated"
            refusal_ok = refused
        else:
            refusal_ok = None
            # Citing the figure is REQUIRED only when the question is about the figure itself (category visual_grounding);
            # for text_in_diagram / table_lookup questions the figure is a bonus and reported separately.
            figure_required = item.get("category") == "visual_grounding"
            passed = (kw_recall is None or kw_recall >= 0.6) and (not figure_required or vis is None or vis >= 0.5) and answer_mode == "generated"

        return {
            "eval_id": item.get("id"), "category": item.get("category"), "passed": passed, "answer_mode": answer_mode,
            "retrieval_doc_hit": doc_hit, "retrieval_any_expected_doc": doc_any, "context_keyword_recall": ctx_recall,
            "keyword_recall": kw_recall, "visual_grounding_score": vis, "refusal_ok": refusal_ok,
            "found_keywords": f"{sum(1 for k in kws if self._contains(answer, k))}/{len(kws)}",
        }

    async def llm_judge(self, item: Dict[str, Any], answer: str, model: str) -> Optional[Dict[str, Any]]:
        """One LLM judge: {"score": 0-1, "reason": ...} for `answer` against the reference. None if the judge is unreachable
        or does not return the JSON it was asked for (that is a finding too: not every model follows the format)."""
        prompt = JUDGE_PROMPT.format(question=item["question"], reference=item["expected_answer"], answer=answer[:2500])
        try:
            # The judges are reasoning models: they think (often 300-1,600 tokens) before they write the JSON. A small
            # max_tokens is spent on thinking alone and returns an empty answer.
            msg = await chat([{"role": "user", "content": prompt}], model, temperature=0.0, max_tokens=3000)
            m = re.search(r"\{.*\}", msg.get("content") or "", re.S)
            if not m:
                return None
            verdict = json.loads(m.group(0))
            return {"score": round(min(max(float(verdict["score"]), 0.0), 1.0), 2), "reason": str(verdict.get("reason", ""))[:300]}
        except (GatewayError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None

    async def judge_panel(self, item: Dict[str, Any], answer: str, judges: Optional[List[str]] = None) -> Dict[str, Any]:
        """Every judge grades the same answer in parallel. `spread` (max - min) of 0.5 or more means the judges disagree."""
        judges = judges or JUDGE_PANEL
        verdicts = await asyncio.gather(*(self.llm_judge(item, answer, j) for j in judges))
        scores = [v["score"] for v in verdicts if v]
        return {
            "judges": dict(zip(judges, verdicts)),
            "judge_mean": round(sum(scores) / len(scores), 2) if scores else None,
            "judge_spread": round(max(scores) - min(scores), 2) if len(scores) > 1 else None,
        }

    def log_to_langfuse(self, scores: Dict[str, Any], pipeline: str, question: str):
        """Pushes the main scores to Langfuse (best-effort; needs the keys from .env and the Langfuse container)."""
        try:
            from langfuse import Langfuse
            pk, sk = os.getenv("LANGFUSE_PUBLIC_KEY"), os.getenv("LANGFUSE_SECRET_KEY")
            if not (pk and sk):
                return
            lf = Langfuse(public_key=pk, secret_key=sk, host=os.getenv("LANGFUSE_HOST", "http://localhost:13000"))
            trace = lf.trace(name=f"eval:{scores['eval_id']}", input=question, metadata={"pipeline": pipeline, "category": scores.get("category")})
            for name in ("keyword_recall", "visual_grounding_score", "context_keyword_recall"):
                if scores.get(name) is not None:
                    lf.score(trace_id=trace.id, name=f"{pipeline}.{name}", value=float(scores[name]), comment=question[:80])
            for judge, verdict in (scores.get("judges") or {}).items():
                if verdict:
                    lf.score(trace_id=trace.id, name=f"{pipeline}.{judge}", value=float(verdict["score"]), comment=verdict["reason"])
            lf.flush()
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Langfuse scoring skipped: {e}")
