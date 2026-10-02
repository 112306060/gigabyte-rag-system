"""Build docs/EXPERIMENTS.md from eval/results/ (every number comes straight from the JSON).

Main part: the experiment matrix produced by scripts/run_matrix.ps1
(3 generator models x 6 configs, named "<model>_<config>.json").
Appendix: the earlier development runs on Qwen2.5-3B (v1_evalfix / v2 / v3), used to
check that the matrix rerun reproduces them.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "eval" / "results"
OUT = ROOT / "docs" / "EXPERIMENTS.md"

MODELS = [("qwen2.5-1.5b", "Qwen2.5-1.5B"), ("qwen2.5-3b", "Qwen2.5-3B"), ("qwen3-4b", "Qwen3-4B-2507")]
CONFIGS = [
    ("prompt-v1", "prompt v1", "基準 prompt（含低相關度提示）"),
    ("prompt-v2", "prompt v2", "理解英文資料、專有名詞保留原文、不照抄標籤"),
    ("prompt-v3", "prompt v3", "v2 + 禁止用其他項目的數值代替（**系統預設**）"),
    ("no-prune", "v3 無後處理", "v3，但 context 不做同列去重 / 相對門檻（repeat=1）"),
    ("dense", "v3 只用 dense", "v3，檢索只用向量（repeat=1）"),
    ("bm25", "v3 只用 BM25", "v3，檢索只用 BM25（repeat=1）"),
]
PROMPTS = CONFIGS[:3]
HISTORY = [("v1_evalfix", "prompt-v1"), ("v2", "prompt-v2"), ("v3", "prompt-v3")]


def load(stem):
    p = RES / f"{stem}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def pct(x):
    return f"{x:.1%}"


def cell(d, fn):
    return fn(d) if d and d.get("summary") else "—"


def esc(s, n):
    return s.strip().replace("\n", " ").replace("|", "\\|")[:n]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    runs = {(m, c): load(f"{m}_{c}") for m, _ in MODELS for c, _, _ in CONFIGS}
    golden = [json.loads(l) for l in (ROOT / "eval" / "golden_qa.jsonl").read_text(encoding="utf-8").splitlines() if l]
    rows = {k: ({r["id"]: r for r in d["rows"]} if d else {}) for k, d in runs.items()}

    L = ["# 實驗紀錄 Experiments", "",
         "所有數字由 `eval/make_report.py` 從 `eval/results/*.json` 自動產生；實驗由 `scripts/run_matrix.ps1` 執行，"
         "每個模型單獨載入 GPU，並先向 server 確認載入的模型正確。", "",
         f"評測集 `eval/golden_qa.jsonl`：{len(golden)} 題（{sum(bool(g['gold_chunks']) for g in golden)} 題有答案、"
         f"{sum(not g['gold_chunks'] for g in golden)} 題無答案）。**錯 1 題 ≈ 2.4 個百分點**，差距在 1–2 題內視為誤差範圍。", "",
         "## 1. 實驗設定", "", "| 設定 | 說明 |", "|---|---|"]
    L += [f"| {lab} | {desc} |" for _, lab, desc in CONFIGS]
    L += ["", "共通：hybrid 檢索（BM25 + bge-m3 + RRF）、k=5、llama.cpp b11276、Q4_K_M 量化、ctx 4096、temperature 0.1；"
              "prompt 設定每題跑 3 輪取延遲 p50/p95，品質以第 1 輪評分。", ""]

    def matrix(title, fn, note=""):
        out = [f"### {title}", "", "| 設定 | " + " | ".join(lab for _, lab in MODELS) + " |",
               "|---|" + "---|" * len(MODELS)]
        for c, clab, _ in CONFIGS:
            out.append(f"| {clab} | " + " | ".join(cell(runs[(m, c)], fn) for m, _ in MODELS) + " |")
        return out + ([note] if note else []) + [""]

    L += ["## 2. 模型 × 設定 總表", ""]
    L += matrix("整體準確率", lambda d: pct(d["summary"]["overall"]["acc"]))
    L += matrix("有答案題準確率", lambda d: pct(d["summary"]["answerable"]["acc"]))
    L += matrix("無答案題 → 正確拒答率（越高越不會編造）", lambda d: pct(d["summary"]["unanswerable_refusal"]["acc"]))
    L += matrix("誤拒率（有答案卻說沒有）", lambda d: pct(d["summary"]["false_refusal_rate"]))
    L += matrix("引用遵守率", lambda d: pct(d["summary"]["citation_rate"]))
    L += matrix("簡體字外洩率（中文/混合題）", lambda d: pct(d["summary"]["simplified_leak_rate"]))
    L += matrix("E2E TTFT p50 / p95 (ms)", lambda d: f"{d['summary']['latency_ms']['e2e_ttft']['p50']:.0f} / "
                                                     f"{d['summary']['latency_ms']['e2e_ttft']['p95']:.0f}")
    L += matrix("解碼 TPS（固定 256 tokens，mean ± std）",
                lambda d: f"{d['throughput']['client_tps_mean']:.1f} ± {d['throughput']['client_tps_std']:.1f}")
    L += matrix("平均 prompt tokens", lambda d: f"{d['summary']['avg_prompt_tokens']:.0f}")
    L += matrix("峰值 VRAM (MiB / 4096)", lambda d: str(d["peak_vram_mib"]))

    # retrieval (model independent)
    any_run = next(d for d in runs.values() if d)
    r = any_run["retrieval"]; cal = any_run["calibration"]
    L += ["## 3. 檢索評測（與生成模型無關）", "", "| 模式 | Hit@1 | Hit@3 | Hit@5 | MRR |", "|---|---|---|---|---|"]
    L += [f"| {m} | {r[m]['hit@1']:.3f} | {r[m]['hit@3']:.3f} | {r[m]['hit@5']:.3f} | {r[m]['mrr']:.3f} |"
          for m in ["dense", "bm25", "hybrid"]]
    pc = r["pruned_context"]
    L += ["", f"最終 context（hybrid + 後處理）：正確 chunk 出現率 **{pc['gold_in_context']:.1%}**，平均 {pc['avg_chunks']:.2f} 個 chunk。",
          f"Top-1 cosine：有答案題最低 {min(cal['answerable'])}；無答案題 {cal['unanswerable']} → 分布重疊，無法用門檻判斷有無答案。", ""]

    # per-question matrix, prompt configs only (9 columns)
    cols = [(m, c) for m, _ in MODELS for c, _, _ in PROMPTS]
    short = {"qwen2.5-1.5b": "1.5B", "qwen2.5-3b": "3B", "qwen3-4b": "4B"}
    L += ["## 4. 逐題對錯矩陣（prompt v1 / v2 / v3 × 三個模型）", "",
          "| 題號 | 類別 | 問題 | " + " | ".join(f"{short[m]} {c[-2:]}" for m, c in cols) + " |",
          "|---|---|---|" + "---|" * len(cols)]
    shown = 0
    for g in golden:
        marks = ["✓" if rows[k].get(g["id"], {}).get("correct") else "✗" for k in cols]
        if all(x == "✓" for x in marks):
            continue
        shown += 1
        L.append(f"| {g['id']} | {g['category']} | {g['query']} | " + " | ".join(marks) + " |")
    L += ["", f"其餘 {len(golden) - shown} 題在這 9 組中全部答對，未列出。", ""]

    # failure answers per model under the default prompt
    L += ["## 5. 預設設定（prompt v3）下三個模型的回答對照（只列至少一個模型答錯的題目）", ""]
    for g in golden:
        rs = [rows[(m, "prompt-v3")].get(g["id"]) for m, _ in MODELS]
        if all(x and x["correct"] for x in rs):
            continue
        L += [f"#### {g['id']}（{g['category']}）{g['query']}", "", "| 模型 | 判定 | 回答 |", "|---|---|---|"]
        for (m, lab), x in zip(MODELS, rs):
            if x:
                L.append(f"| {lab} | {'✓' if x['correct'] else '✗'} | {esc(x['answer'], 220)} |")
        L.append("")

    # reproducibility vs. earlier development runs
    L += ["## 附錄 A. 可重現性：Qwen2.5-3B 矩陣重跑 vs. 開發期間的結果", "",
          "| 開發期間 | 矩陣重跑 | 整體（開發 → 重跑） | 對錯不同的題目 |", "|---|---|---|---|"]
    for old, new in HISTORY:
        a, b = load(old), runs[("qwen2.5-3b", new)]
        if not (a and b):
            continue
        ra, rb = {x["id"]: x for x in a["rows"]}, rows[("qwen2.5-3b", new)]
        diff = [q for q in ra if ra[q]["correct"] != rb[q]["correct"]]
        L.append(f"| `{old}` | `qwen2.5-3b_{new}` | {pct(a['summary']['overall']['acc'])} → "
                 f"{pct(b['summary']['overall']['acc'])} | {', '.join(diff) or '無'} |")
    L += ["", "## 附錄 B. 評測方法的修正紀錄", "",
          "- 同一題連續重跑會讓整段 prompt 命中快取 → 改為「外層輪次、內層題目」。",
          "- llama-server 預設 `--cache-ram 8192` 會重放跑過的 prompt → 啟動時設 `--cache-ram 0`。",
          "- 短回答（平均約 30 tokens）的 TPS 雜訊大 → 另做固定 256 tokens（ignore_eos）的吞吐量測試。",
          "- 評分規則支援 regex（q34 回答「2」原本被誤判）；簡體字表補齊（原本漏掉「笔」）。",
          "- 第一版（`qwen2.5-3b-q4km_v1`）的數字受上述問題影響，僅保留作紀錄。",
          "- 評分規則修正（矩陣跑完後，逐題人工檢查回答時發現的誤判，只修正「對的被判錯」）："
          "q10「有背光嗎」原本要求必須出現 RGB → 接受 背光 / backlit / RGB；"
          "q33 原本只接受「4個」→ 也接受國字「四個」。所有結果以 `eval/regrade.py` 用同一套規則重新評分。", ""]

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
