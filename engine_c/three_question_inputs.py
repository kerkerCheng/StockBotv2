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
- 台股：`shares_cover` 改取 `tw_share_capital_observations`（季報股本換算、可知日＝法定期限；`shares_rejected` 帶核對沒過的季）。
- `gate`：這一檔的已定價①在取數這一層就知道算不了的（台股一筆可用的季報股數都沒有、非美非台沒有歷史來源…）——
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
    # 日韓財報來源 S1（2026-10-21）：日本 EDINET 的半年序列
    "revenue_half": "revenue_halves", "operating_income_half": "operating_income_halves",
}
_SEGMENT_FIELDS = ("segment_revenue_share", "product_line_revenue_share")
#: 除權日落在期末前幾天內，那一期的期末股數可能是分割前的（日本常把基準日訂在期末；6594.T 2024-09-27 ×2 實測：
#: 期末發行 596,284,468、提出日現在 1,192,568,936）——那一期股數整期不用（照台股 `split_in_window` 的先例）。
SPLIT_NEAR_PERIOD_END_DAYS = 10
_JP_KR_SOURCES = ("edinet://", "opendart://")
_JP_SUFFIXES = (".T",)
_KR_SUFFIXES = (".KS", ".KQ")


def _rows(conn: Any, ticker: str, metric: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        """SELECT period_start, period_end, filed, accession, form, value, currency, derived, tag, source
           FROM fundamental_history WHERE ticker = ? AND metric = ? ORDER BY period_end, filed, accession""",
        (ticker, metric))
    return [{"period_start": r[0], "period_end": r[1], "filed": r[2], "accession": r[3], "form": r[4],
             "value": r[5], "currency": r[6], "derived": r[7], "tag": r[8], "source": r[9]} for r in cur.fetchall()]


def split_near_period_end(rows: list[dict[str, Any]], splits: list[tuple[date, float]], *,
                          days: int = SPLIT_NEAR_PERIOD_END_DAYS) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """日韓的股數列：除權日 s 落在（期末 − days, 期末］的那一期整期不用、計數進 shares_rejected（INV-3）——前一期的股數由
    `shares_on` 乘上分割比例接續。只套在日韓來源的列（美股封面股數與台股另有自己的規則）。"""
    from datetime import timedelta

    kept, rejected = [], []
    for row in rows:
        if not str(row.get("source") or "").startswith(_JP_KR_SOURCES):
            kept.append(row)
            continue
        try:
            end = date.fromisoformat(str(row["period_end"])[:10])
        except (TypeError, ValueError, KeyError):
            kept.append(row)
            continue
        hit = next((s for s, _r in splits if end - timedelta(days=days) < s <= end), None)
        if hit is None:
            kept.append(row)
            continue
        rejected.append({"period_end": end.isoformat(), "status": "split_near_period_end",
                         "observation_id": row.get("accession"),
                         "reason": f"除權日 {hit.isoformat()} 在期末前 {days} 天內——期末股數可能是分割前（6594.T 2024-09-27 實測），"
                                   "整期不用，由前一期股數乘分割比例接續"})
    return kept, rejected


def _segment_points(conn: Any, ticker: str, *, today: date | None = None) -> list[dict[str, Any]]:
    """分部／產品線占比：每個 (欄位, as_of) 取生效那一筆（`live_observation_ids`：supersedes 與取代關係都沒指到的）；
    解析不了的不收。`today`＝as-of：只看那天以前**記錄**的列與關係（2026-10-14 取代鏈 A R2 非阻擋 #6——同一函式的價格與營收
    早就有 as-of，占比沒有，回看那天會看到之後才寫的更正）。

    同一 (欄位, as_of) 有多筆生效 → `{"conflict": [...]}`，不挑一個、也不默默丟（INV-3；同 going-concern 的前例）。
    """
    from engine_c.manual_observations import live_observation_ids

    cutoff = today.isoformat() if today is not None else None
    out = []
    for field in _SEGMENT_FIELDS:
        dates = [r[0] for r in conn.execute(
            "SELECT DISTINCT as_of FROM manual_observations WHERE ticker = ? AND field_name = ? ORDER BY as_of",
            (ticker, field)).fetchall()]
        for as_of in dates:
            live = live_observation_ids(conn, ticker, field, as_of, recorded_by=cutoff)
            if len(live) > 1:
                out.append({"as_of": str(as_of)[:10], "field": field, "conflict": sorted(live)})
                continue
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
        "segment_shares": _segment_points(conn, ticker, today=today),
        "source": "engine_c：price_history＋fundamental_history（SEC companyfacts）",
    }
    for metric, key in _METRIC_KEYS.items():
        inp[key] = _rows(conn, ticker, metric)
    if ticker.endswith((".TW", ".TWO")):
        from engine_c.history import tw_shares_as_of

        mr = monthly_revenue_as_of(conn, ticker, as_of=today)
        shares = tw_shares_as_of(conn, ticker, as_of=today)
        inp.update(filer_class="taiwan_monthly", revenue_kind="monthly", monthly_revenue=mr["months"],
                   monthly_conflicts=mr["conflicts"], shares_cover=shares["cover"], shares_rejected=shares["rejected"],
                   source=("engine_c：price_history＋monthly_revenue_observations（MOPS 月營收）"
                           "＋tw_share_capital_observations（MOPS 季報股本）"))
        # 股數＝當時已知的季報股本（可知日＝法定期限，`engine_c.tw_share_capital`）。一筆可用的都沒有時，
        # 市值序列組不出來，已定價①整列缺席——仍然不用今天的股數回推。
        if not shares["cover"]:
            bad = len(shares["rejected"])
            inp["gate"] = {"absence_kind": "upstream_unavailable",
                           "reason": ("台股季報股數還沒有可用的觀測（`python -m engine_c.tw_share_capital --backfill 14`）"
                                      + (f"；交叉核對沒過或同季衝突 {bad} 筆" if bad else "")
                                      + "——市值序列組不出來，不用今天的股數回推")}
        return inp
    klass, basis = filer_class(conn, ticker, today=today)
    inp["filer_class"] = klass
    inp["filer_basis"] = basis
    inp["monthly_revenue"] = []
    if klass in ("jp_semiannual", "kr_quarterly"):
        # 日韓（2026-10-21，使用者「日韓 AAA」）：期末附近分割的那一期股數不用（6594.T 實測），計數印在稽核區
        kept, rejected = split_near_period_end(inp["shares_cover"], inp["splits"])
        inp["shares_cover"] = kept
        if rejected:
            inp["shares_rejected"] = rejected
    if klass == "domestic_quarterly":
        inp["revenue_kind"] = "quarterly"
    elif klass == "foreign_annual":
        inp["revenue_kind"] = "annual"
    elif klass == "jp_semiannual":
        inp.update(revenue_kind="semiannual", source="engine_c：price_history＋fundamental_history（EDINET）",
                   shares_basis="期末發行（議決権の状況）−自己保有株式；相互保有與信託持有不扣")
    elif klass == "kr_quarterly":
        inp.update(revenue_kind="quarterly", source="engine_c：price_history＋fundamental_history（OpenDART）",
                   shares_basis="只算普通股（OpenDART 股式總數現況 distb_stock_co＝發行−庫藏；優先股不加）")
    else:
        inp["revenue_kind"] = "none"
        has_rows = any(inp[k] for k in _METRIC_KEYS.values())
        if ticker.endswith(_JP_SUFFIXES + _KR_SUFFIXES):
            japan = ticker.endswith(_JP_SUFFIXES)
            module, registry = ("edinet_history", "EDINET") if japan else ("dart_history", "OpenDART")
            reason = ("最近 18 個月沒有可用的 EDINET／OpenDART 定期申報（或回填落後、這一輪沒寫）——沒有可用的財報歷史"
                      if has_rows else
                      f"{'日本' if japan else '韓國'}申報人：{registry} 回填還沒跑或這一檔沒有可用的定期報告"
                      f"（python -m engine_c.{module} --backfill --ticker {ticker}）——不是歷史不可得")
            inp["no_series_reason"] = reason
        elif has_rows or "." not in ticker:
            reason = "companyfacts 這一檔最近 18 個月沒有 10-Q／20-F（或回填時落後、這一輪沒寫）——沒有可用的財報歷史"
        else:
            reason = "非美國 SEC 申報人、非台股、非日韓：這個市場的機械財報來源還沒接（不是歷史不可得）"
            inp["no_series_reason"] = reason
        inp["gate"] = {"absence_kind": "upstream_unavailable", "reason": reason}
    return inp


__all__ = ["SPLIT_NEAR_PERIOD_END_DAYS", "get_three_question_inputs", "split_near_period_end"]
