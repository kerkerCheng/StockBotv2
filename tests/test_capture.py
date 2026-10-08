"""吃到多少（個股頁 S3b，2026-10-08）：歷史匯率（FRED H.10 → `fx_history`）、季均價、台股月營收轉季、EDGAR 季對齊、
營收（美元）÷ 錨。

守六件事：
1. FRED CSV：表頭不對就拒收；`.`（美國假日沒有報價）不是觀測、照實計數；抓不到 raise，不回空清單。
2. 抓哪些幣別從資料導出（營收序列實際出現的非美元幣別）；一個幣別抓不到只記那一個；同一天重抓覆寫（可重建投影）。
3. 時點（INV-6）：日匯率只收「觀測日 + 10 天 ≤ T」（H.10 每週一公布前一週、週一假日延到週二，再留兩天；S3 R2 C1）；
   吃到多少的可知日＝營收、錨、匯率三者最晚，as-of T 時還不可知的那一季不算。
4. 季均價：整季頭尾都要有報價；歐元、英鎊的報價方向（一歐元換幾美元）先換成「一美元換幾單位」；同一天兩個數不挑一個。
5. 公司的季：台股三個月都公告才算一季（可知日＝第三個月的法定期限）；EDGAR 會計季期末不在曆季末 ±10 天內、或期間長度與
   曆季差超過 5 天（14 週的季；S3 R2 C2）、或沒有起始日，就缺席、不估。
6. 營收路從資料判（有月營收走台股路）；缺席分開：沒有加總型的錨／沒有季營收／三者湊不齊。
"""
from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from alpha import capture as cap
from alpha.providers.capture import page_capture
from engine_c import history as eh
from engine_c import history_backfill as hb
from fetchers import fred


# ---------------------------------------------------------------------------
# 1. FRED CSV
# ---------------------------------------------------------------------------

def test_fred_csv_skips_no_quote_days_and_rejects_an_unexpected_header() -> None:
    rows, blanks = fred.parse_csv("observation_date,DEXTAUS\n2026-07-01,31.63\n2026-07-03,.\n2026-07-06,31.70\n", "DEXTAUS")
    assert rows == [(date(2026, 7, 1), 31.63), (date(2026, 7, 6), 31.70)] and blanks == 1
    with pytest.raises(fred.FredUnavailable, match="表頭"):
        fred.parse_csv("<html>error</html>", "DEXTAUS")
    with pytest.raises(fred.FredUnavailable, match="表頭"):
        fred.parse_csv("observation_date,DEXJPUS\n2026-07-01,150\n", "DEXTAUS")


# ---------------------------------------------------------------------------
# 2. fx_history 的寫入
# ---------------------------------------------------------------------------

def _db() -> sqlite3.Connection:
    from engine_c.db import _ensure_sqlite_schema

    conn = sqlite3.connect(":memory:")
    _ensure_sqlite_schema(conn)
    return conn


def _monthly(conn, ticker, month, revenue, deadline, currency="TWD", scale=1000):
    conn.execute("INSERT INTO monthly_revenue_observations (observation_id, ticker, market, company_code, company_name, "
                 "data_month, revenue_current, currency, unit_scale, disclosure_deadline, published_at_basis, source, "
                 "fetched_at, payload_digest, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (f"{ticker}-{month}", ticker, "tpex", ticker[:4], ticker, month, revenue, currency, scale, deadline,
                  "statutory_deadline_only", "test", "2026-10-08T00:00:00+00:00", f"d-{ticker}-{month}",
                  "2026-10-08T00:00:00+00:00"))


def test_only_the_currencies_that_revenue_actually_uses_are_fetched_and_rewrites_are_idempotent() -> None:
    conn = _db()
    _monthly(conn, "3081.TWO", "2026-07", 100, "2026-08-10")
    calls = []

    def fetch(series, *, start):
        calls.append((series, start))
        return [(date(2026, 7, 1), 31.6), (date(2026, 7, 2), 31.7)], 1

    out = hb.backfill_fx(conn, today=date(2026, 10, 8), incremental=False, fetched_at="t", fetch=fetch)
    assert [c[0] for c in calls] == ["DEXTAUS"] and out["TWD"]["rows"] == 2 and out["TWD"]["no_quote_days"] == 1
    hb.backfill_fx(conn, today=date(2026, 10, 8), incremental=False, fetched_at="t", fetch=fetch)
    assert conn.execute("SELECT COUNT(*) FROM fx_history").fetchone()[0] == 2         # 同一天重抓覆寫
    hb.backfill_fx(conn, today=date(2026, 10, 8), incremental=True, fetched_at="t", fetch=fetch)
    assert calls[-1][1] == date(2026, 6, 18)                                            # 增量：最後一筆往回 14 天


def test_one_currency_failing_is_recorded_without_stopping_the_step() -> None:
    conn = _db()
    _monthly(conn, "3081.TWO", "2026-07", 100, "2026-08-10")

    def broken(series, *, start):
        raise fred.FredUnavailable("FRED 取不到")

    out = hb.backfill_fx(conn, today=date(2026, 10, 8), incremental=False, fetched_at="t", fetch=broken)
    assert out["TWD"]["outcome"] == "unavailable" and "取不到" in out["TWD"]["absence"]
    assert hb.fx_currencies_needed(_db()) == []                                          # 沒有非美元營收＝不抓


def test_a_rate_is_only_known_ten_days_after_its_date_even_when_the_monday_release_is_a_holiday() -> None:
    """H.10 每週一公布前一週：週一的匯率下週一才公布；那個週一是聯邦假日就延到週二——2026-01-12 的匯率 01-20 才公布
    （01-19 是 MLK 日）。原本的 7 天會在 01-19 就看到（S3 R2 C1）；上界取 10 天，寧可晚兩天也不偷看。"""
    conn = _db()
    conn.executemany("INSERT INTO fx_history VALUES (?,?,?,?,?,?,?)",
                     [("fred:DEXTAUS", "TWD", "per_usd", d, 31.0, "s", "t")
                      for d in ("2026-01-12", "2026-09-29", "2026-09-30", "2026-10-02")])

    def visible(as_of: date) -> list[str]:
        return [r["obs_date"] for r in eh.fx_daily(conn, "TWD", as_of=as_of)]

    assert "2026-01-12" not in visible(date(2026, 1, 19)) and "2026-01-12" in visible(date(2026, 1, 22))
    assert visible(date(2026, 10, 10))[-2:] == ["2026-09-29", "2026-09-30"]
    # 季均價的可知日用同一個上界（alpha 核心不 import engine_c，所以各寫一份——這裡守兩個數相等）
    assert cap.FX_KNOWN_LAG_DAYS == eh.FX_PUBLICATION_LAG_DAYS


# ---------------------------------------------------------------------------
# 3. 季均價、公司的季、吃到多少（純函式）
# ---------------------------------------------------------------------------

def _days(start: str, end: str, rate: float, quote: str = "per_usd"):
    d0, d1 = date.fromisoformat(start), date.fromisoformat(end)
    out = []
    while d0 <= d1:
        if d0.weekday() < 5:
            out.append({"obs_date": d0.isoformat(), "rate": rate, "quote": quote})
        d0 = date.fromordinal(d0.toordinal() + 1)
    return out


def test_the_quarterly_average_needs_the_whole_quarter_and_normalises_the_quote() -> None:
    q, gaps = cap.quarter_fx(_days("2026-04-01", "2026-06-30", 31.6) + _days("2026-07-01", "2026-07-20", 32.0))
    assert set(q) == {"2026Q2"} and q["2026Q2"]["per_usd"] == pytest.approx(31.6)
    assert q["2026Q2"]["known_on"] == "2026-07-10" and any(g["period"] == "2026Q3" for g in gaps)   # 末筆 06-30 + 10 天
    eur, _ = cap.quarter_fx(_days("2026-04-01", "2026-06-30", 1.25, "usd_per"))
    assert eur["2026Q2"]["per_usd"] == pytest.approx(0.8)                              # 一歐元 1.25 美元 → 一美元 0.8 歐元
    clash = _days("2026-04-01", "2026-06-30", 31.6) + [{"obs_date": "2026-05-04", "rate": 30.0, "quote": "per_usd"}]
    q2, gaps2 = cap.quarter_fx(clash)
    assert "2026Q2" not in q2 and "兩個不同" in gaps2[0]["reason"]
    late_start, gaps3 = cap.quarter_fx(_days("2026-05-01", "2026-06-30", 31.6))       # 季初一個月沒有報價
    assert late_start == {} and "不是整季" in gaps3[0]["reason"]


def test_a_taiwan_quarter_needs_all_three_months_and_is_known_at_the_third_deadline() -> None:
    months = [{"data_month": "2026-04", "revenue": 100, "unit_scale": 1000, "currency": "TWD", "available_on": "2026-05-10"},
              {"data_month": "2026-05", "revenue": 110, "unit_scale": 1000, "currency": "TWD", "available_on": "2026-06-10"},
              {"data_month": "2026-06", "revenue": 120, "unit_scale": 1000, "currency": "TWD", "available_on": "2026-07-10"},
              {"data_month": "2026-07", "revenue": 130, "unit_scale": 1000, "currency": "TWD", "available_on": "2026-08-10"}]
    q, gaps = cap.tw_quarters(months)
    assert q["2026Q2"]["value"] == 330_000 and q["2026Q2"]["known_on"] == "2026-07-10"
    assert "2026Q3" not in q and "8 月、9 月" in gaps[0]["reason"]


def test_a_fiscal_quarter_that_does_not_end_near_a_calendar_quarter_is_not_estimated() -> None:
    rows = [{"period_start": "2026-04-01", "period_end": "2026-06-30", "value": 10.0, "currency": "USD", "filed": "2026-08-14",
             "derived": None},
            {"period_start": "2026-05-03", "period_end": "2026-08-01", "value": 20.0, "currency": "USD", "filed": "2026-08-28",
             "derived": None}]
    q, gaps = cap.fiscal_quarters(rows, {"2026-06-30": "2025-08-15"})
    assert set(q) == {"2026Q2"} and q["2026Q2"]["known_on"] == "2025-08-15"
    assert "2026-08-01" in gaps[0]["reason"] and "不估" in gaps[0]["reason"]


def test_a_fourteen_week_quarter_or_one_without_a_start_is_not_matched_to_the_calendar_quarter() -> None:
    """S3 R2 C2：期末落在曆季末 ±10 天內不夠——14 週的會計季（98 天）多一週營收，會把那一季的「吃到多少」灌大約 7%
    （真資料：KLIC 2025Q3、LRCX 2024Q1、MTSI 2024Q4、FN 2022Q3、FORM 2022Q4）。13 週（91 天）照算；沒有起始日量不出長度也不算。"""
    rows = [{"period_start": "2025-12-28", "period_end": "2026-03-28", "value": 10.0, "currency": "USD", "filed": "2026-05-01"},
            {"period_start": "2026-06-28", "period_end": "2026-10-03", "value": 30.0, "currency": "USD", "filed": "2026-11-01"},
            {"period_end": "2026-12-31", "value": 40.0, "currency": "USD", "filed": "2027-02-01"}]
    q, gaps = cap.fiscal_quarters(rows, {})
    assert set(q) == {"2026Q1"}                                                   # 91 天 vs 曆季 90 天
    why = {g["period"]: g["reason"] for g in gaps}
    assert "98 天" in why["2026Q3"] and "92 天" in why["2026Q3"] and "不估" in why["2026Q3"]
    assert "起始日" in why["2026Q4"]


def test_two_fiscal_periods_in_one_calendar_quarter_are_not_resolved_by_whichever_came_last() -> None:
    """S3 R2 N6：兩個會計期對到同一個曆季（例：改會計年度）——不挑一個、不讓後一筆蓋掉前一筆（INV-3）；第三筆也不收。"""
    rows = [{"period_start": "2026-04-01", "period_end": "2026-06-30", "value": 10.0, "currency": "USD", "filed": "2026-08-01"},
            {"period_start": "2026-03-29", "period_end": "2026-06-27", "value": 11.0, "currency": "USD", "filed": "2026-08-02"},
            {"period_start": "2026-04-03", "period_end": "2026-07-02", "value": 12.0, "currency": "USD", "filed": "2026-08-03"},
            {"period_start": "2026-07-01", "period_end": "2026-09-30", "value": 20.0, "currency": "USD", "filed": "2026-11-01"}]
    q, gaps = cap.fiscal_quarters(rows, {})
    assert set(q) == {"2026Q3"} and q["2026Q3"]["value"] == 20.0
    assert any(g["period"] == "2026Q2" and "兩個會計期" in g["reason"] for g in gaps)


def test_capture_is_revenue_in_dollars_over_the_anchor_and_waits_for_all_three() -> None:
    company = {"2026Q2": {"value": 31_600_000_000.0, "currency": "TWD", "known_on": "2026-07-10"}}
    fx = {"TWD": {"2026Q2": {"per_usd": 31.6, "known_on": "2026-07-07"}}}
    anchor = [{"period": "2026Q2", "value": 100_000_000_000.0, "known_on": "2026-07-31"}]
    out = cap.capture_series(company, fx, anchor, as_of=date(2026, 10, 8))
    p = out["points"][0]
    assert p["revenue_usd"] == pytest.approx(1e9) and p["ratio"] == pytest.approx(0.01)
    assert p["per_billion"] == pytest.approx(1e7) and p["known_on"] == "2026-07-31"
    early = cap.capture_series(company, fx, anchor, as_of=date(2026, 7, 20))
    assert early["points"] == [] and "還不可知" in early["gaps"][0]["reason"]
    no_fx = cap.capture_series(company, {}, anchor, as_of=date(2026, 10, 8))
    assert no_fx["points"] == [] and "沒有 TWD" in no_fx["gaps"][0]["reason"]
    no_anchor = cap.capture_series(company, fx, [], as_of=date(2026, 10, 8))
    assert "錨沒有這一季" in no_anchor["gaps"][0]["reason"]
    # 匯率最晚齊的時候，可知日就是匯率那天（三者取最晚，不漏任何一個）
    fx_last = {"TWD": {"2026Q2": {"per_usd": 31.6, "known_on": "2026-07-09"}}}
    anchor_early = [{"period": "2026Q2", "value": 100_000_000_000.0, "known_on": "2026-07-05"}]
    late = cap.capture_series(company, fx_last, anchor_early, as_of=date(2026, 10, 8))
    assert late["points"][0]["known_on"] == "2026-07-10"                               # 公司 07-10 最晚
    company_early = {"2026Q2": {**company["2026Q2"], "known_on": "2026-07-03"}}
    by_fx = cap.capture_series(company_early, fx_last, anchor_early, as_of=date(2026, 10, 8))
    assert by_fx["points"][0]["known_on"] == "2026-07-09"
    assert cap.capture_series(company_early, fx_last, anchor_early, as_of=date(2026, 7, 8))["points"] == []


# ---------------------------------------------------------------------------
# 4. 一頁（取數＋組）
# ---------------------------------------------------------------------------

DEMAND = {"series": [
    {"key": "nv", "aggregation": "single", "points": [{"period": "2026-07-26", "value": 96e9, "known_on": "2026-08-26"}]},
    {"key": "capex4", "label": "雲端四大現金資本支出", "aggregation": "sum_calendar_quarter",
     "points": [{"period": "2026Q2", "value": 100e9, "known_on": "2026-07-31"}]},
], "absence": None}


def test_a_taiwan_page_takes_the_monthly_path_and_converts_with_the_quarterly_average() -> None:
    conn = _db()
    for month, deadline in (("2026-04", "2026-05-10"), ("2026-05", "2026-06-10"), ("2026-06", "2026-07-10")):
        _monthly(conn, "3081.TWO", month, 10_533_333, deadline)
    conn.executemany("INSERT INTO fx_history VALUES (?,?,?,?,?,?,?)",
                     [("fred:DEXTAUS", "TWD", "per_usd", r["obs_date"], 31.6, "s", "t")
                      for r in _days("2026-04-01", "2026-06-30", 31.6)])
    out = page_capture(conn, "3081.TWO", DEMAND, as_of=date(2026, 10, 8))
    assert out["anchor_key"] == "capex4" and out["revenue_source"].startswith("台股月營收")
    p = out["points"][0]
    assert p["period"] == "2026Q2" and p["per_usd"] == pytest.approx(31.6)
    assert p["revenue_usd"] == pytest.approx(10_533_333 * 3 * 1000 / 31.6)


def test_a_page_says_which_absence_it_is() -> None:
    conn = _db()
    no_revenue = page_capture(conn, "ZZZ", DEMAND, as_of=date(2026, 10, 8))
    assert "沒有季營收" in no_revenue["absence"]["reason"]
    only_fiscal = page_capture(conn, "ZZZ", {"series": [DEMAND["series"][0]], "absence": None}, as_of=date(2026, 10, 8))
    assert "加總型" in only_fiscal["absence"]["reason"]
    unread = page_capture(conn, "ZZZ", {"series": [], "absence": {"kind": "upstream_unavailable", "reason": "讀不到"}},
                          as_of=date(2026, 10, 8))
    assert unread["absence"]["kind"] == "upstream_unavailable"
