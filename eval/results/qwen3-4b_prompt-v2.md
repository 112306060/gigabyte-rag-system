# Benchmark: qwen3-4b_prompt-v2

- date: 2026-10-02T13:46:28
- generator: `C:\Users\user\Desktop\技嘉面試實作\models\Qwen3-4B-Instruct-2507-Q4_K_M.gguf`
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
| overall accuracy | 100.0% (42 q) |
| answerable accuracy | 100.0% |
| unanswerable → correct refusal | 100.0% |
| false refusal (answerable) | 0.0% |
| citation compliance (has [n]) | 100.0% |
| citation correctness (cited chunk supports answer) | 100.0% (36 cited answers) |
| Simplified-Chinese leakage | 3.3% |

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
| retrieval (ms) | 29.4 | 37.3 | 29.8 |
| LLM TTFT (ms) | 414.3 | 650.4 | 400.1 |
| E2E TTFT (ms) | 447.4 | 676.5 | 429.9 |

- avg prompt tokens: 1142 (of which served from prompt cache: 476 — the shared system prompt), avg completion tokens: 40

## Throughput (decode)

Fixed 256-token generation (ignore_eos) on a real RAG prompt, 5 runs:

| measured by | TPS mean | std |
|---|---|---|
| client (stream timing) | 53.0 | 0.1 |
| llama-server timings | 53.0 | 0.1 |

- peak VRAM (whole GPU): **3125 MiB** / 4096 MiB

## Failures (0)

