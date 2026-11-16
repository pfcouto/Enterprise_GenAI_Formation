"""
End-to-End Ingestion Runner
Orchestrates Docling parsing -> Google OKF compilation -> Neo4j Knowledge Graph -> Qdrant Hybrid Indexing
"""

import sys
import logging
from pathlib import Path

from backend.ingestion.docling_parser import DoclingDocumentParser
from backend.ingestion.okf_compiler import OKFCompiler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = WORKSPACE_ROOT / "data"
EXTRACTED_IMAGES_DIR = DATA_DIR / "extracted_images"
OKF_STORE_DIR = DATA_DIR / "okf_store"


def run_full_ingestion():
    """Runs end-to-end ingestion across all corpora."""
    logger.info("==================================================================")
    logger.info("STARTING MULTI-CORPUS DOCLING -> GOOGLE OKF INGESTION PIPELINE")
    logger.info("==================================================================")

    parser = DoclingDocumentParser(output_images_dir=EXTRACTED_IMAGES_DIR)
    compiler = OKFCompiler(okf_root_dir=OKF_STORE_DIR)

    corpora = [
        ("syone_corp", DATA_DIR / "raw_syone_corp"),
        ("hardware_manuals", DATA_DIR / "raw_hardware_manuals"),
    ]

    parsed_docs = []

    for corpus_name, raw_path in corpora:
        if not raw_path.exists():
            logger.warning(f"Raw data directory does not exist: {raw_path}. Skipping.")
            continue

        raw_files = sorted(f for f in (list(raw_path.glob("*.md")) + list(raw_path.glob("*.pdf")) + list(raw_path.glob("*.html")))
                           if not f.name.startswith("_"))
        logger.info(f"Processing corpus [{corpus_name}]: Found {len(raw_files)} raw documents.")

        for file_path in raw_files:
            try:
                parsed_docs.append(parser.parse_document(file_path, corpus=corpus_name))
            except Exception as e:  # noqa: BLE001
                logger.error(f"  ✗ Failed parsing {file_path.name}: {e}")

    total_compiled = len(compiler.compile_corpus(parsed_docs))

    logger.info(f"Successfully compiled {total_compiled} canonical Google OKF documents.\n")
    return total_compiled


if __name__ == "__main__":
    run_full_ingestion()
