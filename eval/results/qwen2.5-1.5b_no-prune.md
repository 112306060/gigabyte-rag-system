# Benchmark: qwen2.5-1.5b_no-prune

- date: 2026-10-02T14:02:32
- generator: `qwen2.5-1.5b-instruct-q4_k_m.gguf`
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
| overall accuracy | 85.7% (42 q) |
| answerable accuracy | 94.4% |
| unanswerable → correct refusal | 33.3% |
| false refusal (answerable) | 0.0% |
| citation compliance (has [n]) | 0.0% |
| citation correctness (cited chunk supports answer) | — (0 cited answers) |
| Simplified-Chinese leakage | 0.0% |

| category | n | accuracy |
|---|---|---|
| aggregate | 3 | 100.0% |
| basic | 18 | 100.0% |
| colloquial | 3 | 66.7% |
| mixed | 6 | 100.0% |
| sku | 6 | 83.3% |
| unanswerable | 6 | 33.3% |

| language | n | accuracy |
|---|---|---|
| en | 12 | 100.0% |
| mix | 8 | 87.5% |
| zh | 22 | 77.3% |

## Latency

| metric | p50 | p95 | mean |
|---|---|---|---|
| retrieval (ms) | 33.1 | 47.5 | 33.2 |
| LLM TTFT (ms) | 214.1 | 263.2 | 209.7 |
| E2E TTFT (ms) | 246.6 | 296.9 | 242.9 |

- avg prompt tokens: 1320 (of which served from prompt cache: 528 — the shared system prompt), avg completion tokens: 40

## Throughput (decode)

Fixed 256-token generation (ignore_eos) on a real RAG prompt, 5 runs:

| measured by | TPS mean | std |
|---|---|---|
| client (stream timing) | 107.1 | 1.7 |
| llama-server timings | 107.1 | 1.7 |

- peak VRAM (whole GPU): **1205 MiB** / 4096 MiB

## Failures (6)

- **q31** `顯卡是什麼？` → context ['row02_BXH', 'row02_BZH', 'row02_BYH', 'row02_variants', 'overview']
  > 顯卡是顯示晶片，本產品的顯示晶片為NVIDIA® GeForce RTX™ 5070 Ti Laptop GPU。
- **q35** `可以插記憶卡嗎？` → context ['row04', 'overview', 'row07', 'row02_BZH', 'row05']
  > 可以插記憶卡。根據規格，本產品提供2x SO-DIMM sockets for expansion，這意味著它支持擴充記憶體。
- **q38** `電池續航力可以撐幾小時？` → context ['row12', 'overview', 'row13', 'row04', 'row15']
  > 電池續航力可以撐約2.5小時。
- **q39** `CPU 的 TDP 是多少瓦？` → context ['row02_BXH', 'row01', 'row02_BZH', 'overview', 'row13']
  > CPU 的 TDP（Thermal Design Power）是 175W。
- **q40** `螢幕是觸控螢幕嗎？` → context ['row03', 'row00', 'row02_BZH', 'row02_variants', 'row02_BXH']
  > 螢幕不是觸控螢幕。
- **q42** `有指紋辨識嗎？` → context ['row10', 'row00', 'row09', 'row02_variants', 'row01']
  > 有指紋辨識功能。附註（補充說明，非規格值）：May vary by scenario。
