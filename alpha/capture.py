"""吃到多少（個股頁 S3b，2026-10-08；brainstorm 2026-10-05-stock-page-schema §5.4 B2「吃到多少」）——**純函式**。

公司同一曆季的營收（換美元）÷ 當季題材錨（雲端四大現金資本支出）：往上＝吃到的比例變大。取數住 `alpha/providers/capture.py`。

- **公司的季**：台股＝月營收**三個月都公告**才算一季，可知日＝第三個月的法定公告期限（上界，`monthly_revenue_as_of` 的
  `available_on`）；美股＝EDGAR 季營收，期末落在曆季末 ±10 天內、**而且期間長度與曆季差不到 5 天**才算那一曆季——
  會計季對不上曆季的照實缺席，**不拿重疊天數去估**（例：MRVL 的季 8 月初結束；14 週的季多一週營收）。
- **換匯**：季均價＝那一季每個有報價日子的平均（FRED H.10），報價方向統一成「一美元換幾單位」。那一季頭尾都要有報價
  （首筆不晚於季初 +7 天、末筆不早於季末 −7 天）才算完整；可知日＝末筆 + 10 天（H.10 公布上界，含週一假日延後）。
  用季均價不用期末價：營收是一整季累積的流量，用季末那一天的匯率會把季內的匯率變動算錯。
- **吃到多少**＝營收（美元）÷ 錨（美元），呈現成「每 10 億美元的錨對應它多少美元營收」。可知日＝營收、錨、匯率三者最晚的
  那天；as-of T 時還不可知的那一季不算（INV-6）。

本檔不判讀、不排序、不打分、沒有門檻。
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Mapping, Sequence

from alpha.demand_anchor import calendar_quarter, period_length_problem

#: 季均價要算完整的一季：首筆不晚於季初 +7 天、末筆不早於季末 −7 天（涵蓋假日與週末，不涵蓋整段缺資料）。
FX_EDGE_DAYS = 7
#: H.10 的公布上界（與 `engine_c.history.FX_PUBLICATION_LAG_DAYS` 同一個數，理由寫在那裡；這裡不 import engine_c——alpha 核心
#: 不碰外部；兩個數相等由 `tests/test_capture.py` 守）。
FX_KNOWN_LAG_DAYS = 10
PER = 1_000_000_000          # 「每 10 億美元的錨」


def _label(year: int, quarter: int) -> str:
    return f"{year}Q{quarter}"


def _bounds(year: int, quarter: int) -> tuple[date, date]:
    start = date(year, 3 * quarter - 2, 1)
    end = date(year + (quarter == 4), (3 * quarter) % 12 + 1, 1) - timedelta(days=1)
    return start, end


def quarter_fx(rows: Sequence[Mapping[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """日匯率 → 每個曆季的季均價（一美元換幾單位）。回 `({季: {per_usd, days, first, last, known_on}}, gaps)`。
    同一天兩個不同的數（兩條序列）→ 那一季不算、寫原因（不挑一個）。"""
    by_quarter: dict[tuple[int, int], dict[str, float]] = {}
    clashes: set[tuple[int, int]] = set()
    for row in rows:
        day = date.fromisoformat(str(row["obs_date"])[:10])
        rate = float(row["rate"])
        per_usd = rate if row.get("quote") == "per_usd" else 1 / rate
        key = ((day.month - 1) // 3 + 1)
        bucket = by_quarter.setdefault((day.year, key), {})
        if day.isoformat() in bucket and abs(bucket[day.isoformat()] - per_usd) > 1e-9:
            clashes.add((day.year, key))
        bucket[day.isoformat()] = per_usd
    quarters: dict[str, dict[str, Any]] = {}
    gaps: list[dict[str, Any]] = []
    for (year, q), days in sorted(by_quarter.items()):
        label = _label(year, q)
        start, end = _bounds(year, q)
        first, last = min(days), max(days)
        if (year, q) in clashes:
            gaps.append({"period": label, "reason": "同一天有兩個不同的匯率（兩條序列）——不挑一個"})
            continue
        if date.fromisoformat(first) > start + timedelta(days=FX_EDGE_DAYS) or date.fromisoformat(last) < end - timedelta(days=FX_EDGE_DAYS):
            gaps.append({"period": label, "reason": f"匯率不是整季都有（{first} → {last}）——季均價不算"})
            continue
        quarters[label] = {"per_usd": sum(days.values()) / len(days), "days": len(days), "first": first, "last": last,
                           "known_on": (date.fromisoformat(last) + timedelta(days=FX_KNOWN_LAG_DAYS)).isoformat()}
    return quarters, gaps


def tw_quarters(months: Sequence[Mapping[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """台股月營收（`monthly_revenue_as_of` 的 months）→ 曆季：三個月都公告才算一季；值＝三個月相加（照 unit_scale 還原），
    可知日＝三個月法定公告期限最晚的那個。"""
    by_quarter: dict[tuple[int, int], dict[int, Mapping[str, Any]]] = {}
    for month in months:
        year, mon = (int(x) for x in str(month["data_month"])[:7].split("-"))
        by_quarter.setdefault((year, (mon - 1) // 3 + 1), {})[mon] = month
    quarters: dict[str, dict[str, Any]] = {}
    gaps: list[dict[str, Any]] = []
    for (year, q), got in sorted(by_quarter.items()):
        label = _label(year, q)
        want = [3 * q - 2, 3 * q - 1, 3 * q]
        missing = [m for m in want if m not in got or got[m].get("revenue") is None]
        currencies = {str(got[m].get("currency")) for m in want if m in got}
        if missing:
            gaps.append({"period": label, "reason": f"月營收缺 {'、'.join(f'{m} 月' for m in missing)}（三個月都公告才算一季）"})
            continue
        if len(currencies) != 1:
            gaps.append({"period": label, "reason": f"三個月的幣別不同 {sorted(currencies)}——不加總"})
            continue
        quarters[label] = {
            "value": sum(float(got[m]["revenue"]) * float(got[m].get("unit_scale") or 1) for m in want),
            "currency": currencies.pop(), "known_on": max(str(got[m]["available_on"])[:10] for m in want),
            "source": "台股月營收（三個月相加）",
        }
    return quarters, gaps


def fiscal_quarters(rows: Sequence[Mapping[str, Any]], first: Mapping[str, str]
                    ) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """EDGAR 季營收（`fundamental_series` 每期最新版本）→ 曆季：期末落在曆季末 ±10 天內、期間長度與曆季差不超過
    `alpha.demand_anchor.PERIOD_LENGTH_SLACK_DAYS` 才算（沒有起始日＝量不出長度，也不算；與錨的加總同一條）；
    兩個會計期對到同一個曆季＝不挑一個；可知日用最早的申報日。"""
    quarters: dict[str, dict[str, Any]] = {}
    gaps: list[dict[str, Any]] = []
    collided: set[str] = set()
    for row in rows:
        end = date.fromisoformat(str(row["period_end"])[:10])
        quarter = calendar_quarter(end)
        if quarter is None:
            gaps.append({"period": end.isoformat(), "reason": f"會計季期末 {end.isoformat()} 不在曆季末 ±10 天內——與曆季的錨對不起來，不估"})
            continue
        problem = period_length_problem(row, quarter)
        if problem:
            gaps.append({"period": _label(*quarter), "reason": f"會計季{problem}——與曆季的錨對不起來，不估"})
            continue
        if _label(*quarter) in quarters or _label(*quarter) in collided:
            # 兩個會計期對到同一個曆季（例：改會計年度）——不挑一個、不讓後一筆蓋掉前一筆（INV-3；S3 R2 N6）
            quarters.pop(_label(*quarter), None)
            collided.add(_label(*quarter))
            gaps.append({"period": _label(*quarter), "reason": "兩個會計期對到同一個曆季——不挑一個，不估"})
            continue
        quarters[_label(*quarter)] = {"value": float(row["value"]), "currency": str(row.get("currency")),
                                      "known_on": first.get(end.isoformat(), str(row["filed"])[:10]),
                                      "source": "EDGAR 季營收" + ("（年度差分推算）" if row.get("derived") else "")}
    return quarters, gaps


def capture_series(company: Mapping[str, Mapping[str, Any]], fx: Mapping[str, Mapping[str, Mapping[str, Any]]],
                   anchor_points: Sequence[Mapping[str, Any]], *, as_of: date) -> dict[str, Any]:
    """每個曆季：營收（美元）÷ 錨。`fx`＝幣別 → 季均價表（`quarter_fx` 的結果）；美元營收不用換。
    回 `{"points": [{period, revenue, currency, per_usd, revenue_usd, anchor, ratio, per_billion, known_on}], "gaps": [...]}`。"""
    anchors = {str(p["period"]): p for p in anchor_points}
    points: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    for label, q in sorted(company.items()):
        anchor = anchors.get(label)
        if anchor is None or not anchor.get("value"):
            gaps.append({"period": label, "reason": "錨沒有這一季（四家還沒都申報，或超出錨的期間）"})
            continue
        currency = str(q.get("currency"))
        rate = None
        known = [str(q["known_on"]), str(anchor["known_on"])]
        if currency != "USD":
            table = fx.get(currency)
            if table is None:
                gaps.append({"period": label, "reason": f"沒有 {currency} 的歷史匯率——不換算"})
                continue
            quarter_rate = table.get(label)
            if quarter_rate is None:
                gaps.append({"period": label, "reason": f"{currency} 那一季沒有完整的季均價"})
                continue
            rate = float(quarter_rate["per_usd"])
            known.append(str(quarter_rate["known_on"]))
        known_on = max(known)
        if known_on > as_of.isoformat():
            gaps.append({"period": label, "reason": f"as-of {as_of.isoformat()} 時還不可知（{known_on} 才齊）"})
            continue
        revenue_usd = float(q["value"]) / rate if rate else float(q["value"])
        ratio = revenue_usd / float(anchor["value"])
        points.append({"period": label, "revenue": float(q["value"]), "currency": currency, "per_usd": rate,
                       "revenue_usd": revenue_usd, "anchor": float(anchor["value"]), "ratio": ratio,
                       "per_billion": ratio * PER, "known_on": known_on, "source": q.get("source")})
    return {"points": points, "gaps": gaps}


__all__ = ["FX_EDGE_DAYS", "FX_KNOWN_LAG_DAYS", "PER", "capture_series", "fiscal_quarters", "quarter_fx", "tw_quarters"]
