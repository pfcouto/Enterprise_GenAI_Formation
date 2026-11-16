#!/usr/bin/env python3
"""
Pre-downloads the local models into ./models/ so nothing is downloaded during the live session.

  python scripts/download_models.py --download          # fastembed (dense + BM25) + Docling layout/TableFormer/OCR  (~600 MB)
  python scripts/download_models.py --download --glm    # additionally GLM-OCR 0.9B (~2.5 GB, optional comparison engine)
  python scripts/download_models.py --check             # what is cached?
"""

import argparse
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
MODELS = ROOT / "models"
os.environ.setdefault("HF_HOME", str(MODELS / "huggingface"))
os.environ.setdefault("DOCLING_CACHE_DIR", str(MODELS / "docling"))


def size_mb(path: Path) -> float:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e6 if path.exists() else 0.0


def check() -> bool:
    hub = MODELS / "huggingface" / "hub"
    checks = {
        "fastembed dense (bge-small-en-v1.5)": any((MODELS / "fastembed").glob("models--*bge-small*")),
        "fastembed BM25 sparse (Qdrant/bm25)": any((MODELS / "fastembed").glob("models--*bm25*")),
        "Docling layout model": any(hub.glob("models--docling-project--docling-layout*")) if hub.exists() else False,
        "Docling TableFormer": any(hub.glob("models--docling-project--docling-models*")) if hub.exists() else False,
        "GLM-OCR 0.9B (optional)": any(hub.glob("models--zai-org--GLM-OCR*")) if hub.exists() else False,
    }
    print("Local model cache (./models/)")
    for name, ok in checks.items():
        print(f"  {'OK     ' if ok else 'missing'}  {name}")
    print(f"  total on disk: {size_mb(MODELS):.0f} MB")
    required = list(checks.values())[:4]
    print("\nStatus:", "READY for offline use" if all(required) else "run: python scripts/download_models.py --download")
    return all(required)


def download(glm: bool):
    print("[1/3] fastembed dense + BM25 ...")
    from fastembed import SparseTextEmbedding, TextEmbedding
    list(TextEmbedding(model_name="BAAI/bge-small-en-v1.5", cache_dir=str(MODELS / "fastembed")).embed(["warm-up"]))
    list(SparseTextEmbedding(model_name="Qdrant/bm25", cache_dir=str(MODELS / "fastembed")).embed(["warm-up"]))
    print("  done")

    print("[2/3] Docling layout + TableFormer (+ RapidOCR weights ship inside the package) ...")
    from docling.utils.model_downloader import download_models
    download_models(progress=True)
    print("  done")

    if glm:
        print("[3/3] GLM-OCR 0.9B (about 2.5 GB) ...")
        from huggingface_hub import snapshot_download
        snapshot_download("zai-org/GLM-OCR")
        print("  done")
    else:
        print("[3/3] GLM-OCR skipped (add --glm to download it)")
    print()
    check()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--glm", action="store_true", help="also download GLM-OCR (optional engine)")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.download:
        download(args.glm)
    else:
        check()
