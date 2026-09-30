"""Hand-written BM25 for mixed Chinese / English spec text.

Tokenisation:
  * English words and numbers stay whole, keeping inner "." / "-" so that model names
    and specs survive as single tokens: "rtx", "5090", "usb3.2", "type-c", "99wh".
  * Chinese has no spaces, so we use character unigrams + bigrams:
    "電池容量" -> 電 池 容 量 電池 池容 容量
    Bigrams capture words without needing a dictionary-based segmenter (e.g. jieba);
    unigrams keep recall for one-character queries like "重".
"""

from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np

_LATIN = re.compile(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*")
_CJK_RUN = re.compile(r"[一-鿿]+")


def tokenize(text: str) -> list[str]:
    text = text.lower().replace("®", "").replace("™", "")
    tokens = _LATIN.findall(text)
    for run in _CJK_RUN.findall(text):
        tokens.extend(run)                                      # unigrams
        tokens.extend(run[i : i + 2] for i in range(len(run) - 1))  # bigrams
    return tokens


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tfs = [Counter(tokenize(d)) for d in docs]
        self.lens = np.array([sum(tf.values()) for tf in self.tfs], dtype=np.float32)
        self.avgdl = float(self.lens.mean())
        n = len(docs)
        df = Counter(t for tf in self.tfs for t in tf)
        # BM25+ style idf (never negative): rare terms weigh more.
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def scores(self, query: str) -> np.ndarray:
        out = np.zeros(len(self.tfs), dtype=np.float32)
        q_terms = set(tokenize(query))
        for i, tf in enumerate(self.tfs):
            norm = self.k1 * (1 - self.b + self.b * self.lens[i] / self.avgdl)
            for t in q_terms:
                f = tf.get(t)
                if f:
                    out[i] += self.idf[t] * f * (self.k1 + 1) / (f + norm)
        return out
