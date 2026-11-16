"""
Entity & relationship extractor for the knowledge graph (Neo4j).

Rule-based and fully data-driven: gazetteers say WHAT to look for (backend/ingestion/knowledge.py); the facts
(tiers, fault-code causes, LED states, remediation steps...) are read from the OKF documents themselves.
That is the point of this module in the formation: you can read it top to bottom and see exactly why each node exists.
An LLM-based extractor is the usual upgrade path (see notebook 02, "going further").

Graph model
  Syone corpus:    (Organization)-[:PARTNERS_WITH]->(Partner), (Organization)-[:OFFERS]->(Service), (Organization)-[:DEVELOPS]->(Solution),
                   (Organization)-[:USES_TECH]->(Technology), (Document)-[:MENTIONS]->(Partner|Technology|Certification|Location|Event)
  Hardware corpus: (Component)-[:RAISES]->(ErrorCode)-[:INDICATED_BY]->(LEDState), (ErrorCode)-[:IN_SUBSYSTEM]->(Subsystem),
                   (ErrorCode)-[:AFFECTS]->(Part), (Document)-[:DOCUMENTS]->(ErrorCode), (Document)-[:CONTAINS_VISUAL]->(VisualDiagram)
"""

import re
from pathlib import Path
from typing import Any, Dict, List

from backend.graph_rag.chunker import split_frontmatter
from backend.ingestion.knowledge import (
    FAULT_CODE_RE, FRU_RE, HARDWARE_COMPONENTS, SECTION_ENTITY_KIND, SYONE_OTHER, SYONE_PARTNERS, SYONE_TECHNOLOGIES,
    find_mentions,
)

SUBSYSTEM_COMPONENT = {  # which hardware component raises faults of a subsystem (read from the manuals' structure)
    "Power VRM": "PS-3000 power shelf", "Power shelf": "PS-3000 power shelf", "Thermal": "FW-6 fan wall",
    "PMBus": "BMC (OpenBMC)", "BMC": "BMC (OpenBMC)", "DDR5 Memory": "CS-2U compute sled", "Storage": "CS-2U compute sled",
    "Network PHY": "AS-100G switch", "Security": "BMC (OpenBMC)", "Liquid cooling": "FW-6 fan wall",
}


class EntityExtractor:
    """Extracts typed nodes and relationships from a canonical OKF file."""

    def extract_from_okf_file(self, okf_path: Path) -> Dict[str, Any]:
        fm, body = split_frontmatter(okf_path.read_text(encoding="utf-8"))
        corpus = fm.get("corpus", okf_path.parent.name)
        doc_id = fm.get("doc_id", okf_path.stem)
        doc_node = f"doc:{corpus}:{doc_id}"

        nodes: List[Dict[str, Any]] = [{
            "id": doc_node, "label": "Document",
            "properties": {"name": fm.get("title", doc_id), "doc_id": doc_id, "corpus": corpus, "type": fm.get("type", "document"),
                           "summary": fm.get("summary", ""), "source": fm.get("source", "")},
        }]
        rels: List[Dict[str, str]] = []

        if corpus == "syone_corp":
            self._syone(fm, body, doc_node, nodes, rels)
        else:
            self._hardware(fm, body, doc_node, nodes, rels)

        for img in fm.get("images", []) or []:
            img_id = f"img:{corpus}:{Path(img['path']).stem}"
            nodes.append({"id": img_id, "label": "VisualDiagram", "properties": {
                "name": img.get("caption", img_id)[:80], "caption": img.get("caption", ""), "path": img["path"],
                "description": (img.get("description") or "")[:400], "corpus": corpus}})
            rels.append({"source": doc_node, "target": img_id, "type": "CONTAINS_VISUAL"})

        for rel in fm.get("related", []) or []:
            rels.append({"source": doc_node, "target": f"doc:{corpus}:{Path(rel).stem}", "type": "RELATED_TO"})

        return {"doc_id": doc_id, "corpus": corpus, "nodes": self._dedupe(nodes), "relationships": rels}

    # ------------------------------------------------------------------ Syone
    def _syone(self, fm, body, doc_node, nodes, rels):
        org = "org:syone"
        nodes.append({"id": org, "label": "Organization", "properties": {
            "name": "Syone", "location": "Lisbon, Portugal", "founded": "1999", "focus": "Open source, IT services, digital transformation"}})
        rels.append({"source": doc_node, "target": org, "type": "ABOUT"})

        section, title = fm.get("section", ""), fm.get("title", "")
        kind = SECTION_ENTITY_KIND.get(section)
        text = f"{title}\n{body}"

        if kind == "Partner":
            name = next(iter(find_mentions(title, SYONE_PARTNERS)), None) or next(iter(find_mentions(text[:600], SYONE_PARTNERS)), None)
            if name:
                nodes.append({"id": f"partner:{self._slug(name)}", "label": "Partner",
                              "properties": {"name": name, "tier": self._tier(text)}})
                rels.append({"source": org, "target": f"partner:{self._slug(name)}", "type": "PARTNERS_WITH"})
                rels.append({"source": doc_node, "target": f"partner:{self._slug(name)}", "type": "DESCRIBES"})
        elif kind in ("Service", "DeliveryModel"):
            sid = f"{kind.lower()}:{self._slug(title)}"
            nodes.append({"id": sid, "label": kind, "properties": {"name": re.sub(r"\s*[|-]\s*Syone.*$", "", title)[:80], "summary": fm.get("summary", "")}})
            rels.append({"source": org, "target": sid, "type": "OFFERS"})
            rels.append({"source": doc_node, "target": sid, "type": "DESCRIBES"})
        elif kind == "Solution":
            nodes.append({"id": "solution:ezsearch", "label": "Solution", "properties": {
                "name": "ezSearch", "type": "AI-powered enterprise search", "vendor": "Syone", "summary": fm.get("summary", "")}})
            rels.append({"source": org, "target": "solution:ezsearch", "type": "DEVELOPS"})
            rels.append({"source": doc_node, "target": "solution:ezsearch", "type": "DESCRIBES"})
        elif kind == "Technology":
            name = find_mentions(title, SYONE_TECHNOLOGIES)
            if name:
                tid = f"tech:{self._slug(name[0])}"
                nodes.append({"id": tid, "label": "Technology", "properties": {"name": name[0]}})
                rels.append({"source": org, "target": tid, "type": "USES_TECH"})
                rels.append({"source": doc_node, "target": tid, "type": "DESCRIBES"})

        for canon in find_mentions(text, SYONE_PARTNERS):
            nodes.append({"id": f"partner:{self._slug(canon)}", "label": "Partner", "properties": {"name": canon}})
            rels.append({"source": doc_node, "target": f"partner:{self._slug(canon)}", "type": "MENTIONS"})
        for canon in find_mentions(text, SYONE_TECHNOLOGIES):
            nodes.append({"id": f"tech:{self._slug(canon)}", "label": "Technology", "properties": {"name": canon}})
            rels.append({"source": doc_node, "target": f"tech:{self._slug(canon)}", "type": "MENTIONS"})
        for label, vocab in SYONE_OTHER.items():
            for canon in find_mentions(text, vocab):
                nid = f"{label.lower()}:{self._slug(canon)}"
                nodes.append({"id": nid, "label": label, "properties": {"name": canon}})
                rels.append({"source": doc_node, "target": nid, "type": "MENTIONS"})

    @staticmethod
    def _tier(text: str) -> str:
        m = re.search(r"\b(Premier|Elite|Gold|Silver|Certified|Official|Advanced|Solutions?)\s+(?:Partner|Provider)", text, re.I)
        return m.group(0) if m else "Partner"

    # ------------------------------------------------------------------ hardware
    def _hardware(self, fm, body, doc_node, nodes, rels):
        for comp in find_mentions(body, HARDWARE_COMPONENTS):
            nodes.append({"id": f"component:{self._slug(comp)}", "label": "Component", "properties": {"name": comp}})
            rels.append({"source": doc_node, "target": f"component:{self._slug(comp)}", "type": "COVERS"})

        # Fault-code table rows: | Code | Subsystem | Severity | LED state | Root cause | Remediation | SEL event |
        header: List[str] = []
        for line in body.splitlines():
            if not line.strip().startswith("|"):
                header = []
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            if not header:
                header = [c.lower() for c in cells]
                continue
            if not cells or not FAULT_CODE_RE.fullmatch(cells[0].replace("`", "").strip()):
                continue
            row = dict(zip(header, cells))
            self._error_code(row, doc_node, nodes, rels)

        # Codes only mentioned in prose still become nodes (name only) so cross-document links work
        for m in FAULT_CODE_RE.finditer(body):
            code = m.group(0)
            nodes.append({"id": f"code:{m.group(1)}", "label": "ErrorCode", "properties": {"name": code, "code": m.group(1)}})
            rels.append({"source": doc_node, "target": f"code:{m.group(1)}", "type": "DOCUMENTS"})

        for part in sorted({m.group(1) for m in FRU_RE.finditer(body)}):
            if re.fullmatch(r"R[1-6]", part):
                continue  # too ambiguous outside the power-shelf context
            nodes.append({"id": f"part:{self._slug(part)}", "label": "Part", "properties": {"name": part}})

    def _error_code(self, row: Dict[str, str], doc_node, nodes, rels):
        raw = next((v for k, v in row.items() if k.startswith("code")), "").replace("`", "").strip()
        m = FAULT_CODE_RE.fullmatch(raw)
        if not m:
            return
        cid = f"code:{m.group(1)}"
        get = lambda *keys: next((row[k] for k in row if any(k.startswith(x) for x in keys)), "")  # noqa: E731
        subsystem, severity, led = get("subsys"), get("sev"), get("led")
        props = {"name": raw, "code": m.group(1), "subsystem": subsystem, "severity": severity, "led_state": led,
                 "root_cause": get("root"), "remediation": get("remed"), "sel_event": get("sel")}
        nodes.append({"id": cid, "label": "ErrorCode", "properties": {k: v for k, v in props.items() if v}})
        rels.append({"source": doc_node, "target": cid, "type": "DOCUMENTS"})
        if subsystem:
            sid = f"subsystem:{self._slug(subsystem)}"
            nodes.append({"id": sid, "label": "Subsystem", "properties": {"name": subsystem}})
            rels.append({"source": cid, "target": sid, "type": "IN_SUBSYSTEM"})
            comp = SUBSYSTEM_COMPONENT.get(subsystem)
            if comp:
                cmp_id = f"component:{self._slug(comp)}"
                nodes.append({"id": cmp_id, "label": "Component", "properties": {"name": comp}})
                rels.append({"source": cmp_id, "target": cid, "type": "RAISES"})
        if led:
            lid = f"led:{self._slug(led)}"
            nodes.append({"id": lid, "label": "LEDState", "properties": {"name": led}})
            rels.append({"source": cid, "target": lid, "type": "INDICATED_BY"})
        for part in {p.group(1) for p in FRU_RE.finditer(f"{get('root')} {get('remed')}")}:
            if re.fullmatch(r"R[1-6]", part):
                continue
            pid = f"part:{self._slug(part)}"
            nodes.append({"id": pid, "label": "Part", "properties": {"name": part}})
            rels.append({"source": cid, "target": pid, "type": "AFFECTS"})

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _slug(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:60]

    @staticmethod
    def _dedupe(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged: Dict[str, Dict[str, Any]] = {}
        for n in nodes:
            if n["id"] in merged:
                merged[n["id"]]["properties"].update({k: v for k, v in n["properties"].items() if v})
            else:
                merged[n["id"]] = {"id": n["id"], "label": n["label"], "properties": dict(n["properties"])}
        return list(merged.values())
