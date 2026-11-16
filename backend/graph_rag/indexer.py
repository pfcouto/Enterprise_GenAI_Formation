"""
Indexer: OKF store -> chunks -> Qdrant (dense + BM25)  and  OKF store -> entities -> Neo4j.

Used by the API (POST /api/ingestion/run), by notebook 02, and from the command line:
    python -m backend.graph_rag.indexer            # (re)index every corpus found in data/okf_store
Re-running is safe: each corpus is cleared first, ids are deterministic.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.graph_rag.chunker import chunk_okf_document, split_frontmatter
from backend.graph_rag.entity_extractor import EntityExtractor
from backend.graph_rag.neo4j_client import Neo4jGraphClient
from backend.graph_rag.qdrant_hybrid import QdrantHybridStore

logger = logging.getLogger(__name__)
WORKSPACE_ROOT = Path(__file__).parent.parent.parent
OKF_STORE_DIR = WORKSPACE_ROOT / "data" / "okf_store"


def okf_files(corpus: str) -> List[Path]:
    d = OKF_STORE_DIR / corpus
    return sorted(p for p in d.glob("*.md") if p.name != "INDEX.md") if d.exists() else []


def build_chunks(corpus: str) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    for f in okf_files(corpus):
        fm, body = split_frontmatter(f.read_text(encoding="utf-8"))
        chunks.extend(chunk_okf_document(fm, body))
    return chunks


def index_okf_store(neo4j: Neo4jGraphClient, qdrant: QdrantHybridStore, corpora: Optional[List[str]] = None) -> Dict[str, Any]:
    corpora = corpora or sorted(p.name for p in OKF_STORE_DIR.iterdir() if p.is_dir()) if OKF_STORE_DIR.exists() else []
    report: Dict[str, Any] = {}
    extractor = EntityExtractor()
    for corpus in corpora:
        files = okf_files(corpus)
        if not files:
            continue
        info: Dict[str, Any] = {"documents": len(files)}
        chunks = build_chunks(corpus)
        info["chunks"] = len(chunks)
        if qdrant.reconnect() and qdrant.ready:
            qdrant.reset(corpus)
            info["qdrant_points"] = qdrant.index_chunks(chunks)
        else:
            info["qdrant_points"] = "skipped: Qdrant/embeddings unavailable"
        if neo4j.reconnect():
            neo4j.clear_corpus(corpus)
            neo4j.insert_many([extractor.extract_from_okf_file(f) for f in files])
            # unique counts (entities shared by many documents are merged into one node)
            info["graph"] = {
                "nodes": neo4j.run_cypher("MATCH (n {corpus: $c}) RETURN count(n) AS n", c=corpus)[0]["n"],
                "relationships": neo4j.run_cypher("MATCH (a {corpus: $c})-[r]->() RETURN count(r) AS n", c=corpus)[0]["n"]}
        else:
            info["graph"] = "skipped: Neo4j unavailable"
        report[corpus] = info
        logger.info(f"Indexed corpus '{corpus}': {info}")
    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    print(index_okf_store(Neo4jGraphClient(), QdrantHybridStore()))
