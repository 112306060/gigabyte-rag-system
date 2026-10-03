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
from pathlib import Path

import httpx
import numpy as np

from aorus_rag.llm_client import GenStats, stream_chat
from aorus_rag.index import load_chunks
from aorus_rag.parser import ROOT
from aorus_rag.prompt import DEFAULT_PROMPT, PROMPT_RULES, build_messages
from aorus_rag.rag import RAG, RunStats
from aorus_rag.retriever import Retriever

GOLDEN = ROOT / "eval" / "golden_qa.jsonl"
RESULTS_DIR = ROOT / "eval" / "results"

REFUSAL_MARKERS = ["未提及", "沒有提到", "未列出", "notlisted", "notmentioned", "notspecified"]
# Characters that exist only in Simplified Chinese (their Traditional forms differ).
SIMPLIFIED_ONLY = set(
    "这个们为显电处录页说请读与发设备应该对时间长实际过还进从网络视频键盘线统连储规载较级内驱动术体图总数单"
    "笔记脑么吗样种务汉买卖门问关开东车书见话语让认识计运选边质带宽轻环无机号"
)


def norm(s: str) -> str:
    """Lowercase, drop ®/™ and all whitespace so '2560 x 1600' == '2560x1600'."""
    return re.sub(r"\s+", "", s.lower().replace("®", "").replace("™", ""))


def load_cases(path=GOLDEN) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


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


def _fact_present(alt: str, a: str) -> bool:
    """alt is a substring, or a regex when prefixed with 're:' (matched on the normalised answer)."""
    if alt.startswith("re:"):
        return re.search(alt[3:], a) is not None
    return norm(alt) in a


_chunk_text: dict[str, str] = {}


def _supports(case: dict, chunk_id: str) -> bool:
    """A chunk supports the answer if it is a gold chunk or contains at least one required fact.

    "At least one" because multi-fact answers cite a different chunk per sentence
    (e.g. an overview citing the GPU comparison chunk for the GPU sentence only).
    For single-fact questions this is the same as requiring the fact.
    """
    if not _chunk_text:
        _chunk_text.update({c["id"]: norm(c["text"]) for c in load_chunks()})
    if chunk_id in case["gold_chunks"]:
        return True
    text = _chunk_text[chunk_id]
    return any(any(_fact_present(alt, text) for alt in group) for group in case["must_include"])


NEGATIONS = ["沒有", "沒", "無", "不", "非", "not", "no", "without"]
NEGATION_WINDOW = 8  # characters (after norm) before a forbidden term that may negate it


def _violations(case: dict, a: str) -> list[str]:
    """Forbidden content found in the normalised answer.

    Each must_not item is {"term": str, "unless_negated": bool}; a term is a substring or a
    're:' regex. With unless_negated, an occurrence preceded by a negation within
    NEGATION_WINDOW characters is allowed ("右側沒有 HDMI" is a correct answer).
    """
    found = []
    for item in case.get("must_not", []):
        term = item["term"]
        pattern = term[3:] if term.startswith("re:") else re.escape(norm(term))
        for m in re.finditer(pattern, a):
            before = a[max(0, m.start() - NEGATION_WINDOW):m.start()]
            if item.get("unless_negated") and any(n in before for n in NEGATIONS):
                continue
            found.append(m.group(0))
            break
    return found


def grade(case: dict, answer: str, context: list[str]) -> dict:
    a = norm(answer)
    refused = any(m in a for m in REFUSAL_MARKERS)
    violations = _violations(case, a)
    if case["gold_chunks"]:
        groups = case["must_include"]
        hit = sum(any(_fact_present(alt, a) for alt in group) for group in groups)
        facts_ok = hit >= case.get("min_match", len(groups))
        # refusal_ok: the ideal answer itself says part of it is not listed (e.g. "99Wh is
        # capacity, not hours; battery life is not listed"), so a refusal phrase is fine.
        correct = facts_ok and (case.get("refusal_ok", False) or not refused) and not violations
    else:
        correct = refused and not violations

    # Citation correctness: every [n] must point to an existing context chunk that supports
    # the answer. Only judged for answerable questions (a refusal has nothing to support).
    cites = sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer)})
    bad = [n for n in cites if not (1 <= n <= len(context) and _supports(case, context[n - 1]))]
    citation_correct = (not bad) if (cites and case["gold_chunks"]) else None
    return {
        "correct": correct,
        "refused": refused,
        # a refusal phrase on an answerable question, unless the question allows it
        "false_refusal": bool(case["gold_chunks"]) and refused and not case.get("refusal_ok", False),
        "violations": violations,
        "cited": bool(cites),
        "citation_correct": citation_correct,
        "bad_citations": [[n, context[n - 1] if 1 <= n <= len(context) else None] for n in bad],
        "simplified_chars": sorted({ch for ch in answer if ch in SIMPLIFIED_ONLY}),
    }


def eval_generation(rag: RAG, cases: list[dict], repeat: int) -> list[dict]:
    # Warm-up: the first request pays one-off costs (CUDA kernels, KV-cache allocation).
    for _ in rag.answer("warm up", RunStats()):
        pass

    # Passes are the OUTER loop: consecutive requests are always different questions, so
    # llama-server's prompt cache can only reuse the shared system-prompt prefix (as in real
    # use). Repeating the same question back-to-back would reuse the whole prompt and
    # make TTFT look unrealistically low.
    runs: dict[str, list] = {c["id"]: [] for c in cases}
    for p in range(repeat):
        print(f"  pass {p + 1}/{repeat}", flush=True)
        for c in cases:
            st = RunStats()
            answer = "".join(rag.answer(c["query"], st))
            runs[c["id"]].append((answer, st))

    rows = []
    for c in cases:
        case_runs = runs[c["id"]]
        answer, st = case_runs[0]  # headline quality = first pass; every pass is graded below
        context = [h.chunk["id"] for h in st.hits]
        rows.append({
            "id": c["id"], "query": c["query"], "lang": c["lang"], "category": c["category"],
            "answer": answer,
            "context": context,
            **grade(c, answer, context),
            # generation varies even at temperature 0.1, so grade every pass for stability
            "answers_all": [a for a, _ in case_runs],
            "correct_runs": [grade(c, a, [h.chunk["id"] for h in s.hits])["correct"] for a, s in case_runs],
            "retrieval_ms": [s.retrieval_ms for _, s in case_runs],
            "ttft_ms": [s.gen.ttft_ms for _, s in case_runs],
            "e2e_ttft_ms": [s.e2e_ttft_ms for _, s in case_runs],
            "cache_tokens": [int(s.gen.server.get("cache_n", 0)) for _, s in case_runs],
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
    judged = [r for r in answerable if r.get("citation_correct") is not None]
    stability = None
    if rows and "correct_runs" in rows[0]:
        n_pass = len(rows[0]["correct_runs"])
        stability = {
            "passes": n_pass,
            "per_pass_acc": [sum(r["correct_runs"][p] for r in rows) / len(rows) for p in range(n_pass)],
            "all_passes_correct": sum(all(r["correct_runs"]) for r in rows),
            "unstable": [r["id"] for r in rows if len(set(r["correct_runs"])) > 1],
        }
    return {
        "stability": stability,
        "citation_correctness": (sum(r["citation_correct"] for r in judged) / len(judged)) if judged else None,
        "citation_judged": len(judged),
        "overall": acc(rows),
        "answerable": acc(answerable),
        "unanswerable_refusal": acc(r for r in rows if r["category"] == "unanswerable"),
        "false_refusal_rate": sum(r.get("false_refusal", r["refused"]) for r in answerable) / len(answerable),
        "by_category": {k: acc(r for r in rows if r["category"] == k) for k in sorted({r["category"] for r in rows})},
        "by_lang": {k: acc(r for r in rows if r["lang"] == k) for k in sorted({r["lang"] for r in rows})},
        "citation_rate": sum(r["cited"] for r in answerable) / len(answerable),
        "simplified_leak_rate": sum(bool(r["simplified_chars"]) for r in rows if r["lang"] != "en")
                                / max(1, sum(r["lang"] != "en" for r in rows)),
        "latency_ms": {"retrieval": pct("retrieval_ms"), "llm_ttft": pct("ttft_ms"), "e2e_ttft": pct("e2e_ttft_ms")},
        "avg_prompt_tokens": float(np.mean([r["prompt_tokens"] for r in rows])),
        "avg_cached_prompt_tokens": float(np.mean([v for r in rows for v in r["cache_tokens"]])),
        "avg_completion_tokens": float(np.mean([r["completion_tokens"] for r in rows])),
    }


def eval_throughput(rag: RAG, runs: int = 5, n_tokens: int = 256) -> dict:
    """Decode speed on a fixed-length generation.

    RAG answers average ~30 tokens, too short for a stable TPS (timer noise on a few tokens
    dominates). Here we force exactly n_tokens with ignore_eos, using a real RAG prompt.
    """
    query = "介紹一下這台筆電"
    hits = rag.retriever.search(query, k=rag.k, mode=rag.mode, prune=rag.prune)
    messages = build_messages(query, hits, rag.prompt_version)
    client, server = [], []
    for _ in range(runs):
        st = GenStats()
        for _ in stream_chat(messages, st, max_tokens=n_tokens, extra={"ignore_eos": True}):
            pass
        client.append(st.tps)
        server.append(st.server.get("predicted_per_second", 0.0))
    return {"runs": runs, "tokens": n_tokens,
            "client_tps_mean": float(np.mean(client)), "client_tps_std": float(np.std(client)),
            "server_tps_mean": float(np.mean(server)), "server_tps_std": float(np.std(server))}


# ---------------------------------------------------------------- report

def to_markdown(res: dict) -> str:
    L = [f"# Benchmark: {res['name']}", "",
         f"- date: {res['date']}", f"- generator: `{res.get('model')}`",
         f"- config: prompt={res['config'].get('prompt', 'v3')}, k={res['config']['k']}, "
         f"mode={res['config']['mode']}, prune={res['config']['prune']}, repeat={res['config']['repeat']}, "
         f"traditional={res['config'].get('traditional', False)}", ""]

    L += ["## Retrieval (raw ranking, answerable questions)", "",
          "| mode | Hit@1 | Hit@3 | Hit@5 | MRR |", "|---|---|---|---|---|"]
    for m in ["dense", "bm25", "hybrid"]:
        r = res["retrieval"][m]
        L.append(f"| {m} | {r['hit@1']:.3f} | {r['hit@3']:.3f} | {r['hit@5']:.3f} | {r['mrr']:.3f} |")
    pc = res["retrieval"]["pruned_context"]
    L += ["", f"Final context (hybrid + prune): gold chunk present **{pc['gold_in_context']:.1%}**, "
              f"avg {pc['avg_chunks']:.2f} chunks", ""]

    cal = res["calibration"]
    if cal.get("answerable") and cal.get("unanswerable"):
        L += ["## Top-1 cosine (threshold calibration)", "",
              f"- answerable:   min {min(cal['answerable'])}, median {np.median(cal['answerable']):.3f}",
              f"- unanswerable: max {max(cal['unanswerable'])}, values {cal['unanswerable']}", ""]

    s = res.get("summary")
    if not s:
        return "\n".join(L)
    cite_ok = "—" if s.get("citation_correctness") is None else f"{s['citation_correctness']:.1%}"
    refusal = "—" if not s.get("unanswerable_refusal") else f"{s['unanswerable_refusal']['acc']:.1%}"
    L += ["## Answer quality", "", "| metric | value |", "|---|---|",
          f"| overall accuracy | {s['overall']['acc']:.1%} ({s['overall']['n']} q) |",
          f"| answerable accuracy | {s['answerable']['acc']:.1%} |",
          f"| unanswerable → correct refusal | {refusal} |",
          f"| false refusal (answerable) | {s['false_refusal_rate']:.1%} |",
          f"| citation compliance (has [n]) | {s['citation_rate']:.1%} |",
          f"| citation correctness (cited chunk supports answer) | {cite_ok} ({s.get('citation_judged', 0)} cited answers) |",
          f"| Simplified-Chinese leakage | {s['simplified_leak_rate']:.1%} |", ""]
    st = s.get("stability")
    if st and st["passes"] > 1:
        L += [f"### Stability over {st['passes']} passes", "", "| pass | accuracy |", "|---|---|"]
        L += [f"| {i + 1} | {a:.1%} |" for i, a in enumerate(st["per_pass_acc"])]
        L += ["", f"- correct in **all** passes: **{st['all_passes_correct']} / {s['overall']['n']}**",
              f"- questions whose result changed between passes: {st['unstable'] or 'none'}", ""]
    bad = [r for r in res["rows"] if r.get("citation_correct") is False]
    if bad:
        L += ["### Incorrect citations", ""]
        L += [f"- **{r['id']}** cited {r['bad_citations']} → `{r['answer'].strip()[:120]}`" for r in bad]
        L.append("")
    L += ["| category | n | accuracy |", "|---|---|---|"]
    L += [f"| {k} | {v['n']} | {v['acc']:.1%} |" for k, v in s["by_category"].items()]
    L += ["", "| language | n | accuracy |", "|---|---|---|"]
    L += [f"| {k} | {v['n']} | {v['acc']:.1%} |" for k, v in s["by_lang"].items()]

    lat = s["latency_ms"]
    L += ["", "## Latency", "", "| metric | p50 | p95 | mean |", "|---|---|---|---|"]
    for name, v in [("retrieval (ms)", lat["retrieval"]), ("LLM TTFT (ms)", lat["llm_ttft"]),
                    ("E2E TTFT (ms)", lat["e2e_ttft"])]:
        L.append(f"| {name} | {v['p50']:.1f} | {v['p95']:.1f} | {v['mean']:.1f} |")
    L += ["", f"- avg prompt tokens: {s['avg_prompt_tokens']:.0f} "
              f"(of which served from prompt cache: {s['avg_cached_prompt_tokens']:.0f} — the shared system prompt), "
              f"avg completion tokens: {s['avg_completion_tokens']:.0f}"]
    t = res["throughput"]
    L += ["", "## Throughput (decode)", "",
          f"Fixed {t['tokens']}-token generation (ignore_eos) on a real RAG prompt, {t['runs']} runs:", "",
          "| measured by | TPS mean | std |", "|---|---|---|",
          f"| client (stream timing) | {t['client_tps_mean']:.1f} | {t['client_tps_std']:.1f} |",
          f"| llama-server timings | {t['server_tps_mean']:.1f} | {t['server_tps_std']:.1f} |",
          "", f"- peak VRAM (whole GPU): **{res['peak_vram_mib']} MiB** / 4096 MiB", ""]

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
    p.add_argument("--prompt", default=DEFAULT_PROMPT, choices=sorted(PROMPT_RULES))
    p.add_argument("--no-traditional", action="store_true", help="disable OpenCC s2tw output conversion")
    p.add_argument("--questions", default=str(GOLDEN), help="question set (default: eval/golden_qa.jsonl)")
    p.add_argument("--skip-gen", action="store_true")
    args = p.parse_args()

    cases = load_cases(Path(args.questions))
    rag = RAG(k=args.k, mode=args.mode, prune=not args.no_prune, prompt_version=args.prompt,
              traditional=not args.no_traditional)
    res = {"name": args.name, "date": datetime.now().isoformat(timespec="seconds"),
           "questions": Path(args.questions).name,
           "config": {"k": args.k, "mode": args.mode, "prune": not args.no_prune, "repeat": args.repeat,
                      "prompt": args.prompt, "traditional": not args.no_traditional}}

    print("retrieval ...")
    res["retrieval"] = eval_retrieval(rag.retriever, cases, args.k)
    res["calibration"] = calibration(rag.retriever, cases)

    if not args.skip_gen:
        res["model"] = httpx.get("http://127.0.0.1:8080/v1/models").json()["data"][0]["id"]
        print(f"generation ({len(cases)} questions x {args.repeat}) ...")
        t0 = time.perf_counter()
        with VramSampler() as vram:
            res["rows"] = eval_generation(rag, cases, args.repeat)
            print("throughput ...")
            res["throughput"] = eval_throughput(rag)
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
