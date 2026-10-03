# Benchmark: qwen3-4b_prompt-v1

- date: 2026-10-02T13:43:29
- generator: `Qwen3-4B-Instruct-2507-Q4_K_M.gguf`
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
| overall accuracy | 97.6% (42 q) |
| answerable accuracy | 97.2% |
| unanswerable → correct refusal | 100.0% |
| false refusal (answerable) | 2.8% |
| citation compliance (has [n]) | 97.2% |
| citation correctness (cited chunk supports answer) | 100.0% (35 cited answers) |
| Simplified-Chinese leakage | 3.3% |

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
| retrieval (ms) | 28.3 | 38.0 | 29.2 |
| LLM TTFT (ms) | 404.1 | 627.2 | 391.3 |
| E2E TTFT (ms) | 436.6 | 666.2 | 420.5 |

- avg prompt tokens: 1061 (of which served from prompt cache: 395 — the shared system prompt), avg completion tokens: 39

## Throughput (decode)

Fixed 256-token generation (ignore_eos) on a real RAG prompt, 5 runs:

| measured by | TPS mean | std |
|---|---|---|
| client (stream timing) | 51.4 | 0.1 |
| llama-server timings | 51.4 | 0.1 |

- peak VRAM (whole GPU): **3125 MiB** / 4096 MiB

## Failures (1)

- **q27** `BXH 的顯卡功耗是多少？` → context ['row02_BXH', 'overview', 'row03', 'row04', 'row01']
  > BXH 的顯卡功耗在參考資料中並未明確列出。   規格資料中未提及此資訊。
