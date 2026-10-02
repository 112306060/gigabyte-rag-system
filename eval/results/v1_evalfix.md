# Benchmark: v1_evalfix

- date: 2026-10-02T13:05:55
- generator: `C:\Users\user\Desktop\技嘉面試實作\models\qwen2.5-3b-instruct-q4_k_m.gguf`
- config: k=5, mode=hybrid, prune=True, repeat=3

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
| overall accuracy | 92.9% (42 q) |
| answerable accuracy | 91.7% |
| unanswerable → correct refusal | 100.0% |
| false refusal (answerable) | 5.6% |
| citation rate | 13.9% |
| Simplified-Chinese leakage | 3.3% |

| category | n | accuracy |
|---|---|---|
| aggregate | 3 | 100.0% |
| basic | 18 | 88.9% |
| colloquial | 3 | 100.0% |
| mixed | 6 | 100.0% |
| sku | 6 | 83.3% |
| unanswerable | 6 | 100.0% |

| language | n | accuracy |
|---|---|---|
| en | 12 | 100.0% |
| mix | 8 | 87.5% |
| zh | 22 | 90.9% |

## Latency

| metric | p50 | p95 | mean |
|---|---|---|---|
| retrieval (ms) | 28.0 | 36.9 | 29.2 |
| LLM TTFT (ms) | 304.7 | 472.6 | 298.9 |
| E2E TTFT (ms) | 338.6 | 498.3 | 328.1 |

- avg prompt tokens: 1061 (of which served from prompt cache: 395 — the shared system prompt), avg completion tokens: 30

## Throughput (decode)

Fixed 256-token generation (ignore_eos) on a real RAG prompt, 5 runs:

| measured by | TPS mean | std |
|---|---|---|
| client (stream timing) | 70.1 | 1.1 |
| llama-server timings | 70.1 | 1.1 |

- peak VRAM (whole GPU): **2159 MiB** / 4096 MiB

## Failures (3)

- **q09** `視訊鏡頭支援人臉辨識嗎？` → context ['row10']
  > 規格資料中未提及此資訊。
- **q11** `這台是什麼顏色？` → context ['row16', 'row00', 'row03', 'row06', 'row02_variants']
  > 這台是暗 Tide 風色。
- **q32** `RTX 5070 Ti 版本的電池容量跟其他型號一樣嗎？` → context ['row02_BXH', 'overview', 'row12']
  > 規格資料中未提及此資訊。
