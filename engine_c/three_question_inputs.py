"""財務三題的**取數**（Phase 3 Step 3.3）：從 Engine C 的機械歷史表、月營收、人工觀測組出
`alpha.three_questions` 要的輸入。**一個判斷都不做**——口徑、百分位、缺席分類在 alpha 那一層。

為什麼另立一檔而不塞進 `engine_c/checklist.py`：checklist 是 L9 前置條件的財務核驗清單（gate 凍結五項），
三題的取數與它無關；塞進去會讓「動三題」與「動 gate 清單」變成改同一個檔（plan §0.6 偏差紀錄）。

輸出形狀（`get_three_question_inputs`）：

- `filer_class`：`engine_c.history_backfill.filer_class`（讀已存列，零網路）；台股固定 `taiwan_monthly`。
- `revenue_kind`：`quarterly`（10-Q 申報人）｜`annual`（20-F）｜`monthly`（台股）｜`none`。
- `price_bars`／`adjusted_bars`：`[(date, close_raw)]`／`[(date, close_adjusted)]`。
- `price_to_settlement`：報價單位 → 結算幣別的倍數（`GBp` → 0.01；registry＋`identity/currency.py`，不自己 parse）。
- `revenue_quarters`／`revenue_annual`／`operating_income_quarters`／`cash`／`total_debt`／`shares_cover`：
  `fundamental_history` 的**全部列（每份申報各一列）**——逐日 as-of 由三題那一層用 `shared.as_of` 取。
- `monthly_revenue`／`monthly_conflicts`：`engine_c.history.monthly_revenue_as_of`（可用日＝法定期限）。
- `segment_shares`：`segment_revenue_share`／`product_line_revenue_share` 人工觀測（每個觀測日一點）。
- `gate`：這一檔的已定價①在取數這一層就知道算不了的（台股沒有歷史股數、非美非台沒有歷史來源…）——
  `{absence_kind, reason}`，由產生缺席的這段程式自己宣告（L16）。
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any

_METRIC_KEYS = {
    "revenue_quarter": "revenue_quarters", "revenue_annual": "revenue_annual",
    "operating_income_quarter": "operating_income_quarters", "cash": "cash", "total_debt": "total_debt",
    "shares_outstanding_cover": "shares_cover",
}
_SEGMENT_FIELDS = ("segment_revenue_share", "product_line_revenue_share")


def _rows(conn: Any, ticker: str, metric: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        """SELECT period_start, period_end, filed, accession, form, value, currency, derived, tag
           FROM fundamental_history WHERE ticker = ? AND metric = ? ORDER BY period_end, filed, accession""",
        (ticker, metric))
    return [{"period_start": r[0], "period_end": r[1], "filed": r[2], "accession": r[3], "form": r[4],
             "value": r[5], "currency": r[6], "derived": r[7], "tag": r[8]} for r in cur.fetchall()]


def _segment_points(conn: Any, ticker: str) -> list[dict[str, Any]]:
    """分部／產品線占比：每個 (欄位, as_of) 取生效那一筆（supersedes 沒被指到的）；解析不了的不收。"""
    from engine_c.manual_observations import live_observation_ids

    out = []
    for field in _SEGMENT_FIELDS:
        dates = [r[0] for r in conn.execute(
            "SELECT DISTINCT as_of FROM manual_observations WHERE ticker = ? AND field_name = ? ORDER BY as_of",
            (ticker, field)).fetchall()]
        for as_of in dates:
            live = live_observation_ids(conn, ticker, field, as_of)
            if len(live) != 1:
                continue
            row = conn.execute("SELECT value FROM manual_observations WHERE observation_id = ?",
                               (live[0],)).fetchone()
            try:
                value = json.loads(row[0])
            except (TypeError, ValueError):
                continue
            if isinstance(value, dict):
                out.append({"as_of": str(as_of)[:10], "value": value, "field": field})
    return out


def _quote_units(company_id: str | None) -> tuple[str | None, str | None, float | None]:
    if not company_id:
        return None, None, None
    from identity.currency import resolve_quote_unit
    from identity.registry import get_registry

    company = get_registry().company(company_id)
    raw_unit = getattr(company, "market_quote_unit", None)
    settlement = getattr(company, "market_currency", None)
    unit = resolve_quote_unit(raw_unit) if raw_unit else None
    factor = unit.factor if unit is not None else None
    return raw_unit, settlement, factor


def get_three_question_inputs(ticker: str, *, conn: Any, today: date, company_id: str | None = None) -> dict[str, Any]:
    """一檔的三題原始輸入。取不到的欄位留空 list，並由 `gate` 說明已定價①為什麼算不了。"""
    from engine_c.history import monthly_revenue_as_of, price_series
    from engine_c.history_backfill import filer_class

    ticker = ticker.strip().upper()
    if company_id is None:
        from identity.registry import get_registry

        company_id = get_registry().company_id_for_ticker(ticker)
    raw_unit, settlement, factor = _quote_units(company_id)
    bars = price_series(conn, ticker, as_of=today)
    inp: dict[str, Any] = {
        "ticker": ticker, "company_id": company_id, "today": today.isoformat(),
        "price_bars": [(date.fromisoformat(b["bar_date"]), b["close_raw"]) for b in bars],
        "adjusted_bars": [(date.fromisoformat(b["bar_date"]), b["close_adjusted"]) for b in bars],
        "price_quote_unit": raw_unit, "price_settlement_currency": settlement, "price_to_settlement": factor,
        "splits": [(date.fromisoformat(str(d)[:10]), float(r)) for d, r in conn.execute(
            "SELECT action_date, ratio FROM corporate_actions WHERE ticker = ? AND kind = 'split' ORDER BY action_date",
            (ticker,)).fetchall()],
        "segment_shares": _segment_points(conn, ticker),
        "source": "engine_c：price_history＋fundamental_history（SEC companyfacts）",
    }
    for metric, key in _METRIC_KEYS.items():
        inp[key] = _rows(conn, ticker, metric)
    if ticker.endswith((".TW", ".TWO")):
        mr = monthly_revenue_as_of(conn, ticker, as_of=today)
        inp.update(filer_class="taiwan_monthly", revenue_kind="monthly", monthly_revenue=mr["months"],
                   monthly_conflicts=mr["conflicts"],
                   source="engine_c：price_history＋monthly_revenue_observations（MOPS）")
        # 台股歷史股數沒有機械來源（Step 3.2 回填報告）：市值序列組不出來，已定價①整列缺席——不用今天的股數回推。
        inp["gate"] = {"absence_kind": "upstream_unavailable",
                       "reason": "台股歷史股數沒有機械來源（TWSE／TPEx 只有當期股本），市值序列組不出來；不用今天的股數回推"}
        return inp
    klass, basis = filer_class(conn, ticker, today=today)
    inp["filer_class"] = klass
    inp["filer_basis"] = basis
    inp["monthly_revenue"] = []
    if klass == "domestic_quarterly":
        inp["revenue_kind"] = "quarterly"
    elif klass == "foreign_annual":
        inp["revenue_kind"] = "annual"
    else:
        inp["revenue_kind"] = "none"
        has_rows = any(inp[k] for k in _METRIC_KEYS.values())
        inp["gate"] = {"absence_kind": "upstream_unavailable",
                       "reason": ("companyfacts 這一檔最近 18 個月沒有 10-Q／20-F（或回填時落後、這一輪沒寫）——"
                                  "沒有可用的財報歷史" if has_rows or "." not in ticker else
                                  "非美國 SEC 申報人、非台股：沒有機械的財報歷史來源（歷史不可得）")}
    return inp


__all__ = ["get_three_question_inputs"]
