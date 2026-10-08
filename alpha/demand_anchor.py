"""需求錨序列的組法（個股頁 S3a，2026-10-08；brainstorm 2026-10-05-stock-page-schema §5.4 B2「錨的變化」）——**純函式**。

取數住 `alpha/providers/demand_anchor.py`（讀 Engine C `fundamental_history` 與 `config/demand_anchor_series.json`）；
這裡只把取到的列組成題材錨的季度序列（alpha 核心不碰外部世界——`tests/test_layer_separation.py`）。

- **加總型**（`sum_calendar_quarter`，雲端四大現金資本支出）：每一家的每一期（取數端已 as-of T 取 `filed ≤ T` 的最新一列），
  期末落在曆季末 ±10 天內才歸到那一季；**每一家同一曆季都有**才算那一季，值＝相加。缺任何一家就整季缺席、寫出缺誰——
  半套加總不得出現（INV-6、L13）。可知日＝每一家最早申報日取最晚的；版本日＝值用的那一版（隔年比較欄重列時是隔年）。
- **單一型**（`single`，NVIDIA 營收）：照它自己的會計季（期末就是標籤），不與曆季相加。
- 幣別：每一家每一期都要是序列宣告的那一種（USD），不換算；不符的那一期當缺那一家、原因寫出實際幣別。
- 年增：同一季的前一年（曆季：同季別；會計季：期末前 365±10 天那一期）也有值才算，不外推。

**不判讀、不排序、不打分**；序列住 artifact，敘事那一句引用它。
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Iterable, Mapping, Sequence

AGGREGATIONS = ("sum_calendar_quarter", "single")
#: 期末離曆季末多遠還算同一季（52／53 週制、月底不是 31 號的公司）。
CALENDAR_SLACK_DAYS = 10


class DemandAnchorError(ValueError):
    """設定檔的形狀不對（未知的聚合方式、空的成分、對到不存在的序列）——fail closed，不猜。"""


def validate_config(data: Mapping[str, Any]) -> dict[str, Any]:
    """`config/demand_anchor_series.json` 的形狀檢查；不對就 raise（不猜）。回原內容。"""
    series = data.get("series") or {}
    for key, spec in series.items():
        if spec.get("aggregation") not in AGGREGATIONS:
            raise DemandAnchorError(f"序列 {key} 的聚合方式 {spec.get('aggregation')!r} 不認得（{AGGREGATIONS}）")
        if not spec.get("components") or not spec.get("metric"):
            raise DemandAnchorError(f"序列 {key} 要有 metric 與至少一個成分")
        if spec["aggregation"] == "single" and len(spec["components"]) != 1:
            raise DemandAnchorError(f"序列 {key} 是單一型，成分只能一個")
    for anchor, keys in (data.get("anchors") or {}).items():
        missing = [k for k in keys if k not in series]
        if missing:
            raise DemandAnchorError(f"錨 {anchor} 對到不存在的序列 {missing}")
    return dict(data)


def series_keys_for(anchors: Iterable[str], config: Mapping[str, Any]) -> list[str]:
    """這幾個需求錨節點對到的序列（照設定檔 `series` 的順序，同一條只列一次）。"""
    table = config.get("anchors") or {}
    wanted = {key for anchor in anchors for key in table.get(str(anchor), ())}
    return [key for key in (config.get("series") or {}) if key in wanted]


def calendar_quarter(period_end: date) -> tuple[int, int] | None:
    """期末 → 曆季（年, 1..4）；離最近的曆季末超過 `CALENDAR_SLACK_DAYS` 天＝不是曆季（回 None）。"""
    for year in (period_end.year - 1, period_end.year, period_end.year + 1):
        for quarter, (month, day) in enumerate(((3, 31), (6, 30), (9, 30), (12, 31)), start=1):
            if abs((period_end - date(year, month, day)).days) <= CALENDAR_SLACK_DAYS:
                return year, quarter
    return None


def assemble_series(key: str, spec: Mapping[str, Any], rows_by_ticker: Mapping[str, Sequence[Mapping[str, Any]]],
                    first_by_ticker: Mapping[str, Mapping[str, str]], *, as_of: date) -> dict[str, Any]:
    """一條錨序列：`{key, label, proxy, aggregation, metric, currency, as_of, components, points, gaps, absence}`。

    `rows_by_ticker`：每一家 as-of T 每期最新的那一列（`engine_c.history.fundamental_series`；照成分順序）；
    `first_by_ticker`：每一家每期最早的申報日（`first_filed_by_period`）。`points`：`{period, period_end, value, known_on,
    version_on, parts, derived, yoy}`，依期末升序；`gaps`：那一季為什麼沒有值（缺哪幾家、幣別）。"""
    currency = spec.get("currency") or "USD"
    out: dict[str, Any] = {"key": key, "label": spec.get("label") or key, "proxy": spec.get("proxy") or "",
                           "aggregation": spec["aggregation"], "metric": spec["metric"], "currency": currency,
                           "as_of": as_of.isoformat(), "points": [], "gaps": [], "absence": None,
                           "components": [{"ticker": t, "periods": len(rows)} for t, rows in rows_by_ticker.items()]}
    if spec["aggregation"] == "single":
        ticker = next(iter(rows_by_ticker))
        out["points"], out["gaps"] = _single(rows_by_ticker[ticker], first_by_ticker.get(ticker) or {}, currency)
    else:
        out["points"], out["gaps"] = _sum_by_calendar_quarter(rows_by_ticker, first_by_ticker, currency)
    if not out["points"]:
        out["absence"] = {"kind": "not_yet_recorded",
                          "reason": f"as-of {as_of.isoformat()} 沒有任何一季每一家都申報了（{'、'.join(rows_by_ticker)}）"}
    return out


def _single(rows: Sequence[Mapping[str, Any]], first: Mapping[str, str], currency: str
            ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    points, gaps = [], []
    for row in rows:
        end = date.fromisoformat(str(row["period_end"])[:10])
        if str(row.get("currency")) != currency:
            gaps.append({"period": end.isoformat(), "reason": f"幣別是 {row.get('currency')}、不是 {currency}（不換算）"})
            continue
        version = str(row["filed"])[:10]
        points.append({"period": end.isoformat(), "period_end": end.isoformat(), "value": float(row["value"]),
                       "known_on": first.get(end.isoformat(), version), "version_on": version, "parts": None,
                       "derived": [row["derived"]] if row.get("derived") else [], "yoy": None})
    for point in points:
        end = date.fromisoformat(point["period_end"])
        prior = [p for p in points
                 if abs((date.fromisoformat(p["period_end"]) - (end - timedelta(days=365))).days) <= CALENDAR_SLACK_DAYS]
        if prior and prior[0]["value"]:
            point["yoy"] = point["value"] / prior[0]["value"] - 1
    return points, gaps


def _sum_by_calendar_quarter(per_company: Mapping[str, Sequence[Mapping[str, Any]]], first: Mapping[str, Mapping[str, str]],
                             currency: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_quarter: dict[tuple[int, int], dict[str, Mapping[str, Any]]] = {}
    off_calendar: dict[str, list[str]] = {}
    for ticker, rows in per_company.items():
        for row in rows:
            end = date.fromisoformat(str(row["period_end"])[:10])
            quarter = calendar_quarter(end)
            if quarter is None:
                off_calendar.setdefault(ticker, []).append(end.isoformat())
                continue
            by_quarter.setdefault(quarter, {})[ticker] = row
    points, gaps = [], []
    for (year, q), parts in sorted(by_quarter.items()):
        label = f"{year}Q{q}"
        missing = [t for t in per_company if t not in parts]
        wrong = [t for t, r in parts.items() if str(r.get("currency")) != currency]
        if missing or wrong:
            reasons = []
            if missing:
                reasons.append(f"缺 {'、'.join(missing)}（as-of 那天還沒申報或沒有這一期）")
            if wrong:
                found = "、".join(f"{t} 是 {parts[t].get('currency')}" for t in wrong)
                reasons.append(f"幣別不是 {currency}：{found}（不換算）")
            gaps.append({"period": label, "missing": missing + wrong, "reason": "；".join(reasons)})
            continue
        quarter_end = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}[q]
        points.append({
            "period": label, "period_end": date(year, *quarter_end).isoformat(),
            "value": sum(float(r["value"]) for r in parts.values()),
            "known_on": max(first.get(t, {}).get(str(r["period_end"])[:10], str(r["filed"])[:10]) for t, r in parts.items()),
            "version_on": max(str(r["filed"])[:10] for r in parts.values()),
            "parts": {t: float(r["value"]) for t, r in sorted(parts.items())},
            "derived": sorted(t for t, r in parts.items() if r.get("derived")), "yoy": None,
        })
    index = {p["period"]: p for p in points}
    for point in points:
        year, q = int(point["period"][:4]), point["period"][-1]
        prior = index.get(f"{year - 1}Q{q}")
        if prior and prior["value"]:
            point["yoy"] = point["value"] / prior["value"] - 1
    for ticker, ends in sorted(off_calendar.items()):
        gaps.append({"period": None, "missing": [ticker],
                     "reason": f"{ticker} 有 {len(ends)} 期的期末不在曆季末 ±{CALENDAR_SLACK_DAYS} 天內（{ends[-1]} 等）——不歸季、不加總"})
    return points, gaps


def page_anchor(context: Mapping[str, Any] | None, anchors: Mapping[str, str] | None,
                names: Mapping[str, str] | None = None) -> dict[str, Any]:
    """一頁的「錨的變化」：這家公司走到的需求錨（結構表逐列錨，`candidates.bet_index` 那一份）→ 對到的序列。

    回 `{"anchors": [{node, name, basis}], "series": [序列…], "absence": …}`。缺席分開講（L12）：這一輪沒載入
    （`upstream_unavailable`）、這家公司走不到任何需求錨、走得到錨但題材沒宣告序列（`not_yet_recorded`）。"""
    if context is None or context.get("absence"):
        return {"anchors": [], "series": [], "absence": (context or {}).get("absence")
                or {"kind": "upstream_unavailable", "reason": "這一輪沒有載入需求錨序列"}}
    listed = [{"node": node, "name": (names or {}).get(node) or node, "basis": basis}
              for node, basis in sorted((anchors or {}).items())]
    if not listed:
        return {"anchors": [], "series": [], "absence": {
            "kind": "not_yet_recorded", "reason": "結構表裡這家公司走不到任何需求錨（不在鏈上，或鏈還沒接到錨）"}}
    keys = series_keys_for([a["node"] for a in listed], context.get("config") or {})
    if not keys:
        return {"anchors": listed, "series": [], "absence": {
            "kind": "not_yet_recorded",
            "reason": f"題材沒宣告錨序列：{'、'.join(a['name'] for a in listed)} 還沒對到任何序列（config/demand_anchor_series.json）"}}
    return {"anchors": listed, "series": [context["series"][k] for k in keys], "absence": None}


__all__ = ["AGGREGATIONS", "CALENDAR_SLACK_DAYS", "DemandAnchorError", "assemble_series", "calendar_quarter",
           "page_anchor", "series_keys_for", "validate_config"]
