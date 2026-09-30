"""Streaming client for llama-server's OpenAI-compatible chat endpoint, with timing.

Metrics (measured on the client, cross-checked with the server's own `timings`):
  * TTFT : request sent -> first non-empty content token arrives
  * TPS  : (generated tokens - 1) / (last token time - first token time)
           The first token is excluded because its latency is TTFT (prompt processing),
           so TPS reflects pure decode speed.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from dataclasses import dataclass, field

import httpx

CHAT_URL = "http://127.0.0.1:8080/v1/chat/completions"
_client = httpx.Client(timeout=300)


@dataclass
class GenStats:
    ttft_ms: float = 0.0
    tps: float = 0.0
    completion_tokens: int = 0
    prompt_tokens: int = 0
    total_ms: float = 0.0
    server: dict = field(default_factory=dict)  # llama-server `timings` block


def stream_chat(messages: list[dict], stats: GenStats, *, temperature: float = 0.1,
                max_tokens: int = 512) -> Iterator[str]:
    """Yield content tokens as they arrive; fill `stats` when the stream ends."""
    payload = {
        "messages": messages,
        "stream": True,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "cache_prompt": True,  # reuse KV cache for the shared system-prompt prefix
    }
    t0 = time.perf_counter()
    t_first = t_last = None
    with _client.stream("POST", CHAT_URL, json=payload) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            event = json.loads(line[len("data: "):])
            if "timings" in event:
                stats.server = event["timings"]
            for choice in event.get("choices", []):
                token = choice.get("delta", {}).get("content")
                if token:
                    t_last = time.perf_counter()
                    if t_first is None:
                        t_first = t_last
                    yield token
    t_end = time.perf_counter()

    stats.total_ms = 1000 * (t_end - t0)
    stats.completion_tokens = int(stats.server.get("predicted_n", 0))
    stats.prompt_tokens = int(stats.server.get("prompt_n", 0)) + int(stats.server.get("cache_n", 0))
    if t_first is not None:
        stats.ttft_ms = 1000 * (t_first - t0)
        if stats.completion_tokens > 1 and t_last > t_first:
            stats.tps = (stats.completion_tokens - 1) / (t_last - t_first)
