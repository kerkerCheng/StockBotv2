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


def page_capture(conn: Any, ticker: str, demand_anchor: Mapping[str, Any] | None, *, as_of: date) -> dict[str, Any]:
    """一頁的「吃到多少」：`{anchor_key, anchor_label, revenue_source, points, gaps, absence}`。"""
    from engine_c.history import first_filed_by_period, fundamental_series, fx_daily, monthly_revenue_as_of

    demand = demand_anchor or {}
    if (demand.get("absence") or {}).get("kind") in ("upstream_unavailable", "point_in_time_unavailable"):
        return {"points": [], "gaps": [], "absence": dict(demand["absence"])}
    anchor = next((s for s in demand.get("series") or () if s.get("aggregation") == "sum_calendar_quarter"
                   and s.get("points")), None)
    if anchor is None:
        reason = (demand.get("absence") or {}).get("reason") or "這一頁的需求錨沒有加總型（曆季）的序列"
        return {"points": [], "gaps": [], "absence": {"kind": "not_yet_recorded", "reason": f"沒有可以比的錨：{reason}"}}
    monthly = monthly_revenue_as_of(conn, ticker, as_of=as_of)
    if monthly["months"]:
        company, gaps = tw_quarters(monthly["months"])
        source = "台股月營收（三個月相加）"
        gaps += [{"period": c["data_month"], "reason": f"同一個月兩個不同的數 {c['values']}——那個月不用"}
                 for c in monthly.get("conflicts") or ()]
    else:
        rows = fundamental_series(conn, ticker, "revenue_quarter", as_of=as_of)
        if not rows:
            return {"anchor_key": anchor["key"], "anchor_label": anchor.get("label"), "points": [], "gaps": [],
                    "absence": {"kind": "not_yet_recorded",
                                "reason": "公司沒有季營收序列（不是台股月營收、也沒有 EDGAR 季營收——海外公司的財報來源還沒接）"}}
        company, gaps = fiscal_quarters(rows, first_filed_by_period(conn, ticker, "revenue_quarter", as_of=as_of))
        source = "EDGAR 季營收"
    fx: dict[str, Any] = {}
    for currency in sorted({str(q.get("currency")) for q in company.values()} - {"USD"}):
        rates = fx_daily(conn, currency, as_of=as_of)
        if rates:
            fx[currency], fx_gaps = quarter_fx(rates)
            gaps += [{**g, "reason": f"{currency}：{g['reason']}"} for g in fx_gaps]
    result = capture_series(company, fx, anchor["points"], as_of=as_of)
    out = {"anchor_key": anchor["key"], "anchor_label": anchor.get("label"), "revenue_source": source,
           "points": result["points"], "gaps": gaps + result["gaps"], "absence": None}
    if not out["points"]:
        out["absence"] = {"kind": "not_yet_recorded",
                          "reason": "沒有任何一季營收、錨、匯率三者都齊（缺哪個寫在 gaps）"}
    return out


__all__ = ["page_capture"]
