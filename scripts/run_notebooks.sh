#!/usr/bin/env bash
# Executes all notebooks headless (CI-style smoke test of the whole formation). Needs `docker compose up -d` and the data pipeline done.
# Usage: scripts/run_notebooks.sh [01 02 ...]     Outputs are written next to the notebooks (executed copies in notebooks/_executed/).
set -e
cd "$(dirname "$0")/.."
[ -d .venv ] && source .venv/bin/activate || true
mkdir -p notebooks/_executed
for nb in ${@:-01 02 03 04 05}; do
  f=$(ls notebooks/${nb}_*.ipynb)
  echo ">>> executing $f"
  jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=3600 --output-dir notebooks/_executed "$f"
done
