"""Build the chat messages sent to the generator.

Design choices (small 3B model => be explicit, keep it short):
  * Answer language is decided in code, not left to the model: a 3B model asked to
    "reply in the user's language" often drifts into Simplified Chinese or English.
  * Product background (the SKU -> GPU mapping) is generated from the parsed data,
    so the model always knows the three SKUs differ only in GPU even when retrieval
    returns just one SKU's chunk.
  * Context chunks are numbered [1]..[k] so answers can cite sources.
  * No similarity-threshold "low relevance" hint: on the eval set the top-1 cosine of
    answerable (min 0.44) and unanswerable (max 0.53) questions overlap, so any threshold
    would mislabel one side. Refusal is left to the model reading the context (100% on eval).
"""

from __future__ import annotations

import json
import re

from aorus_rag.parser import OUT as RECORDS_PATH, PRODUCT

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


# Prompt versions are kept side by side so every model can be benchmarked on each one
# (see docs/EXPERIMENTS.md). v3 is the default.
_R_GROUND = "只能根據使用者提供的 <參考資料> 回答，不可使用外部知識，不可推測或編造任何數值。"
_R_NOT_FOUND = f"若 <參考資料> 中沒有答案，中文問題請回答「{NOT_FOUND_ZH}」，英文問題請回答 \"{NOT_FOUND_EN}\"，不要猜測。"
_R_GPU = "若問題與顯示晶片有關但未指定型號，請分別列出各型號的規格。"
_R_CONCISE = "回答簡潔、直接切入重點，項目多時使用條列。"
_R_CITE = "在引用資料的句子後標註來源編號，例如 [1]。"
_R_PROPER = "數值、型號、單位與專有名稱（如顏色名稱、技術名稱）一律保留英文原文，不要翻譯（例如 2560×1600、99Wh、Thunderbolt™5）。"
_R_FIRST = "第一句話直接回答問題，不要加「規格值：」之類的標籤；標示為「附註」的內容只是補充說明，必要時才用一句話簡短提及。"

PROMPT_RULES: dict[str, list[str]] = {
    # v1: baseline rules
    "v1": [
        _R_GROUND,
        _R_NOT_FOUND,
        "數值、型號與單位照原文保留（例如 2560×1600、99Wh、Thunderbolt™5）。",
        "先直接給出規格值；標示為「附註」的內容只是補充說明，不是答案本身，必要時才簡短提及。",
        _R_GPU, _R_CONCISE, _R_CITE,
    ],
    # v2: understand English context, keep proper nouns, no label echo
    "v2": [
        _R_GROUND,
        _R_NOT_FOUND,
        "<參考資料> 多為英文：請先理解英文的意思再用問題的語言回答；英文寫法與中文說法意思相同時視為同一件事（例如 Dual-band 就是雙頻）。",
        _R_PROPER, _R_FIRST, _R_GPU, _R_CONCISE, _R_CITE,
    ],
    # v3: v2 + forbid substituting another spec item's value (v2 hallucinated on Qwen2.5-3B)
    "v3": [
        _R_GROUND,
        "回答的數值必須是問題所問規格項目本身的數值；資料沒有直接寫出時，就視為沒有答案，不可以用其他項目的數值代替或推算。",
        _R_NOT_FOUND,
        "<參考資料> 多為英文：請理解英文名詞的意思再用問題的語言回答（例如 Dual-band 就是雙頻）；這只用於翻譯理解，不可據此推論資料沒寫的內容。",
        _R_PROPER, _R_FIRST, _R_GPU, _R_CONCISE, _R_CITE,
    ],
}
DEFAULT_PROMPT = "v3"

# v1 also appended a hint when the top chunk's cosine was below this value. Dropped from v2:
# answerable/unanswerable top-1 cosine overlap on the eval set, so no threshold separates them.
_V1_LOW_SIM_THRESHOLD = 0.35


def system_prompt(version: str = DEFAULT_PROMPT) -> str:
    rules = "\n".join(f"{i}. {r}" for i, r in enumerate(PROMPT_RULES[version], 1))
    return f"你是技嘉 GIGABYTE「{PRODUCT}」筆記型電腦的產品規格助理。\n{_product_background()}\n\n回答規則：\n{rules}"


SYSTEM_PROMPT = system_prompt()


def build_messages(query: str, hits: list, version: str = DEFAULT_PROMPT) -> list[dict]:
    """hits: list of retriever.Hit (best first)."""
    lang = answer_language(query)
    context = "\n\n".join(f"[{i}] {h.chunk['text']}" for i, h in enumerate(hits, 1))

    parts = [f"<參考資料>\n{context}\n</參考資料>", f"問題：{query}"]
    if version == "v1" and hits and hits[0].dense < _V1_LOW_SIM_THRESHOLD:
        parts.append("（提示：參考資料與問題的相關度偏低，可能不包含答案。）")
    parts.append("請使用繁體中文（台灣用語）回答。" if lang == "zh" else "Please answer in English.")

    return [
        {"role": "system", "content": system_prompt(version)},
        {"role": "user", "content": "\n\n".join(parts)},
    ]
