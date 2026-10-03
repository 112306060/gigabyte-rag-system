# Benchmark: heldout_final

- date: 2026-10-03T12:49:09
- generator: `C:\Users\user\Desktop\技嘉面試實作\models\Qwen3-4B-Instruct-2507-Q4_K_M.gguf`
- config: prompt=v2, k=5, mode=hybrid, prune=True, repeat=3, traditional=True

## Retrieval (raw ranking, answerable questions)

| mode | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|
| dense | 0.833 | 1.000 | 1.000 | 0.889 |
| bm25 | 0.583 | 0.917 | 1.000 | 0.757 |
| hybrid | 0.750 | 1.000 | 1.000 | 0.875 |

Final context (hybrid + prune): gold chunk present **100.0%**, avg 3.17 chunks

## Answer quality

| metric | value |
|---|---|
| overall accuracy | 83.3% (12 q) |
| answerable accuracy | 83.3% |
| unanswerable → correct refusal | — |
| false refusal (answerable) | 0.0% |
| citation compliance (has [n]) | 91.7% |
| citation correctness (cited chunk supports answer) | 90.9% (11 cited answers) |
| Simplified-Chinese leakage | 0.0% |

### Stability over 3 passes

| pass | accuracy |
|---|---|
| 1 | 83.3% |
| 2 | 91.7% |
| 3 | 83.3% |

- correct in **all** passes: **10 / 12**
- questions whose result changed between passes: ['h10']

### Incorrect citations

- **h02** cited [[5, 'row14']] → `這台與行動辦公比較有關的規格包括：  
- 記憶體：支援最高 64GB DDR5 5600MHz，可透過 2x SO-DIMM 插槽擴充，提供充足的多任務處理與資料處理能力 [2]。  
- 儲存裝置：提供 1x PCIe Gen5 M.2`

| category | n | accuracy |
|---|---|---|
| colloquial | 1 | 100.0% |
| cross_field | 2 | 100.0% |
| hallucination_trap | 3 | 33.3% |
| io | 2 | 100.0% |
| mixed | 1 | 100.0% |
| sku | 3 | 100.0% |

| language | n | accuracy |
|---|---|---|
| en | 1 | 100.0% |
| mix | 5 | 80.0% |
| zh | 6 | 83.3% |

## Latency

| metric | p50 | p95 | mean |
|---|---|---|---|
| retrieval (ms) | 28.5 | 41.3 | 30.6 |
| LLM TTFT (ms) | 323.1 | 656.2 | 338.2 |
| E2E TTFT (ms) | 382.1 | 700.7 | 400.4 |

- avg prompt tokens: 1037 (of which served from prompt cache: 474 — the shared system prompt), avg completion tokens: 75

## Throughput (decode)

Fixed 256-token generation (ignore_eos) on a real RAG prompt, 5 runs:

| measured by | TPS mean | std |
|---|---|---|
| client (stream timing) | 52.6 | 0.9 |
| llama-server timings | 52.6 | 0.9 |

- peak VRAM (whole GPU): **3125 MiB** / 4096 MiB

## Failures (2)

- **h10** `這台跑得動《黑神話：悟空》嗎？` → context ['row02_variants', 'row00', 'row01', 'row06', 'row05']
  > 這台筆電的顯示晶片規格從 RTX 5070 Ti 到 RTX 5090，皆為最新世代的 NVIDIA GeForce RTX 系列，支援 AI 加速與高階遊戲效能，且所有型號皆具備 175W 最大顯示核心功率（BZH、BYH）或 140W（BXH），搭配 GDDR7 記憶體與高頻運作，足以輕鬆運行《黑神話：悟空》這類高畫質、高設定的遊戲。[1]
- **h11** `CPU TDP 沒寫的話，可以從時脈推算嗎？` → context ['row01', 'row02_variants', 'overview', 'row11']
  > 規格資料中未提及此資訊。
