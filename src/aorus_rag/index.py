"""Build the vector index: embed every chunk's embed_text and save to index/.

The index is tiny (21 x 1024 float32 = 86 KB), so a brute-force numpy matrix is the
right tool; ANN libraries (FAISS/HNSW) only pay off at ~100k+ vectors.
"""

from __future__ import annotations

import json
import time

import numpy as np

from aorus_rag.chunker import OUT as CHUNKS_PATH
from aorus_rag.embedder import embed
from aorus_rag.parser import ROOT

INDEX_DIR = ROOT / "index"
VECTORS_PATH = INDEX_DIR / "vectors.npy"
META_PATH = INDEX_DIR / "meta.json"
EMBED_MODEL = "bge-m3-Q8_0"


def load_chunks() -> list[dict]:
    return [json.loads(l) for l in CHUNKS_PATH.read_text(encoding="utf-8").splitlines()]


def main() -> None:
    chunks = load_chunks()
    t0 = time.perf_counter()
    vecs = embed([c["embed_text"] for c in chunks])
    dt = time.perf_counter() - t0
    INDEX_DIR.mkdir(exist_ok=True)
    np.save(VECTORS_PATH, vecs)
    # Store chunk ids with the vectors so a stale index (chunks changed) is detectable.
    META_PATH.write_text(json.dumps({
        "embed_model": EMBED_MODEL,
        "dim": int(vecs.shape[1]),
        "chunk_ids": [c["id"] for c in chunks],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"embedded {len(chunks)} chunks -> {vecs.shape} in {dt:.2f}s -> {VECTORS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
