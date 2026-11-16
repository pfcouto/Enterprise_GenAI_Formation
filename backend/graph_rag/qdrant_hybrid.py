"""
Qdrant hybrid store: dense semantic vectors + BM25 sparse vectors in ONE collection, fused with Reciprocal Rank Fusion.

  dense  : BAAI/bge-small-en-v1.5 (384-d, ONNX, local)             -> good at paraphrase ("fan stopped spinning")
  bm25   : Qdrant/bm25 sparse vectors with server-side IDF modifier -> good at exact tokens ("0x4A7B_VRM_OVERVOLT")
  fusion : RRF in Python (so you can print both ranks and SEE why a chunk won)

Both indexes live in Qdrant, so they survive restarts and are shared by the notebooks and the API
(the first version kept BM25 in process memory, which silently emptied it after every restart).
"""

import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).parent.parent.parent
FASTEMBED_CACHE = str(WORKSPACE_ROOT / "models" / "fastembed")
_NS = uuid.UUID("6f1f2b7e-2a53-4a52-9c7a-5b1c4c4d9a11")
RRF_K = 60


class QdrantHybridStore:
    """Manages the hybrid collection. `client is None` means Qdrant is unreachable (reported, never faked)."""

    def __init__(self, host: str = None, port: int = None, collection_name: str = "syone_knowledge_hybrid"):
        self.host = host or os.getenv("QDRANT_HOST", "localhost")
        self.port = int(port or os.getenv("QDRANT_PORT", 16333))
        self.collection_name = collection_name
        self.client = None
        self.dense = None
        self.sparse = None
        self._init_client()
        self._init_embedders()

    # ------------------------------------------------------------------ setup
    def _init_client(self):
        try:
            from qdrant_client import QdrantClient
            self.client = QdrantClient(host=self.host, port=self.port, timeout=10.0)
            self.client.get_collections()
            self._ensure_collection()
            logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Qdrant not reachable at {self.host}:{self.port}: {e}")
            self.client = None

    def reconnect(self) -> bool:
        if self.client is None:
            self._init_client()
        return self.client is not None

    def _ensure_collection(self):
        from qdrant_client.http import models
        names = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config={"dense": models.VectorParams(size=384, distance=models.Distance.COSINE)},
                sparse_vectors_config={"bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)},
            )
            self.client.create_payload_index(self.collection_name, "corpus", models.PayloadSchemaType.KEYWORD)
            logger.info(f"Created Qdrant collection '{self.collection_name}' (dense + bm25)")

    def _init_embedders(self):
        try:
            from fastembed import SparseTextEmbedding, TextEmbedding
            self.dense = TextEmbedding(model_name="BAAI/bge-small-en-v1.5", cache_dir=FASTEMBED_CACHE)
            self.sparse = SparseTextEmbedding(model_name="Qdrant/bm25", cache_dir=FASTEMBED_CACHE)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Embedding models could not be loaded: {e}")

    @property
    def ready(self) -> bool:
        return self.client is not None and self.dense is not None and self.sparse is not None

    @staticmethod
    def _sparse_text(text: str) -> str:
        # The BM25 tokenizer keeps "0x4A7B_VRM_OVERVOLT" as ONE token; also index the split form so "0x4A7B" alone matches.
        return text + " " + re.sub(r"[_\-/]", " ", text)

    # ------------------------------------------------------------------ indexing
    def reset(self, corpus: Optional[str] = None):
        """Deletes all points (or only one corpus) so re-running indexing never duplicates chunks."""
        if not self.client:
            return
        from qdrant_client.http import models
        if corpus:
            self.client.delete(self.collection_name, points_selector=models.FilterSelector(
                filter=models.Filter(must=[models.FieldCondition(key="corpus", match=models.MatchValue(value=corpus))])))
        else:
            self.client.delete_collection(self.collection_name)
            self._ensure_collection()

    def index_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 64) -> int:
        """Embeds (dense + BM25) and upserts chunks. Point ids are deterministic -> idempotent."""
        if not chunks:
            return 0
        if not self.ready:
            raise RuntimeError("Qdrant or the embedding models are not available; cannot index.")
        from qdrant_client.http import models
        total = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c["text"] for c in batch]
            dense_vecs = list(self.dense.embed(texts))
            sparse_vecs = list(self.sparse.embed([self._sparse_text(t) for t in texts]))
            points = []
            for c, dv, sv in zip(batch, dense_vecs, sparse_vecs):
                cid = c.get("chunk_id") or f"{c.get('doc_id')}#{total}"
                points.append(models.PointStruct(
                    id=str(uuid.uuid5(_NS, cid)),
                    vector={"dense": dv.tolist(), "bm25": models.SparseVector(indices=sv.indices.tolist(), values=sv.values.tolist())},
                    payload={k: c.get(k) for k in ("chunk_id", "doc_id", "corpus", "title", "section", "kind", "text", "images")},
                ))
            self.client.upsert(self.collection_name, points=points)
            total += len(points)
        logger.info(f"Upserted {total} chunks into '{self.collection_name}'")
        return total

    def count(self, corpus: Optional[str] = None) -> int:
        if not self.client:
            return 0
        from qdrant_client.http import models
        flt = models.Filter(must=[models.FieldCondition(key="corpus", match=models.MatchValue(value=corpus))]) if corpus else None
        return self.client.count(self.collection_name, count_filter=flt, exact=True).count

    # ------------------------------------------------------------------ search
    def hybrid_search(self, query: str, corpus: Optional[str] = None, top_k: int = 5, candidates: int = 20) -> List[Dict[str, Any]]:
        if not self.ready:
            return []
        from qdrant_client.http import models
        flt = models.Filter(must=[models.FieldCondition(key="corpus", match=models.MatchValue(value=corpus))]) if corpus else None

        dvec = next(iter(self.dense.query_embed(query))).tolist()
        svec = next(iter(self.sparse.query_embed(self._sparse_text(query))))
        dense_hits = self.client.query_points(self.collection_name, query=dvec, using="dense", query_filter=flt,
                                              limit=candidates, with_payload=True).points
        sparse_hits = self.client.query_points(
            self.collection_name, query=models.SparseVector(indices=svec.indices.tolist(), values=svec.values.tolist()),
            using="bm25", query_filter=flt, limit=candidates, with_payload=True).points

        fused: Dict[str, Dict[str, Any]] = {}
        for method, hits in (("dense", dense_hits), ("bm25", sparse_hits)):
            for rank, h in enumerate(hits, 1):
                item = fused.setdefault(str(h.id), {**h.payload, "hybrid_score": 0.0, "dense_rank": None, "bm25_rank": None,
                                                    "dense_score": None, "bm25_score": None})
                item["hybrid_score"] += 1.0 / (RRF_K + rank)
                item[f"{method}_rank"], item[f"{method}_score"] = rank, round(float(h.score), 4)
        for item in fused.values():
            item["retrieval_method"] = ("hybrid_dense_and_bm25" if item["dense_rank"] and item["bm25_rank"]
                                        else "dense_vector" if item["dense_rank"] else "bm25_sparse")
            item["hybrid_score"] = round(item["hybrid_score"], 5)
        return sorted(fused.values(), key=lambda x: x["hybrid_score"], reverse=True)[:top_k]
