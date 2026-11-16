"""
Step 2a: Docling Document Parser — Standalone CLI Runner

Run this AFTER the data acquisition scripts:
  python scripts/scrape_syone.py              # Step 1a: Syone website
  python scripts/download_hardware_manuals.py # Step 1b: Hardware PDFs

Usage:
  python -m backend.ingestion.run_docling
  python -m backend.ingestion.run_docling --corpus hardware_manuals
  python -m backend.ingestion.run_docling --list

Outputs intermediate parsed JSON files to: data/docling_output/
"""

import sys
import json
import logging
import argparse
from pathlib import Path

from backend.ingestion.docling_parser import DoclingDocumentParser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = WORKSPACE_ROOT / "data"
EXTRACTED_IMAGES_DIR = DATA_DIR / "extracted_images"
DOCLING_OUTPUT_DIR = DATA_DIR / "docling_output"

CORPORA = {
    "syone_corp": DATA_DIR / "raw_syone_corp",
    "hardware_manuals": DATA_DIR / "raw_hardware_manuals",
}


def list_raw_files():
    """Lists all raw source files available for parsing."""
    print("\n=== Available Raw Source Files ===")
    for corpus_name, raw_path in CORPORA.items():
        if not raw_path.exists():
            print(f"  [{corpus_name}] Directory missing: {raw_path}")
            print(f"    → Run the acquisition script first!")
            continue
        files = list(raw_path.glob("*.md")) + list(raw_path.glob("*.pdf")) + list(raw_path.glob("*.html"))
        print(f"\n  [{corpus_name}] {len(files)} files in {raw_path}:")
        for f in files:
            size_kb = f.stat().st_size / 1024
            print(f"    • {f.name} ({size_kb:.1f} KB)")
    print()


def run_docling_parsing(engine: str = "docling_standard", corpus_filter: str = "all", max_pages: int = None) -> int:
    """
    Runs Docling parsing on raw source files and saves intermediate JSON output.

    Args:
        engine: 'docling_standard' (the only engine; kept as a parameter for the notebooks)
        corpus_filter: 'all', 'syone_corp', or 'hardware_manuals'

    Returns:
        Number of documents successfully parsed.
    """
    logger.info("=" * 70)
    logger.info(f"DOCLING PARSING STAGE — Engine: [{engine.upper()}]")
    logger.info("=" * 70)
    logger.info(f"Output directory: {DOCLING_OUTPUT_DIR}")

    DOCLING_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parser = DoclingDocumentParser(
        output_images_dir=EXTRACTED_IMAGES_DIR,
        ocr_engine=engine,
        max_pages=max_pages,
    )

    total_parsed = 0
    corpora = {k: v for k, v in CORPORA.items() if corpus_filter == "all" or k == corpus_filter}

    for corpus_name, raw_path in corpora.items():
        if not raw_path.exists():
            logger.warning(f"Raw data directory missing: {raw_path}")
            logger.warning(f"  → Run the acquisition script first.")
            continue

        raw_files = sorted(
            f for f in (list(raw_path.glob("*.md")) + list(raw_path.glob("*.pdf")) + list(raw_path.glob("*.html")))
            if not f.name.startswith("_")
        )

        logger.info(f"\nProcessing corpus [{corpus_name}]: {len(raw_files)} raw files found.")

        for file_path in raw_files:
            try:
                parsed = parser.parse_document(file_path, corpus=corpus_name)

                # Filename encodes the document and the engine used
                out_file = DOCLING_OUTPUT_DIR / f"{corpus_name}__{file_path.stem}__standard.json"

                # Tables may contain non-JSON-serializable types — convert safely
                safe_tables = []
                for t in parsed.get("tables", []):
                    if isinstance(t, list):
                        safe_tables.append(t)
                    elif hasattr(t, "to_dict"):
                        try:
                            safe_tables.append(t.to_dict(orient="records"))
                        except Exception:
                            safe_tables.append(str(t))
                    else:
                        safe_tables.append(str(t))

                output = {**parsed, "tables": safe_tables}

                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(output, f, indent=2, ensure_ascii=False)

                logger.info(
                    f"  ✓ [{parsed['ocr_engine_used']}] {file_path.name}"
                    f" → {out_file.name}"
                    f" ({len(parsed.get('markdown_content', ''))} chars,"
                    f" {len(parsed.get('images', []))} images)"
                )
                total_parsed += 1

            except Exception as e:
                logger.error(f"  ✗ Failed parsing {file_path.name}: {e}")

    logger.info("\n" + "=" * 70)
    logger.info(f"✓ Docling parsing complete: {total_parsed} documents → {DOCLING_OUTPUT_DIR}")
    logger.info("Next step: compile to Google OKF format:")
    logger.info("  python -m backend.ingestion.run_okf")
    logger.info("=" * 70)
    return total_parsed


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Docling Document Parser — Step 2a of the formation pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m backend.ingestion.run_docling --list
  python -m backend.ingestion.run_docling --corpus hardware_manuals
        """
    )
    arg_parser.add_argument(
        "--corpus",
        choices=["all", "syone_corp", "hardware_manuals"],
        default="all",
        help="Which corpus to parse (default: all)"
    )
    arg_parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Parse only the first N pages of each PDF (a quick test)"
    )
    arg_parser.add_argument(
        "--list",
        action="store_true",
        help="List available raw source files without parsing"
    )

    args = arg_parser.parse_args()

    if args.list:
        list_raw_files()
        sys.exit(0)

    run_docling_parsing("docling_standard", args.corpus, args.max_pages)
