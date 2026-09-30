"""Hybrid retrieval: dense (bge-m3 cosine) + sparse (BM25), fused with Reciprocal Rank Fusion.

Why hybrid:
  * Dense handles paraphrase and cross-lingual queries ("多重" -> "Weight: ~2.5 kg").
  * BM25 handles exact tokens dense models blur: model numbers, "5070 Ti", "HDMI 2.1".
Why RRF: cosine scores (~0.3-0.7) and BM25 scores (0-20+) live on different scales.
RRF ignores raw scores and only uses ranks: score = sum(1 / (k + rank)), so no tuning
of score normalisation is needed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np

from aorus_rag.bm25 import BM25
from aorus_rag.embedder import embed
from aorus_rag.index import META_PATH, VECTORS_PATH, load_chunks

RRF_K = 60


@dataclass
class Hit:
    chunk: dict
    score: float       # fused score used for ranking
    dense: float       # cosine similarity (for thresholds / debugging)
    dense_rank: int
    bm25_rank: int


class Retriever:
    def __init__(self):
        self.chunks = load_chunks()
        meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        if meta["chunk_ids"] != [c["id"] for c in self.chunks]:
            raise RuntimeError("index is stale: chunks changed, rerun `python -m aorus_rag.index`")
        self.vectors = np.load(VECTORS_PATH)
        self.bm25 = BM25([c["embed_text"] for c in self.chunks])

    def search(self, query: str, k: int = 5, mode: str = "hybrid") -> list[Hit]:
        cos = self.vectors @ embed([query])[0]
        bm = self.bm25.scores(query)
        dense_rank = _ranks(cos)
        bm25_rank = _ranks(bm)

        if mode == "dense":
            fused = cos
        elif mode == "bm25":
            fused = bm
        elif mode == "hybrid":
            fused = 1 / (RRF_K + dense_rank) + 1 / (RRF_K + bm25_rank)
        else:
            raise ValueError(mode)

        order = np.argsort(-fused)[:k]
        return [
            Hit(self.chunks[i], float(fused[i]), float(cos[i]), int(dense_rank[i]), int(bm25_rank[i]))
            for i in order
        ]


def _ranks(scores: np.ndarray) -> np.ndarray:
    """1-based rank of each element (1 = highest score)."""
    ranks = np.empty(len(scores), dtype=np.int64)
    ranks[np.argsort(-scores)] = np.arange(1, len(scores) + 1)
    return ranks
