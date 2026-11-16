"""
Neo4j client: schema, bulk loading and graph retrieval.

Retrieval = "find seed entities that match the question, then walk semantic edges 1-2 hops". Document nodes are
deliberately NOT walked through (a document mentions everything, so a 2-hop walk through it would return the whole
graph); they are only attached afterwards as provenance of the seed entities.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

from backend.ingestion.knowledge import FAULT_CODE_RE, STOPWORDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)

SEMANTIC_RELS = "RAISES|INDICATED_BY|IN_SUBSYSTEM|AFFECTS|PARTNERS_WITH|OFFERS|DEVELOPS|USES_TECH"
PROVENANCE_RELS = "DOCUMENTS|MENTIONS|DESCRIBES|ABOUT|COVERS"
SHOWN_PROPS = ("tier", "subsystem", "severity", "led_state", "root_cause", "remediation", "sel_event", "summary", "state", "type")


class Neo4jGraphClient:
    """Connection + Cypher helpers. `driver is None` means 'not connected' (the API reports it, nothing is faked)."""

    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:17687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "syone2026")
        self.driver = None
        self._connect()

    def _connect(self):
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
            self._init_constraints()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Neo4j not reachable at {self.uri}: {e}")
            self.driver = None

    def reconnect(self) -> bool:
        if self.driver is None:
            self._connect()
        return self.driver is not None

    def _init_constraints(self):
        labels = ["Document", "Partner", "Service", "DeliveryModel", "Solution", "Technology", "Organization", "Component",
                  "ErrorCode", "Subsystem", "LEDState", "Part", "VisualDiagram", "Certification", "Location", "Event"]
        with self.driver.session() as session:
            for label in labels:
                session.run(f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS FOR (n:`{label}`) REQUIRE n.id IS UNIQUE")
            session.run("CREATE INDEX node_corpus IF NOT EXISTS FOR (n:Document) ON (n.corpus)")

    # ------------------------------------------------------------------ generic
    def run_cypher(self, query: str, **params) -> List[Dict[str, Any]]:
        """Runs a Cypher query and returns the rows as dicts (used by the notebooks)."""
        if not self.driver:
            raise RuntimeError("Neo4j is not connected (is `docker compose up` running?)")
        with self.driver.session() as session:
            return [r.data() for r in session.run(query, **params)]

    def clear_corpus(self, corpus: str):
        if self.driver:
            self.run_cypher("MATCH (n {corpus: $c}) DETACH DELETE n", c=corpus)

    def stats(self) -> Dict[str, Any]:
        if not self.driver:
            return {"connected": False}
        nodes = self.run_cypher("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY n DESC")
        rels = self.run_cypher("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS n ORDER BY n DESC")
        return {"connected": True, "nodes": nodes, "relationships": rels,
                "total_nodes": sum(r["n"] for r in nodes), "total_relationships": sum(r["n"] for r in rels)}

    # ------------------------------------------------------------------ loading
    def insert_many(self, extractions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Loads several extraction results: ALL nodes first, then ALL relationships (so cross-document links resolve)."""
        if not self.driver:
            return {"nodes": 0, "relationships": 0}
        n_nodes = n_rels = 0
        with self.driver.session() as session:
            for ex in extractions:
                for node in ex.get("nodes", []):
                    props = dict(node.get("properties", {}))
                    props["id"] = node["id"]
                    props.setdefault("corpus", ex.get("corpus", ""))
                    session.run(f"MERGE (n:`{node['label']}` {{id: $id}}) SET n += $props", id=node["id"], props=props)
                    n_nodes += 1
            for ex in extractions:
                for rel in ex.get("relationships", []):
                    res = session.run(
                        f"MATCH (s {{id: $s}}) MATCH (t {{id: $t}}) MERGE (s)-[r:`{rel['type']}`]->(t) RETURN count(r) AS c",
                        s=rel["source"], t=rel["target"]).single()
                    n_rels += res["c"] if res else 0
        return {"nodes": n_nodes, "relationships": n_rels}

    def insert_graph_data(self, extraction_result: Dict[str, Any]):
        return self.insert_many([extraction_result])

    # ------------------------------------------------------------------ retrieval
    @staticmethod
    def extract_keywords(query: str) -> List[str]:
        """Question -> graph search terms: fault codes first (exact), then content words."""
        terms: List[str] = []
        for m in FAULT_CODE_RE.finditer(query):
            terms += [m.group(0).lower(), m.group(1).lower()]
        for tok in re.findall(r"[A-Za-z0-9][A-Za-z0-9_\-\.#/]*", query):
            low = tok.lower().strip(".-")
            if len(low) >= 3 and low not in STOPWORDS and low not in terms:
                terms.append(low)
        return terms[:14]

    def query_graph_neighborhood(self, keywords: List[str], corpus: Optional[str] = None, hops: int = 2) -> Dict[str, Any]:
        if not self.driver:
            return {"available": False, "nodes": [], "relationships": [], "seeds": [],
                    "formatted_context": "(Knowledge graph unavailable: Neo4j is not connected.)"}
        corpus_filter = "AND n.corpus = $corpus" if corpus else ""
        seed_q = f"""
        MATCH (n) WHERE NOT n:Document AND NOT n:VisualDiagram {corpus_filter}
        WITH n, [k IN $keywords WHERE toLower(coalesce(n.name,'')) CONTAINS k
                                   OR toLower(coalesce(n.code,'')) = k
                                   OR toLower(n.id) CONTAINS k] AS hits
        WHERE size(hits) > 0
        RETURN n, size(hits) AS score ORDER BY score DESC, size(split(n.name,' ')) ASC LIMIT 6
        """
        walk_q = f"""
        MATCH (n {{id: $id}})
        MATCH p = (n)-[:{SEMANTIC_RELS}*1..{max(1, min(hops, 2))}]-(m)
        RETURN p LIMIT 25
        """
        prov_q = f"""
        MATCH (n {{id: $id}})<-[r:{PROVENANCE_RELS}]-(d:Document) RETURN d.name AS doc, d.doc_id AS doc_id, type(r) AS rel LIMIT 5
        """
        nodes: Dict[str, Dict[str, Any]] = {}
        links, lines, seeds = {}, [], []

        def add_node(node):
            nid = node.get("id", str(node.element_id))
            nodes[nid] = {"id": nid, "label": next(iter(node.labels), "Node"), "name": node.get("name", nid),
                          "properties": {k: v for k, v in dict(node).items() if k in SHOWN_PROPS or k in ("name", "code")}}
            return nid

        with self.driver.session() as session:
            for rec in session.run(seed_q, keywords=[k.lower() for k in keywords], corpus=corpus):
                seed = rec["n"]
                sid = add_node(seed)
                seeds.append(sid)
                facts = "; ".join(f"{k}={v}" for k, v in nodes[sid]["properties"].items() if k not in ("name",) and v)
                lines.append(f"* {nodes[sid]['label']} '{nodes[sid]['name']}': {facts}" if facts else f"* {nodes[sid]['label']} '{nodes[sid]['name']}'")
                for rec2 in session.run(walk_q, id=sid):
                    for rel in rec2["p"].relationships:
                        a, b = add_node(rel.start_node), add_node(rel.end_node)
                        key = (a, b, rel.type)
                        if key not in links:
                            links[key] = {"source": a, "target": b, "type": rel.type}
                            lines.append(f"  ({nodes[a]['name']}) -[:{rel.type}]-> ({nodes[b]['name']})")
                for rec3 in session.run(prov_q, id=sid):
                    lines.append(f"  (source: {rec3['doc']} [{rec3['rel']}])")
                    did = f"doc:{corpus}:{rec3['doc_id']}" if corpus else rec3["doc_id"]
                    nodes.setdefault(did, {"id": did, "label": "Document", "name": rec3["doc"], "properties": {}})
                    links.setdefault((did, sid, rec3["rel"]), {"source": did, "target": sid, "type": rec3["rel"]})

        return {"available": True, "seeds": seeds, "nodes": list(nodes.values()), "relationships": list(links.values()),
                "formatted_context": "\n".join(dict.fromkeys(lines)) or "(No graph entities matched this question.)"}

    def close(self):
        if self.driver:
            self.driver.close()
