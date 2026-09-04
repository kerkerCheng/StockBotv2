"""Markdown 呈現的中立原語：外部文字轉義與百分比格式。

## 為什麼住在 shared

B6 之後每個 pane 的 markdown 由它自己的 domain 擁有（`alpha/brief.py` 的排序區、
`portfolio/brief.py` 的 NAV 區、Engine D 的 action card），而那三者分屬不同層。
**轉義規則只能有一份**——同一段外部文字在不同 pane escape 得不一樣，就是三個會
各自漂移的真相，而漂移的後果是某一個 pane 把 `|` 原樣印進表格、整張表錯位。

判準沿用 `shared/__init__.py`：多個不同層的消費端 ＋ 自己不擁有任何 authority。
"""
from __future__ import annotations

import re
from typing import Any

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()<>#+.!|-])")

__all__ = ["markdown_text", "pct"]


def markdown_text(value: Any) -> str:
    """將外部文字限制成單行並 escape Markdown／terminal control。"""

    text = _ANSI_ESCAPE.sub("", str(value)).replace("\r", " ").replace("\n", " ")
    text = "".join(character if character >= " " else " " for character in text)
    return _MARKDOWN_SPECIAL.sub(r"\\\1", text)


def pct(value: Any) -> str:
    """比例 → 帶正負號的百分比字串。

    非數值一律回「未知」，**不用 0 冒充**——一個算不出來的報酬印成 `+0.0%`
    會被讀成「持平」，那是憑空造出來的事實（L12：缺席與零不得同形）。
    """

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "未知"
    return f"{value * 100:+.1f}%"
