"""
Document parser, running locally (weights live in ./models/):

  * docling_standard - Docling's classic pipeline: layout model + TableFormer (tables) + RapidOCR for scanned text.

(An earlier version also drove GLM-OCR, a 0.9B vision-language model, through Docling's VLM pipeline. Measured on
the 8 manuals it was 18 times slower even on the GPU and lost a table that crosses a page, so it was removed.)

Scraped Markdown/HTML pages need no OCR: they are read natively (engine reported as "native-markdown").

Figures: every figure that belongs to a document is attached with its caption AND a text description. For the
synthetic hardware manuals the description comes from the sidecar `figure_captions.json` that is generated together
with the images; for scraped pages it is the curated alt text. In a production pipeline this is the slot where a VLM
captioning step (or Docling's picture-description) would write its output.
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).parent.parent.parent
os.environ.setdefault("HF_HOME", str(WORKSPACE_ROOT / "models" / "huggingface"))
os.environ.setdefault("TORCH_HOME", str(WORKSPACE_ROOT / "models" / "torch"))
os.environ.setdefault("DOCLING_CACHE_DIR", str(WORKSPACE_ROOT / "models" / "docling"))

IMG_MD_RE = re.compile(r"!\[([^\]]*)\]\((/static/images/[^)]+)\)(?:\s*\n+> Figure description: ([^\n]+))?")
HEADER_FIELDS = ("Source", "Section", "Published", "Summary", "Scraped")


class DoclingDocumentParser:
    """Parses raw files into a uniform dict consumed by the OKF compiler."""

    def __init__(self, output_images_dir: Path, ocr_engine: str = "docling_standard", max_pages: Optional[int] = None):
        self.output_images_dir = output_images_dir
        self.output_images_dir.mkdir(parents=True, exist_ok=True)
        self.ocr_engine = ocr_engine.lower()
        self.max_pages = max_pages  # optional: parse only the first N pages of each PDF
        self._converter: Any = None

    # ------------------------------------------------------------------ engines
    def _get_converter(self):
        """Lazily builds (and caches) the Docling standard converter."""
        if self._converter is None:
            from docling.document_converter import DocumentConverter
            self._converter = DocumentConverter()
            logger.info("Docling standard pipeline ready (layout model + TableFormer + RapidOCR).")
        return self._converter

    # ------------------------------------------------------------------ public API
    def parse_document(self, file_path: Path, corpus: str, override_engine: Optional[str] = None) -> Dict[str, Any]:
        engine = (override_engine or self.ocr_engine).lower()
        suffix = file_path.suffix.lower()
        doc_id = file_path.stem
        started = time.time()
        meta: Dict[str, Any] = {}

        if suffix in (".md", ".markdown", ".txt"):
            raw = file_path.read_text(encoding="utf-8", errors="ignore")
            markdown, meta = self._split_scraped_header(raw)
            engine_label, tables = "native-markdown", []
        elif suffix in (".pdf", ".docx", ".pptx", ".html"):
            conv = self._get_converter()
            logger.info(f"Parsing [{corpus}] {file_path.name} with [docling_standard]")
            kwargs = {"page_range": (1, self.max_pages)} if (self.max_pages and suffix == ".pdf") else {}
            result = conv.convert(str(file_path), **kwargs)
            doc = result.document
            markdown = doc.export_to_markdown()
            tables = []
            for t in doc.tables:
                try:
                    tables.append(t.export_to_dataframe(doc).to_dict(orient="records"))
                except Exception:  # noqa: BLE001
                    pass
            engine_label = "Docling standard (layout + TableFormer + RapidOCR)"
        else:
            raise ValueError(f"Unsupported file type: {file_path.name}")

        markdown = self._clean_markdown(markdown)
        markdown, images = self._attach_figures(markdown, corpus)
        title = meta.get("title") or self._first_heading(markdown) or doc_id.replace("-", " ").replace("_", " ").title()
        return {
            "doc_id": doc_id,
            "corpus": corpus,
            "title": title,
            "source_path": str(file_path.relative_to(WORKSPACE_ROOT)) if WORKSPACE_ROOT in file_path.parents else str(file_path),
            "source_url": meta.get("Source", ""),
            "section": meta.get("Section", ""),
            "summary_hint": meta.get("Summary", ""),
            "published": meta.get("Published", ""),
            "ocr_engine_used": engine_label,
            "parse_seconds": round(time.time() - started, 1),
            "markdown_content": markdown,
            "tables": tables,
            "images": images,
        }

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _split_scraped_header(raw: str):
        """Scraped pages start with '# Title' + 'Source:/Section:/...' lines; lift them into metadata."""
        lines = raw.splitlines()
        meta: Dict[str, str] = {}
        if lines and lines[0].startswith("# "):
            meta["title"] = lines[0][2:].strip()
            i = 1
            while i < len(lines) and (not lines[i].strip() or any(lines[i].startswith(f"{f}:") for f in HEADER_FIELDS)):
                for f in HEADER_FIELDS:
                    if lines[i].startswith(f"{f}:"):
                        meta[f] = lines[i].split(":", 1)[1].strip()
                i += 1
            return "# " + meta["title"] + "\n\n" + "\n".join(lines[i:]).strip(), meta
        return raw, meta

    @staticmethod
    def _clean_markdown(md: str) -> str:
        # Docling escapes underscores ("0x4A7B\_VRM\_OVERVOLT"), which would silently break exact-match (BM25/grep) search.
        md = md.replace("\\_", "_")
        md = re.sub(r"[ \t]+\n", "\n", md)
        return re.sub(r"\n{3,}", "\n\n", md).strip()

    @staticmethod
    def _first_heading(md: str) -> str:
        m = re.search(r"^#{1,2}\s+(.+)$", md, re.M)
        return m.group(1).strip() if m else ""

    def _load_sidecar(self, corpus: str) -> Dict[str, Dict[str, str]]:
        path = self.output_images_dir / corpus / "figure_captions.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def _attach_figures(self, md: str, corpus: str):
        """Resolves figure placeholders to real image files and returns (markdown, images)."""
        sidecar = self._load_sidecar(corpus)
        by_fig = {v["figure"]: (fname, v) for fname, v in sidecar.items()}
        images: List[Dict[str, Any]] = []
        seen = set()

        def add(fname: str, caption: str, fig_id: str = "", description: str = ""):
            if fname in seen:
                return
            seen.add(fname)
            images.append({"path": f"/static/images/{corpus}/{fname}", "file": fname, "caption": caption,
                           "figure_id": fig_id, "description": description or caption})

        # (a) Bind figures by their caption line "Figure F4: ...". (Docling's '<!-- image -->' placeholder is not reliable:
        #     it is missing for chart-like figures, so the caption line is the anchor we trust.)
        md = md.replace("<!-- image -->", "")

        def bind(m):
            cap_text = m.group(1).strip("*_ ")
            fig_id = m.group(2)
            if fig_id in by_fig and by_fig[fig_id][0] not in seen:
                fname, info = by_fig[fig_id]
                add(fname, cap_text, fig_id, info["description"])
                return f"![{cap_text}](/static/images/{corpus}/{fname})\n\n*{cap_text}*\n\n> Figure description: {info['description']}"
            return m.group(0)

        md = re.sub(r"(?m)^[*_]*(Figure (F\d+): [^\n]*?)[*_]*$", bind, md)

        # (b) Markdown images already in the text (scraped pages; native Markdown input)
        for m in IMG_MD_RE.finditer(md):
            fname = Path(m.group(2)).name
            if m.group(2).startswith(f"/static/images/{corpus}/"):
                info = sidecar.get(fname, {})
                add(fname, m.group(1), info.get("figure", ""), m.group(3) or info.get("description", m.group(1)))
        return md, images

