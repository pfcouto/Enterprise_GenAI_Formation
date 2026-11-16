"""
Step 2b: Google OKF Compiler — Standalone CLI Runner

Run this AFTER the Docling parsing step:
  python -m backend.ingestion.run_docling    # Step 2a

Reads intermediate parsed JSON files from: data/docling_output/
Compiles canonical Google OKF Markdown files to: data/okf_store/

Usage:
  python -m backend.ingestion.run_okf
  python -m backend.ingestion.run_okf --corpus hardware_manuals
  python -m backend.ingestion.run_okf --list

By separating this step from Docling parsing, you can:
  - Inspect intermediate JSON before committing to OKF format
  - Re-compile OKF with different settings without re-running OCR
"""

import sys
import json
import logging
import argparse
from pathlib import Path

from backend.ingestion.okf_compiler import OKFCompiler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = WORKSPACE_ROOT / "data"
DOCLING_OUTPUT_DIR = DATA_DIR / "docling_output"
OKF_STORE_DIR = DATA_DIR / "okf_store"


def list_docling_outputs():
    """Lists all intermediate Docling JSON outputs available for OKF compilation."""
    if not DOCLING_OUTPUT_DIR.exists() or not list(DOCLING_OUTPUT_DIR.glob("*.json")):
        print(f"\n⚠  No Docling output files found in {DOCLING_OUTPUT_DIR}")
        print("  → Run first: python -m backend.ingestion.run_docling")
        return

    print(f"\n=== Docling Parsed Files in {DOCLING_OUTPUT_DIR} ===")
    for f in sorted(DOCLING_OUTPUT_DIR.glob("*.json")):
        size_kb = f.stat().st_size / 1024
        print(f"  • {f.name} ({size_kb:.1f} KB)")
    print()


def run_okf_compilation(engine_filter: str = "all", corpus_filter: str = "all") -> int:
    """
    Compiles Docling intermediate JSON outputs into canonical Google OKF Markdown files.

    Args:
        engine_filter: kept for the notebooks; only Docling standard output exists
        corpus_filter: 'all', 'syone_corp', or 'hardware_manuals'

    Returns:
        Number of OKF files successfully compiled.
    """
    if not DOCLING_OUTPUT_DIR.exists():
        logger.error(f"Docling output directory not found: {DOCLING_OUTPUT_DIR}")
        logger.error("  → Run first: python -m backend.ingestion.run_docling")
        return 0

    json_files = list(DOCLING_OUTPUT_DIR.glob("*.json"))
    if not json_files:
        logger.error("No intermediate Docling JSON files found.")
        logger.error("  → Run first: python -m backend.ingestion.run_docling")
        return 0

    # Docling standard output is the knowledge base: data/okf_store/
    compilers = {"standard": OKFCompiler(okf_root_dir=OKF_STORE_DIR)}

    logger.info("=" * 70)
    logger.info("GOOGLE OKF COMPILATION STAGE")
    logger.info("=" * 70)
    logger.info(f"  Docling standard → {OKF_STORE_DIR}")

    # Related links are computed across a whole corpus, so load every parsed doc first, then compile per engine.
    batches: dict = {key: [] for key in compilers}
    for json_file in sorted(json_files):
        # Parse filename: {corpus}__{doc_id}__{engine_tag}.json
        parts = json_file.stem.split("__")
        if len(parts) != 3:
            logger.warning(f"  Skipping unexpected filename format: {json_file.name}")
            continue
        corpus_name, doc_id, engine_tag = parts
        if corpus_filter != "all" and corpus_name != corpus_filter:
            continue
        if engine_tag != "standard":   # e.g. files left by an older engine
            continue
        engine_key = "standard"
        try:
            batches[engine_key].append(json.loads(json_file.read_text(encoding="utf-8")))
        except Exception as e:  # noqa: BLE001
            logger.error(f"  ✗ Failed reading {json_file.name}: {e}")

    total_compiled = 0
    for engine_key, docs in batches.items():
        if not docs:
            continue
        for okf_file in compilers[engine_key].compile_corpus(docs):
            logger.info(f"  ✓ [{engine_key}] → {okf_file.relative_to(WORKSPACE_ROOT)}")
            total_compiled += 1

    logger.info("\n" + "=" * 70)
    logger.info(f"✓ OKF compilation complete: {total_compiled} OKF documents generated.")
    logger.info(f"  OKF store: {OKF_STORE_DIR}")
    logger.info("Next step: start Docker Compose and run Notebook 2 to index into Neo4j + Qdrant")
    logger.info("=" * 70)
    return total_compiled


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Google OKF Compiler — Step 2b of the formation pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m backend.ingestion.run_okf --list
  python -m backend.ingestion.run_okf
  python -m backend.ingestion.run_okf --corpus hardware_manuals
        """
    )
    arg_parser.add_argument(
        "--corpus",
        choices=["all", "syone_corp", "hardware_manuals"],
        default="all",
        help="Which corpus to compile (default: all)"
    )
    arg_parser.add_argument(
        "--list",
        action="store_true",
        help="List available Docling output files without compiling"
    )

    args = arg_parser.parse_args()

    if args.list:
        list_docling_outputs()
        sys.exit(0)

    run_okf_compilation("docling_standard", args.corpus)
