"""
OKF agent tools: the four verbs an agent needs to navigate a Markdown knowledge base.

  list_okf_topics    - what documents exist (frontmatter summaries)          ~ `ls` + `head`
  grep_okf           - exact / regex search across documents                  ~ `grep -rn`
  read_okf_document  - the FULL document, no chunking                         ~ `cat`
  follow_related_links - the cross-links declared in the frontmatter         ~ following hyperlinks

They are plain Python functions (usable from notebooks) and are also exposed to LLMs as OpenAI-style tool schemas
(`TOOL_SCHEMAS`) so any tool-calling model can drive them.
"""

import re
import yaml
from pathlib import Path
from typing import Any, Dict, List

WORKSPACE_ROOT = Path(__file__).parent.parent.parent
OKF_STORE_DIR = WORKSPACE_ROOT / "data" / "okf_store"
MAX_DOC_CHARS = 60000


def _docs(corpus: str) -> List[Path]:
    d = OKF_STORE_DIR / corpus
    return sorted(p for p in d.glob("*.md") if p.name != "INDEX.md") if d.exists() else []


def _split(raw: str):
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            try:
                return yaml.safe_load(parts[1]) or {}, parts[2].strip()
            except Exception:  # noqa: BLE001
                pass
    return {}, raw


def list_okf_topics(corpus: str = "syone_corp") -> List[Dict[str, Any]]:
    """All documents of the corpus with their frontmatter summary."""
    topics = []
    for path in _docs(corpus):
        fm, _ = _split(path.read_text(encoding="utf-8"))
        topics.append({"doc_id": path.stem, "title": fm.get("title", path.stem), "type": fm.get("type", "document"),
                       "summary": fm.get("summary", ""), "tags": fm.get("tags", []), "entities": fm.get("entities", []),
                       "related": fm.get("related", [])})
    return topics


def read_okf_document(corpus: str, doc_id: str) -> Dict[str, Any]:
    """Full canonical document (frontmatter + body). `doc_id` may be given with or without '.md'."""
    stem = Path(doc_id).name.removesuffix(".md")  # Path().name blocks '../' traversal
    path = OKF_STORE_DIR / corpus / f"{stem}.md"
    if not path.exists():
        candidates = [p for p in _docs(corpus) if stem.lower() in p.stem.lower()]
        if not candidates:
            return {"error": f"Document '{stem}' not found in corpus '{corpus}'. Use list_okf_topics."}
        path = candidates[0]
    fm, body = _split(path.read_text(encoding="utf-8"))
    truncated = len(body) > MAX_DOC_CHARS
    return {"doc_id": path.stem, "corpus": corpus, "frontmatter": fm, "content": body[:MAX_DOC_CHARS],
            "truncated": truncated, "images": fm.get("images", []), "related": fm.get("related", [])}


def grep_okf(corpus: str, pattern: str, max_docs: int = 8) -> List[Dict[str, Any]]:
    """Case-insensitive literal search in every document; returns up to 5 matching lines per document."""
    regex = re.compile(re.escape(pattern.strip()), re.IGNORECASE)
    hits = []
    for path in _docs(corpus):
        matches = [{"line_number": n, "text": line.strip()[:240]}
                   for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1) if regex.search(line)]
        if matches:
            hits.append({"doc_id": path.stem, "match_count": len(matches), "matches": matches[:5]})
    hits.sort(key=lambda h: h["match_count"], reverse=True)
    return hits[:max_docs]


def follow_related_links(corpus: str, doc_id: str) -> List[Dict[str, Any]]:
    """Documents linked from the frontmatter `related:` list, with a short excerpt each."""
    doc = read_okf_document(corpus, doc_id)
    if "error" in doc:
        return []
    out = []
    for link in doc.get("related", []):
        target = read_okf_document(corpus, Path(link).name)
        if "error" not in target:
            out.append({"link": link, "doc_id": target["doc_id"], "title": target["frontmatter"].get("title", ""),
                        "summary": target["frontmatter"].get("summary", ""), "excerpt": target["content"][:300]})
    return out


# ---------------------------------------------------------------- LLM tool schemas
TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "list_okf_topics", "description": "List every document in the knowledge base with type, summary and tags.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "grep_okf", "description": "Exact, case-insensitive text search across all documents. Best for codes, part numbers, names.",
        "parameters": {"type": "object", "properties": {"pattern": {"type": "string", "description": "literal text to find"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {
        "name": "read_okf_document", "description": "Read one whole document (frontmatter + full body).",
        "parameters": {"type": "object", "properties": {"doc_id": {"type": "string", "description": "file name without .md"}}, "required": ["doc_id"]}}},
    {"type": "function", "function": {
        "name": "follow_related_links", "description": "List documents cross-linked from a document's frontmatter.",
        "parameters": {"type": "object", "properties": {"doc_id": {"type": "string"}}, "required": ["doc_id"]}}},
]


def run_tool(corpus: str, name: str, args: Dict[str, Any]) -> Any:
    """Dispatches a tool call coming from an LLM."""
    if name == "list_okf_topics":
        return [{k: t[k] for k in ("doc_id", "title", "type", "summary")} for t in list_okf_topics(corpus)]
    if name == "grep_okf":
        return grep_okf(corpus, str(args.get("pattern", "")))
    if name == "read_okf_document":
        return read_okf_document(corpus, str(args.get("doc_id", "")))
    if name == "follow_related_links":
        return follow_related_links(corpus, str(args.get("doc_id", "")))
    return {"error": f"unknown tool {name}"}
