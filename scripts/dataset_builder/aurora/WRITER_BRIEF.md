# Writer brief — Aurora Open Rack AOR-3 manual library (FICTIONAL)

You are a technical writer producing one chapter of a realistic, *fictional* hardware service library
for a RAG / knowledge-graph training exercise. Vendor "Aurora Systems", product "Aurora Open Rack AOR-3".

## Hard rules
1. **Facts come only from `scripts/dataset_builder/aurora/spec.py`.** Read it fully first. Never contradict a number,
   code, port name, VLAN, LED state, U-position or threshold in it. You may add *procedures, rationale, tips, warnings,
   tables and examples*, but any new numeric value must be clearly non-critical (e.g. step durations) and must not
   conflict with the spec.
2. Fault codes must be written **exactly** as in the spec (e.g. `0x4A7B_VRM_OVERVOLT`) — same hex, same suffix.
3. Output is **Markdown**, one file per document, saved to `scripts/dataset_builder/aurora/src/<doc_id>.md`
   (doc ids are listed in `DOCUMENTS` in spec.py). Start with `# <Document title>`, then a short metadata line
   `Document ref: <doc_id> | Revision: <DOC_REV> | Classification: Fictional training material`.
4. Length: **2,500-4,000 words per document.** Rich, specific, numbered sections (`## 1. ...`, `### 1.1 ...`).
5. Use **Markdown pipe tables** for any tabular data (spec tables, step tables, thresholds). Tables are important:
   downstream, a document-parsing model must extract them.
6. **Figures**: where the spec lists figures for your document, embed each with exactly this syntax, on its own line,
   introduced by a sentence that tells the reader *when* to look at it, and followed by an italic caption:
   `![Figure F2: Front-panel LED legend](figures/F2_front_panel_led_legend.png)` — use the file stem from `FIGURES` in spec.py
   (`figures/<ID>_<stem>.png`). Refer to figures in the text as "Figure F2". Do not invent other figures.
7. Include cross-references to other documents by their title (e.g. "see *Fault Code Reference and Troubleshooting Flowcharts*").
8. Include a `## Frequently asked questions` section near the end with 5-8 realistic technician Q&As grounded in the spec.
9. Style: precise, imperative procedures ("1. Power down the sled..."), WARNING / CAUTION / NOTE callouts as
   blockquotes (`> **WARNING:** ...`). No marketing language. No emojis.
10. Never mention that this is AI-written. Never claim the product is real; the metadata line says fictional.
11. Do not touch any file other than your assigned outputs.

When finished, reply with: files written, word counts (`wc -w`), and any spec ambiguity you noticed.
