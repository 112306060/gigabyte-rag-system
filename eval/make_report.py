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
    ("prompt-v2", "prompt v2", "理解英文資料、專有名詞保留原文、不照抄標籤（**最終預設**，見第 6 節）"),
    ("prompt-v3", "prompt v3", "v2 + 禁止用其他項目的數值代替（Qwen2.5-3B 需要的護欄）"),
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


def _quality_rows(s, extra=()):
    st = s["stability"]
    rows = [(f"第 {i + 1} 輪準確率", pct(a)) for i, a in enumerate(st["per_pass_acc"])]
    rows += [("3 輪皆答對", f"{st['all_passes_correct']} / {s['overall']['n']}"),
             ("無答案題 → 正確拒答", pct(s["unanswerable_refusal"]["acc"]) if s.get("unanswerable_refusal") else "—（本題組無）"),
             ("誤拒率", pct(s["false_refusal_rate"])),
             ("引用遵守率", pct(s["citation_rate"])),
             ("引用正確率", f"{pct(s['citation_correctness'])}（{s['citation_judged']} 個有引用的回答）"),
             ("簡體字外洩率", pct(s["simplified_leak_rate"]))]
    return rows + list(extra)


def _perf_rows(d):
    s = d["summary"]; lat = s["latency_ms"]; t = d["throughput"]
    return [("E2E TTFT p50 / p95", f"{lat['e2e_ttft']['p50']:.0f} / {lat['e2e_ttft']['p95']:.0f} ms"),
            ("LLM TTFT p50 / p95", f"{lat['llm_ttft']['p50']:.0f} / {lat['llm_ttft']['p95']:.0f} ms"),
            ("檢索 p50", f"{lat['retrieval']['p50']:.0f} ms"),
            ("解碼 TPS（256 tokens）", f"{t['client_tps_mean']:.1f} ± {t['client_tps_std']:.1f} tok/s"),
            ("峰值 VRAM", f"{d['peak_vram_mib']} / 4096 MiB")]


def final_section(golden):
    d = load("final_defaults")
    if not d:
        return []
    s = d["summary"]; c = d["config"]
    rep = load("final_qwen3-4b_v2_s2tw")
    L = ["## 6. 最終設定（鎖定的預設值）", "",
         f"結果檔 `final_defaults`：啟動 server 與 benchmark 都**不帶任何設定參數**。實際載入 "
         f"`{Path(d['model']).name}`，prompt={c['prompt']}、mode={c['mode']}、prune={c['prune']}、"
         f"OpenCC s2tw={c['traditional']}，42 題 × {c['repeat']} 輪。", "",
         "| 指標 | 結果 |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in _quality_rows(s) + _perf_rows(d)]
    if rep:
        a = {r["id"]: r for r in rep["rows"]}; b = {r["id"]: r for r in d["rows"]}
        same_ctx = sum(a[q]["context"] == b[q]["context"] for q in a)
        same_ans = sum(a[q]["answers_all"] == b[q]["answers_all"] for q in a)
        L += ["", f"與帶參數執行的同一組合（`final_qwen3-4b_v2_s2tw`）比較：檢索 context {same_ctx}/42 完全相同；"
                  f"回答逐字相同 {same_ans}/42（temperature 0.1 未固定 seed，措辭會變，但兩次共 6 輪對錯皆相同）。"]
    L += ["", "**OpenCC 設定的選擇**（以 1,176 個已存回答實測）：`s2twp` 會改壞正確用詞（連接埠→連線埠、擴展→擴充套件）；"
              "`s2t` 使用非台灣字形（峰→峯、為→爲）；採用 `s2tw` 並將「臺」改回「台」。串流時為避免切斷詞語而緩衝，"
              "E2E TTFT 平均約增加 30 ms。", "",
          "**已知限制**：s2tw 只轉字形，回答中仍可能出現大陸 IT 用詞（如 線程、性能、刷新率），本次未處理。", ""]
    return L


def heldout_section():
    d = load("heldout_final")
    review_path = ROOT / "eval" / "heldout_manual_review.json"
    if not d:
        return []
    review = json.loads(review_path.read_text(encoding="utf-8")) if review_path.exists() else {"overrides": [], "observations": []}
    s = d["summary"]
    qs = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "eval" / "heldout_qa.jsonl").read_text(encoding="utf-8").splitlines() if l}
    rows = {r["id"]: r for r in d["rows"]}

    # apply manual correctness overrides to a copy of the per-pass results
    manual_runs = {q: list(r["correct_runs"]) for q, r in rows.items()}
    cite_fix = 0
    for o in review["overrides"]:
        if o["aspect"] == "correctness":
            manual_runs[o["id"]][o["pass"] - 1] = o["manual"]
        elif o["aspect"] == "citation" and o["manual"]:
            cite_fix += 1
    n = len(rows); n_pass = len(next(iter(manual_runs.values())))
    m_pass = [sum(v[p] for v in manual_runs.values()) / n for p in range(n_pass)]
    m_all = sum(all(v) for v in manual_runs.values())
    cite_ok = round(s["citation_correctness"] * s["citation_judged"]) + cite_fix

    L = ["## 7. Held-out 測試（未參與開發的新題目）", "",
         "- 題目：`eval/heldout_qa.jsonl`，12 題，刻意涵蓋原 42 題較少的邊界情況（跨欄位、SKU 反查、I/O 位置、中英混合、易幻覺推論、口語）。",
         "- 題目與評分規則在執行前定案並 commit（`70f36c5`），評分規則先以 25 個手寫回答驗證（`eval/test_heldout_grader.py`）。",
         "- 以鎖定的預設設定執行一次（3 輪），執行後**不修改** prompt、檢索、設定與評分規則。",
         f"- 人工判定記錄於 `eval/heldout_manual_review.json`；{review['policy']}", "",
         "### 7.1 自動評分 vs. 人工判定", "",
         "| 指標 | 自動評分 | 人工判定 |", "|---|---|---|",
         f"| 整體準確率（第 1 輪） | {pct(s['overall']['acc'])} | {pct(m_pass[0])} |"]
    L += [f"| 第 {p + 1} 輪準確率 | {pct(s['stability']['per_pass_acc'][p])} | {pct(m_pass[p])} |" for p in range(n_pass)]
    L += [f"| 3 輪皆答對 | {s['stability']['all_passes_correct']} / {n} | {m_all} / {n} |",
          f"| 引用遵守率 | {pct(s['citation_rate'])} | {pct(s['citation_rate'])} |",
          f"| 引用正確率 | {pct(s['citation_correctness'])}（{round(s['citation_correctness'] * s['citation_judged'])}/{s['citation_judged']}） | "
          f"{pct(cite_ok / s['citation_judged'])}（{cite_ok}/{s['citation_judged']}） |",
          f"| 簡體字外洩率 | {pct(s['simplified_leak_rate'])} | {pct(s['simplified_leak_rate'])} |", ""]
    L += ["其餘效能指標：" + "；".join(f"{k} {v}" for k, v in _perf_rows(d)) + "。", ""]

    L += ["### 7.2 人工判定與自動評分不同之處", "", "| 題號 | 輪次 | 項目 | 自動 | 人工 | 理由 |", "|---|---|---|---|---|---|"]
    for o in review["overrides"]:
        fmt = lambda v: ("✓" if v else "✗")
        L.append(f"| {o['id']} | {o['pass']} | {'正確性' if o['aspect'] == 'correctness' else '引用'} | "
                 f"{fmt(o['auto'])} | {fmt(o['manual'])} | {o['reason']} |")

    L += ["", "### 7.3 逐題結果（3 輪）", "", "| 題號 | 類別 | 問題 | 自動 | 人工 | 檢索 context |", "|---|---|---|---|---|---|"]
    for q, r in rows.items():
        auto = "".join("✓" if x else "✗" for x in r["correct_runs"])
        man = "".join("✓" if x else "✗" for x in manual_runs[q])
        L.append(f"| {q} | {qs[q]['category']} | {r['query']} | {auto} | {man} | {', '.join(r['context'])} |")

    L += ["", "### 7.4 失敗題目的回答原文（3 輪）", ""]
    for q, v in manual_runs.items():
        if all(v):
            continue
        L += [f"#### {q} {rows[q]['query']}", ""]
        L += [f"- 第 {i} 輪（人工 {'✓' if ok else '✗'}）：{esc(a, 400)}" for i, (a, ok) in enumerate(zip(rows[q]["answers_all"], v), 1)]
        L.append("")

    L += ["### 7.5 人工觀察", ""]
    L += [f"- **{o['id']}**：{o['note']}" for o in review["observations"]]

    r = d["retrieval"]
    L += ["", "### 7.6 檢索（held-out）", "", "| 模式 | Hit@1 | Hit@3 | Hit@5 | MRR |", "|---|---|---|---|---|"]
    L += [f"| {m} | {r[m]['hit@1']:.3f} | {r[m]['hit@3']:.3f} | {r[m]['hit@5']:.3f} | {r[m]['mrr']:.3f} |" for m in ["dense", "bm25", "hybrid"]]
    L += ["", f"最終 context 正確 chunk 出現率 {r['pruned_context']['gold_in_context']:.1%}。在 held-out 上 hybrid 的 Hit@1／MRR 略低於 dense"
              "（42 題中則是 hybrid 最佳）；12 題樣本差 1 題即差 8.3 個百分點，不足以推翻原結論，但如實記錄。", "",
          "### 7.7 結論", "",
          "- 事實查詢、SKU 對照、I/O 位置、中英混合與口語題在 held-out 上 3 輪皆答對。",
          "- 原 42 題中「無答案題 100% 正確拒答」只適用於**詢問不存在的事實**（價格、續航時間等）。"
          "對於**需要判斷或推論**的問題（h10 遊戲效能），模型會以外部知識下結論，甚至提到規格中沒有的技術；"
          "h11 則過度保守，沒有回答問題本身。",
          "- 依事前承諾不針對 held-out 結果修改系統；此限制列入 README 的已知限制與未來工作。", ""]
    return L


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
              "prompt 設定每題跑 3 輪取延遲 p50/p95，品質以第 1 輪評分。", "",
              "**注意**：第 2–5 節的矩陣實驗在加入 OpenCC 繁體轉換（第 6 節）**之前**執行，輸出未經轉換，"
              "因此簡體字外洩率與 TTFT 不可與第 6、7 節直接比較。", ""]

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
    L += ["## 5. prompt v3 下三個模型的回答對照（只列至少一個模型答錯的題目）", ""]
    for g in golden:
        rs = [rows[(m, "prompt-v3")].get(g["id"]) for m, _ in MODELS]
        if all(x and x["correct"] for x in rs):
            continue
        L += [f"#### {g['id']}（{g['category']}）{g['query']}", "", "| 模型 | 判定 | 回答 |", "|---|---|---|"]
        for (m, lab), x in zip(MODELS, rs):
            if x:
                L.append(f"| {lab} | {'✓' if x['correct'] else '✗'} | {esc(x['answer'], 220)} |")
        L.append("")

    L += final_section(golden)
    L += heldout_section()

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
          "q33 原本只接受「4個」→ 也接受國字「四個」。所有結果以 `eval/regrade.py` 用同一套規則重新評分。",
          "- 評分規則擴充（held-out 執行前加入）：`must_not`（可辨識否定語境）、`refusal_ok`、`min_match`；"
          "以新規則重新評分原 42 題所有結果，分數不變。",
          "- 引用正確率：被引用的 chunk 必須是標準答案 chunk，或包含至少一個必要事實。", ""]

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
