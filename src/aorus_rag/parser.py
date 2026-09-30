"""Parse GIGABYTE spec pages (saved HTML) into structured key-value records.

The spec table on the page is laid out as:
  .multiple-spec-content-wrapper
    .spec-column    -> 17 row titles (OS, CPU, Video Graphics, ...)
    .content-column -> one .swiper-slide per SKU, each with 17 .spec-item-list cells
The page also contains a mobile copy of the table (.mobile-spec-content); we skip it
to avoid duplicated records.

The zh-TW page and the en-US page share identical values (all English); only the
row titles differ. We read titles from both pages and align them by row index.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup, Tag

PRODUCT = "AORUS MASTER 16 AM6H"
# Column order of the spec table, confirmed against the page's compare view.
SKUS = ["AORUS MASTER 16 BZH", "AORUS MASTER 16 BYH", "AORUS MASTER 16 BXH"]

ROOT = Path(__file__).resolve().parents[2]
RAW_EN = ROOT / "data" / "raw" / "spec_en-us.html"
RAW_ZH = ROOT / "data" / "raw" / "spec_zh-tw.html"
OUT = ROOT / "data" / "processed" / "spec_records.json"


@dataclass
class SpecRecord:
    row: int              # row index in the table (stable id)
    key_en: str           # e.g. "Video Graphics"
    key_zh: str           # e.g. "顯示晶片"
    sku: str              # SKU this value belongs to
    lines: list[str]      # value, one item per line (footnotes removed)
    notes: list[str] = field(default_factory=list)  # footnotes / disclaimers


def _clean(text: str) -> str:
    # Collapse whitespace; keep ®/™ since they are part of official names.
    return re.sub(r"\s+", " ", text).strip()


def _is_note(line: str) -> bool:
    # Footnotes start with "*" (e.g. "*May vary by scenario", "**If there is ...").
    # "* 2x SO-DIMM sockets for expansion" is also written like a note on the page,
    # but it is real spec content, so keep lines that contain digits right after "*".
    if not line.startswith("*"):
        return False
    return not re.match(r"^\*\s*\d", line)


def _cell_lines(cell: Tag) -> tuple[list[str], list[str]]:
    lines, notes = [], []
    for raw in cell.get_text("\n").split("\n"):
        line = _clean(raw)
        if not line:
            continue
        if _is_note(line):
            notes.append(line)
        elif line.startswith("http") and notes:
            notes[-1] += line  # link inside a footnote is a separate <a> text node
        else:
            lines.append(line.lstrip("* "))  # "* 2x SO-DIMM ..." -> "2x SO-DIMM ..."
    return lines, notes


def _load_table(path: Path) -> tuple[list[str], list[list[Tag]]]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    wrap = soup.select_one(".multiple-spec-content-wrapper")
    if wrap is None:
        raise ValueError(f"spec table not found in {path.name}")
    titles = [_clean(t.get_text()) for t in wrap.select(".spec-column .multiple-title")]
    slides = wrap.select(".content-column .swiper-slide")
    columns = [s.select(".spec-item-list") for s in slides]
    for col in columns:
        if len(col) != len(titles):
            raise ValueError(f"{path.name}: {len(col)} cells but {len(titles)} titles")
    return titles, columns


def parse() -> list[SpecRecord]:
    titles_en, columns = _load_table(RAW_EN)
    titles_zh, _ = _load_table(RAW_ZH)
    if len(titles_en) != len(titles_zh):
        raise ValueError("en/zh tables have different row counts")
    if len(columns) != len(SKUS):
        raise ValueError(f"expected {len(SKUS)} SKU columns, got {len(columns)}")

    records = []
    for sku, col in zip(SKUS, columns):
        for i, cell in enumerate(col):
            lines, notes = _cell_lines(cell)
            records.append(SpecRecord(i, titles_en[i], titles_zh[i], sku, lines, notes))
    return records


def main() -> None:
    records = parse()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps([asdict(r) for r in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(records)} records -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
