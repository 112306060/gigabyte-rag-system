# Benchmark: qwen3-4b_bm25

- date: 2026-10-02T13:53:38
- generator: `C:\Users\user\Desktop\技嘉面試實作\models\Qwen3-4B-Instruct-2507-Q4_K_M.gguf`
- config: prompt=v3, k=5, mode=bm25, prune=True, repeat=1, traditional=False

## Retrieval (raw ranking, answerable questions)

| mode | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|
| dense | 0.889 | 0.972 | 0.972 | 0.926 |
| bm25 | 0.889 | 0.972 | 1.000 | 0.933 |
| hybrid | 0.917 | 0.972 | 1.000 | 0.942 |

Final context (hybrid + prune): gold chunk present **100.0%**, avg 3.75 chunks

## Top-1 cosine (threshold calibration)

- answerable:   min 0.44, median 0.567
- unanswerable: max 0.531, values [0.408, 0.456, 0.479, 0.497, 0.523, 0.531]

## Answer quality

| metric | value |
|---|---|
| overall accuracy | 97.6% (42 q) |
| answerable accuracy | 97.2% |
| unanswerable → correct refusal | 100.0% |
| false refusal (answerable) | 2.8% |
| citation compliance (has [n]) | 97.2% |
| citation correctness (cited chunk supports answer) | 100.0% (35 cited answers) |
| Simplified-Chinese leakage | 3.3% |

| category | n | accuracy |
|---|---|---|
| aggregate | 3 | 100.0% |
| basic | 18 | 100.0% |
| colloquial | 3 | 100.0% |
| mixed | 6 | 100.0% |
| sku | 6 | 83.3% |
| unanswerable | 6 | 100.0% |

| language | n | accuracy |
|---|---|---|
| en | 12 | 100.0% |
| mix | 8 | 100.0% |
| zh | 22 | 95.5% |

## Latency

| metric | p50 | p95 | mean |
|---|---|---|---|
| retrieval (ms) | 29.9 | 41.5 | 31.2 |
| LLM TTFT (ms) | 404.0 | 620.4 | 404.3 |
| E2E TTFT (ms) | 432.4 | 647.1 | 435.6 |

- avg prompt tokens: 1182 (of which served from prompt cache: 520 — the shared system prompt), avg completion tokens: 35

## Throughput (decode)

Fixed 256-token generation (ignore_eos) on a real RAG prompt, 5 runs:

| measured by | TPS mean | std |
|---|---|---|
| client (stream timing) | 52.5 | 0.1 |
| llama-server timings | 52.5 | 0.1 |

- peak VRAM (whole GPU): **3132 MiB** / 4096 MiB

## Failures (1)

- **q27** `BXH 的顯卡功耗是多少？` → context ['row02_BXH', 'overview', 'row03', 'row04', 'row01']
  > BXH 的顯卡功耗在參考資料中未提及此資訊。[1]
