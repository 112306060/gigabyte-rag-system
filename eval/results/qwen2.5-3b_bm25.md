# Benchmark: qwen2.5-3b_bm25

- date: 2026-10-02T14:10:38
- generator: `C:\Users\user\Desktop\技嘉面試實作\models\qwen2.5-3b-instruct-q4_k_m.gguf`
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
| overall accuracy | 92.9% (42 q) |
| answerable accuracy | 94.4% |
| unanswerable → correct refusal | 83.3% |
| false refusal (answerable) | 5.6% |
| citation compliance (has [n]) | 2.8% |
| citation correctness (cited chunk supports answer) | 100.0% (1 cited answers) |
| Simplified-Chinese leakage | 3.3% |

| category | n | accuracy |
|---|---|---|
| aggregate | 3 | 100.0% |
| basic | 18 | 94.4% |
| colloquial | 3 | 100.0% |
| mixed | 6 | 100.0% |
| sku | 6 | 83.3% |
| unanswerable | 6 | 83.3% |

| language | n | accuracy |
|---|---|---|
| en | 12 | 100.0% |
| mix | 8 | 75.0% |
| zh | 22 | 95.5% |

## Latency

| metric | p50 | p95 | mean |
|---|---|---|---|
| retrieval (ms) | 28.6 | 36.6 | 29.5 |
| LLM TTFT (ms) | 305.3 | 481.0 | 307.5 |
| E2E TTFT (ms) | 334.3 | 507.3 | 337.0 |

- avg prompt tokens: 1182 (of which served from prompt cache: 520 — the shared system prompt), avg completion tokens: 23

## Throughput (decode)

Fixed 256-token generation (ignore_eos) on a real RAG prompt, 5 runs:

| measured by | TPS mean | std |
|---|---|---|
| client (stream timing) | 71.1 | 0.1 |
| llama-server timings | 71.1 | 0.1 |

- peak VRAM (whole GPU): **2159 MiB** / 4096 MiB

## Failures (3)

- **q09** `視訊鏡頭支援人臉辨識嗎？` → context ['row10']
  > 規格資料中未提及此資訊。
- **q32** `RTX 5070 Ti 版本的電池容量跟其他型號一樣嗎？` → context ['row12', 'row02_BXH', 'overview']
  > 規格資料中未提及此資訊。
- **q39** `CPU 的 TDP 是多少瓦？` → context ['row15', 'row01', 'overview', 'row02_variants', 'row03']
  > CPU 的 TDP 是 5.4 GHz。
