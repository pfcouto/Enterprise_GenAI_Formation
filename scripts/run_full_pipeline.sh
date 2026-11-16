#!/usr/bin/env bash
# ==============================================================================
# Presenter shortcut: runs every data stage in one go (the formation runs them one by one).
#   1a scrape syone.com   1b verify hardware manuals   2 Docling parse   3 OKF compile   (+ validation)
# Then start the stack and index:  docker compose up --build -d && python -m backend.graph_rag.indexer
# ==============================================================================
set -e
cd "$(dirname "$0")/.."
[ -d .venv ] && source .venv/bin/activate
export HF_HOME="$PWD/models/huggingface"

echo "== 1a. Scraping syone.com (live, ~2 min) =="
python scripts/scrape_syone.py

echo "== 1b. Hardware manuals =="
python scripts/download_hardware_manuals.py

echo "== 2. Docling parsing (docling_standard, all documents) =="
python -m backend.ingestion.run_docling --engine docling_standard

echo "== 3. OKF compilation =="
python -m backend.ingestion.run_okf --engine docling_standard

echo "== Validation =="
python scripts/validate_dataset.py

echo
echo "Data pipeline complete. Next:"
echo "  docker compose up --build -d"
echo "  python -m backend.graph_rag.indexer      # or run notebook 02"
