"""TechnicalObservation math, persistence and degraded refresh are deterministic。"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from decision_lab.beta_policy import load_beta_policy, unique_benchmarks
from engine_c.etl_technical import refresh_technical_observations
from engine_c.technical import (
    append_technical_observation,
    build_technical_observation,
    ensure_technical_schema,
    latest_technical_status,
    recent_technical_observations,
    unavailable_observation,
)
from engine_c.technical import _row_to_observation


FETCHED = "2026-07-28T00:00:00+00:00"


def _rows(count: int, *, start: float = 100.0, step: float = 0.2):
    origin = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return [
        {
            "as_of": (origin + timedelta(days=index)).isoformat(),
            "close_raw": start + step * index,
            "close_adjusted": start + step * index,
            "complete": True,
        }
        for index in range(count)
    ]


def _observation(count: int = 300, *, key: str = "fixture", step: float = 0.2):
    return build_technical_observation(
        benchmark_key=key,
        provider_symbol=key.upper(),
        rows=_rows(count, step=step),
        fetched_at=FETCHED,
        source=f"fixture://{key}",
    )


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_technical_schema(conn)
    return conn


def test_indicator_builder_emits_complete_finite_observation() -> None:
    result = _observation()

    assert result["data_status"] == "observed"
    assert result["session_count"] == 300
    assert result["rsi_14"] == pytest.approx(100.0)
    assert result["drawdown_252"] == pytest.approx(0.0)
    assert result["sma_20"] < result["close_adjusted"]
    assert result["distance_sma_200"] > 0
    assert result["sma_50_slope_5"] > 0
    assert result["macd_line"] > 0
    assert result["series_digest"]
    assert result["blockers"] == []


def test_short_history_and_forming_row_fail_closed_without_hiding_partial_metrics() -> None:
    rows = _rows(251)
    rows.append(
        {
            "as_of": "2026-07-28T00:00:00+08:00",
            "close_raw": 200.0,
            "close_adjusted": 200.0,
            "complete": False,
        }
    )
    result = build_technical_observation(
        benchmark_key="dram",
        provider_symbol="DRAM",
        rows=rows,
        fetched_at=FETCHED,
        source="fixture://dram",
    )

    assert result["data_status"] == "insufficient_history"
    assert result["session_count"] == 251
    assert result["rsi_14"] is not None
    assert result["drawdown_252"] is None
    assert result["blockers"] == ["technical_history_insufficient_252_sessions"]
    assert "forming_session_excluded" in result["warnings"]


def test_missing_adjusted_close_never_falls_back_to_raw_close() -> None:
    rows = _rows(300)
    for row in rows:
        row["close_adjusted"] = None

    result = build_technical_observation(
        benchmark_key="bad",
        provider_symbol="BAD",
        rows=rows,
        fetched_at=FETCHED,
        source="fixture://bad",
    )

    assert result["data_status"] == "unavailable"
    assert result["blockers"] == ["technical_history_missing"]
    assert "technical_history_rows_skipped" in result["warnings"]


def test_append_is_idempotent_and_recent_query_deduplicates_session() -> None:
    conn = _conn()
    first = _observation(key="qqq")

    first_id = append_technical_observation(conn, first)
    assert append_technical_observation(conn, first) == first_id
    assert conn.execute("SELECT COUNT(*) FROM technical_observations").fetchone()[0] == 1

    newer = dict(first)
    newer["fetched_at"] = "2026-07-28T01:00:00+00:00"
    append_technical_observation(conn, newer)
    assert conn.execute("SELECT COUNT(*) FROM technical_observations").fetchone()[0] == 2
    assert len(recent_technical_observations(conn, "qqq")) == 1
    assert latest_technical_status(conn, "qqq")["fetched_at"] == newer["fetched_at"]
    conn.close()


def test_refresh_fetches_each_unique_benchmark_once_and_keeps_partial_results() -> None:
    policy = load_beta_policy()
    calls: list[tuple[str, str]] = []

    def fetcher(key: str, symbol: str):
        calls.append((key, symbol))
        if key == "dram":
            return _observation(100, key=key)
        return _observation(key=key)

    conn = _conn()
    result = refresh_technical_observations(policy=policy, fetcher=fetcher, conn=conn)

    assert len(calls) == len(unique_benchmarks(policy)) == 11
    assert len(set(calls)) == 11
    assert result["status"] == "partial"
    assert result["observed_count"] == 10
    assert conn.execute("SELECT COUNT(*) FROM technical_observations").fetchone()[0] == 11
    conn.close()


def test_unavailable_observation_is_appendable_and_sanitized() -> None:
    conn = _conn()
    result = unavailable_observation(
        benchmark_key="qqq",
        provider_symbol="QQQ",
        fetched_at=FETCHED,
        blocker="technical_history_unavailable",
    )

    append_technical_observation(conn, result)
    stored = latest_technical_status(conn, "qqq")

    assert stored["data_status"] == "unavailable"
    assert stored["blockers"] == ["technical_history_unavailable"]
    conn.close()


def test_postgres_decimal_and_date_rows_normalize_to_public_scalars() -> None:
    raw = {
        "observation_id": "to_x",
        "benchmark_key": "qqq",
        "provider_symbol": "QQQ",
        "session_date": datetime(2026, 7, 27, tzinfo=timezone.utc).date(),
        "session_count": 300,
        "data_status": "observed",
        **{key: Decimal("1.25") for key in (
            "close_raw",
            "close_adjusted",
            "drawdown_252",
            "rsi_14",
            "macd_line",
            "macd_signal",
            "macd_histogram",
            "macd_histogram_slope",
            "sma_20",
            "sma_50",
            "sma_200",
            "distance_sma_20",
            "distance_sma_50",
            "distance_sma_200",
            "sma_50_slope_5",
            "realized_vol_20",
            "realized_vol_60",
        )},
        "source": "fixture://qqq",
        "series_digest": "a" * 64,
        "fetched_at": datetime(2026, 7, 28, tzinfo=timezone.utc),
        "payload_digest": "b" * 64,
        "blockers_json": '{"items":[]}',
        "warnings_json": '{"items":[]}',
    }

    normalized = _row_to_observation(raw)

    assert normalized["session_date"] == "2026-07-27"
    assert normalized["fetched_at"] == "2026-07-28T00:00:00+00:00"
    assert normalized["rsi_14"] == 1.25
