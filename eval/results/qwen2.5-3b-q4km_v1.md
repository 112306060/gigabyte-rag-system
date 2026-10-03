# Benchmark: qwen2.5-3b-q4km_v1

- date: 2026-09-30T18:17:37
- generator: `qwen2.5-3b-instruct-q4_k_m.gguf`
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
| overall accuracy | 90.5% (42 q) |
| answerable accuracy | 88.9% |
| unanswerable → correct refusal | 100.0% |
| false refusal (answerable) | 5.6% |
| citation rate | 13.9% |
| Simplified-Chinese leakage | 0.0% |

| category | n | accuracy |
|---|---|---|
| aggregate | 3 | 66.7% |
| basic | 18 | 88.9% |
| colloquial | 3 | 100.0% |
| mixed | 6 | 100.0% |
| sku | 6 | 83.3% |
| unanswerable | 6 | 100.0% |

| language | n | accuracy |
|---|---|---|
| en | 12 | 91.7% |
| mix | 8 | 87.5% |
| zh | 22 | 90.9% |

## Latency & throughput

| metric | p50 | p95 | mean |
|---|---|---|---|
| retrieval (ms) | 26.7 | 44.9 | 28.2 |
| LLM TTFT (ms) | 40.1 | 437.1 | 115.9 |
| E2E TTFT (ms) | 70.2 | 459.2 | 144.1 |
| TPS client (tok/s) | 76.5 | 89.4 | 77.3 |
| TPS server (tok/s) | 70.9 | 72.9 | 70.1 |

- avg prompt tokens: 1061, avg completion tokens: 30
- peak VRAM (whole GPU): **2159 MiB** / 4096 MiB

## Failures (4)

- **q09** `視訊鏡頭支援人臉辨識嗎？` → context ['row10']
  > 規格資料中未提及此資訊。
- **q11** `這台是什麼顏色？` → context ['row16', 'row00', 'row03', 'row06', 'row02_variants']
  > 這台是暗 Tide 風色。
- **q32** `RTX 5070 Ti 版本的電池容量跟其他型號一樣嗎？` → context ['row02_BXH', 'overview', 'row12']
  > 規格資料中未提及此資訊。
- **q34** `How many Type-C ports are there?` → context ['row07']
  > 2  Source: [1]
