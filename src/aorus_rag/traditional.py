"""Deterministic Simplified -> Traditional (Taiwan) conversion for streamed output.

The prompt asks for Traditional Chinese, but the model still occasionally emits a
Simplified character (3.3% of Chinese answers on the eval set), so the output is
converted with OpenCC as a final safety net.

Config choice, checked against all 1,176 saved answers:
  * s2twp also rewrites vocabulary and broke correct text: 連接埠 -> 連線埠,
    刷新率 -> 重新整理率, 擴展 -> 擴充套件 (wrong meaning).
  * s2t uses OpenCC's own standard: 峰 -> 峯, 为 -> 爲 (not Taiwan usage).
  * s2tw converts glyphs only, to Taiwan standard. Its one unwanted change is 台 -> 臺
    (台 is also the Simplified form of 臺), which we map back since 台 is everyday usage.

Streaming: some conversions depend on the next character (头发 -> 頭髮), so text is
buffered and converted at boundaries (punctuation, spaces, ASCII), which never split a
word. A long run of Chinese is flushed early, holding back the last character.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

import opencc

_cc = opencc.OpenCC("s2tw")
MAX_CJK_RUN = 4  # flush a long run of Chinese early to keep time-to-first-text low


def to_traditional(text: str) -> str:
    return _cc.convert(text).replace("臺", "台")


def _is_cjk(ch: str) -> bool:
    return "一" <= ch <= "鿿"


def stream_traditional(tokens: Iterable[str]) -> Iterator[str]:
    buf = ""
    for token in tokens:
        buf += token
        # last position that is not a Chinese character = a safe place to cut
        cut = max((i for i, ch in enumerate(buf) if not _is_cjk(ch)), default=-1)
        if cut >= 0:
            out, buf = buf[: cut + 1], buf[cut + 1 :]
        elif len(buf) > MAX_CJK_RUN:
            out, buf = buf[:-1], buf[-1:]
        else:
            continue
        yield to_traditional(out)
    if buf:
        yield to_traditional(buf)
