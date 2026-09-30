"""Turn parsed spec records into retrieval chunks.

Strategy (structure-aware, not fixed-size):
  * One spec row = one chunk. A row is the natural semantic unit of a spec table.
  * Rows whose value is identical across all SKUs are merged into ONE shared chunk
    (16 of 17 rows), so duplicates don't crowd out top-k.
  * Rows that differ between SKUs (the GPU row) get one chunk per SKU, plus a
    comparison chunk listing all variants side by side.
  * One overview chunk summarises the headline specs for "introduce this laptop" questions.

Each chunk has two texts:
  * text       -> shown to the LLM (includes footnotes, so answers can carry caveats)
  * embed_text -> used for indexing (no footnotes, plus bilingual aliases). Footnotes are
                  long boilerplate that would dilute the embedding; aliases bridge the gap
                  between how users ask ("幾公斤") and how the page is written ("Weight").
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from itertools import groupby
from pathlib import Path

from aorus_rag.parser import OUT as RECORDS_PATH, PRODUCT, ROOT, SKUS

OUT = ROOT / "data" / "processed" / "chunks.jsonl"

# Document-side expansion: words users actually say, in both languages.
KEY_ALIASES: dict[str, list[str]] = {
    "OS": ["作業系統", "系統", "Windows", "operating system"],
    "CPU": ["處理器", "中央處理器", "核心", "執行緒", "時脈", "processor", "cores", "clock"],
    "Video Graphics": ["顯卡", "顯示卡", "獨顯", "GPU", "VRAM", "顯存", "graphics card", "TGP"],
    "Display": ["螢幕", "面板", "解析度", "更新率", "刷新率", "亮度", "screen", "resolution", "refresh rate"],
    "System Memory": ["記憶體", "RAM", "內存", "擴充", "插槽", "memory"],
    "Storage": ["硬碟", "儲存空間", "SSD", "容量", "M.2", "storage", "disk"],
    "Keyboard Type": ["鍵盤", "背光", "鍵程", "RGB", "keyboard", "backlight"],
    "I/O Port": ["連接埠", "接口", "插孔", "USB", "Type-C", "Thunderbolt", "雷電", "HDMI", "網路孔", "讀卡機", "ports"],
    "Audio": ["音效", "喇叭", "揚聲器", "麥克風", "speakers", "sound"],
    "Communications": ["網路", "無線網路", "WiFi", "Wi-Fi", "藍牙", "有線網路", "wireless", "bluetooth"],
    "Webcam": ["鏡頭", "攝影機", "視訊", "人臉辨識", "camera"],
    "Security": ["安全", "TPM", "加密", "security chip"],
    "Battery": ["電池", "續航", "電量", "電池容量", "Wh", "battery"],
    "Adapter": ["變壓器", "充電器", "電源", "供電", "瓦數", "charger", "power supply"],
    "Dimensions": ["尺寸", "大小", "厚度", "長寬高", "size", "thickness"],
    "Weight": ["重量", "多重", "幾公斤", "輕", "weight", "heavy"],
    "Color": ["顏色", "配色", "外觀", "colour"],
}

ALL_SKUS_LABEL = " / ".join(s.replace("AORUS MASTER 16 ", "") for s in SKUS)


@dataclass
class Chunk:
    id: str
    type: str            # "spec" | "spec_sku" | "variants" | "overview"
    key_en: str
    key_zh: str
    skus: list[str]
    text: str
    embed_text: str


def _body(lines: list[str]) -> str:
    return "\n".join(f"- {l}" if not l.endswith(":") else l for l in lines)


def _make(cid, ctype, key_en, key_zh, skus, lines, notes, scope) -> Chunk:
    header = f"產品 Product: {PRODUCT}（{scope}）\n規格項目 Spec: {key_zh} / {key_en}"
    body = _body(lines)
    text = f"{header}\n{body}"
    if notes:
        text += "\n附註 Notes: " + " ".join(n.lstrip("*") for n in notes)
    aliases = " ".join(KEY_ALIASES.get(key_en, []))
    embed_text = f"{header}\n{body}\n關鍵字 Keywords: {aliases}"
    return Chunk(cid, ctype, key_en, key_zh, skus, text, embed_text)


def build_chunks(records: list[dict]) -> list[Chunk]:
    chunks: list[Chunk] = []
    by_row = sorted(records, key=lambda r: r["row"])
    for row, group in groupby(by_row, key=lambda r: r["row"]):
        group = list(group)
        first = group[0]
        key_en, key_zh = first["key_en"], first["key_zh"]
        identical = all(g["lines"] == first["lines"] for g in group)

        if identical:
            chunks.append(_make(
                f"row{row:02d}", "spec", key_en, key_zh, SKUS,
                first["lines"], first["notes"], f"全型號共用 all models: {ALL_SKUS_LABEL}",
            ))
            continue

        for g in group:
            short = g["sku"].replace("AORUS MASTER 16 ", "")
            chunks.append(_make(
                f"row{row:02d}_{short}", "spec_sku", key_en, key_zh, [g["sku"]],
                g["lines"], g["notes"], f"型號 model: {g['sku']}",
            ))
        # Side-by-side comparison, for "which GPUs are available / 差在哪" questions.
        variant_lines = [f"{g['sku']}: {', '.join(g['lines'])}" for g in group]
        chunks.append(_make(
            f"row{row:02d}_variants", "variants", key_en, key_zh, SKUS,
            variant_lines, first["notes"],
            f"各型號比較 model comparison: {ALL_SKUS_LABEL}，其餘規格皆相同 other specs identical",
        ))

    chunks.append(_overview(records))
    return chunks


def _overview(records: list[dict]) -> Chunk:
    first_sku = [r for r in records if r["sku"] == SKUS[0]]
    # How many leading lines of each row are "headline" facts.
    pick = {"CPU": 1, "Display": 2, "System Memory": 2, "Storage": 3, "Battery": 1, "Weight": 1}
    lines = [
        f"{r['key_zh']} {r['key_en']}: {'; '.join(r['lines'][:pick[r['key_en']]])}"
        for r in first_sku if r["key_en"] in pick
    ]
    gpus = [r["lines"][0] for r in records if r["key_en"] == "Video Graphics"]
    lines.insert(1, "顯示晶片 Video Graphics: " + " / ".join(gpus))
    header = f"產品 Product: {PRODUCT}（型號 models: {ALL_SKUS_LABEL}）\n規格總覽 Overview"
    body = _body(lines)
    return Chunk(
        "overview", "overview", "Overview", "規格總覽", SKUS,
        f"{header}\n{body}",
        f"{header}\n{body}\n關鍵字 Keywords: 介紹 簡介 總覽 主要規格 規格表 overview summary introduce",
    )


def main() -> None:
    records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
    chunks = build_chunks(records)
    with OUT.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
    print(f"{len(records)} records -> {len(chunks)} chunks -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
