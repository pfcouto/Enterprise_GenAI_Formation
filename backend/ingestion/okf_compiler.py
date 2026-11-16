"""
Google Open Knowledge Format (OKF) compiler.

Turns parsed documents into an "LLM-wiki": a folder per corpus of Markdown files with strict YAML frontmatter
(type, title, summary, tags, entities, related, images) plus an INDEX.md that is the agent's entry point.

Everything is derived from the documents themselves:
  * type      <- the page section (scraped pages) or the document kind (manuals)
  * entities  <- gazetteer mentions (backend/ingestion/knowledge.py)
  * related   <- explicit mentions of other documents' titles + overlap of entities (computed across the corpus)
"""

import re
import yaml
from pathlib import Path
from typing import Any, Dict, List

from backend.ingestion.knowledge import (
    FAULT_CODE_RE, HARDWARE_COMPONENTS, SECTION_ENTITY_KIND, SYONE_OTHER, SYONE_PARTNERS, SYONE_TECHNOLOGIES,
    find_mentions,
)

MAX_RELATED = 4


class OKFCompiler:
    """Compiles parsed documents of one corpus into canonical OKF Markdown files."""

    def __init__(self, okf_root_dir: Path):
        self.okf_root_dir = okf_root_dir
        self.okf_root_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ public
    def compile_corpus(self, parsed_docs: List[Dict[str, Any]]) -> List[Path]:
        """Compiles all documents of (possibly several) corpora; related links need the whole corpus."""
        by_corpus: Dict[str, List[Dict[str, Any]]] = {}
        for d in parsed_docs:
            by_corpus.setdefault(d["corpus"], []).append(d)

        written: List[Path] = []
        for corpus, docs in by_corpus.items():
            meta = {d["doc_id"]: self._describe(d) for d in docs}
            for d in docs:
                d_meta = meta[d["doc_id"]]
                d_meta["related"] = self._related(d, d_meta, docs, meta)
                written.append(self._write(d, d_meta))
            self._write_index(corpus, docs, meta)
        return written

    def compile_document(self, parsed_doc: Dict[str, Any]) -> Path:
        """Single-document convenience (no cross-corpus related links beyond mentions)."""
        return self.compile_corpus([parsed_doc])[0]

    # ------------------------------------------------------------------ describe
    def _describe(self, d: Dict[str, Any]) -> Dict[str, Any]:
        corpus, text = d["corpus"], d.get("markdown_content", "")
        entities: List[str] = []
        tags = [corpus, "enterprise-ai", "formation"]

        if corpus == "syone_corp":
            section = d.get("section") or "company"
            doc_type = {"partners": "partner_profile", "what-we-do": "service_practice", "how-we-do-it": "delivery_model",
                        "technologies": "technology_page", "ezsearch-syone": "solution_page", "news": "news_item",
                        "blog": "technical_article", "home": "corporate_overview", "about": "corporate_overview",
                        "careers": "corporate_info", "contact-us": "corporate_info"}.get(section, "corporate_knowledge")
            entities += find_mentions(text, SYONE_PARTNERS) + find_mentions(text, SYONE_TECHNOLOGIES)
            for vocab in SYONE_OTHER.values():
                entities += find_mentions(text, vocab)
            tags += ["syone", section]
            has_faq = bool(re.search(r"^##\s+Frequently asked questions", text, re.M | re.I))
            if has_faq:
                tags.append("faq")
        else:
            section = "manual"
            codes = sorted({m.group(0) for m in FAULT_CODE_RE.finditer(text)})
            low_id = d["doc_id"].lower()
            doc_type = ("fault_reference" if "fault" in low_id else "service_manual" if "manual" in low_id or "power" in low_id
                        else "operations_guide" if "guide" in low_id else "release_notes" if "release" in low_id
                        else "system_overview" if "overview" in low_id else "hardware_documentation")
            entities += find_mentions(text, HARDWARE_COMPONENTS)
            tags += ["aurora-aor3", "hardware", "troubleshooting"]
            if codes:
                tags.append("fault-codes")
            entities += codes[:25]

        summary = d.get("summary_hint") or self._summary(text, d["title"])
        return {"type": doc_type, "section": section, "tags": sorted(set(tags)), "entities": sorted(set(entities)),
                "summary": summary[:300]}

    @staticmethod
    def _summary(text: str, title: str) -> str:
        for para in re.split(r"\n\s*\n", text):
            p = para.strip()
            if len(p) > 60 and not p.startswith(("#", "|", "!", ">", "-", "Document ref")):
                return re.sub(r"\s+", " ", p)
        return f"Canonical knowledge document: {title}"

    def _related(self, d, d_meta, docs, meta) -> List[str]:
        text_low = d.get("markdown_content", "").lower()
        mine = set(d_meta["entities"])
        scored = []
        for o in docs:
            if o["doc_id"] == d["doc_id"]:
                continue
            score = 0.0
            title = o["title"].lower()
            if len(title) > 8 and title in text_low:
                score += 3  # explicit cross-reference by title (manuals do this a lot)
            theirs = set(meta[o["doc_id"]]["entities"])
            if mine and theirs:
                score += 2 * len(mine & theirs) / len(mine | theirs)
            if d_meta["section"] == meta[o["doc_id"]]["section"]:
                score += 0.2
            if score > 0.35:
                scored.append((score, o["doc_id"]))
        scored.sort(reverse=True)
        return [f"./{doc_id}.md" for _, doc_id in scored[:MAX_RELATED]]

    # ------------------------------------------------------------------ write
    def _write(self, d: Dict[str, Any], m: Dict[str, Any]) -> Path:
        corpus, doc_id = d["corpus"], d["doc_id"]
        target_dir = self.okf_root_dir / corpus
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{doc_id}.md"

        frontmatter = {
            "type": m["type"], "title": d["title"], "corpus": corpus, "doc_id": doc_id, "section": m["section"],
            "source": d.get("source_url") or d.get("source_path", ""), "parsed_with": d.get("ocr_engine_used", ""),
            "tags": m["tags"], "entities": m["entities"], "summary": m["summary"], "related": m["related"],
            "images": d.get("images", []),
        }
        header = yaml.dump(frontmatter, sort_keys=False, default_flow_style=False, allow_unicode=True, width=1000)
        body = d.get("markdown_content", "").strip()
        target.write_text(f"---\n{header}---\n\n{body}\n", encoding="utf-8")
        return target

    def _write_index(self, corpus: str, docs: List[Dict[str, Any]], meta: Dict[str, Dict[str, Any]]):
        lines = [f"# OKF index: {corpus}", "",
                 "Entry point for agents. One line per document: `file` - type - summary. Read this first, then open files.", ""]
        for d in sorted(docs, key=lambda x: (meta[x["doc_id"]]["section"], x["doc_id"])):
            m = meta[d["doc_id"]]
            lines.append(f"- `{d['doc_id']}.md` - {m['type']} - **{d['title']}**: {m['summary'][:140]}")
        (self.okf_root_dir / corpus / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
