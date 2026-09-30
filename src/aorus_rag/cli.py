"""Interactive Q&A in the terminal.

    uv run aorus-rag                     # interactive
    uv run aorus-rag -q "這台多重？"      # single question
    uv run aorus-rag --show-context      # also print retrieved chunk ids
"""

from __future__ import annotations

import argparse
import sys

from aorus_rag.rag import RAG, RunStats


def ask(rag: RAG, query: str, show_context: bool) -> None:
    stats = RunStats()
    for token in rag.answer(query, stats):
        print(token, end="", flush=True)
    print()
    if show_context:
        print("  context:", ", ".join(f"{h.chunk['id']}({h.dense:.2f})" for h in stats.hits))
    g = stats.gen
    print(f"  [retrieval {stats.retrieval_ms:.0f} ms | LLM TTFT {g.ttft_ms:.0f} ms | "
          f"E2E TTFT {stats.e2e_ttft_ms:.0f} ms | {g.tps:.1f} tok/s | "
          f"prompt {g.prompt_tokens} tok, output {g.completion_tokens} tok]")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="AORUS MASTER 16 AM6H spec assistant")
    p.add_argument("-q", "--query", help="ask one question and exit")
    p.add_argument("-k", type=int, default=5, help="number of chunks to retrieve")
    p.add_argument("--mode", choices=["hybrid", "dense", "bm25"], default="hybrid")
    p.add_argument("--show-context", action="store_true")
    args = p.parse_args()

    rag = RAG(k=args.k, mode=args.mode)
    if args.query:
        ask(rag, args.query, args.show_context)
        return

    print("AORUS MASTER 16 AM6H 規格助理（輸入 exit 離開）")
    while True:
        try:
            query = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if query.lower() in {"exit", "quit"}:
            break
        if query:
            ask(rag, query, args.show_context)


if __name__ == "__main__":
    main()
