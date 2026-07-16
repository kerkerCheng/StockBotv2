"""Engine C persists coverage observations, never policy classifications."""
from __future__ import annotations

import sqlite3
import sys
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from engine_c.db import (
    _ensure_sqlite_schema,
    get_latest_coverage_observation,
    upsert_coverage_observation,
)
from engine_c.etl_yfinance import (
    coverage_observation_from_snapshot,
    fetch_snapshot,
    main,
    run_etl,
)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    return conn


def _snapshot(count):
    return {
        "ticker": "COHR",
        "snapshot_date": date(2026, 7, 16),
        "analyst_target_count": count,
        "fetched_at": datetime(2026, 7, 16, tzinfo=timezone.utc),
    }


def test_coverage_value_is_stored_as_raw_observation() -> None:
    observation = coverage_observation_from_snapshot(_snapshot(9))
    conn = _conn()

    upsert_coverage_observation(conn, observation)
    stored = get_latest_coverage_observation(conn, "COHR")

    assert stored["analyst_count"] == 9
    assert stored["data_status"] == "observed"
    assert stored["source"] == "yfinance.info.numberOfAnalystOpinions"
    assert "crowding" not in stored


def test_missing_field_becomes_manual_required_observation() -> None:
    observation = coverage_observation_from_snapshot(_snapshot(None))
    conn = _conn()

    upsert_coverage_observation(conn, observation)
    stored = get_latest_coverage_observation(conn, "COHR")

    assert stored["analyst_count"] is None
    assert stored["data_status"] == "manual_required"


def test_same_day_rerun_is_idempotent() -> None:
    conn = _conn()

    upsert_coverage_observation(conn, coverage_observation_from_snapshot(_snapshot(None)))
    upsert_coverage_observation(conn, coverage_observation_from_snapshot(_snapshot(9)))

    count = conn.execute("SELECT COUNT(*) FROM consensus_coverage_observations").fetchone()[0]
    stored = get_latest_coverage_observation(conn, "COHR")
    assert count == 1
    assert stored["analyst_count"] == 9
    assert stored["data_status"] == "observed"


def test_yfinance_field_is_read_when_available(monkeypatch) -> None:
    class FakeTicker:
        info = {
            "regularMarketPrice": 91.0,
            "numberOfAnalystOpinions": 7,
        }

    class FakeYFinance:
        @staticmethod
        def Ticker(ticker):
            assert ticker == "COHR"
            return FakeTicker()

    monkeypatch.setattr("engine_c.etl_yfinance.yf", FakeYFinance())

    snapshot = fetch_snapshot("COHR")

    assert snapshot["analyst_target_count"] == 7
    assert coverage_observation_from_snapshot(snapshot)["data_status"] == "observed"


def test_non_finite_current_price_falls_back_to_regular_market_price(monkeypatch) -> None:
    class FakeTicker:
        info = {"currentPrice": float("nan"), "regularMarketPrice": 91.0}

    class FakeYFinance:
        @staticmethod
        def Ticker(_ticker):
            return FakeTicker()

    monkeypatch.setattr("engine_c.etl_yfinance.yf", FakeYFinance())

    assert fetch_snapshot("COHR")["price"] == 91.0


def test_manual_required_observation_cannot_carry_a_count() -> None:
    conn = _conn()
    observation = coverage_observation_from_snapshot(_snapshot(None))
    observation["analyst_count"] = 9

    with pytest.raises(ValueError, match="must not include"):
        upsert_coverage_observation(conn, observation)


def test_snapshot_and_coverage_write_roll_back_together(monkeypatch) -> None:
    class NoCloseConnection(sqlite3.Connection):
        def close(self):
            pass

    conn = sqlite3.connect(":memory:", factory=NoCloseConnection)
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    conn.execute(
        """
        CREATE TRIGGER reject_coverage BEFORE INSERT ON consensus_coverage_observations
        BEGIN SELECT RAISE(ABORT, 'coverage rejected'); END
        """
    )
    snap = {
        **_snapshot(9),
        "gross_margin": .4,
        "operating_margin": .2,
        "revenue_ttm": 100,
        "shares_outstanding": 10,
        "ev_revenue": 2,
        "pe_trailing": 10,
        "pe_forward": 9,
        "price": 20,
        "analyst_target_mean": 21,
        "analyst_target_high": 22,
        "analyst_target_low": 18,
    }
    monkeypatch.setattr("engine_c.etl_yfinance.get_conn", lambda: conn)
    monkeypatch.setattr("engine_c.etl_yfinance.fetch_snapshot", lambda _ticker: snap)

    assert run_etl(["COHR"]) == 0
    assert conn.execute("SELECT COUNT(*) FROM financial_snapshots").fetchone()[0] == 0


def test_postgres_connection_uses_bounded_timeout(monkeypatch) -> None:
    calls = []
    fake = SimpleNamespace(
        connect=lambda *args, **kwargs: calls.append((args, kwargs)) or object()
    )
    monkeypatch.setitem(sys.modules, "psycopg2", fake)
    monkeypatch.setenv("POSTGRES_DSN", "postgresql://example/stockbot")
    monkeypatch.setenv("POSTGRES_CONNECT_TIMEOUT", "7")

    from engine_c import db

    db.get_conn()

    assert calls == [(("postgresql://example/stockbot",), {"connect_timeout": 7})]


def test_etl_cli_returns_nonzero_when_an_intended_write_fails(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["etl_yfinance.py", "COHR"])
    monkeypatch.setattr("engine_c.etl_yfinance.run_etl", lambda *_args, **_kwargs: 0)

    assert main() == 1


def test_schema_has_no_persisted_crowding_column() -> None:
    conn = _conn()
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(consensus_coverage_observations)")
    }

    assert "crowding" not in columns
    assert columns == {
        "id",
        "ticker",
        "observation_date",
        "analyst_count",
        "source",
        "data_status",
        "fetched_at",
    }
