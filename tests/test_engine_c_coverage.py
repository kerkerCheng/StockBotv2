"""Engine C persists coverage observations, never policy classifications."""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone

from engine_c.db import (
    _ensure_sqlite_schema,
    get_latest_coverage_observation,
    upsert_coverage_observation,
)
from engine_c.etl_yfinance import coverage_observation_from_snapshot, fetch_snapshot


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
