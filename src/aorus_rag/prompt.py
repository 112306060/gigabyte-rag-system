"""Build the chat messages sent to the generator.

Design choices (small 3B model => be explicit, keep it short):
  * Answer language is decided in code, not left to the model: a 3B model asked to
    "reply in the user's language" often drifts into Simplified Chinese or English.
  * Product background (the SKU -> GPU mapping) is generated from the parsed data,
    so the model always knows the three SKUs differ only in GPU even when retrieval
    returns just one SKU's chunk.
  * Context chunks are numbered [1]..[k] so answers can cite sources.
  * If the best dense similarity is low, we tell the model the context may not contain
    the answer; this makes "not listed" answers more reliable than rules alone.
"""

from __future__ import annotations

import json
import re

from aorus_rag.parser import OUT as RECORDS_PATH, PRODUCT

# Below this cosine similarity the top chunk is probably unrelated to the question.
# Placeholder value; calibrated on the evaluation set later.
LOW_SIM_THRESHOLD = 0.35

NOT_FOUND_ZH = "規格資料中未提及此資訊。"
NOT_FOUND_EN = "This information is not listed in the specifications."

_CJK = re.compile(r"[一-鿿]")


def answer_language(query: str) -> str:
    """Any Chinese character => answer in Traditional Chinese; otherwise English."""
    return "zh" if _CJK.search(query) else "en"


def _product_background() -> str:
    records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
    gpus = [f"{r['sku'].replace('AORUS MASTER 16 ', '')}（{r['lines'][0]}）"
            for r in records if r["key_en"] == "Video Graphics"]
    return f"本產品有 {len(gpus)} 個型號：{'、'.join(gpus)}；各型號只有顯示晶片不同，其餘規格完全相同。"


SYSTEM_PROMPT = f"""你是技嘉 GIGABYTE「{PRODUCT}」筆記型電腦的產品規格助理。
{_product_background()}

回答規則：
1. 只能根據使用者提供的 <參考資料> 回答，不可使用外部知識，不可推測或編造任何數值。
2. 若 <參考資料> 中沒有答案，中文問題請回答「{NOT_FOUND_ZH}」，英文問題請回答 "{NOT_FOUND_EN}"，不要猜測。
3. 數值、型號與單位照原文保留（例如 2560×1600、99Wh、Thunderbolt™5）。
4. 先直接給出規格值；標示為「附註」的內容只是補充說明，不是答案本身，必要時才簡短提及。
5. 若問題與顯示晶片有關但未指定型號，請分別列出各型號的規格。
6. 回答簡潔、直接切入重點，項目多時使用條列。
7. 在引用資料的句子後標註來源編號，例如 [1]。"""


def build_messages(query: str, hits: list) -> list[dict]:
    """hits: list of retriever.Hit (best first)."""
    lang = answer_language(query)
    context = "\n\n".join(f"[{i}] {h.chunk['text']}" for i, h in enumerate(hits, 1))

    parts = [f"<參考資料>\n{context}\n</參考資料>", f"問題：{query}"]
    if hits and hits[0].dense < LOW_SIM_THRESHOLD:
        parts.append("（提示：參考資料與問題的相關度偏低，可能不包含答案。）")
    parts.append("請使用繁體中文（台灣用語）回答。" if lang == "zh" else "Please answer in English.")

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(parts)},
    ]
