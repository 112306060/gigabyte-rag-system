"""End-to-end RAG pipeline: retrieve -> build prompt -> stream generation -> Traditional Chinese."""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass, field

from aorus_rag.llm_client import GenStats, stream_chat
from aorus_rag.prompt import DEFAULT_PROMPT, answer_language, build_messages
from aorus_rag.retriever import Hit, Retriever
from aorus_rag.traditional import stream_traditional


@dataclass
class RunStats:
    retrieval_ms: float = 0.0
    e2e_ttft_ms: float = 0.0  # question submitted -> first text the user sees
    gen: GenStats = field(default_factory=GenStats)
    hits: list[Hit] = field(default_factory=list)


class RAG:
    def __init__(self, k: int = 5, mode: str = "hybrid", prune: bool = True,
                 prompt_version: str = DEFAULT_PROMPT, traditional: bool = True):
        self.retriever = Retriever()
        self.k, self.mode, self.prune = k, mode, prune
        self.prompt_version = prompt_version
        self.traditional = traditional

    def answer(self, query: str, stats: RunStats) -> Iterator[str]:
        t0 = time.perf_counter()
        stats.hits = self.retriever.search(query, k=self.k, mode=self.mode, prune=self.prune)
        stats.retrieval_ms = 1000 * (time.perf_counter() - t0)
        messages = build_messages(query, stats.hits, self.prompt_version)

        tokens = stream_chat(messages, stats.gen)
        if self.traditional and answer_language(query) == "zh":
            tokens = stream_traditional(tokens)
        for text in tokens:
            if not stats.e2e_ttft_ms:
                # Measured on what is actually shown, so any buffering by the
                # Traditional-Chinese converter is included.
                stats.e2e_ttft_ms = 1000 * (time.perf_counter() - t0)
            yield text
