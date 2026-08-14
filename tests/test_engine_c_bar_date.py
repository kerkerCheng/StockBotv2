"""`snapshot_date` 與 `bar_date` 是兩種語意，不得再壓在同一欄。

2026-08-13 查證：`snapshot_date` 存的是**跑 ETL 的當地日期**，不是行情交易日。
收盤後跑的批次被標成隔天（`fetched_at` 07-28 22:34 取到 07-28 收盤 42.76，
卻標 `snapshot_date=07-29`），盤中跑的存的是盤中價。一個欄位承載三種語意（L12），
任何拿它當 as-of 的消費者都系統性差一天，point-in-time 重建全部失準。
"""
from __future__ import annotations

import sqlite3

from engine_c.db import _ensure_sqlite_schema, upsert_snapshot
from engine_c.etl_yfinance import _bar_identity

# upsert_snapshot 的契約是收完整 snapshot dict（ETL 產出的形狀）；
# 這裡補齊其餘欄位，而不是為了測試放寬 production 契約。
_NUMERIC_FIELDS = (
    "gross_margin", "operating_margin", "revenue_ttm", "shares_outstanding",
    "cash_and_equivalents", "total_debt", "free_cash_flow_ttm", "ev_revenue",
    "pe_trailing", "pe_forward", "analyst_target_mean", "analyst_target_high",
    "analyst_target_low", "analyst_target_count",
)


def _snapshot(**over) -> dict:
    row = {field: None for field in _NUMERIC_FIELDS}
    row.update(
        ticker="AXTI",
        snapshot_date="2026-08-14",
        price=77.45,
        fetched_at="2026-08-14T02:00:00+00:00",
    )
    row.update(over)
    return row


def test_bar_date_comes_from_provider_quote_time_not_local_date() -> None:
    """收盤後跑：regularMarketTime 落在交易日，本機日期已翻頁。"""
    # 2026-08-13 16:00:01 America/New_York（收盤後），本機可能已是 08-14。
    info = {
        "regularMarketTime": 1786651201,
        "exchangeTimezoneName": "America/New_York",
        "marketState": "PREPRE",
    }
    assert _bar_identity(info) == ("2026-08-13", "close")


def test_intraday_run_is_labelled_intraday() -> None:
    """盤中跑存的是盤中價——它不是任何交易日的收盤，下游必須分得出來。"""
    info = {
        "regularMarketTime": 1786651201,
        "exchangeTimezoneName": "America/New_York",
        "marketState": "REGULAR",
    }
    bar_date, kind = _bar_identity(info)
    assert bar_date == "2026-08-13"
    assert kind == "intraday"


def test_missing_provider_fields_fail_closed_to_none() -> None:
    """導不出就誠實回 None——NULL 表示「as-of 未知」，不猜。

    「不採 provider 推斷」是報價單位那條路教過的錯誤（AGENTS.md）。
    """
    for info in (
        {},
        {"regularMarketTime": 1786651201},                      # 缺時區
        {"exchangeTimezoneName": "America/New_York"},           # 缺時間
        {"regularMarketTime": "not-an-epoch", "exchangeTimezoneName": "America/New_York"},
        {"regularMarketTime": True, "exchangeTimezoneName": "America/New_York"},
    ):
        assert _bar_identity(info) == (None, None)


def test_schema_migration_adds_columns_and_leaves_existing_rows_null() -> None:
    """既有列一律留 NULL：它們的 as-of 真的不可知，補值等於用猜測冒充事實。"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # 先建一個「舊版」表（沒有新欄位），再跑 migration。
    conn.execute(
        "CREATE TABLE financial_snapshots ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT NOT NULL,"
        " snapshot_date TEXT NOT NULL, price REAL,"
        " fetched_at TEXT NOT NULL DEFAULT (datetime('now')),"
        " UNIQUE (ticker, snapshot_date))"
    )
    conn.execute(
        "INSERT INTO financial_snapshots (ticker, snapshot_date, price, fetched_at)"
        " VALUES ('AXTI', '2026-07-29', 42.76, '2026-07-28T22:34:08')"
    )
    _ensure_sqlite_schema(conn)

    columns = {row[1] for row in conn.execute("PRAGMA table_info(financial_snapshots)")}
    assert {"bar_date", "price_kind"} <= columns

    row = conn.execute("SELECT * FROM financial_snapshots WHERE ticker='AXTI'").fetchone()
    assert row["bar_date"] is None
    assert row["price_kind"] is None
    # 這一列正是那個一天偏差的實例：fetched 07-28 晚間、標成 07-29。
    assert row["snapshot_date"] == "2026-07-29"
    conn.close()


def test_new_rows_persist_bar_date_and_price_kind() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    upsert_snapshot(conn, _snapshot(bar_date="2026-08-13", price_kind="close"))
    row = conn.execute("SELECT * FROM financial_snapshots WHERE ticker='AXTI'").fetchone()
    assert row["snapshot_date"] == "2026-08-14", "ETL 執行日"
    assert row["bar_date"] == "2026-08-13", "真正的行情交易日"
    assert row["price_kind"] == "close"
    conn.close()


def test_snapshot_without_bar_date_still_writes() -> None:
    """provider 導不出 bar_date 時不得讓整筆 snapshot 寫不進去——缺 as-of 只是降級。"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    upsert_snapshot(conn, _snapshot(ticker="IQE.L", price=50.3))
    row = conn.execute("SELECT * FROM financial_snapshots WHERE ticker='IQE.L'").fetchone()
    assert row["price"] == 50.3
    assert row["bar_date"] is None
    conn.close()
