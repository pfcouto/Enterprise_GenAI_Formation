"""
Structure-aware chunker for canonical OKF documents.

Naive "split on blank lines" destroys exactly the things this formation is about: tables (one fault code per row)
and figure references. This chunker:
  * keeps the heading path ("3. Switch > 3.1 Port groups") with every chunk,
  * turns every table row into its own chunk, prefixed with the table's column names (so a row is searchable on
    its own: "Code: 0x4A7B_VRM_OVERVOLT | Subsystem: Power VRM | ..."),
  * packs prose paragraphs up to ~max_chars,
  * attaches the figures a chunk mentions (markdown image or "Figure F4").
"""

import re
from typing import Any, Dict, List, Tuple

IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
FIG_RE = re.compile(r"\bFigure\s+(F\d+)\b")


def split_frontmatter(raw: str) -> Tuple[Dict[str, Any], str]:
    import yaml
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            try:
                return yaml.safe_load(parts[1]) or {}, parts[2].strip()
            except Exception:  # noqa: BLE001
                pass
    return {}, raw


def _parse_table(lines: List[str], i: int):
    rows = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            rows.append(cells)
        i += 1
    return rows, i


def _images_for(text: str, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    hit = []
    paths = {m.group(2) for m in IMG_RE.finditer(text)}
    figs = set(FIG_RE.findall(text))
    for img in images:
        if img.get("path") in paths or (img.get("figure_id") and img["figure_id"] in figs):
            hit.append(img)
    return hit


def chunk_okf_document(frontmatter: Dict[str, Any], body: str, max_chars: int = 900) -> List[Dict[str, Any]]:
    doc_id = frontmatter.get("doc_id", "document")
    corpus = frontmatter.get("corpus", "")
    title = frontmatter.get("title", doc_id)
    images = frontmatter.get("images", []) or []

    lines = body.splitlines()
    path: List[Tuple[int, str]] = []
    chunks: List[Dict[str, Any]] = []
    buf: List[str] = []

    # "Document card": title, section and summary live in the frontmatter, not in the body. Without this chunk a fact that
    # only appears in a page's meta description (e.g. "Founded in 1999 in Lisbon ...") could never be retrieved.
    card = " | ".join(x for x in (f"Document: {title}", f"Type: {frontmatter.get('type', '')}", f"Section: {frontmatter.get('section', '')}",
                                  f"Summary: {frontmatter.get('summary', '')}", f"Source: {frontmatter.get('source', '')}") if not x.endswith(": "))
    if frontmatter.get("summary"):
        chunks.append({"chunk_id": f"{doc_id}#card", "doc_id": doc_id, "corpus": corpus, "title": title, "section": "summary",
                       "kind": "card", "text": card, "images": []})

    def heading_path() -> str:
        return " > ".join(h for _, h in path)

    def emit(text: str, kind: str):
        text = text.strip()
        if len(text) < 25:
            return
        chunks.append({
            "chunk_id": f"{doc_id}#{len(chunks):03d}", "doc_id": doc_id, "corpus": corpus, "title": title,
            "section": heading_path(), "kind": kind,
            "text": f"{title} | {heading_path()}\n{text}" if heading_path() else f"{title}\n{text}",
            "images": _images_for(text, images),
        })

    def flush():
        nonlocal buf
        text = "\n".join(buf).strip()
        buf = []
        while len(text) > max_chars:
            cut = text.rfind(". ", 0, max_chars)
            cut = cut + 1 if cut > max_chars // 2 else max_chars
            emit(text[:cut], "text")
            text = text[cut:].strip()
        emit(text, "text")

    i = 0
    while i < len(lines):
        s = lines[i].strip()
        m = re.match(r"^(#{1,4})\s+(.*)", s)
        if m:
            flush()
            level = len(m.group(1))
            while path and path[-1][0] >= level:
                path.pop()
            path.append((level, m.group(2).strip()))
            i += 1
        elif IMG_RE.match(s):
            # A figure becomes its own chunk: caption + description (the text that stands for the pixels), image attached.
            flush()
            block, i = [s], i + 1
            while i < len(lines) and len(block) < 8 and (lines[i].strip() == "" or lines[i].lstrip().startswith((">", "*", "_"))):
                if lines[i].strip():
                    block.append(lines[i].strip())
                i += 1
            parts = [re.sub(r"^[>*_\s]+|[*_\s]+$", "", b) if not IMG_RE.match(b) else IMG_RE.match(b).group(1) for b in block]
            figure_text = " ".join(p for k, p in enumerate(parts) if p.rstrip(".") not in {q.rstrip(".") for q in parts[:k]})
            chunks.append({
                "chunk_id": f"{doc_id}#{len(chunks):03d}", "doc_id": doc_id, "corpus": corpus, "title": title,
                "section": heading_path(), "kind": "figure", "text": f"{title} | {heading_path()}\nFIGURE: {figure_text}",
                "images": _images_for(s, images) or _images_for(figure_text, images)})
        elif s.startswith("|"):
            flush()
            rows, i = _parse_table(lines, i)
            if len(rows) >= 2:
                header = rows[0]
                for row in rows[1:]:
                    pairs = [f"{h}: {v}" for h, v in zip(header, row) if v]
                    emit(" | ".join(pairs), "table_row")
            elif rows:
                emit(" | ".join(rows[0]), "text")
        elif not s:
            if sum(len(b) for b in buf) > max_chars * 0.6:
                flush()
            i += 1
        else:
            buf.append(s)
            i += 1
            if sum(len(b) for b in buf) > max_chars:
                flush()
    flush()
    return chunks
