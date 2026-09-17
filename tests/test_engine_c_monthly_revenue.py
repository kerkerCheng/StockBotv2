"""台股月營收：解析、單位、point-in-time 與冪等（ROADMAP Phase 6 / D15）。

守的是四件會靜默出錯的事：
1. 兩個交易所的欄位名不同 → 照單一份鍵名寫死，另一邊會回空集合而不是報錯。
2. 單位是千元 → 差 1000 倍。
3. `出表日期` 不是公告日 → 不得寫進 `published_at`（AGENTS.md 明令）。
4. 重跑不得長出重複列，且 `written` 要回報**真的多了幾列**。
"""
from __future__ import annotations

import sqlite3

import pytest

from engine_c.monthly_revenue import (
    CURRENCY,
    PUBLISHED_AT_BASIS,
    UNIT_SCALE,
    MonthlyRevenueError,
    append_monthly_revenue,
    build_observation,
    disclosure_deadline,
    ensure_monthly_revenue_schema,
    monthly_revenue_series,
)
from fetchers.mops_open_data import (
    MARKETS,
    REVENUE_HISTORY_KINDS,
    _announcement_row,
    _revenue_row,
    company_code,
    market_for_ticker,
    roc_date_to_iso,
    roc_month_to_iso,
    select_tickers,
    ticker_for,
)


TWSE_ROW = {
    "出表日期": "1150916",
    "資料年月": "11508",
    "公司代號": "2455",
    "公司名稱": "全新",
    "產業別": "光電業",
    "營業收入-當月營收": "470904",
    "營業收入-上月營收": "422106",
    "營業收入-去年當月營收": "275126",
    "營業收入-上月比較增減(%)": "11.560603260792313",
    "營業收入-去年同月增減(%)": "71.15939605853318",
    "累計營業收入-當月累計營收": "2817693",
    "累計營業收入-去年累計營收": "2073751",
    "累計營業收入-前期比較增減(%)": "35.87422019326332",
    "備註": "客戶需求增加",
}

#: 上櫃的鍵名是英文，而且**重訊的「主旨」在上市那邊尾端多一個空格**。
TPEX_ANNOUNCEMENT = {
    "Date": "1150917",
    "發言日期": "1150916",
    "發言時間": "70003",
    "SecuritiesCompanyCode": "3105",
    "CompanyName": "穩懋",
    "主旨": "本公司訂購廠務工程公告。",
    "符合條款": "第23款",
    "事實發生日": "1150916",
    "說明": "1.事實發生日：民國115年09月16日",
}
TWSE_ANNOUNCEMENT = dict(TPEX_ANNOUNCEMENT)
del TWSE_ANNOUNCEMENT["SecuritiesCompanyCode"]
del TWSE_ANNOUNCEMENT["CompanyName"]
del TWSE_ANNOUNCEMENT["主旨"]
TWSE_ANNOUNCEMENT["公司代號"] = "3105"
TWSE_ANNOUNCEMENT["公司名稱"] = "穩懋"
TWSE_ANNOUNCEMENT["主旨 "] = "本公司訂購廠務工程公告。"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = None
    ensure_monthly_revenue_schema(conn)
    return conn


def test_roc_dates_convert_to_gregorian() -> None:
    assert roc_date_to_iso("1150917") == "2026-09-17"
    assert roc_month_to_iso("11508") == "2026-08"
    # 不合法一律 None——不猜、不補今天。
    assert roc_date_to_iso("1151317") is None
    assert roc_month_to_iso("11599") is None
    assert roc_month_to_iso("") is None


def test_disclosure_deadline_is_the_tenth_of_next_month() -> None:
    assert disclosure_deadline("2026-08") == "2026-09-10"
    assert disclosure_deadline("2026-12") == "2027-01-10"
    assert disclosure_deadline("亂寫") is None


def test_ticker_and_market_round_trip_via_suffix_only() -> None:
    assert market_for_ticker("3081.TWO") == "tpex"
    assert market_for_ticker("2455.TW") == "twse"
    assert market_for_ticker("AAPL") is None
    assert company_code("3081.TWO") == "3081"
    assert ticker_for("tpex", "3081") == "3081.TWO"
    assert ticker_for("nasdaq", "3081") is None


def test_both_exchanges_field_names_are_parsed() -> None:
    """照單一份鍵名寫死時，另一邊會安靜地回空集合而不是報錯（L13-2）。"""

    twse = _revenue_row(TWSE_ROW, market="twse", source_url="u")
    assert twse is not None
    assert twse["ticker"] == "2455.TW"
    assert twse["revenue_current"] == 470904

    tpex_row = {
        "Date": "1150917",
        "資料年月": "11508",
        "SecuritiesCompanyCode": "3081",
        "CompanyName": "聯亞",
        "營業收入-當月營收": "520469",
    }
    tpex = _revenue_row(tpex_row, market="tpex", source_url="u")
    assert tpex is not None
    assert tpex["ticker"] == "3081.TWO"
    assert tpex["company_name"] == "聯亞"

    # 重訊：上市的欄名是 `主旨 `（尾端一個空格），上櫃是 `主旨`。兩邊都要解得出來。
    for market, row in (("twse", TWSE_ANNOUNCEMENT), ("tpex", TPEX_ANNOUNCEMENT)):
        parsed = _announcement_row(row, market=market, source_url="u")
        assert parsed is not None, market
        assert parsed["subject"] == "本公司訂購廠務工程公告。", market
        assert parsed["spoke_date"] == "2026-09-16", market
        # 發言時間 70003 是 07:00:03，不是 70:00:3。
        assert parsed["spoke_time"] == "07:00:03", market


def test_unit_and_currency_live_on_the_row() -> None:
    observation = build_observation(_revenue_row(TWSE_ROW, market="twse", source_url="u"))
    assert observation["unit_scale"] == UNIT_SCALE == 1000
    assert observation["currency"] == CURRENCY == "TWD"


def test_report_date_never_becomes_published_at() -> None:
    """AGENTS.md：不得用 ingest／retrieval 日期冒充 `published_at`。"""

    observation = build_observation(_revenue_row(TWSE_ROW, market="twse", source_url="u"))
    assert observation["published_at"] is None
    assert observation["published_at_basis"] == "statutory_deadline_only"
    # 出表日期仍然留著，只是住在自己的欄位。
    assert observation["report_date"] == "2026-09-16"
    assert observation["disclosure_deadline"] == "2026-09-10"


def test_unregistered_basis_is_rejected() -> None:
    conn = _conn()
    observation = build_observation(_revenue_row(TWSE_ROW, market="twse", source_url="u"))
    observation["published_at_basis"] = "我猜的"
    with pytest.raises(MonthlyRevenueError):
        append_monthly_revenue(conn, observation)


def test_missing_revenue_is_rejected_not_zeroed() -> None:
    row = dict(TWSE_ROW)
    row["營業收入-當月營收"] = "-"
    parsed = _revenue_row(row, market="twse", source_url="u")
    assert parsed["revenue_current"] is None
    with pytest.raises(MonthlyRevenueError):
        build_observation(parsed)


def test_unresolved_ticker_is_rejected() -> None:
    """INV-1：identity 不猜。代號解析不出來時不得寫入。"""

    parsed = _revenue_row(TWSE_ROW, market="twse", source_url="u")
    parsed["ticker"] = None
    with pytest.raises(MonthlyRevenueError):
        build_observation(parsed)


def test_rerun_is_idempotent() -> None:
    conn = _conn()
    observation = build_observation(_revenue_row(TWSE_ROW, market="twse", source_url="u"))
    first = append_monthly_revenue(conn, observation)
    # fetched_at 不同也不該長出第二列——digest 刻意不含它。
    again = dict(observation)
    again["fetched_at"] = "2027-01-01T00:00:00+00:00"
    second = append_monthly_revenue(conn, again)
    assert first == second
    assert conn.execute("SELECT COUNT(*) FROM monthly_revenue_observations").fetchone()[0] == 1


def test_conflicting_sources_are_reported_not_silently_picked() -> None:
    conn = _conn()
    base = _revenue_row(TWSE_ROW, market="twse", source_url="來源A")
    append_monthly_revenue(conn, build_observation(base))
    other = dict(base)
    other["source_url"] = "來源B"
    other["revenue_current"] = 999999
    append_monthly_revenue(conn, build_observation(other))

    payload = monthly_revenue_series(conn, "2455.TW")
    assert payload["months"] == 1
    assert len(payload["conflicts"]) == 1
    assert sorted(payload["conflicts"][0]["revenue_current"]) == [470904, 999999]


def test_matching_sources_are_not_a_conflict() -> None:
    conn = _conn()
    base = _revenue_row(TWSE_ROW, market="twse", source_url="opendata")
    append_monthly_revenue(conn, build_observation(base))
    other = dict(base)
    other["source_url"] = "歷史頁"
    other["report_date"] = None
    append_monthly_revenue(conn, build_observation(other))

    payload = monthly_revenue_series(conn, "2455.TW")
    assert payload["months"] == 1
    assert payload["conflicts"] == []


def test_filter_report_separates_two_reasons() -> None:
    """INV-3：「沒有你的公司」與「代號解析不出來」壓成一個數字就看不出版型變了。"""

    rows = [
        {"ticker": "3081.TWO"},
        {"ticker": "9999.TWO"},
        {"ticker": None},
    ]
    accepted, report = select_tickers(rows, ["3081.TWO"])
    assert len(accepted) == 1
    assert report == {
        "input": 3,
        "accepted": 1,
        "filtered": 2,
        "filtered_not_watched": 1,
        "filtered_unresolved_ticker": 1,
    }


def test_history_pages_cover_both_registrations() -> None:
    """外國企業（KY 股）住 `_1` 檔。只抓 `_0` 時 4971.TWO 在 24 個月回補裡一筆都沒有。"""

    assert REVENUE_HISTORY_KINDS == ("0", "1")
    assert MARKETS == ("twse", "tpex")


def test_module_import_stays_network_free() -> None:
    """心跳第 1 段會 import 它，而心跳的契約是**零網路**。

    `requests` 只能在 `sync`／`backfill` 的函式內被 import——放到模組層會讓心跳
    在沒有網路套件的環境裡直接死掉，而那是它最該活著的時候。
    """

    source = (
        __import__("pathlib").Path(__file__).resolve().parent.parent
        / "engine_c" / "monthly_revenue.py"
    ).read_text(encoding="utf-8")
    header = source.split("def ", 1)[0]
    assert "import requests" not in header
    assert "from fetchers" not in header
