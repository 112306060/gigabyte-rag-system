# Benchmark: qwen3-4b_no-prune

- date: 2026-10-02T13:54:57
- generator: `C:\Users\user\Desktop\技嘉面試實作\models\Qwen3-4B-Instruct-2507-Q4_K_M.gguf`
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
| overall accuracy | 100.0% (42 q) |
| answerable accuracy | 100.0% |
| unanswerable → correct refusal | 100.0% |
| false refusal (answerable) | 0.0% |
| citation compliance (has [n]) | 91.7% |
| citation correctness (cited chunk supports answer) | 97.0% (33 cited answers) |
| Simplified-Chinese leakage | 3.3% |

### Incorrect citations

- **q30** cited [[2, 'row07'], [3, 'row16'], [4, 'row06'], [5, 'row14']] → `三個型號的主要差異在於顯示晶片（Video Graphics）的型號與相關規格，具體如下：

- AORUS MASTER 16 BZH：NVIDIA® GeForce RTX™ 5090 Laptop GPU，配備 24GB GDDR7，`

| category | n | accuracy |
|---|---|---|
| aggregate | 3 | 100.0% |
| basic | 18 | 100.0% |
| colloquial | 3 | 100.0% |
| mixed | 6 | 100.0% |
| sku | 6 | 100.0% |
| unanswerable | 6 | 100.0% |

| language | n | accuracy |
|---|---|---|
| en | 12 | 100.0% |
| mix | 8 | 100.0% |
| zh | 22 | 100.0% |

## Latency

| metric | p50 | p95 | mean |
|---|---|---|---|
| retrieval (ms) | 31.9 | 39.6 | 31.8 |
| LLM TTFT (ms) | 508.9 | 595.9 | 475.9 |
| E2E TTFT (ms) | 537.9 | 634.5 | 507.7 |

- avg prompt tokens: 1320 (of which served from prompt cache: 528 — the shared system prompt), avg completion tokens: 36

## Throughput (decode)

Fixed 256-token generation (ignore_eos) on a real RAG prompt, 5 runs:

| measured by | TPS mean | std |
|---|---|---|
| client (stream timing) | 52.3 | 0.0 |
| llama-server timings | 52.3 | 0.0 |

- peak VRAM (whole GPU): **3125 MiB** / 4096 MiB

## Failures (0)

