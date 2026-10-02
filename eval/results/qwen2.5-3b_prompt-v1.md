# Benchmark: qwen2.5-3b_prompt-v1

- date: 2026-10-02T14:03:24
- generator: `C:\Users\user\Desktop\技嘉面試實作\models\qwen2.5-3b-instruct-q4_k_m.gguf`
- config: prompt=v1, k=5, mode=hybrid, prune=True, repeat=3, traditional=False

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
| citation compliance (has [n]) | 11.1% |
| citation correctness (cited chunk supports answer) | 100.0% (4 cited answers) |
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
| retrieval (ms) | 31.0 | 44.7 | 32.0 |
| LLM TTFT (ms) | 324.8 | 498.2 | 311.6 |
| E2E TTFT (ms) | 359.4 | 526.4 | 343.6 |

- avg prompt tokens: 1061 (of which served from prompt cache: 395 — the shared system prompt), avg completion tokens: 30

## Throughput (decode)

Fixed 256-token generation (ignore_eos) on a real RAG prompt, 5 runs:

| measured by | TPS mean | std |
|---|---|---|
| client (stream timing) | 67.6 | 0.4 |
| llama-server timings | 67.6 | 0.4 |

- peak VRAM (whole GPU): **2159 MiB** / 4096 MiB

## Failures (3)

- **q09** `視訊鏡頭支援人臉辨識嗎？` → context ['row10']
  > 規格資料中未提及此資訊。
- **q11** `這台是什麼顏色？` → context ['row16', 'row00', 'row03', 'row06', 'row02_variants']
  > 這台是暗 Tide 風色。
- **q32** `RTX 5070 Ti 版本的電池容量跟其他型號一樣嗎？` → context ['row02_BXH', 'overview', 'row12']
  > 規格資料中未提及此資訊。
