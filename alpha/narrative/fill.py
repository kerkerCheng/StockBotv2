"""把 authority 的數字填進短評的 placeholder。**格式化不是算術**：這裡沒有加減乘除。

輸入是一張 `values` 表（placeholder → 已格式化字串或 None），由 read model 端**選取**既有 Datum 的值
後經 `format_value` 產生；本檔不知道數字從哪來，也不重算任何東西。缺值的 placeholder 印「（尚無）」
並回報，讓那一格能標成 missing——**不留白、不補 0**。
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from .contracts import PARAM_PLACEHOLDER, SIMPLE_PLACEHOLDER, InvestorBrief

ABSENT = "（尚無）"


def format_value(kind: str, value: Any, *, unit: str | None = None) -> str | None:
    """authority 值 → 人讀的字串。`kind`：price／currency／ratio／multiple／count／date／raw。"""
    if value is None:
        return None
    if kind == "ratio":
        return f"{float(value) * 100:+.1f}%".replace("-", "−")
    if kind == "multiple":
        return f"{float(value):.1f} 倍"
    if kind == "count":
        return f"{int(value)}"
    if kind == "date":
        return value.isoformat() if isinstance(value, date) else str(value)[:10]
    if kind == "money":
        # 財報等級的金額：億／百萬，讀者要的是量級不是每一位數。
        number = float(value)
        if abs(number) >= 1e8:
            text = f"{number / 1e8:,.1f} 億"
        elif abs(number) >= 1e6:
            text = f"{number / 1e6:,.0f} 百萬"
        else:
            text = f"{number:,.0f}"
        return f"{text} {unit}" if unit else text
    if kind in ("price", "currency"):
        number = float(value)
        text = f"{number:,.0f}" if abs(number) >= 1000 else f"{number:,.2f}".rstrip("0").rstrip(".")
        return f"{text} {unit}" if unit else text
    return str(value)


def fill_brief(brief: InvestorBrief, values: Mapping[str, str | None]) -> tuple[dict[str, str], dict[str, list[str]]]:
    """回傳 `(每格填好的文字, 每格缺值的 placeholder)`。`values` 的 key 是不含大括號的 placeholder
    名（`price`）或帶參數的全文（`{bet_assumption:operating_margin_delta[mix_and_utilization]}`）。"""
    filled: dict[str, str] = {}
    missing: dict[str, list[str]] = {}

    def _lookup(token: str) -> str | None:
        if PARAM_PLACEHOLDER.fullmatch(token):
            return values.get(token)
        return values.get(token[1:-1])

    for slot in brief.slots:
        text = slot.text
        absent: list[str] = []
        for token in slot.placeholders:
            replacement = _lookup(token)
            if replacement is None:
                absent.append(token)
                replacement = ABSENT
            text = text.replace(token, replacement)
        filled[slot.key] = text
        if absent:
            missing[slot.key] = absent
    return filled, missing


__all__ = ["ABSENT", "fill_brief", "format_value"]
