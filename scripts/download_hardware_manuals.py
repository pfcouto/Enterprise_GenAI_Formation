#!/usr/bin/env python3
"""
Stage 1b: the hardware corpus (Aurora Open Rack AOR-3, a FICTIONAL product line).

The 8 PDF manuals and their 9 figures are committed in data/raw_hardware_manuals/ and data/extracted_images/hardware_manuals/,
so a fresh clone already has them (no download needed: the name of this script is historical).

  python scripts/download_hardware_manuals.py            # verify the dataset is present and intact
  python scripts/download_hardware_manuals.py --rebuild  # regenerate figures + PDFs from scripts/dataset_builder/aurora/
                                                         # (needs: reportlab, matplotlib; both are in requirements.txt)
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
RAW = ROOT / "data" / "raw_hardware_manuals"
IMG = ROOT / "data" / "extracted_images" / "hardware_manuals"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true", help="re-render figures and PDFs from the markdown sources")
    args = ap.parse_args()
    if args.rebuild:
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "dataset_builder" / "aurora" / "render_figures.py")])
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "dataset_builder" / "aurora" / "build_manuals.py")])
    pdfs, figs = sorted(RAW.glob("*.pdf")), sorted(IMG.glob("F*.png"))
    print(f"Aurora AOR-3 manuals: {len(pdfs)} PDFs, {len(figs)} figures")
    for p in pdfs:
        print(f"  {p.name:42s} {p.stat().st_size / 1024:6.0f} KB")
    if len(pdfs) != 8 or len(figs) != 9 or not (IMG / "figure_captions.json").exists():
        sys.exit("Dataset incomplete: run  python scripts/download_hardware_manuals.py --rebuild")
    print("OK. (Fictional vendor and product: values are inspired by OCP Open Rack concepts, not real specifications.)")


if __name__ == "__main__":
    main()
