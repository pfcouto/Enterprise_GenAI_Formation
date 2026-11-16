#!/usr/bin/env python3
"""
Builds the Aurora AOR-3 manual library: src/*.md  ->  PDFs with embedded figures and real tables.

  1. runs render_figures.py logic (figures are regenerated if missing)
  2. converts every src/<doc_id>.md into data/raw_hardware_manuals/<doc_id>.pdf (ReportLab, no browser needed)
  3. copies figures + captions into data/extracted_images/hardware_manuals/
  4. validates the text against spec.py (every fault code present, no unknown codes, figures exist)

Usage: python scripts/dataset_builder/aurora/build_manuals.py
"""

import html
import json
import re
import shutil
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image as RLImage, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle, HRFlowable)
from PIL import Image as PILImage

HERE = Path(__file__).parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(HERE))
import spec  # noqa: E402
import render_figures  # noqa: E402

SRC = HERE / "src"
FIG = HERE / "figures"
PDF_OUT = ROOT / "data" / "raw_hardware_manuals"
IMG_OUT = ROOT / "data" / "extracted_images" / "hardware_manuals"

INK = colors.HexColor("#1f2937")
styles = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("t", parent=styles["Title"], fontSize=22, leading=27, textColor=INK, alignment=0, spaceAfter=6),
    "meta": ParagraphStyle("m", parent=styles["Normal"], fontSize=8.5, textColor=colors.HexColor("#6b7280"), spaceAfter=14),
    "h2": ParagraphStyle("h2", parent=styles["Heading2"], fontSize=15, leading=19, textColor=INK, spaceBefore=14, spaceAfter=6),
    "h3": ParagraphStyle("h3", parent=styles["Heading3"], fontSize=12, leading=15, textColor=INK, spaceBefore=10, spaceAfter=4),
    "h4": ParagraphStyle("h4", parent=styles["Heading4"], fontSize=10.5, textColor=INK, spaceBefore=8, spaceAfter=3),
    "p": ParagraphStyle("p", parent=styles["BodyText"], fontSize=9.5, leading=13.5, spaceAfter=5),
    "li": ParagraphStyle("li", parent=styles["BodyText"], fontSize=9.5, leading=13, leftIndent=14, bulletIndent=3, spaceAfter=2),
    "quote": ParagraphStyle("q", parent=styles["BodyText"], fontSize=9, leading=12.5, leftIndent=10, rightIndent=6,
                            backColor=colors.HexColor("#fef3c7"), borderPadding=(5, 6, 5, 8), spaceBefore=4, spaceAfter=8),
    "cell": ParagraphStyle("c", parent=styles["BodyText"], fontSize=7.8, leading=10),
    "cellh": ParagraphStyle("ch", parent=styles["BodyText"], fontSize=7.8, leading=10, textColor=colors.white, fontName="Helvetica-Bold"),
    "cap": ParagraphStyle("cap", parent=styles["BodyText"], fontSize=8.3, textColor=colors.HexColor("#4b5563"), alignment=1, spaceAfter=8),
}


def inline(text: str, code_size: float = 7.4) -> str:
    t = html.escape(text, quote=False)
    t = re.sub(r"`([^`]+)`", rf'<font face="Courier" size="{code_size}">\1</font>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", t)
    t = re.sub(r"(?<![\w_])_([^_\n]+)_(?![\w_])", r"<i>\1</i>", t)
    return t


def table_flowable(rows, avail_width):
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    # Column widths: never narrower than the longest unbreakable token (fault codes must not wrap mid-code).
    # If the tokens do not fit at the default font size, shrink the table font until they do.
    def longest_token(c):
        return max(len(tok) for r in rows for tok in (r[c].replace("`", "").split() or [""]))

    fs = 7.8
    while True:
        mins = [longest_token(c) * fs * 0.64 + 12 for c in range(ncol)]
        if sum(mins) <= avail_width or fs <= 5.6:
            break
        fs -= 0.3
    lens = [max(min(len(r[c]), 70) for r in rows) + 4 for c in range(ncol)]
    spare = max(avail_width - sum(mins), 0)
    widths = [m + spare * l / sum(lens) for m, l in zip(mins, lens)]
    scale = avail_width / sum(widths)
    widths = [w * scale for w in widths]
    cell = ParagraphStyle("cx", parent=S["cell"], fontSize=fs, leading=fs * 1.28)
    cellh = ParagraphStyle("cxh", parent=S["cellh"], fontSize=fs, leading=fs * 1.28)
    data = [[Paragraph(inline(c, fs - 0.2), cellh if i == 0 else cell) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def parse_table(lines, i):
    rows = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            rows.append(cells)
        i += 1
    return rows, i


def md_to_story(md: str, avail_width):
    lines = md.splitlines()
    story, i, used_figs = [], 0, []
    while i < len(lines):
        line = lines[i].rstrip()
        s = line.strip()
        if not s:
            i += 1
        elif s.startswith("# "):
            story.append(Paragraph(inline(s[2:]), S["title"]))
            i += 1
        elif s.startswith("## "):
            story.append(Paragraph(inline(s[3:]), S["h2"]))
            i += 1
        elif s.startswith("### "):
            story.append(Paragraph(inline(s[4:]), S["h3"]))
            i += 1
        elif s.startswith("#### "):
            story.append(Paragraph(inline(s[5:]), S["h4"]))
            i += 1
        elif s.startswith("|"):
            rows, i = parse_table(lines, i)
            if rows:
                story.append(table_flowable(rows, avail_width))
                story.append(Spacer(1, 7))
        elif s.startswith("!["):
            m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", s)
            i += 1
            if m:
                fig_file = FIG / Path(m.group(2)).name
                if not fig_file.exists():
                    sys.exit(f"ERROR: figure referenced but not rendered: {fig_file.name}")
                used_figs.append(fig_file.name)
                with PILImage.open(fig_file) as im:
                    ratio = im.height / im.width
                w = avail_width * 0.97
                h = min(w * ratio, 215 * mm)
                w = h / ratio
                caption = None
                if i < len(lines) and lines[i].strip().startswith(("*", "_")):
                    caption = lines[i].strip().strip("*_")
                    i += 1
                block = [RLImage(str(fig_file), width=w, height=h), Paragraph(inline(caption or m.group(1)), S["cap"])]
                story.append(KeepTogether(block))
        elif s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip("> ").strip())
                i += 1
            story.append(Paragraph(inline(" ".join(buf)), S["quote"]))
        elif re.match(r"^(\d+)\.\s", s) or s.startswith(("- ", "* ")):
            while i < len(lines) and (re.match(r"^\s*(\d+)\.\s", lines[i]) or re.match(r"^\s*[-*]\s", lines[i])):
                it = lines[i].strip()
                m = re.match(r"^(\d+)\.\s+(.*)", it)
                if m:
                    story.append(Paragraph(inline(m.group(2)), S["li"], bulletText=f"{m.group(1)}."))
                else:
                    story.append(Paragraph(inline(it[2:]), S["li"], bulletText="•"))
                i += 1
            story.append(Spacer(1, 3))
        elif re.fullmatch(r"-{3,}", s):
            story.append(HRFlowable(width="100%", color=colors.HexColor("#d1d5db")))
            i += 1
        else:
            buf = [s]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||!\[|>|\d+\.\s|[-*]\s)", lines[i].strip()):
                buf.append(lines[i].strip())
                i += 1
            style = S["meta"] if buf[0].startswith("Document ref:") else S["p"]
            story.append(Paragraph(inline(" ".join(buf)), style))
    return story, used_figs


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(18 * mm, 10 * mm, f"{spec.VENDOR} - {spec.PRODUCT} - {doc.title}  |  FICTIONAL TRAINING MATERIAL")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def validate(all_text: str):
    expected = {c[0] for c in spec.FAULT_CODES}
    found = set(re.findall(r"0x[0-9A-F]{4}_[A-Z0-9_]+", all_text))
    missing = expected - found
    unknown = {c for c in found if c not in expected and not any(c.startswith(e) for e in expected)}
    # tolerate truncated references like 0x4A7B (prefix only) but not fully-formed unknown codes
    problems = []
    if missing:
        problems.append(f"codes in spec but never in the manuals: {sorted(missing)}")
    if unknown:
        problems.append(f"codes in the manuals that are not in spec.py: {sorted(unknown)}")
    return problems


def main():
    PDF_OUT.mkdir(parents=True, exist_ok=True)
    IMG_OUT.mkdir(parents=True, exist_ok=True)
    if not list(FIG.glob("F*.png")):
        render_figures.main()
    for old in PDF_OUT.glob("*.pdf"):
        old.unlink()
    for old in IMG_OUT.glob("*"):
        if old.is_file():
            old.unlink()

    texts = []
    for doc_id, title, figs in spec.DOCUMENTS:
        src = SRC / f"{doc_id}.md"
        if not src.exists():
            sys.exit(f"ERROR: missing source {src}")
        md = src.read_text(encoding="utf-8")
        texts.append(md)
        out = PDF_OUT / f"{doc_id}.pdf"
        doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                                bottomMargin=18 * mm, title=title, author=spec.VENDOR + " (fictional)", subject=spec.PRODUCT)
        avail = A4[0] - 36 * mm
        story, used = md_to_story(md, avail)
        missing_figs = [f for f in figs if not any(u.startswith(f + "_") for u in used)]
        if missing_figs:
            print(f"  WARNING {doc_id}: spec lists figures {missing_figs} that the text does not embed")
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        print(f"  built {out.name}  ({len(md.split())} words, {len(used)} figures)")

    for f in FIG.glob("F*.png"):
        shutil.copy(f, IMG_OUT / f.name)
    shutil.copy(FIG / "figure_captions.json", IMG_OUT / "figure_captions.json")
    problems = validate("\n".join(texts))
    if problems:
        print("\nVALIDATION WARNINGS:")
        for p in problems:
            print("  -", p)
    else:
        print("\nValidation OK: every spec fault code is documented and no unknown code appears.")
    print(f"PDFs: {PDF_OUT}\nFigures: {IMG_OUT}")


if __name__ == "__main__":
    main()
