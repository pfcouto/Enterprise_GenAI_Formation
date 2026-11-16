"""
GraphRAG + BM25 track: hybrid retrieval (Qdrant dense + BM25) + graph facts (Neo4j) -> grounded answer.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from backend.graph_rag.neo4j_client import Neo4jGraphClient
from backend.graph_rag.qdrant_hybrid import QdrantHybridStore
from backend.llm import FIGURE_RULES, GRAPHRAG_PROMPT, GatewayError, chat, extractive_answer, figures_block

logger = logging.getLogger(__name__)


class GraphRAGPipeline:
    def __init__(self, neo4j_client: Neo4jGraphClient, qdrant_store: QdrantHybridStore):
        self.neo4j = neo4j_client
        self.qdrant = qdrant_store

    async def execute_query(self, query: str, corpus: Optional[str] = None, model_name: str = "formation-fast",
                            system_prompt: Optional[str] = None, top_k: int = 5, include_context: bool = False) -> Dict[str, Any]:
        start = time.time()
        self.qdrant.reconnect()
        self.neo4j.reconnect()

        chunks = self.qdrant.hybrid_search(query, corpus=corpus, top_k=top_k)
        keywords = self.neo4j.extract_keywords(query)
        graph = self.neo4j.query_graph_neighborhood(keywords, corpus=corpus, hops=2)

        images: List[Dict[str, Any]] = []
        for c in chunks:
            for img in c.get("images") or []:
                if img["path"] not in {i["path"] for i in images}:
                    images.append(img)

        text_context = "\n\n".join(f"--- [{i}] {c.get('title')} / {c.get('section', '')} ({c.get('doc_id')}) ---\n{c.get('text')}"
                                   for i, c in enumerate(chunks, 1)) or "(nothing retrieved: has the index been built? run notebook 02)"
        template = system_prompt or GRAPHRAG_PROMPT
        prompt = template.replace("{figure_rules}", FIGURE_RULES).replace("{text_context}", text_context) \
                         .replace("{graph_context}", graph["formatted_context"]).replace("{figures}", figures_block(images))

        llm_error, mode = None, "generated"
        try:
            answer = (await chat([{"role": "system", "content": prompt}, {"role": "user", "content": query}], model_name,
                                 temperature=0.2, max_tokens=3000)).get("content", "")
        except GatewayError as e:
            llm_error, mode = str(e), "extractive"
            answer = extractive_answer(chunks, images, llm_error)

        result = {
            "pipeline": "GraphRAG + BM25", "query": query, "corpus": corpus, "model_used": model_name,
            "answer": answer, "answer_mode": mode, "llm_error": llm_error,
            "latency_seconds": round(time.time() - start, 3), "retrieved_chunks": chunks, "keywords": keywords,
            "graph_subgraph": {"nodes": graph["nodes"], "relationships": graph["relationships"], "available": graph["available"]},
            "associated_images": images[:4],
            "context_chars": len(text_context) + len(graph["formatted_context"]),
            "retrieved_doc_ids": list(dict.fromkeys(c.get("doc_id") for c in chunks)),
        }
        if include_context:
            result["context_text"] = text_context + "\n" + graph["formatted_context"]
        return result
