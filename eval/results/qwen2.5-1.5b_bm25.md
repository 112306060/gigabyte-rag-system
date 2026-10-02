# Benchmark: qwen2.5-1.5b_bm25

- date: 2026-10-02T14:01:46
- generator: `C:\Users\user\Desktop\技嘉面試實作\models\qwen2.5-1.5b-instruct-q4_k_m.gguf`
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
| retrieval (ms) | 30.6 | 45.0 | 32.6 |
| LLM TTFT (ms) | 181.8 | 268.7 | 181.6 |
| E2E TTFT (ms) | 215.0 | 294.8 | 214.1 |

- avg prompt tokens: 1182 (of which served from prompt cache: 520 — the shared system prompt), avg completion tokens: 41

## Throughput (decode)

Fixed 256-token generation (ignore_eos) on a real RAG prompt, 5 runs:

| measured by | TPS mean | std |
|---|---|---|
| client (stream timing) | 107.4 | 1.2 |
| llama-server timings | 107.4 | 1.2 |

- peak VRAM (whole GPU): **1205 MiB** / 4096 MiB

## Failures (5)

- **q35** `可以插記憶卡嗎？` → context ['row04', 'overview', 'row07', 'row02_variants', 'row00']
  > 可以插記憶卡。根據資料，本產品的記憶體規格為Up to 64GB DDR5 5600MHz，並且有2x SO-DIMM sockets for expansion，這意味著本產品支持插記憶卡。
- **q38** `電池續航力可以撐幾小時？` → context ['row12', 'overview', 'row02_variants']
  > 電池續航力為99Wh，可以撐約4.5小時。
- **q39** `CPU 的 TDP 是多少瓦？` → context ['row15', 'row01', 'overview', 'row02_variants', 'row03']
  > 根據提供的資料，AORUS MASTER 16 AM6H 的中央處理器 Intel® Core™ Ultra 9 Processor 275HX 的 TDP（熱設計功耗）為 175W。
- **q40** `螢幕是觸控螢幕嗎？` → context ['row03', 'row00', 'row02_variants', 'row06', 'row07']
  > 螢幕不是觸控螢幕。
- **q42** `有指紋辨識嗎？` → context ['row10', 'row09', 'row00', 'row01', 'row02_variants']
  > 有指紋辨識功能。附註（補充說明，非規格值）：此功能可能因使用情境而有所差異。
