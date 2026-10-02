# Benchmark: ablation_no-prune

- date: 2026-10-02T13:14:21
- generator: `C:\Users\user\Desktop\技嘉面試實作\models\qwen2.5-3b-instruct-q4_k_m.gguf`
- config: prompt=v3, k=5, mode=hybrid, prune=False, repeat=1, traditional=False

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
| overall accuracy | 95.2% (42 q) |
| answerable accuracy | 97.2% |
| unanswerable → correct refusal | 83.3% |
| false refusal (answerable) | 0.0% |
| citation compliance (has [n]) | 2.8% |
| citation correctness (cited chunk supports answer) | 100.0% (1 cited answers) |
| Simplified-Chinese leakage | 3.3% |

| category | n | accuracy |
|---|---|---|
| aggregate | 3 | 100.0% |
| basic | 18 | 94.4% |
| colloquial | 3 | 100.0% |
| mixed | 6 | 100.0% |
| sku | 6 | 100.0% |
| unanswerable | 6 | 83.3% |

| language | n | accuracy |
|---|---|---|
| en | 12 | 100.0% |
| mix | 8 | 87.5% |
| zh | 22 | 95.5% |

## Latency

| metric | p50 | p95 | mean |
|---|---|---|---|
| retrieval (ms) | 31.6 | 39.4 | 32.4 |
| LLM TTFT (ms) | 369.7 | 437.1 | 352.0 |
| E2E TTFT (ms) | 400.9 | 468.2 | 384.4 |

- avg prompt tokens: 1320 (of which served from prompt cache: 528 — the shared system prompt), avg completion tokens: 30

## Throughput (decode)

Fixed 256-token generation (ignore_eos) on a real RAG prompt, 5 runs:

| measured by | TPS mean | std |
|---|---|---|
| client (stream timing) | 72.5 | 0.2 |
| llama-server timings | 72.5 | 0.2 |

- peak VRAM (whole GPU): **2159 MiB** / 4096 MiB

## Failures (2)

- **q11** `這台是什麼顏色？` → context ['row16', 'row00', 'row03', 'row06', 'row02_BZH']
  > 這台是暗 Tide 風。
- **q39** `CPU 的 TDP 是多少瓦？` → context ['row02_BXH', 'row01', 'row02_BZH', 'overview', 'row13']
  > CPU 的 TDP 是 5.4 GHz。
