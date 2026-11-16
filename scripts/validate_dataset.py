#!/usr/bin/env python3
"""
Sanity-checks the knowledge base BEFORE you spend LLM calls on it:
  1. every fault code of the hardware spec survived PDF parsing intact (no code split by a line wrap),
  2. every golden question is answerable from the OKF store: its expected keywords occur in its expected documents,
  3. every expected figure exists on disk.
Run after the ingestion steps:  python scripts/validate_dataset.py
Exit code 1 if anything is broken.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "dataset_builder" / "aurora"))

from backend.evaluation.golden_dataset import GOLDEN_EVALUATION_DATASET  # noqa: E402
import spec  # noqa: E402

OKF = ROOT / "data" / "okf_store"
IMG = ROOT / "data" / "extracted_images"


def norm(s: str) -> str:
    return re.sub(r"[\s_\-]+", "", s).lower()


def main() -> int:
    problems = 0
    hw = {p.stem: p.read_text(encoding="utf-8") for p in (OKF / "hardware_manuals").glob("*.md") if p.name != "INDEX.md"}
    sy = {p.stem: p.read_text(encoding="utf-8") for p in (OKF / "syone_corp").glob("*.md") if p.name != "INDEX.md"}
    print(f"OKF store: {len(sy)} Syone documents, {len(hw)} hardware documents")
    if not hw or not sy:
        print("ERROR: OKF store is empty - run the ingestion steps first")
        return 1

    ref = hw.get("aor3_06_fault_code_reference", "")
    broken = [c[0] for c in spec.FAULT_CODES if c[0] not in ref]
    print(f"[1] fault codes intact in the reference manual: {len(spec.FAULT_CODES) - len(broken)}/{len(spec.FAULT_CODES)}")
    for c in broken:
        print("    BROKEN:", c)
    problems += len(broken)

    bad = []
    for item in GOLDEN_EVALUATION_DATASET:
        store = hw if item["corpus"] == "hardware_manuals" else sy
        text = " ".join(store.get(d, "") for d in item["expected_docs"])
        for d in item["expected_docs"]:
            if d not in store:
                bad.append((item["id"], f"expected doc missing: {d}"))
        for kw in item["expected_keywords"]:
            if item["expected_docs"] and norm(kw) not in norm(text):
                bad.append((item["id"], f"keyword not in expected docs: {kw!r}"))
        for im in item["expected_images"]:
            if not (IMG / item["corpus"] / im).exists():
                bad.append((item["id"], f"figure missing on disk: {im}"))
    print(f"[2/3] golden questions verifiable against the store: {len(GOLDEN_EVALUATION_DATASET) - len({b[0] for b in bad})}/{len(GOLDEN_EVALUATION_DATASET)}")
    for b in bad:
        print("    ", *b)
    problems += len(bad)
    print("OK" if not problems else f"{problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
