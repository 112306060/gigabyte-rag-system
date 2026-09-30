"""End-to-end RAG pipeline: retrieve -> build prompt -> stream generation."""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass, field

from aorus_rag.llm_client import GenStats, stream_chat
from aorus_rag.prompt import build_messages
from aorus_rag.retriever import Hit, Retriever


@dataclass
class RunStats:
    retrieval_ms: float = 0.0
    gen: GenStats = field(default_factory=GenStats)
    hits: list[Hit] = field(default_factory=list)

    @property
    def e2e_ttft_ms(self) -> float:
        """What the user feels: question submitted -> first token on screen."""
        return self.retrieval_ms + self.gen.ttft_ms


class RAG:
    def __init__(self, k: int = 5, mode: str = "hybrid"):
        self.retriever = Retriever()
        self.k, self.mode = k, mode

    def answer(self, query: str, stats: RunStats) -> Iterator[str]:
        t0 = time.perf_counter()
        stats.hits = self.retriever.search(query, k=self.k, mode=self.mode)
        stats.retrieval_ms = 1000 * (time.perf_counter() - t0)
        messages = build_messages(query, stats.hits)
        yield from stream_chat(messages, stats.gen)
