"""Benchmark the RAG pipeline on eval/golden_qa.jsonl.

    uv run aorus-bench --name qwen2.5-3b            # full run (servers must be up)
    uv run aorus-bench --name x --skip-gen          # retrieval only (no LLM needed)
    uv run aorus-bench --name x --no-prune          # ablation: raw top-k context

Three parts:
  1. Retrieval   : Hit@1/3/5 and MRR for dense / bm25 / hybrid on the raw ranking,
                   plus how often the final (pruned) context contains a gold chunk.
  2. Generation  : answer accuracy by rule-based checks, refusal accuracy on
                   unanswerable questions, citation rate, Simplified-Chinese leakage,
                   and latency (retrieval, TTFT, E2E TTFT, TPS) with p50/p95.
  3. Calibration : top-1 cosine of answerable vs unanswerable questions, to choose
                   the low-similarity threshold used in the prompt.

Answers are graded with rules (required facts / refusal phrases), not an LLM judge:
a 3B judge is unreliable, and rules give the same score on every run.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime

import httpx
import numpy as np

from aorus_rag.parser import ROOT
from aorus_rag.rag import RAG, RunStats
from aorus_rag.retriever import Retriever

GOLDEN = ROOT / "eval" / "golden_qa.jsonl"
RESULTS_DIR = ROOT / "eval" / "results"

REFUSAL_MARKERS = ["未提及", "沒有提到", "未列出", "notlisted", "notmentioned", "notspecified"]
# Characters that exist only in Simplified Chinese (their Traditional forms differ).
SIMPLIFIED_ONLY = set("这个们为显电处录页说请读与发设备应该对时间长实际过还进从网络视频键盘线统连储规载较级内驱动术体图总数单")


def norm(s: str) -> str:
    """Lowercase, drop ®/™ and all whitespace so '2560 x 1600' == '2560x1600'."""
    return re.sub(r"\s+", "", s.lower().replace("®", "").replace("™", ""))


def load_cases() -> list[dict]:
    return [json.loads(l) for l in GOLDEN.read_text(encoding="utf-8").splitlines() if l.strip()]


# ---------------------------------------------------------------- retrieval

def eval_retrieval(retriever: Retriever, cases: list[dict], k: int) -> dict:
    answerable = [c for c in cases if c["gold_chunks"]]
    out = {}
    for mode in ["dense", "bm25", "hybrid"]:
        hits = {1: 0, 3: 0, 5: 0}
        rr = 0.0
        for c in answerable:
            ids = [h.chunk["id"] for h in retriever.search(c["query"], k=len(retriever.chunks),
                                                           mode=mode, prune=False)]
            rank = next((i + 1 for i, cid in enumerate(ids) if cid in c["gold_chunks"]), None)
            if rank:
                rr += 1 / rank
                for n in hits:
                    hits[n] += rank <= n
        n = len(answerable)
        out[mode] = {f"hit@{m}": hits[m] / n for m in hits} | {"mrr": rr / n}

    # Final context actually given to the LLM (hybrid + pruning).
    in_ctx, sizes = 0, []
    for c in answerable:
        ids = [h.chunk["id"] for h in retriever.search(c["query"], k=k, mode="hybrid", prune=True)]
        sizes.append(len(ids))
        in_ctx += any(i in c["gold_chunks"] for i in ids)
    out["pruned_context"] = {"gold_in_context": in_ctx / len(answerable), "avg_chunks": float(np.mean(sizes))}
    return out


def calibration(retriever: Retriever, cases: list[dict]) -> dict:
    top = defaultdict(list)
    for c in cases:
        hit = retriever.search(c["query"], k=1, mode="dense", prune=False)[0]
        top["answerable" if c["gold_chunks"] else "unanswerable"].append(round(hit.dense, 3))
    return {k: sorted(v) for k, v in top.items()}


# ---------------------------------------------------------------- generation

class VramSampler:
    """Poll nvidia-smi in the background and keep the peak memory.used (MiB)."""

    def __init__(self, interval: float = 0.25):
        self.interval, self.peak, self._stop = interval, 0, threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self._stop.is_set():
            try:
                out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                                     capture_output=True, text=True, timeout=5).stdout
                self.peak = max(self.peak, int(out.strip().splitlines()[0]))
            except Exception:
                pass
            self._stop.wait(self.interval)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._t.join()


def grade(case: dict, answer: str) -> dict:
    a = norm(answer)
    refused = any(m in a for m in REFUSAL_MARKERS)
    if case["gold_chunks"]:
        facts_ok = all(any(norm(alt) in a for alt in group) for group in case["must_include"])
        correct = facts_ok and not refused
    else:
        correct = refused
    return {
        "correct": correct,
        "refused": refused,
        "cited": bool(re.search(r"\[\d+\]", answer)),
        "simplified_chars": sorted({ch for ch in answer if ch in SIMPLIFIED_ONLY}),
    }


def eval_generation(rag: RAG, cases: list[dict], repeat: int) -> list[dict]:
    # Warm-up: the first request pays one-off costs (CUDA kernels, KV-cache allocation).
    for _ in rag.answer("warm up", RunStats()):
        pass

    rows = []
    for c in cases:
        runs = []
        for _ in range(repeat):
            st = RunStats()
            answer = "".join(rag.answer(c["query"], st))
            runs.append((answer, st))
        answer, st = runs[0]  # quality is graded on the first run (temperature 0.1)
        rows.append({
            "id": c["id"], "query": c["query"], "lang": c["lang"], "category": c["category"],
            "answer": answer,
            "context": [h.chunk["id"] for h in st.hits],
            **grade(c, answer),
            "retrieval_ms": [s.retrieval_ms for _, s in runs],
            "ttft_ms": [s.gen.ttft_ms for _, s in runs],
            "e2e_ttft_ms": [s.e2e_ttft_ms for _, s in runs],
            "tps": [s.gen.tps for _, s in runs if s.gen.completion_tokens > 1],
            "server_tps": [s.gen.server.get("predicted_per_second", 0) for _, s in runs],
            "prompt_tokens": st.gen.prompt_tokens,
            "completion_tokens": st.gen.completion_tokens,
        })
        mark = "✓" if rows[-1]["correct"] else "✗"
        print(f"  {mark} {c['id']} {c['query'][:30]:<30} -> {answer[:60]!r}", flush=True)
    return rows


def summarize(rows: list[dict]) -> dict:
    def acc(sel):
        sel = list(sel)
        return {"n": len(sel), "acc": sum(r["correct"] for r in sel) / len(sel)} if sel else None

    def pct(key):
        vals = [v for r in rows for v in r[key]]
        return {"p50": float(np.percentile(vals, 50)), "p95": float(np.percentile(vals, 95)),
                "mean": float(np.mean(vals))} if vals else None

    answerable = [r for r in rows if r["category"] != "unanswerable"]
    return {
        "overall": acc(rows),
        "answerable": acc(answerable),
        "unanswerable_refusal": acc(r for r in rows if r["category"] == "unanswerable"),
        "false_refusal_rate": sum(r["refused"] for r in answerable) / len(answerable),
        "by_category": {k: acc(r for r in rows if r["category"] == k) for k in sorted({r["category"] for r in rows})},
        "by_lang": {k: acc(r for r in rows if r["lang"] == k) for k in sorted({r["lang"] for r in rows})},
        "citation_rate": sum(r["cited"] for r in answerable) / len(answerable),
        "simplified_leak_rate": sum(bool(r["simplified_chars"]) for r in rows if r["lang"] != "en")
                                / max(1, sum(r["lang"] != "en" for r in rows)),
        "latency_ms": {"retrieval": pct("retrieval_ms"), "llm_ttft": pct("ttft_ms"), "e2e_ttft": pct("e2e_ttft_ms")},
        "tps": pct("tps"),
        "server_tps": pct("server_tps"),
        "avg_prompt_tokens": float(np.mean([r["prompt_tokens"] for r in rows])),
        "avg_completion_tokens": float(np.mean([r["completion_tokens"] for r in rows])),
    }


# ---------------------------------------------------------------- report

def to_markdown(res: dict) -> str:
    L = [f"# Benchmark: {res['name']}", "",
         f"- date: {res['date']}", f"- generator: `{res.get('model')}`",
         f"- config: k={res['config']['k']}, mode={res['config']['mode']}, prune={res['config']['prune']}, "
         f"repeat={res['config']['repeat']}", ""]

    L += ["## Retrieval (raw ranking, answerable questions)", "",
          "| mode | Hit@1 | Hit@3 | Hit@5 | MRR |", "|---|---|---|---|---|"]
    for m in ["dense", "bm25", "hybrid"]:
        r = res["retrieval"][m]
        L.append(f"| {m} | {r['hit@1']:.3f} | {r['hit@3']:.3f} | {r['hit@5']:.3f} | {r['mrr']:.3f} |")
    pc = res["retrieval"]["pruned_context"]
    L += ["", f"Final context (hybrid + prune): gold chunk present **{pc['gold_in_context']:.1%}**, "
              f"avg {pc['avg_chunks']:.2f} chunks", ""]

    cal = res["calibration"]
    L += ["## Top-1 cosine (threshold calibration)", "",
          f"- answerable:   min {min(cal['answerable'])}, median {np.median(cal['answerable']):.3f}",
          f"- unanswerable: max {max(cal['unanswerable'])}, values {cal['unanswerable']}", ""]

    s = res.get("summary")
    if not s:
        return "\n".join(L)
    L += ["## Answer quality", "", "| metric | value |", "|---|---|",
          f"| overall accuracy | {s['overall']['acc']:.1%} ({s['overall']['n']} q) |",
          f"| answerable accuracy | {s['answerable']['acc']:.1%} |",
          f"| unanswerable → correct refusal | {s['unanswerable_refusal']['acc']:.1%} |",
          f"| false refusal (answerable) | {s['false_refusal_rate']:.1%} |",
          f"| citation rate | {s['citation_rate']:.1%} |",
          f"| Simplified-Chinese leakage | {s['simplified_leak_rate']:.1%} |", ""]
    L += ["| category | n | accuracy |", "|---|---|---|"]
    L += [f"| {k} | {v['n']} | {v['acc']:.1%} |" for k, v in s["by_category"].items()]
    L += ["", "| language | n | accuracy |", "|---|---|---|"]
    L += [f"| {k} | {v['n']} | {v['acc']:.1%} |" for k, v in s["by_lang"].items()]

    lat = s["latency_ms"]
    L += ["", "## Latency & throughput", "", "| metric | p50 | p95 | mean |", "|---|---|---|---|"]
    for name, v in [("retrieval (ms)", lat["retrieval"]), ("LLM TTFT (ms)", lat["llm_ttft"]),
                    ("E2E TTFT (ms)", lat["e2e_ttft"]), ("TPS client (tok/s)", s["tps"]),
                    ("TPS server (tok/s)", s["server_tps"])]:
        L.append(f"| {name} | {v['p50']:.1f} | {v['p95']:.1f} | {v['mean']:.1f} |")
    L += ["", f"- avg prompt tokens: {s['avg_prompt_tokens']:.0f}, avg completion tokens: "
              f"{s['avg_completion_tokens']:.0f}", f"- peak VRAM (whole GPU): **{res['peak_vram_mib']} MiB** / 4096 MiB", ""]

    fails = [r for r in res["rows"] if not r["correct"]]
    L += [f"## Failures ({len(fails)})", ""]
    for r in fails:
        L.append(f"- **{r['id']}** `{r['query']}` → context {r['context']}")
        L.append(f"  > {r['answer'].strip().replace(chr(10), ' ')[:300]}")
    return "\n".join(L) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("--name", required=True, help="label for this run, e.g. qwen2.5-3b")
    p.add_argument("-k", type=int, default=5)
    p.add_argument("--mode", default="hybrid", choices=["hybrid", "dense", "bm25"])
    p.add_argument("--no-prune", action="store_true")
    p.add_argument("--repeat", type=int, default=3, help="runs per question for latency percentiles")
    p.add_argument("--skip-gen", action="store_true")
    args = p.parse_args()

    cases = load_cases()
    rag = RAG(k=args.k, mode=args.mode, prune=not args.no_prune)
    res = {"name": args.name, "date": datetime.now().isoformat(timespec="seconds"),
           "config": {"k": args.k, "mode": args.mode, "prune": not args.no_prune, "repeat": args.repeat}}

    print("retrieval ...")
    res["retrieval"] = eval_retrieval(rag.retriever, cases, args.k)
    res["calibration"] = calibration(rag.retriever, cases)

    if not args.skip_gen:
        res["model"] = httpx.get("http://127.0.0.1:8080/v1/models").json()["data"][0]["id"]
        print(f"generation ({len(cases)} questions x {args.repeat}) ...")
        t0 = time.perf_counter()
        with VramSampler() as vram:
            res["rows"] = eval_generation(rag, cases, args.repeat)
        res["peak_vram_mib"] = vram.peak
        res["summary"] = summarize(res["rows"])
        print(f"done in {time.perf_counter() - t0:.0f}s")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / f"{args.name}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    md = to_markdown(res)
    (RESULTS_DIR / f"{args.name}.md").write_text(md, encoding="utf-8")
    print("\n" + md)


if __name__ == "__main__":
    main()
