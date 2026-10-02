# Benchmark: qwen2.5-1.5b_prompt-v3

- date: 2026-10-02T13:59:25
- generator: `C:\Users\user\Desktop\技嘉面試實作\models\qwen2.5-1.5b-instruct-q4_k_m.gguf`
- config: prompt=v3, k=5, mode=hybrid, prune=True, repeat=3, traditional=False

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
| Simplified-Chinese leakage | 0.0% |

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
| retrieval (ms) | 32.7 | 55.0 | 35.0 |
| LLM TTFT (ms) | 190.7 | 285.6 | 180.8 |
| E2E TTFT (ms) | 225.5 | 315.8 | 215.8 |

- avg prompt tokens: 1193 (of which served from prompt cache: 527 — the shared system prompt), avg completion tokens: 43

## Throughput (decode)

Fixed 256-token generation (ignore_eos) on a real RAG prompt, 5 runs:

| measured by | TPS mean | std |
|---|---|---|
| client (stream timing) | 106.6 | 1.4 |
| llama-server timings | 106.6 | 1.4 |

- peak VRAM (whole GPU): **1205 MiB** / 4096 MiB

## Failures (5)

- **q35** `可以插記憶卡嗎？` → context ['row04', 'overview', 'row07', 'row02_variants', 'row05']
  > 可以插記憶卡。該筆記型電腦提供2x SO-DIMM sockets，可以插入記憶體模組以擴充記憶體容量。
- **q38** `電池續航力可以撐幾小時？` → context ['row12', 'overview', 'row02_variants']
  > 電池續航力為99Wh，可以撐約4.5小時。
- **q39** `CPU 的 TDP 是多少瓦？` → context ['row02_variants', 'row01', 'overview', 'row03', 'row11']
  > CPU 的 TDP（Thermal Design Power）是 275W。
- **q40** `螢幕是觸控螢幕嗎？` → context ['row03', 'row00', 'row02_variants', 'row10', 'row06']
  > 螢幕不是觸控螢幕。
- **q42** `有指紋辨識嗎？` → context ['row10', 'row00', 'row09', 'row02_variants', 'row01']
  > 有指紋辨識功能。該筆記型電腦支持Windows Hello Face Authentication，這是一種面部識別技術，可以通過面部特征來識別用戶身份。
