# Benchmark: final_defaults

- date: 2026-10-02T14:48:28
- generator: `Qwen3-4B-Instruct-2507-Q4_K_M.gguf`
- config: prompt=v2, k=5, mode=hybrid, prune=True, repeat=3, traditional=True

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
| citation compliance (has [n]) | 100.0% |
| citation correctness (cited chunk supports answer) | 100.0% (36 cited answers) |
| Simplified-Chinese leakage | 0.0% |

### Stability over 3 passes

| pass | accuracy |
|---|---|
| 1 | 100.0% |
| 2 | 100.0% |
| 3 | 100.0% |

- correct in **all** passes: **42 / 42**
- questions whose result changed between passes: none

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
| retrieval (ms) | 26.2 | 35.1 | 26.9 |
| LLM TTFT (ms) | 400.4 | 619.3 | 389.4 |
| E2E TTFT (ms) | 472.4 | 684.5 | 444.4 |

- avg prompt tokens: 1142 (of which served from prompt cache: 476 — the shared system prompt), avg completion tokens: 39

## Throughput (decode)

Fixed 256-token generation (ignore_eos) on a real RAG prompt, 5 runs:

| measured by | TPS mean | std |
|---|---|---|
| client (stream timing) | 53.4 | 0.1 |
| llama-server timings | 53.4 | 0.1 |

- peak VRAM (whole GPU): **3125 MiB** / 4096 MiB

## Failures (0)

