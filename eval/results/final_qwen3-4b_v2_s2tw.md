# Benchmark: final_qwen3-4b_v2_s2tw

- date: 2026-10-02T14:27:50
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
| retrieval (ms) | 29.6 | 43.3 | 31.0 |
| LLM TTFT (ms) | 400.2 | 624.4 | 390.5 |
| E2E TTFT (ms) | 485.6 | 696.4 | 451.7 |

- avg prompt tokens: 1142 (of which served from prompt cache: 476 — the shared system prompt), avg completion tokens: 38

## Throughput (decode)

Fixed 256-token generation (ignore_eos) on a real RAG prompt, 5 runs:

| measured by | TPS mean | std |
|---|---|---|
| client (stream timing) | 52.8 | 0.9 |
| llama-server timings | 52.8 | 0.8 |

- peak VRAM (whole GPU): **3125 MiB** / 4096 MiB

## Failures (0)

