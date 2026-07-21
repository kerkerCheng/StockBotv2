from __future__ import annotations

import sqlite3

from engine_c.checklist import get_probe_financial_baseline
from engine_c.db import _ensure_sqlite_schema, upsert_snapshot
from engine_c.etl_yfinance import fetch_snapshot


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    return conn


def test_sqlite_schema_and_upsert_preserve_runway_scalars() -> None:
    conn = _conn()
    columns = {row[1] for row in conn.execute("PRAGMA table_info(financial_snapshots)")}
    assert {
        "cash_and_equivalents",
        "total_debt",
        "free_cash_flow_ttm",
    } <= columns

    snapshot = {
        "ticker": "SIVE.ST",
        "snapshot_date": "2026-07-21",
        "gross_margin": 0.4,
        "operating_margin": -0.1,
        "revenue_ttm": 100,
        "shares_outstanding": 10,
        "cash_and_equivalents": 120.0,
        "total_debt": 20.0,
        "free_cash_flow_ttm": -60.0,
        "ev_revenue": 2.0,
        "pe_trailing": None,
        "pe_forward": None,
        "price": 2.5,
        "analyst_target_mean": None,
        "analyst_target_high": None,
        "analyst_target_low": None,
        "analyst_target_count": None,
        "fetched_at": "2026-07-21T01:00:00+00:00",
    }
    upsert_snapshot(conn, snapshot)

    baseline = get_probe_financial_baseline("SIVE.ST", conn=conn)
    assert baseline["status"] == "observed"
    assert baseline["cash_and_equivalents"] == 120.0
    assert baseline["free_cash_flow_ttm"] == -60.0
    assert baseline["source"] == "yfinance.info"


def test_yfinance_snapshot_reads_runway_inputs(monkeypatch) -> None:
    class FakeTicker:
        info = {
            "regularMarketPrice": 2.5,
            "totalCash": 120,
            "totalDebt": 20,
            "freeCashflow": -60,
        }

    class FakeYFinance:
        @staticmethod
        def Ticker(_ticker):
            return FakeTicker()

    monkeypatch.setattr("engine_c.etl_yfinance.yf", FakeYFinance())
    snapshot = fetch_snapshot("SIVE.ST")

    assert snapshot["cash_and_equivalents"] == 120
    assert snapshot["total_debt"] == 20
    assert snapshot["free_cash_flow_ttm"] == -60


def test_missing_runway_scalar_is_manual_required() -> None:
    conn = _conn()
    conn.execute(
        """
        INSERT INTO financial_snapshots (
            ticker, snapshot_date, cash_and_equivalents,
            total_debt, free_cash_flow_ttm, fetched_at
        ) VALUES ('SIVE.ST', '2026-07-21', NULL, 20, -60, '2026-07-21T01:00:00+00:00')
        """
    )
    conn.commit()

    baseline = get_probe_financial_baseline("SIVE.ST", conn=conn)
    assert baseline["status"] == "manual_required"
    assert baseline["cash_and_equivalents"] is None
