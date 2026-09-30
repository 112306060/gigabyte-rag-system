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
import re
from dataclasses import dataclass

import numpy as np

from aorus_rag.bm25 import BM25
from aorus_rag.embedder import embed
from aorus_rag.index import META_PATH, VECTORS_PATH, load_chunks

RRF_K = 60
# Context pruning: drop chunks whose cosine is this far below the best one.
# Placeholder value; calibrated on the evaluation set later.
REL_MARGIN = 0.10


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

        # Rows split per SKU (GPU): map row -> {sku: chunk index} and row -> variants index,
        # plus the words that identify each SKU in a query ("BXH", "5070 Ti").
        self.sku_chunk: dict[str, dict[str, int]] = {}
        self.variants_chunk: dict[str, int] = {}
        self.sku_aliases: dict[str, list[str]] = {}
        for i, c in enumerate(self.chunks):
            row = _row(c)
            if c["type"] == "spec_sku":
                sku = c["skus"][0]
                self.sku_chunk.setdefault(row, {})[sku] = i
                gpu = re.search(r"RTX™?\s*(\d{4})", c["text"])  # "5070" also matches "5070 Ti"
                self.sku_aliases[sku] = [sku.split()[-1].lower()] + ([gpu.group(1)] if gpu else [])
            elif c["type"] == "variants":
                self.variants_chunk[row] = i

    def _mentioned_skus(self, query: str) -> list[str]:
        q = query.lower()
        return [s for s, aliases in self.sku_aliases.items() if any(a in q for a in aliases)]

    def _representative(self, i: int, query: str) -> int:
        """For a per-SKU row, pick the chunk that matches the query's SKU, else the comparison."""
        row = _row(self.chunks[i])
        if row not in self.variants_chunk:
            return i
        skus = self._mentioned_skus(query)
        if len(skus) == 1:
            return self.sku_chunk[row][skus[0]]
        return self.variants_chunk[row]

    def search(self, query: str, k: int = 5, mode: str = "hybrid", prune: bool = True) -> list[Hit]:
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

        order = np.argsort(-fused)
        if prune:
            order = self._prune(order, cos, query, k)
        return [
            Hit(self.chunks[i], float(fused[i]), float(cos[i]), int(dense_rank[i]), int(bm25_rank[i]))
            for i in order[:k]
        ]

    def _prune(self, order: np.ndarray, cos: np.ndarray, query: str, k: int) -> list[int]:
        """Keep one chunk per spec row, and drop weak tail chunks (relative cosine margin)."""
        floor = cos.max() - REL_MARGIN
        picked, seen_rows = [], set()
        for i in order:
            row = _row(self.chunks[i])
            if row in seen_rows:
                continue
            if picked and cos[i] < floor:
                continue
            picked.append(self._representative(int(i), query))
            seen_rows.add(row)
            if len(picked) == k:
                break
        return picked


def _row(chunk: dict) -> str:
    """'row02_BXH' / 'row02_variants' -> 'row02'; 'overview' -> 'overview'."""
    return chunk["id"].split("_")[0]


def _ranks(scores: np.ndarray) -> np.ndarray:
    """1-based rank of each element (1 = highest score)."""
    ranks = np.empty(len(scores), dtype=np.int64)
    ranks[np.argsort(-scores)] = np.arange(1, len(scores) + 1)
    return ranks
