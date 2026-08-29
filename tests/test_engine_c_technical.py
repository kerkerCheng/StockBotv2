"""TechnicalObservation math, persistence and degraded refresh are deterministic。"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from decision_lab.beta_policy import load_beta_policy, unique_technical_targets
from engine_c.etl_technical import refresh_technical_observations
from engine_c.technical import (
    _METRIC_COLUMNS,
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
    assert result["drawdown_252"] == pytest.approx(0.0)
    # 單調上漲序列的最新收盤就是 52 週高點，區間位置＝1.0
    assert result["range_percentile_252"] == pytest.approx(1.0)
    assert 0 < result["return_1d"] < result["return_5d"] < result["return_20d"]
    assert result["sma_20"] < result["close_adjusted"]
    assert result["distance_sma_200"] > 0
    assert result["series_digest"]
    assert result["blockers"] == []


def test_momentum_indicators_are_gone_from_the_observation_payload() -> None:
    """RSI／MACD／sma_50_slope_5 於 2026-08-29 隨 beta 技術訊號移除，不再計算也不再寫入。

    只是「不顯示」不夠——它們必須離開輸出路徑，否則下次很容易被換個名字接回來。
    """
    result = _observation()

    for column in ("rsi_14", "macd_line", "macd_signal", "macd_histogram", "macd_histogram_slope", "sma_50_slope_5"):
        assert column not in result, column
        assert column not in _METRIC_COLUMNS, column
    assert "range_percentile_252" in _METRIC_COLUMNS


def test_range_percentile_places_the_close_inside_its_own_52_week_band() -> None:
    """相對水位的主要欄位：0.0＝52 週低點、1.0＝52 週高點，純位置無動能。"""
    rising = _observation(300)
    falling = build_technical_observation(
        benchmark_key="down",
        provider_symbol="DOWN",
        rows=_rows(300, start=200.0, step=-0.2),
        fetched_at=FETCHED,
        source="fixture://down",
    )

    assert rising["range_percentile_252"] == pytest.approx(1.0)
    assert falling["range_percentile_252"] == pytest.approx(0.0)
    assert falling["drawdown_252"] < 0


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
    assert result["return_1d"] is not None
    assert result["return_5d"] is not None
    assert result["return_20d"] is not None
    assert result["drawdown_252"] is None
    assert result["range_percentile_252"] is None
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

    next_session = dict(first)
    next_session["session_date"] = "2026-07-29"
    next_session["fetched_at"] = "2026-07-29T01:00:00+00:00"
    append_technical_observation(conn, next_session)
    assert len(recent_technical_observations(conn, "qqq")) == 2
    conn.close()


def test_sqlite_schema_upgrade_adds_missing_metric_columns_non_destructively() -> None:
    """舊庫缺欄位就地 ALTER 補上；append-only ledger 不做破壞性重建。"""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE technical_observations (benchmark_key TEXT, session_date TEXT, fetched_at TEXT)"
    )

    ensure_technical_schema(conn)

    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(technical_observations)").fetchall()
    }
    assert set(_METRIC_COLUMNS) <= columns
    assert {"return_1d", "return_5d", "return_20d", "range_percentile_252"} <= columns
    conn.close()


def test_refresh_fetches_every_distinct_price_series_once() -> None:
    policy = load_beta_policy()
    calls: list[tuple[str, str]] = []

    def fetcher(key: str, symbol: str):
        calls.append((key, symbol))
        if key == "dram":
            return _observation(100, key=key)
        return _observation(key=key)

    conn = _conn()
    result = refresh_technical_observations(policy=policy, fetcher=fetcher, conn=conn)

    assert len(calls) == len(unique_technical_targets(policy)) == 14
    assert len(set(calls)) == 14
    assert result["status"] == "partial"
    assert result["observed_count"] == 13
    assert conn.execute("SELECT COUNT(*) FROM technical_observations").fetchone()[0] == 14
    conn.close()


def test_refresh_applies_twse_freshness_to_custom_transport() -> None:
    policy = load_beta_policy()

    def fetcher(key: str, symbol: str):
        return _observation(key=key)

    def twse_fetcher():
        return {
            "0050": {
                "code": "0050",
                "session_date": "2026-07-31",
                "close_raw": 102.85,
                "change_raw": 9.35,
                "change_pct": 0.1,
                "source": "fixture://twse",
            },
            "00981A": {
                "code": "00981A",
                "session_date": "2026-07-31",
                "close_raw": 26.13,
                "change_raw": 2.37,
                "change_pct": 0.1,
                "source": "fixture://twse",
            },
            "2330": {
                "code": "2330",
                "session_date": "2026-07-31",
                "close_raw": 2425.0,
                "change_raw": 220.0,
                "change_pct": 0.1,
                "source": "fixture://twse",
            },
        }

    conn = _conn()
    result = refresh_technical_observations(
        policy=policy,
        fetcher=fetcher,
        twse_fetcher=twse_fetcher,
        conn=conn,
    )

    assert result["twse_freshness"]["status"] == "ok"
    tw50 = next(item for item in result["items"] if item["benchmark_key"] == "tw50")
    assert tw50["data_status"] == "quarantined"
    assert tw50["blockers"] == ["technical_session_stale_vs_twse"]
    assert tw50["twse_reference"]["status"] == "provider_lagging"
    stored = latest_technical_status(conn, "tw50")
    assert "_twse_reference" not in stored
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
        **{key: Decimal("1.25") for key in _METRIC_COLUMNS},
        # legacy 動能欄位仍可能出現在舊庫的 SELECT * 結果裡，必須被安靜忽略
        "rsi_14": Decimal("55.0"),
        "macd_histogram": Decimal("0.1"),
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
    assert normalized["return_20d"] == 1.25
    assert normalized["range_percentile_252"] == 1.25
    assert "rsi_14" not in normalized
    assert "macd_histogram" not in normalized
