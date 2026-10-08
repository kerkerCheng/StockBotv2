"""需求錨序列（個股頁 S3a，2026-10-08；`alpha/demand_anchor.py`）。

守五件事：
1. 加總型（雲端四大）只在**每一家同一曆季都申報了**才有那一季；缺誰照寫（半套加總不得出現）。
2. 時點（INV-6）：as-of T 只用 `filed ≤ T`；可知日＝每一家最早申報日取最晚的、版本日＝值用的那一版（隔年比較欄重列時是隔年）。
3. 曆季對齊：期末離曆季末 ±10 天內才歸季；會計季（NVIDIA）走單一型、不與曆季相加。幣別不是宣告的那一種不換算。
4. 年增只在前一年同一季也有值時算。
5. 一頁的錨：走不到錨、題材沒宣告序列、這一輪沒讀到——三種缺席分開（L12）；設定檔形狀錯 fail closed。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date

import pytest

from alpha.demand_anchor import DemandAnchorError, calendar_quarter, page_anchor, series_keys_for
from alpha.providers.demand_anchor import anchor_context, build_series, load_config
from engine_c import history_backfill as hb

CONFIG = {
    "series": {
        "capex4": {"label": "雲端四大現金資本支出", "metric": "capex_quarter",
                   "components": ["co:a", "co:b"], "aggregation": "sum_calendar_quarter", "currency": "USD"},
        "nv": {"label": "NVIDIA 營收", "metric": "revenue_quarter", "components": ["co:n"],
               "aggregation": "single", "currency": "USD"},
    },
    "anchors": {"tech:ai_switch": ["capex4", "nv"]},
}


class _Company:
    def __init__(self, ticker):
        self.research_ticker = ticker


class _Registry:
    def __init__(self, table):
        self.table = table

    def company(self, company_id):
        ticker = self.table.get(company_id)
        return _Company(ticker) if ticker else None


REGISTRY = _Registry({"co:a": "AAA", "co:b": "BBB", "co:n": "NNN"})


def _conn(rows):
    conn = sqlite3.connect(":memory:")
    hb.ensure_history_schema(conn)
    for r in rows:
        conn.execute("INSERT INTO fundamental_history (ticker, metric, period_start, period_end, filed, accession, form, "
                     "value, currency, unit_scale, derived, tag, source, fetched_at) VALUES (?,?,?,?,?,?,?,?,?,1,?,?,?,?)",
                     (r["ticker"], r.get("metric", "capex_quarter"), r.get("start"), r["end"], r["filed"], r["accn"],
                      r.get("form", "10-Q"), r["value"], r.get("currency", "USD"), r.get("derived"), "us-gaap:X", "edgar",
                      "2026-10-08T00:00:00+00:00"))
    return conn


def _q(ticker, end, value, filed, accn, **kw):
    # 起始日預設＝期末所在曆季的第一天（一般的曆季）；要測「沒有起始日」「14 週的季」的列自己帶 start
    d = date.fromisoformat(end)
    start = date(d.year, 3 * ((d.month - 1) // 3) + 1, 1).isoformat()
    return {"ticker": ticker, "end": end, "value": value, "filed": filed, "accn": accn, "start": start, **kw}


BASE = [
    _q("AAA", "2025-06-30", 10.0, "2025-07-29", "A-Q2-25"), _q("BBB", "2025-06-30", 20.0, "2025-07-31", "B-Q2-25"),
    _q("AAA", "2026-06-30", 15.0, "2026-07-29", "A-Q2-26"), _q("BBB", "2026-06-30", 30.0, "2026-07-31", "B-Q2-26"),
    # 隔年比較欄重列 2025Q2（A 重編成 11）
    _q("AAA", "2025-06-30", 11.0, "2026-07-29", "A-Q2-26"),
]


def test_a_quarter_is_the_sum_only_when_every_component_has_filed_it() -> None:
    conn = _conn(BASE)
    s = build_series(conn, "capex4", CONFIG, as_of=date(2026, 10, 8), registry=REGISTRY)
    by = {p["period"]: p for p in s["points"]}
    assert by["2026Q2"]["value"] == 45.0 and by["2026Q2"]["parts"] == {"AAA": 15.0, "BBB": 30.0}
    assert by["2025Q2"]["value"] == 31.0                     # 用最新版本（A 重編後的 11）
    assert by["2026Q2"]["yoy"] == pytest.approx(45.0 / 31.0 - 1)
    # 可知日＝每家最早申報日取最晚；版本日＝值用的那一版
    assert by["2025Q2"]["known_on"] == "2025-07-31" and by["2025Q2"]["version_on"] == "2026-07-29"
    assert by["2026Q2"]["known_on"] == "2026-07-31" and s["absence"] is None


def test_as_of_between_the_two_filings_the_quarter_is_missing_not_half_summed() -> None:
    conn = _conn(BASE)
    s = build_series(conn, "capex4", CONFIG, as_of=date(2026, 7, 30), registry=REGISTRY)
    assert "2026Q2" not in {p["period"] for p in s["points"]}
    gap = next(g for g in s["gaps"] if g["period"] == "2026Q2")
    assert gap["missing"] == ["BBB"] and "BBB" in gap["reason"]
    # 那一天的 2025Q2 還是原版（A 的 10；重編版 2026-07-29 已申報——取 filed ≤ T 的最新）
    by = {p["period"]: p for p in s["points"]}
    assert by["2025Q2"]["value"] == 31.0 and by["2025Q2"]["version_on"] == "2026-07-29"
    early = build_series(conn, "capex4", CONFIG, as_of=date(2026, 7, 1), registry=REGISTRY)
    assert {p["period"]: p["value"] for p in early["points"]} == {"2025Q2": 30.0}


def test_off_calendar_periods_are_not_bucketed_and_wrong_currency_is_not_converted() -> None:
    rows = BASE + [_q("AAA", "2025-09-30", 12.0, "2025-10-29", "A-Q3"),
                   _q("BBB", "2025-09-30", 22.0, "2025-10-31", "B-Q3", currency="EUR"),
                   _q("AAA", "2025-11-15", 5.0, "2025-12-10", "A-odd")]
    s = build_series(_conn(rows), "capex4", CONFIG, as_of=date(2026, 10, 8), registry=REGISTRY)
    assert "2025Q3" not in {p["period"] for p in s["points"]}
    reasons = " ".join(g["reason"] for g in s["gaps"])
    assert "EUR" in reasons and "不換算" in reasons and "2025-11-15" in reasons


def test_a_fourteen_week_period_or_two_periods_in_one_quarter_are_not_summed() -> None:
    """S3 R2 C2 的對稱面（錨是「吃到多少」的分母）：期末落在曆季末 ±10 天內不夠——14 週的期多一週會把那一季灌大；
    沒有起始日量不出長度；同一家兩個會計期對到同一季不挑一個、不讓後一筆蓋掉前一筆（N6）。那一季缺席、寫是誰、為什麼。
    （真資料 2026-10-08：雲端四大 76 期全是整曆季，這三條今天一筆都不會擋到。）"""
    rows = BASE + [_q("AAA", "2025-10-04", 12.0, "2025-10-29", "A-Q3", start="2025-06-29"),       # 98 天
                   _q("BBB", "2025-09-30", 22.0, "2025-10-31", "B-Q3"),
                   _q("AAA", "2025-12-31", 13.0, "2026-01-29", "A-Q4", start=None),
                   _q("BBB", "2025-12-31", 23.0, "2026-01-31", "B-Q4"),
                   _q("AAA", "2026-03-31", 14.0, "2026-04-29", "A-Q1"), _q("AAA", "2026-03-28", 9.0, "2026-04-30", "A-Q1b",
                                                                            start="2025-12-28"),
                   _q("BBB", "2026-03-31", 24.0, "2026-04-30", "B-Q1")]
    s = build_series(_conn(rows), "capex4", CONFIG, as_of=date(2026, 10, 8), registry=REGISTRY)
    periods = {p["period"] for p in s["points"]}
    assert {"2025Q2", "2026Q2"} <= periods and not periods & {"2025Q3", "2025Q4", "2026Q1"}
    why = {g["period"]: g for g in s["gaps"]}
    assert why["2025Q3"]["missing"] == ["AAA"] and "98 天" in why["2025Q3"]["reason"] and "92 天" in why["2025Q3"]["reason"]
    assert "起始日" in why["2025Q4"]["reason"]
    assert "兩個會計期" in why["2026Q1"]["reason"] and why["2026Q1"]["missing"] == ["AAA"]


def test_a_single_fiscal_quarter_series_keeps_its_own_period_and_year_over_year() -> None:
    rows = [_q("NNN", "2025-07-27", 46.7, "2025-08-27", "N1", metric="revenue_quarter"),
            _q("NNN", "2026-07-26", 96.2, "2026-08-26", "N2", metric="revenue_quarter")]
    s = build_series(_conn(rows), "nv", CONFIG, as_of=date(2026, 10, 8), registry=REGISTRY)
    assert [p["period"] for p in s["points"]] == ["2025-07-27", "2026-07-26"]
    assert s["points"][0]["yoy"] is None and s["points"][1]["yoy"] == pytest.approx(96.2 / 46.7 - 1)


def test_calendar_quarter_mapping_allows_ten_days_only() -> None:
    assert calendar_quarter(date(2026, 6, 30)) == (2026, 2)
    assert calendar_quarter(date(2025, 12, 28)) == (2025, 4)        # 52／53 週制
    assert calendar_quarter(date(2026, 1, 3)) == (2025, 4)
    assert calendar_quarter(date(2026, 7, 26)) is None               # NVIDIA 的會計季：不歸曆季


def test_a_component_missing_from_the_registry_makes_the_whole_series_absent() -> None:
    s = build_series(_conn(BASE), "capex4", CONFIG, as_of=date(2026, 10, 8), registry=_Registry({"co:a": "AAA"}))
    assert s["points"] == [] and s["absence"]["kind"] == "upstream_unavailable" and "co:b" in s["absence"]["reason"]


def test_a_page_says_which_of_three_absences_it_is() -> None:
    ctx = anchor_context(_conn(BASE), as_of=date(2026, 10, 8), config=CONFIG, registry=REGISTRY)
    page = page_anchor(ctx, {"tech:ai_switch": "row"}, {"tech:ai_switch": "Data-center switch"})
    assert [s["key"] for s in page["series"]] == ["capex4", "nv"] and page["absence"] is None
    assert page["anchors"] == [{"node": "tech:ai_switch", "name": "Data-center switch", "basis": "row"}]
    off_chain = page_anchor(ctx, {}, {})
    unmapped = page_anchor(ctx, {"tech:dram_technology": "company"}, {})
    unread = page_anchor({"absence": {"kind": "upstream_unavailable", "reason": "Engine C 讀不到"}}, {"tech:ai_switch": "row"})
    assert off_chain["absence"]["kind"] == "not_yet_recorded" and "走不到" in off_chain["absence"]["reason"]
    assert unmapped["absence"]["kind"] == "not_yet_recorded" and "沒宣告" in unmapped["absence"]["reason"]
    assert unread["absence"]["kind"] == "upstream_unavailable"


def test_a_malformed_config_fails_closed(tmp_path) -> None:
    bad = {"series": {"x": {"metric": "capex_quarter", "components": ["co:a"], "aggregation": "average"}}, "anchors": {}}
    path = tmp_path / "c.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(DemandAnchorError, match="聚合"):
        load_config(path)
    bad = {"series": {}, "anchors": {"tech:x": ["nope"]}}
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(DemandAnchorError, match="不存在"):
        load_config(path)


def test_the_shipped_config_maps_the_ai_anchors_to_the_capex_and_nvidia_series() -> None:
    cfg = load_config()
    assert cfg["series"]["hyperscaler_cash_capex"]["components"] == ["co:microsoft", "co:google", "co:amazon", "co:meta"]
    assert series_keys_for(["tech:ai_switch"], cfg) == ["hyperscaler_cash_capex", "nvidia_revenue"]
    assert series_keys_for(["tech:dram_technology"], cfg) == []
