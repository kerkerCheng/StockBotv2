"""日韓財報來源 S1（2026-10-21；使用者「日韓 AAA」）：半年 TTM、申報人類別、期末附近分割、缺席理由、來源標籤。

守：①日本只有半年與年度申報（2024-04 起沒有 Q1／Q3）——TTM 用最近兩個連續半年、最新一期最多 290 天；②申報人類別從 form 前綴判、
EDGAR 的 builder 不得產生日韓的列；③除權日落在期末前 10 天內的那一期股數整期不用（6594.T 實測）；④日韓沒有列時理由寫「回填還沒跑」，
不是「歷史不可得」；⑤韓國的季營收標籤不得寫成 EDGAR（L18）；⑥美股的季度路徑逐位不變。
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from alpha import three_questions as tq
from engine_c import history_backfill as hb
from engine_c.three_question_inputs import get_three_question_inputs, split_near_period_end

FETCHED = "2026-10-21T00:00:00+00:00"


def _half(end: str, filed: str, value: float, *, start: str, metric="revenue_half", derived=None, accn=None) -> dict:
    return {"ticker": "3110.T", "metric": metric, "period_start": start, "period_end": end, "filed": filed,
            "accession": accn or f"S-{end}", "form": "EDINET-160", "value": value, "currency": "JPY", "unit_scale": 1,
            "derived": derived, "tag": "jppfs_cor:NetSales", "source": hb.SOURCE_EDINET, "fetched_at": FETCHED}


HALVES = [  # FY 4–3 月：H1＝4–9 月（11 月申報）、H2＝10–3 月（年度−H1，6 月有報）
    _half("2024-09-30", "2024-11-12", 50.0, start="2024-04-01"),
    _half("2025-03-31", "2025-06-25", 55.0, start="2024-10-01", derived="FY−H1"),
    _half("2025-09-30", "2025-11-12", 57.4, start="2025-04-01"),
    _half("2026-03-31", "2026-06-25", 60.0, start="2025-10-01", derived="FY−H1"),
]


def test_half_year_ttm_sums_two_consecutive_halves_and_checks_the_gap() -> None:
    value, end, ccy = tq.ttm(HALVES, date(2026, 7, 1), kind="half")
    assert (value, end, ccy) == (117.4, date(2026, 3, 31), "JPY")
    gapped = [HALVES[0], HALVES[3]]                                       # 相鄰期末差一年半：不連續
    assert tq.ttm(gapped, date(2026, 7, 1), kind="half") == (None, None, None)
    assert tq.ttm(HALVES, date(2025, 7, 1), kind="half")[0] == 105.0    # as-of：2025-07 只知道到 2025-03 那一期
    assert tq.ttm(HALVES[:2], date(2026, 7, 1)) == (None, None, None)   # 季度口徑要四期——預設行為不變


def _inp(**over) -> dict:
    bars = [(date(2026, 3, 31) + timedelta(days=n), 100.0) for n in (250, 300)]
    base = {"price_bars": bars, "price_to_settlement": 1.0, "splits": [], "revenue_kind": "semiannual",
            "revenue_halves": HALVES, "shares_cover": [{"period_end": "2026-03-31", "filed": "2026-06-25", "value": 10.0}]}
    base.update(over)
    return base


def test_a_half_year_ttm_is_current_for_290_days_not_200() -> None:
    """最新一期最多 290 天（半年 182＋有報 3 個月＋緩衝）：期末 +250 天有倍數、+300 天沒有。"""
    days = [d for d, _ in tq._multiple_series(_inp(), basis="P/S")]
    assert days == [date(2026, 3, 31) + timedelta(days=250)]


def test_the_half_year_series_is_labelled_edinet_and_kept_for_290_days() -> None:
    today = date(2026, 3, 31) + timedelta(days=250)
    row = tq.in_numbers({**_inp(), "segment_shares": []}, today=today)[0]
    assert row["absence_kind"] is None and row["basis"].startswith("EDINET 半年營收") and "EDGAR" not in row["source"]
    assert row["detail"]["currency"] == "JPY" and row["value"][-1]["yoy"] == pytest.approx(60.0 / 55.0 - 1, abs=1e-4)
    stale = tq.in_numbers({**_inp(), "segment_shares": []}, today=date(2026, 3, 31) + timedelta(days=300))[0]
    assert stale["absence_kind"] == "insufficient_evidence"


def _q(end: str, filed: str, value: float, start: str, source: str) -> dict:
    return {"period_start": start, "period_end": end, "filed": filed, "accession": f"A-{end}", "form": "DART-11013",
            "value": value, "currency": "KRW", "derived": None, "tag": "ifrs-full_Revenue", "source": source}


def test_a_korean_quarterly_series_is_not_labelled_edgar_and_a_us_one_still_is() -> None:
    rows = [_q("2026-03-31", "2026-05-15", 10.0, "2026-01-01", hb.SOURCE_DART),
            _q("2026-06-30", "2026-08-14", 12.0, "2026-04-01", hb.SOURCE_DART)]
    kr = tq.in_numbers({"revenue_kind": "quarterly", "revenue_quarters": rows, "segment_shares": []},
                       today=date(2026, 9, 1))[0]
    assert "EDGAR" not in kr["basis"] and "EDGAR" not in kr["source"] and kr["basis"].startswith("DART")
    us = tq.in_numbers({"revenue_kind": "quarterly", "segment_shares": [],
                        "revenue_quarters": [{**r, "source": hb.SOURCE_EDGAR} for r in rows]}, today=date(2026, 9, 1))[0]
    assert us["basis"] == "EDGAR 季營收（YoY 對同一季）" and us["rule"] == tq._RULE_NUMBERS


@pytest.mark.parametrize("forms, expected", [
    ([("EDINET-160", date(2026, 5, 1))], "jp_semiannual"),
    ([("DART-11012", date(2026, 5, 1))], "kr_quarterly"),
    ([("10-Q", date(2026, 5, 1)), ("DART-11012", date(2026, 6, 1))], "domestic_quarterly"),   # 10-Q 優先
    ([("EDINET-120", date(2024, 1, 1))], "unknown"),                                              # 超過 18 個月
])
def test_the_filer_class_comes_from_the_form_prefix(forms, expected) -> None:
    assert hb.classify_filer(forms, today=date(2026, 10, 21))[0] == expected


def test_the_edgar_builder_refuses_japanese_or_korean_classes() -> None:
    with pytest.raises(hb.HistoryBackfillError, match="EDGAR 的列只認"):
        hb.build_fundamental_rows({"facts": {}}, ticker="3110.T", filer="jp_semiannual", today=date(2026, 10, 21),
                                  fetched_at=FETCHED)


def test_a_split_just_before_period_end_drops_that_periods_shares() -> None:
    """6594.T 實測：除權日 2024-09-27、期末 2024-09-30——期末發行是分割前的 596,284,468（提出日現在已是 1,192,568,936）。"""
    rows = [{"period_end": "2024-03-31", "value": 596_000_000.0, "source": hb.SOURCE_EDINET, "accession": "S1"},
            {"period_end": "2024-09-30", "value": 596_284_468.0, "source": hb.SOURCE_EDINET, "accession": "S100UOHJ"},
            {"period_end": "2024-09-30", "value": 1.0, "source": hb.SOURCE_EDGAR, "accession": "US"}]
    kept, rejected = split_near_period_end(rows, [(date(2024, 9, 27), 2.0)])
    assert [r["accession"] for r in kept] == ["S1", "US"]                  # 只套日韓的列
    assert rejected[0]["status"] == "split_near_period_end" and rejected[0]["observation_id"] == "S100UOHJ"
    # 前一期的股數由 shares_on 乘上分割比例接續（2024-10-01 當天＝分割後）
    assert tq.shares_on([{"period_end": "2024-03-31", "filed": "2024-06-20", "value": 596_000_000.0}],
                        [(date(2024, 9, 27), 2.0)], date(2024, 10, 1)) == 1_192_000_000.0


def _conn() -> sqlite3.Connection:
    from engine_c.db import _ensure_sqlite_schema

    conn = sqlite3.connect(":memory:")
    _ensure_sqlite_schema(conn)
    return conn


def test_japan_and_korea_without_rows_say_the_backfill_has_not_run_not_that_history_is_unavailable() -> None:
    conn = _conn()
    jp = get_three_question_inputs("3110.T", conn=conn, today=date(2026, 10, 21), company_id=None)
    assert jp["filer_class"] == "unknown" and "engine_c.edinet_history --backfill --ticker 3110.T" in jp["gate"]["reason"]
    assert "不是歷史不可得" in jp["gate"]["reason"] and jp["no_series_reason"] == jp["gate"]["reason"]
    kr = get_three_question_inputs("000660.KS", conn=conn, today=date(2026, 10, 21), company_id=None)
    assert "engine_c.dart_history" in kr["gate"]["reason"]
    eu = get_three_question_inputs("IQE.L", conn=conn, today=date(2026, 10, 21), company_id=None)
    assert "非美國" in eu["gate"]["reason"] and "還沒接" in eu["gate"]["reason"]


def test_japanese_rows_make_the_ticker_semiannual_with_the_shares_basis() -> None:
    conn = _conn()
    hb.insert_fundamentals(conn, HALVES)
    jp = get_three_question_inputs("3110.T", conn=conn, today=date(2026, 10, 21), company_id=None)
    assert jp["filer_class"] == "jp_semiannual" and jp["revenue_kind"] == "semiannual" and "gate" not in jp
    assert "EDINET" in jp["source"] and "自己保有株式" in jp["shares_basis"] and len(jp["revenue_halves"]) == 4
