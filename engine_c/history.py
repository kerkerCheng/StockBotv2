"""Engine C 機械歷史表的 **as-of 讀取**（Phase 3 Step 3.2）。寫入端是 `engine_c/history_backfill.py`。

唯一的規則：**T 時刻知道什麼**（INV-6）。

- `fundamental_history`：每個 `period_end` 取 **`filed ≤ T`** 的最新一列（同一期被後來的申報重編時，T 落在兩次
  申報之間拿到的是舊值）。`fetched_at` 不參與任何判斷——那是我們哪天抓的，不是市場哪天知道的。
- `monthly_revenue_observations`：只收 **`disclosure_deadline ≤ T`**（法定公告期限，次月 10 日）。它是可機械推導的
  **上界**，不是實際公告日（`published_at` 恆 NULL，`published_at_basis=statutory_deadline_only`）；
  用上界表示「最晚這天全市場都知道了」，寧可晚幾天也不提早看到。
- `tw_share_capital_observations`（台股季報股數，2026-10-05）：只收 **`available_on ≤ T`**（一般業季後 45 日、年報 3 個月
  的法定期限），同樣是上界；交叉核對沒過或同一季兩個數字的整季不用。
- `price_history`：`bar_date ≤ T`。

本檔只取數、不判讀：百分位、TTM、口徑選擇在三題那一層（`alpha/three_questions.py`，Step 3.3）。
"""
from __future__ import annotations

from datetime import date
from typing import Any


def _iso(value: date | str) -> str:
    return value.isoformat() if isinstance(value, date) else str(value)[:10]


def fundamental_series(conn: Any, ticker: str, metric: str, *, as_of: date | str) -> list[dict[str, Any]]:
    """as-of T 的某一指標序列（`period_end` 升序）；每個期間只留 `filed ≤ T` 的最新那一列。

    規則只住 `shared.as_of.latest_known_by_period`（三題的逐日計算用同一支，L16）。
    """
    from shared.as_of import latest_known_by_period

    rows = conn.execute(
        """SELECT period_start, period_end, filed, accession, form, value, currency, unit_scale, derived, tag
           FROM fundamental_history
           WHERE ticker = ? AND metric = ? AND filed <= ?
           ORDER BY period_end, filed, accession""",
        (ticker, metric, _iso(as_of))).fetchall()
    keys = ("period_start", "period_end", "filed", "accession", "form", "value", "currency", "unit_scale",
            "derived", "tag")
    known = latest_known_by_period([dict(zip(keys, r)) for r in rows], _iso(as_of))
    return [dict(known[k]) for k in sorted(known)]


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


def tw_shares_as_of(conn: Any, ticker: str, *, as_of: date | str) -> dict[str, Any]:
    """as-of T 的台股季報股數：`{"cover": [...], "rejected": [...]}`（`period_end` 升序）。

    只收 **`available_on ≤ T`**（法定期限，見 `engine_c.tw_share_capital`）。交叉核對不是 `ok` 的列**整季不用**、
    列進 `rejected`（帶理由）；同一季兩個不同的 `ok` 股數（重抓時 MOPS 改過數字）也整季不用——不挑一個
    （同月營收衝突的守則；改過的那個版本哪天公開沒有來源，用法定期限頂替會提早看到）。
    `cover` 的形狀對齊 `fundamental_history` 的封面股數列（`period_end`／`filed`／`value`），三題的 `shares_on` 直接吃。
    ⚠ 唯讀連線上表可能還沒建（三題 provider 刻意不在讀取路徑建表）——「表不存在」＝還沒有任何觀測。
    """
    import sqlite3

    try:
        rows = conn.execute(
            """SELECT period_end, available_on, shares_outstanding, cross_check_status, cross_check_reason,
                      observation_id, source
               FROM tw_share_capital_observations
               WHERE ticker = ? AND available_on <= ?
               ORDER BY period_end, fetched_at""",
            (ticker, _iso(as_of))).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table" not in str(exc):
            raise
        return {"cover": [], "rejected": []}
    by_period: dict[str, list[tuple]] = {}
    for r in rows:
        by_period.setdefault(str(r[0]), []).append(r)
    cover: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for period in sorted(by_period):
        group = by_period[period]
        bad = [g for g in group if g[3] != "ok"]
        values = {g[2] for g in group if g[3] == "ok"}
        if bad or len(values) > 1:
            rejected.extend({"period_end": period, "status": g[3], "reason": g[4], "observation_id": g[5]} for g in bad)
            if len(values) > 1:
                rejected.append({"period_end": period, "status": "conflict",
                                 "reason": f"同一季有 {len(values)} 個不同股數：{sorted(values)}", "observation_id": None})
            continue
        first = group[0]
        cover.append({"period_end": period, "filed": first[1], "accession": first[5], "value": float(first[2]),
                      "currency": None, "source": first[6]})
    return {"cover": cover, "rejected": rejected}


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
