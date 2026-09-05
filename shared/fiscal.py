"""會計年度身分的解析——把 provider 的相對標籤（`0y`／`+1y`）變成**絕對的會計期間**。

## 為什麼需要它（2026-09-05 實測）

yfinance 的 `earnings_estimate`／`revenue_estimate` 用 `0y`／`+1y` 標期間，而那是**相對於
抓取當天**的標籤：COHR 的會計年度 6 月底結束，8 月財報後 `0y` 是 FY2027（至 2027-06-30）、
`+1y` 是 FY2028。既有的 `revenue_estimate_next_fy` 欄位存的正是 `+1y`——它的名字叫
「下一會計年度」，但對 COHR 而言那是**下下個**已結束年度之後的第二年。一個標籤兩種語意（L12）。

內部估計與共識做數值比較的前提是**同一個會計期間**；相對標籤答不了這個問題，
所以每一筆共識在**抓取當下**就必須解析成 `fiscal_period_end`（絕對日期）存起來——
今天解析得出來的身分，明天用同一個相對標籤就解不出來了。

## 解析規則（機械，不猜）

- `0y` ＝ 以 `nextFiscalYearEnd` 結束的那個會計年度（進行中的年度）。
- `+1y` ＝ `nextFiscalYearEnd` 再加一年。
- `lastFiscalYearEnd`／`nextFiscalYearEnd` 缺任一個、或兩者相距不像一年（52／53 週制
  允許 350–380 天）→ **回 `None`**，由呼叫端當缺料處理，不用今天的日期硬推。

⚠ **身分是 `end` 日期，`FY2027` 這種標籤只是呈現慣例。** 美股多以結束年命名
（COHR FY2026 至 2026-06-30），日股常以起始年命名（3 月結束的年度叫前一年）。
跨公司比對一律比日期，不比標籤。
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from typing import Any

__all__ = [
    "FISCAL_YEAR_LABELS", "add_years", "epoch_to_date", "fiscal_label",
    "resolve_fiscal_year_end",
]

#: provider 的年度相對標籤 → 相對於 `nextFiscalYearEnd` 的年數。只做年度（v1 不做季度）。
FISCAL_YEAR_LABELS: dict[str, int] = {"0y": 0, "+1y": 1}

_MIN_YEAR_DAYS = 350
_MAX_YEAR_DAYS = 380


def add_years(value: date, years: int) -> date:
    """同月同日加 N 年；2 月 29 日落到平年時取 2 月 28 日（不往後跨月）。"""
    year = value.year + years
    day = min(value.day, calendar.monthrange(year, value.month)[1])
    return date(year, value.month, day)


def epoch_to_date(value: Any) -> date | None:
    """yfinance 的 epoch 秒 → UTC 日期。非數值／bool 一律 `None`。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).date()
    except (OverflowError, OSError, ValueError):
        return None


def fiscal_label(period_end: date) -> str:
    """呈現用標籤（結束年命名）。**不是身分**——身分是 `period_end`。"""
    return f"FY{period_end.year}"


def resolve_fiscal_year_end(
    relative_label: str,
    *,
    last_fiscal_year_end: date | None,
    next_fiscal_year_end: date | None,
) -> date | None:
    """把 `0y`／`+1y` 解析成會計年度結束日；解不出來回 `None`（缺料，不是 0）。"""
    offset = FISCAL_YEAR_LABELS.get(str(relative_label))
    if offset is None:
        return None
    if last_fiscal_year_end is None or next_fiscal_year_end is None:
        return None
    span = (next_fiscal_year_end - last_fiscal_year_end).days
    if not _MIN_YEAR_DAYS <= span <= _MAX_YEAR_DAYS:
        return None
    return add_years(next_fiscal_year_end, offset)
