# Benchmark: qwen2.5-1.5b_prompt-v2

- date: 2026-10-02T13:57:55
- generator: `qwen2.5-1.5b-instruct-q4_k_m.gguf`
- config: prompt=v2, k=5, mode=hybrid, prune=True, repeat=3, traditional=False

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
| basic | 18 | 94.4% |
| colloquial | 3 | 66.7% |
| mixed | 6 | 100.0% |
| sku | 6 | 100.0% |
| unanswerable | 6 | 33.3% |

| language | n | accuracy |
|---|---|---|
| en | 12 | 100.0% |
| mix | 8 | 87.5% |
| zh | 22 | 77.3% |

## Latency

| metric | p50 | p95 | mean |
|---|---|---|---|
| retrieval (ms) | 31.5 | 40.8 | 31.7 |
| LLM TTFT (ms) | 182.5 | 281.8 | 178.1 |
| E2E TTFT (ms) | 214.2 | 311.8 | 209.9 |

- avg prompt tokens: 1142 (of which served from prompt cache: 476 — the shared system prompt), avg completion tokens: 42

## Throughput (decode)

Fixed 256-token generation (ignore_eos) on a real RAG prompt, 5 runs:

| measured by | TPS mean | std |
|---|---|---|
| client (stream timing) | 107.2 | 0.6 |
| llama-server timings | 107.2 | 0.6 |

- peak VRAM (whole GPU): **1205 MiB** / 4096 MiB

## Failures (6)

- **q01** `這台筆電多重？` → context ['row15', 'overview']
  > 這台筆電共有三個型號：BZH（NVIDIA® GeForce RTX™ 5090 Laptop GPU）、BYH（NVIDIA® GeForce RTX™ 5080 Laptop GPU）、BXH（NVIDIA® GeForce RTX™ 5070 Ti Laptop GPU）。
- **q35** `可以插記憶卡嗎？` → context ['row04', 'overview', 'row07', 'row02_variants', 'row05']
  > 可以插記憶卡。該筆記型電腦支持2x SO-DIMM sockets，可以插入最多64GB DDR5 5600MHz的記憶體。
- **q38** `電池續航力可以撐幾小時？` → context ['row12', 'overview', 'row02_variants']
  > 電池續航力為99Wh，可以撐約4.5小時。
- **q39** `CPU 的 TDP 是多少瓦？` → context ['row02_variants', 'row01', 'overview', 'row03', 'row11']
  > CPU 的 TDP（Thermal Design Power）是 275W。
- **q40** `螢幕是觸控螢幕嗎？` → context ['row03', 'row00', 'row02_variants', 'row10', 'row06']
  > 螢幕不是觸控螢幕。它是一種顯示晶片，提供2560×1600的分辨率，並且支持NVIDIA® G-SYNC®技術。
- **q42** `有指紋辨識嗎？` → context ['row10', 'row00', 'row09', 'row02_variants', 'row01']
  > 有指紋辨識功能。該筆記型電腦支持Windows Hello Face Authentication，這意味著它能夠通過面部識別技術進行身份驗證。
