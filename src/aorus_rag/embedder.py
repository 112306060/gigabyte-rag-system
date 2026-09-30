"""Client for the bge-m3 embedding server (llama-server --embedding, OpenAI-compatible API)."""

from __future__ import annotations

import httpx
import numpy as np

EMBED_URL = "http://127.0.0.1:8081/v1/embeddings"

# One shared client per process: creating an httpx.Client builds an SSL context
# (~250 ms on Windows), which would otherwise be paid on every query.
_client = httpx.Client(timeout=120)


def embed(texts: list[str], batch_size: int = 16) -> np.ndarray:
    """Return L2-normalised float32 vectors, shape (len(texts), dim).

    Normalising once here means cosine similarity later is just a dot product.
    """
    vecs = []
    for i in range(0, len(texts), batch_size):
        resp = _client.post(EMBED_URL, json={"input": texts[i : i + batch_size]})
        resp.raise_for_status()
        data = sorted(resp.json()["data"], key=lambda d: d["index"])
        vecs.extend(d["embedding"] for d in data)
    arr = np.asarray(vecs, dtype=np.float32)
    return arr / np.linalg.norm(arr, axis=1, keepdims=True)
