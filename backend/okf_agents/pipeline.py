"""
Google OKF track: agentic navigation over the OKF wiki + answer synthesis from whole (un-chunked) documents.
"""

import logging
import time
from typing import Any, Dict, Optional

from backend.llm import FIGURE_RULES, GatewayError, OKF_SYNTH_PROMPT, chat, extractive_answer, figures_block
from backend.okf_agents.deep_agent_harness import OKFDeepAgentHarness

logger = logging.getLogger(__name__)
MAX_DOC_CHARS_IN_PROMPT = 24000


class OKFAgentPipeline:
    async def execute_query(self, query: str, corpus: str = "syone_corp", model_name: str = "formation-fast",
                            system_prompt: Optional[str] = None, include_context: bool = False) -> Dict[str, Any]:
        start = time.time()
        harness = OKFDeepAgentHarness(corpus=corpus)
        llm_error: Optional[str] = None
        nav: Optional[Dict[str, Any]] = None

        try:
            nav = await harness.run_agent(query, model_name, system_prompt)
            answer = nav["final_answer"]
        except GatewayError as e:
            llm_error = str(e)
            logger.warning(f"OKF agent: LLM tool-calling unavailable ({e}); using scripted navigation")
            nav = harness.scripted_navigation(query)
            answer = None

        docs, images = nav["collected_documents"], nav["attached_images"]
        mode = "generated"
        if answer is None:  # scripted navigation (or empty): synthesize from the opened documents
            sections = [f"=== {d['frontmatter'].get('title', d['doc_id'])} ({d['frontmatter'].get('type')}) ===\n{d['content'][:MAX_DOC_CHARS_IN_PROMPT]}" for d in docs]
            prompt = OKF_SYNTH_PROMPT.format(figure_rules=FIGURE_RULES, documents="\n\n".join(sections) or "(nothing opened)", figures=figures_block(images))
            try:
                answer = (await chat([{"role": "system", "content": prompt}, {"role": "user", "content": query}], model_name,
                                     temperature=0.2, max_tokens=3000)).get("content", "")
            except GatewayError as e:
                llm_error = llm_error or str(e)
                passages = [{"title": d["frontmatter"].get("title", d["doc_id"]), "text": d["content"]} for d in docs]
                answer, mode = extractive_answer(passages, images, llm_error), "extractive"

        result = {
            "pipeline": "Google OKF (agentic navigation)", "query": query, "corpus": corpus, "model_used": model_name,
            "answer": answer, "answer_mode": mode, "agent_mode": nav["agent_mode"], "llm_error": llm_error,
            "latency_seconds": round(time.time() - start, 3), "agent_trajectory": nav["trajectory"],
            "inspected_documents": [d["doc_id"] for d in docs], "associated_images": images,
            "context_chars": sum(len(d["content"]) for d in docs),
            "retrieved_doc_ids": [d["doc_id"] for d in docs],
        }
        if include_context:
            result["context_text"] = "\n".join(d["content"] for d in docs)
        return result
