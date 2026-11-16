"""
OKF navigation harness: an agent that explores the knowledge base with tools instead of searching a vector index.

Two modes, reported honestly in every response (`agent_mode`):
  * llm_tool_calling    - a tool-calling LLM (through the LiteLLM gateway) decides which tool to call next: the real thing.
  * scripted_navigation - deterministic planner (grep -> rank -> read -> follow links) used when no tool-calling LLM is
                          reachable. It exercises the same tools so the trajectory is still meaningful, but nothing is "agentic".
This is the pattern LangChain Deep Agents productises (planning, filesystem tools, sub-agents); here it is ~100 lines so
you can read all of it.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from backend.ingestion.knowledge import FAULT_CODE_RE, STOPWORDS
from backend.llm import FIGURE_RULES, GatewayError, OKF_PROMPT, chat
from backend.okf_agents.tools import (
    TOOL_SCHEMAS, follow_related_links, grep_okf, list_okf_topics, read_okf_document, run_tool,
)

logger = logging.getLogger(__name__)


def _brief(name: str, result: Any) -> str:
    """One-line observation for the trajectory shown in the UI."""
    if name == "read_okf_document":
        if isinstance(result, dict) and "error" in result:
            return result["error"]
        return f"read '{result['doc_id']}' ({len(result['content'])} chars, {len(result.get('images', []))} figures)"
    if name == "grep_okf":
        return "no matches" if not result else "matches in: " + ", ".join(f"{h['doc_id']} ({h['match_count']})" for h in result[:5])
    if name == "list_okf_topics":
        return f"{len(result)} documents listed"
    if name == "follow_related_links":
        return "linked: " + (", ".join(r["doc_id"] for r in result) or "none")
    return str(result)[:120]


class OKFDeepAgentHarness:
    def __init__(self, corpus: str = "syone_corp", max_steps: int = 6):
        self.corpus = corpus
        self.max_steps = max_steps

    # ------------------------------------------------------------------ LLM-driven
    async def run_agent(self, query: str, model_name: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        system = (system_prompt or OKF_PROMPT).replace("{figure_rules}", FIGURE_RULES)
        messages: List[Dict[str, Any]] = [{"role": "system", "content": system}, {"role": "user", "content": query}]
        trajectory: List[Dict[str, Any]] = []
        docs: Dict[str, Dict[str, Any]] = {}
        final: Optional[str] = None

        seen_calls: set = set()
        duplicates = 0
        for step in range(1, self.max_steps + 1):
            msg = await chat(messages, model_name, tools=TOOL_SCHEMAS, temperature=0.1, max_tokens=3000)
            calls = msg.get("tool_calls") or []
            if not calls:
                content = (msg.get("content") or "").strip()
                if content and "<tool_call>" not in content and "<function=" not in content:
                    final = content
                    break
                # Some models leak a tool call as plain text (or return nothing): do not present that as the answer.
                trajectory.append({"step": len(trajectory) + 1, "action": "(guard)", "args": {}, "observation": "model returned a malformed/empty reply; forcing a final answer"})
                break
            messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
            for call in calls:
                fn = call["function"]
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                key = (fn["name"], json.dumps(args, sort_keys=True))
                if key in seen_calls:  # loop guard: the model asked for the exact same call again
                    duplicates += 1
                    result = {"note": "You already made this exact call and have its result. Answer the question now using what you have read."}
                    trajectory.append({"step": len(trajectory) + 1, "action": fn["name"], "args": args, "observation": "duplicate call skipped"})
                else:
                    seen_calls.add(key)
                    result = run_tool(self.corpus, fn["name"], args)
                    if fn["name"] == "read_okf_document" and isinstance(result, dict) and "error" not in result:
                        docs[result["doc_id"]] = result
                    trajectory.append({"step": len(trajectory) + 1, "action": fn["name"], "args": args, "observation": _brief(fn["name"], result)})
                messages.append({"role": "tool", "tool_call_id": call.get("id", f"call_{step}"), "name": fn["name"],
                                 "content": json.dumps(result, ensure_ascii=False)[:90000]})
            if duplicates >= 2:
                break
        if final is None:  # ran out of steps, looped, or got a malformed reply: force an answer from what was read
            messages.append({"role": "user", "content": "Answer now, in plain text and without calling tools, using only what you have read."})
            final = (await chat(messages, model_name, temperature=0.1, max_tokens=3000)).get("content", "")
        return {"agent_mode": "llm_tool_calling", "trajectory": trajectory, "collected_documents": list(docs.values()),
                "final_answer": final, "attached_images": self._images(docs.values(), final)}

    # ------------------------------------------------------------------ deterministic
    def scripted_navigation(self, query: str) -> Dict[str, Any]:
        steps: List[Dict[str, Any]] = []
        topics = list_okf_topics(self.corpus)
        steps.append({"step": 1, "action": "list_okf_topics", "args": {}, "observation": f"{len(topics)} documents listed"})

        terms = [m.group(0) for m in FAULT_CODE_RE.finditer(query)]
        terms += [w for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9_\-\.]*", query)
                  if len(w) > 3 and w.lower() not in STOPWORDS and w not in terms]
        score: Dict[str, float] = {}
        for term in terms[:8]:
            hits = grep_okf(self.corpus, term)
            steps.append({"step": len(steps) + 1, "action": "grep_okf", "args": {"pattern": term}, "observation": _brief("grep_okf", hits)})
            weight = 3.0 if FAULT_CODE_RE.fullmatch(term) else 1.0
            for h in hits:
                score[h["doc_id"]] = score.get(h["doc_id"], 0) + weight * min(h["match_count"], 5)
        for t in topics:  # frontmatter signals (title / summary / entities)
            meta = f"{t['title']} {t['summary']} {' '.join(map(str, t.get('entities', [])))}".lower()
            score[t["doc_id"]] = score.get(t["doc_id"], 0) + sum(1.5 for term in terms if term.lower() in meta)

        ranked = [d for d, _ in sorted(score.items(), key=lambda kv: kv[1], reverse=True)][:2] or [topics[0]["doc_id"]] if topics else []
        docs: Dict[str, Dict[str, Any]] = {}
        for doc_id in ranked:
            doc = read_okf_document(self.corpus, doc_id)
            if "error" in doc:
                continue
            docs[doc["doc_id"]] = doc
            steps.append({"step": len(steps) + 1, "action": "read_okf_document", "args": {"doc_id": doc_id}, "observation": _brief("read_okf_document", doc)})
        if ranked and ranked[0] in docs:
            related = follow_related_links(self.corpus, ranked[0])
            steps.append({"step": len(steps) + 1, "action": "follow_related_links", "args": {"doc_id": ranked[0]}, "observation": _brief("follow_related_links", related)})
            for r in related[:1]:
                extra = read_okf_document(self.corpus, r["doc_id"])
                if "error" not in extra and extra["doc_id"] not in docs:
                    docs[extra["doc_id"]] = extra
                    steps.append({"step": len(steps) + 1, "action": "read_okf_document", "args": {"doc_id": r["doc_id"]}, "observation": _brief("read_okf_document", extra)})
        return {"agent_mode": "scripted_navigation", "trajectory": steps, "collected_documents": list(docs.values()),
                "final_answer": None, "attached_images": self._images(docs.values(), None)}

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _images(docs, answer: Optional[str], limit: int = 4) -> List[Dict[str, Any]]:
        """Figures of the opened documents; those already cited in the answer first."""
        imgs = [img for d in docs for img in d.get("images", [])]
        seen, out = set(), []
        cited = [i for i in imgs if answer and i["path"] in answer]
        for img in cited + [i for i in imgs if i not in cited]:
            if img["path"] not in seen:
                seen.add(img["path"])
                out.append(img)
        return out[:limit]
