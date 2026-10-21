"""吃到多少的取數（個股頁 S3b，2026-10-08）：讀 Engine C 的營收（台股月營收或 EDGAR 季營收）與歷史匯率，交給
`alpha.capture` 的純函式算。錨用這一頁的需求錨裡**加總型**那一條（雲端四大現金資本支出——曆季）；會計季的單一型（NVIDIA 營收）
不拿來算吃到多少（期間對不上）。

哪一條營收路：這一檔在 `monthly_revenue_observations` 有月營收就走台股路，否則走 EDGAR 季營收——從資料判，不從代號猜（L16）。
缺席分開（L12）：這一頁沒有加總型的錨（沿用錨那一格的缺席）／公司沒有季營收序列（海外、或沒有申報）／有序列但沒有任何一季
三者都齊。
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from alpha.capture import capture_series, fiscal_quarters, quarter_fx, tw_quarters

NO_QUARTERLY_REVENUE = "公司沒有季營收序列（不是台股月營收、也沒有 EDGAR 季營收——海外公司的財報來源還沒接）"


def company_quarters(conn: Any, ticker: str, *, as_of: date) -> dict[str, Any]:
    """一家公司 as-of T 的曆季營收：有台股月營收就三個月成一季，否則 EDGAR 季營收對曆季（期末 ±10 天、長度差 ≤5 天、
    兩期同季不挑）。回 `{quarters, gaps, source}`；`source` 是 None＝兩條路都沒有資料。「吃到多少」與路徑上各層共用（L16）。"""
    from engine_c.history import first_filed_by_period, fundamental_series, monthly_revenue_as_of

    monthly = monthly_revenue_as_of(conn, ticker, as_of=as_of)
    if monthly["months"]:
        quarters, gaps = tw_quarters(monthly["months"])
        gaps += [{"period": c["data_month"], "reason": f"同一個月兩個不同的數 {c['values']}——那個月不用"}
                 for c in monthly.get("conflicts") or ()]
        return {"quarters": quarters, "gaps": gaps, "source": "台股月營收（三個月相加）"}
    rows = fundamental_series(conn, ticker, "revenue_quarter", as_of=as_of)
    if not rows:
        if fundamental_series(conn, ticker, "revenue_half", as_of=as_of):
            # R2-S2 F4：與路徑上各層同一個缺席種類（有營收、只是對不上曆季＝輸入不相容，不是「還沒人記」；L16）
            return {"quarters": {}, "gaps": [], "source": None, "absence_reason": SEMIANNUAL_ONLY,
                    "absence_kind": "inputs_incompatible"}
        return {"quarters": {}, "gaps": [], "source": None}
    label = _quarterly_label(conn, ticker)
    quarters, gaps = fiscal_quarters(rows, first_filed_by_period(conn, ticker, "revenue_quarter", as_of=as_of),
                                     label=label)
    return {"quarters": quarters, "gaps": gaps, "source": label}


#: 日本 EDINET 只有半年營收（2026-10-21 日韓財報來源）——對不上曆季的錨，不估（不把半年拆成兩季）。
SEMIANNUAL_ONLY = "只有半年營收（日本 2024-04 起沒有 Q1／Q3 法定申報）——對不上曆季的錨，不估"


def _quarterly_label(conn: Any, ticker: str) -> str:
    """季營收的來源標籤從資料列的 source 取（L18：韓國的列不得被標成 EDGAR）；美股照原字串。"""
    sources = {str(r[0] or "") for r in conn.execute(
        "SELECT DISTINCT source FROM fundamental_history WHERE ticker = ? AND metric = 'revenue_quarter'", (ticker,))}
    return "DART 季營收" if sources and all(s.startswith("opendart://") for s in sources) else "EDGAR 季營收"


def fx_tables(conn: Any, currencies: Any, *, as_of: date) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """幣別 → 季均價表（美元以外）；讀不到某幣別的日匯率就不給那個鍵（換算端照寫「沒有歷史匯率」）。"""
    from engine_c.history import fx_daily

    fx: dict[str, Any] = {}
    gaps: list[dict[str, Any]] = []
    for currency in sorted({str(c) for c in currencies} - {"USD"}):
        rates = fx_daily(conn, currency, as_of=as_of)
        if rates:
            fx[currency], fx_gaps = quarter_fx(rates)
            gaps += [{**g, "reason": f"{currency}：{g['reason']}"} for g in fx_gaps]
    return fx, gaps


def page_capture(conn: Any, ticker: str, demand_anchor: Mapping[str, Any] | None, *, as_of: date) -> dict[str, Any]:
    """一頁的「吃到多少」：`{anchor_key, anchor_label, revenue_source, points, gaps, absence}`。"""
    demand = demand_anchor or {}
    if (demand.get("absence") or {}).get("kind") in ("upstream_unavailable", "point_in_time_unavailable"):
        return {"points": [], "gaps": [], "absence": dict(demand["absence"])}
    anchor = next((s for s in demand.get("series") or () if s.get("aggregation") == "sum_calendar_quarter"
                   and s.get("points")), None)
    if anchor is None:
        reason = (demand.get("absence") or {}).get("reason") or "這一頁的需求錨沒有加總型（曆季）的序列"
        return {"points": [], "gaps": [], "absence": {"kind": "not_yet_recorded", "reason": f"沒有可以比的錨：{reason}"}}
    got = company_quarters(conn, ticker, as_of=as_of)
    if got["source"] is None:
        return {"anchor_key": anchor["key"], "anchor_label": anchor.get("label"), "points": [], "gaps": [],
                "absence": {"kind": got.get("absence_kind") or "not_yet_recorded",
                            "reason": got.get("absence_reason") or NO_QUARTERLY_REVENUE}}
    company, gaps, source = got["quarters"], list(got["gaps"]), got["source"]
    fx, fx_gaps = fx_tables(conn, {str(q.get("currency")) for q in company.values()}, as_of=as_of)
    gaps += fx_gaps
    result = capture_series(company, fx, anchor["points"], as_of=as_of)
    out = {"anchor_key": anchor["key"], "anchor_label": anchor.get("label"), "revenue_source": source,
           "points": result["points"], "gaps": gaps + result["gaps"], "absence": None}
    if not out["points"]:
        out["absence"] = {"kind": "not_yet_recorded",
                          "reason": "沒有任何一季營收、錨、匯率三者都齊（缺哪個寫在 gaps）"}
    return out


__all__ = ["NO_QUARTERLY_REVENUE", "SEMIANNUAL_ONLY", "company_quarters", "fx_tables", "page_capture"]
