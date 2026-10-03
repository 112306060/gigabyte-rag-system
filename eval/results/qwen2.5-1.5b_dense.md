# Benchmark: qwen2.5-1.5b_dense

- date: 2026-10-02T14:01:02
- generator: `qwen2.5-1.5b-instruct-q4_k_m.gguf`
- config: prompt=v3, k=5, mode=dense, prune=True, repeat=1, traditional=False

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
| overall accuracy | 88.1% (42 q) |
| answerable accuracy | 97.2% |
| unanswerable → correct refusal | 33.3% |
| false refusal (answerable) | 0.0% |
| citation compliance (has [n]) | 0.0% |
| citation correctness (cited chunk supports answer) | — (0 cited answers) |
| Simplified-Chinese leakage | 3.3% |

| category | n | accuracy |
|---|---|---|
| aggregate | 3 | 100.0% |
| basic | 18 | 100.0% |
| colloquial | 3 | 66.7% |
| mixed | 6 | 100.0% |
| sku | 6 | 100.0% |
| unanswerable | 6 | 33.3% |

| language | n | accuracy |
|---|---|---|
| en | 12 | 100.0% |
| mix | 8 | 87.5% |
| zh | 22 | 81.8% |

## Latency

| metric | p50 | p95 | mean |
|---|---|---|---|
| retrieval (ms) | 32.3 | 50.3 | 33.9 |
| LLM TTFT (ms) | 186.7 | 291.9 | 183.8 |
| E2E TTFT (ms) | 217.7 | 326.2 | 217.7 |

- avg prompt tokens: 1215 (of which served from prompt cache: 533 — the shared system prompt), avg completion tokens: 40

## Throughput (decode)

Fixed 256-token generation (ignore_eos) on a real RAG prompt, 5 runs:

| measured by | TPS mean | std |
|---|---|---|
| client (stream timing) | 105.7 | 0.1 |
| llama-server timings | 105.7 | 0.1 |

- peak VRAM (whole GPU): **1205 MiB** / 4096 MiB

## Failures (5)

- **q35** `可以插記憶卡嗎？` → context ['row04', 'row05', 'row07', 'overview', 'row02_variants']
  > 可以插記憶卡。本產品支持2x SO-DIMM sockets for expansion，允許插入記憶卡進行擴充。
- **q38** `電池續航力可以撐幾小時？` → context ['row12', 'overview', 'row02_variants']
  > 電池續航力為99Wh，可以撐約4.5小時。
- **q39** `CPU 的 TDP 是多少瓦？` → context ['row02_variants', 'row01', 'overview', 'row11', 'row03']
  > CPU 的 TDP（Thermal Design Power）是 5.4 GHz。
- **q40** `螢幕是觸控螢幕嗎？` → context ['row03', 'row10', 'overview', 'row02_variants', 'row00']
  > 螢幕不是觸控螢幕。
- **q42** `有指紋辨識嗎？` → context ['row10', 'row11', 'row07', 'row03', 'row06']
  > 有指紋辨識。此產品支持Windows Hello Face Authentication，提供FHD (1080p) IR Webcam和內建麥克風，並支援Intel® Platform Trust Technology (Intel® PTT)。
