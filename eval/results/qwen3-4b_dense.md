# Benchmark: qwen3-4b_dense

- date: 2026-10-02T13:52:18
- generator: `Qwen3-4B-Instruct-2507-Q4_K_M.gguf`
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
| overall accuracy | 97.6% (42 q) |
| answerable accuracy | 97.2% |
| unanswerable → correct refusal | 100.0% |
| false refusal (answerable) | 2.8% |
| citation compliance (has [n]) | 97.2% |
| citation correctness (cited chunk supports answer) | 97.1% (35 cited answers) |
| Simplified-Chinese leakage | 3.3% |

### Incorrect citations

- **q36** cited [[3, 'row06']] → `技嘉 AORUS MASTER 16 AM6H 是一款高性能筆電，提供三種顯示晶片型號：BZH（RTX 5090）、BYH（RTX 5080）與 BXH（RTX 5070 Ti），其餘規格完全相同。  

- 中央處理器：Intel® Co`

| category | n | accuracy |
|---|---|---|
| aggregate | 3 | 100.0% |
| basic | 18 | 100.0% |
| colloquial | 3 | 100.0% |
| mixed | 6 | 100.0% |
| sku | 6 | 83.3% |
| unanswerable | 6 | 100.0% |

| language | n | accuracy |
|---|---|---|
| en | 12 | 100.0% |
| mix | 8 | 100.0% |
| zh | 22 | 95.5% |

## Latency

| metric | p50 | p95 | mean |
|---|---|---|---|
| retrieval (ms) | 29.5 | 37.7 | 30.5 |
| LLM TTFT (ms) | 413.3 | 708.8 | 415.4 |
| E2E TTFT (ms) | 445.5 | 744.5 | 446.0 |

- avg prompt tokens: 1215 (of which served from prompt cache: 533 — the shared system prompt), avg completion tokens: 36

## Throughput (decode)

Fixed 256-token generation (ignore_eos) on a real RAG prompt, 5 runs:

| measured by | TPS mean | std |
|---|---|---|
| client (stream timing) | 52.6 | 0.1 |
| llama-server timings | 52.6 | 0.1 |

- peak VRAM (whole GPU): **3125 MiB** / 4096 MiB

## Failures (1)

- **q27** `BXH 的顯卡功耗是多少？` → context ['row02_BXH', 'overview', 'row01', 'row04', 'row03']
  > BXH 的顯卡功耗在參考資料中未提及此資訊。[1]
