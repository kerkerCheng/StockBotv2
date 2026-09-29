"""Engine C 機械歷史表的 **as-of 讀取**（Phase 3 Step 3.2）。寫入端是 `engine_c/history_backfill.py`。

唯一的規則：**T 時刻知道什麼**（INV-6）。

- `fundamental_history`：每個 `period_end` 取 **`filed ≤ T`** 的最新一列（同一期被後來的申報重編時，T 落在兩次
  申報之間拿到的是舊值）。`fetched_at` 不參與任何判斷——那是我們哪天抓的，不是市場哪天知道的。
- `monthly_revenue_observations`：只收 **`disclosure_deadline ≤ T`**（法定公告期限，次月 10 日）。它是可機械推導的
  **上界**，不是實際公告日（`published_at` 恆 NULL，`published_at_basis=statutory_deadline_only`）；
  用上界表示「最晚這天全市場都知道了」，寧可晚幾天也不提早看到。
- `price_history`：`bar_date ≤ T`。

本檔只取數、不判讀：百分位、TTM、口徑選擇在三題那一層（`alpha/three_questions.py`，Step 3.3）。
"""
from __future__ import annotations

from datetime import date
from typing import Any


def _iso(value: date | str) -> str:
    return value.isoformat() if isinstance(value, date) else str(value)[:10]


def fundamental_series(conn: Any, ticker: str, metric: str, *, as_of: date | str) -> list[dict[str, Any]]:
    """as-of T 的某一指標序列（`period_end` 升序）；每個期間只留 `filed ≤ T` 的最新那一列。"""
    rows = conn.execute(
        """SELECT period_start, period_end, filed, accession, form, value, currency, unit_scale, derived, tag
           FROM fundamental_history
           WHERE ticker = ? AND metric = ? AND filed <= ?
           ORDER BY period_end, filed, accession""",
        (ticker, metric, _iso(as_of))).fetchall()
    latest: dict[str, dict[str, Any]] = {}
    for r in rows:
        latest[str(r[1])] = {"period_start": r[0], "period_end": r[1], "filed": r[2], "accession": r[3],
                             "form": r[4], "value": r[5], "currency": r[6], "unit_scale": r[7],
                             "derived": r[8], "tag": r[9]}
    return [latest[k] for k in sorted(latest)]


def monthly_revenue_as_of(conn: Any, ticker: str, *, as_of: date | str) -> dict[str, Any]:
    """as-of T 的台股月營收：`{"months": [...], "conflicts": [...]}`（`data_month` 升序）。

    同一個月有多列（例：openapi 當期檔與歷史頁各抓一次）時：`revenue_current` 相同就視為同一筆；
    **不同就兩列都不用、列進 `conflicts`**——不挑一個（與 EDGAR 白名單歧異同一條守則）。
    """
    rows = conn.execute(
        """SELECT data_month, revenue_current, revenue_year_ago, unit_scale, currency, disclosure_deadline, source
           FROM monthly_revenue_observations
           WHERE ticker = ? AND disclosure_deadline <= ?
           ORDER BY data_month""",
        (ticker, _iso(as_of))).fetchall()
    by_month: dict[str, list[tuple]] = {}
    for r in rows:
        by_month.setdefault(str(r[0]), []).append(r)
    months: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for month in sorted(by_month):
        group = by_month[month]
        values = {g[1] for g in group}
        if len(values) > 1:
            conflicts.append({"data_month": month, "values": sorted(v for v in values if v is not None),
                              "sources": sorted({str(g[6]) for g in group})})
            continue
        first = group[0]
        months.append({"data_month": month, "revenue": first[1], "revenue_year_ago": first[2],
                       "unit_scale": first[3], "currency": first[4], "available_on": first[5],
                       "sources": sorted({str(g[6]) for g in group})})
    return {"months": months, "conflicts": conflicts}


def price_series(conn: Any, ticker: str, *, as_of: date | str, start: date | str | None = None
                 ) -> list[dict[str, Any]]:
    """`bar_date ≤ T`（且 ≥ start）的日線，升序。"""
    params: list[Any] = [ticker, _iso(as_of)]
    clause = ""
    if start is not None:
        clause = " AND bar_date >= ?"
        params.append(_iso(start))
    rows = conn.execute(
        "SELECT bar_date, close_raw, close_adjusted, quote_unit, settlement_currency FROM price_history "
        f"WHERE ticker = ? AND bar_date <= ?{clause} ORDER BY bar_date", params).fetchall()
    return [{"bar_date": r[0], "close_raw": r[1], "close_adjusted": r[2], "quote_unit": r[3],
             "settlement_currency": r[4]} for r in rows]


__all__ = ["fundamental_series", "monthly_revenue_as_of", "price_series"]
