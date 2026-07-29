"""The Engine C MCP surface is narrow, read-only, and policy-derived."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from engine_c.db import _ensure_sqlite_schema, upsert_coverage_observation
from engine_c import db as engine_db
from mcp_server.engine_c_tools import get_financial_checklist_core
from mcp_server import graph_mcp


def _checklist(ticker: str) -> dict:
    return {
        "ticker": ticker,
        "engine_c_available": True,
        "items": {
            "gross_margin_trend": {"status": "ok", "value": [["2026-07-16", .4]]},
            "customer_concentration": {"status": "manual_reviewed", "value": "42%"},
            "backlog": {"status": "manual_reviewed", "value": "12 months"},
            "dilution": {"status": "ok", "value": [["2026-07-16", 100]]},
            "valuation_pressure": {"status": "ok", "value": {"pe_forward": 20}},
        },
        "gate_pass": True,
    }


def _database(path: Path, *, count: int | None = 9) -> None:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    upsert_coverage_observation(
        conn,
        {
            "ticker": "COHR",
            "observation_date": date(2026, 7, 16),
            "analyst_count": count,
            "source": "yfinance.info.numberOfAnalystOpinions",
            "data_status": "observed" if count is not None else "manual_required",
            "fetched_at": datetime(2026, 7, 16, tzinfo=timezone.utc),
        },
    )
    conn.close()


def _factory(path: Path):
    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    return connect


def _policy(threshold: int) -> dict:
    return {
        "policy_version": f"threshold-{threshold}",
        "single_position_nav_cap": .05,
        "minimum_open_conviction": 3,
        "conviction_coefficients": {"3": .08, "4": .10, "5": .15},
        "analyst_coverage_threshold": threshold,
        "analyst_coverage_discount_levels": 1,
        "minimum_holding_days": 90,
    }


def test_financial_tool_returns_five_items_raw_coverage_and_policy_view(tmp_path: Path) -> None:
    db = tmp_path / "engine.db"
    _database(db)

    result = get_financial_checklist_core(
        "cohr",
        checklist_getter=_checklist,
        connection_factory=_factory(db),
        sqlite_path=db,
        policy=_policy(8),
    )

    assert len(result["items"]) == 5
    assert result["raw_coverage_observation"]["analyst_count"] == 9
    assert result["policy_view"]["coverage_status"] == "threshold_met"
    assert result["policy_view"]["policy_version"] == "threshold-8"
    assert "crowding" not in json.dumps(result)


def test_policy_threshold_changes_view_without_mutating_row(tmp_path: Path) -> None:
    db = tmp_path / "engine.db"
    _database(db)

    low = get_financial_checklist_core(
        "COHR", checklist_getter=_checklist, connection_factory=_factory(db),
        sqlite_path=db, policy=_policy(8)
    )
    high = get_financial_checklist_core(
        "COHR", checklist_getter=_checklist, connection_factory=_factory(db),
        sqlite_path=db, policy=_policy(12)
    )
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT analyst_count, source FROM consensus_coverage_observations"
    ).fetchone()
    conn.close()

    assert low["policy_view"]["coverage_status"] == "threshold_met"
    assert high["policy_view"]["coverage_status"] == "below_threshold"
    assert row == (9, "yfinance.info.numberOfAnalystOpinions")


def test_missing_ticker_data_is_explicit_and_not_fabricated(tmp_path: Path) -> None:
    db = tmp_path / "engine.db"
    _database(db)

    def missing(ticker):
        return {
            "ticker": ticker,
            "engine_c_available": True,
            "items": {name: {"status": "missing", "value": None} for name in range(5)},
            "gate_pass": False,
            "note": "no snapshot",
        }

    result = get_financial_checklist_core(
        "NONE", checklist_getter=missing, connection_factory=_factory(db),
        sqlite_path=db, policy=_policy(8)
    )

    assert result["gate_pass"] is False
    assert result["raw_coverage_observation"] is None
    assert result["policy_view"]["coverage_status"] == "unknown"
    assert "尚無" in result["coverage_note"]


def test_manual_required_row_never_becomes_a_verified_policy_count(
    tmp_path: Path, monkeypatch
) -> None:
    db = tmp_path / "engine.db"
    _database(db)
    monkeypatch.setattr(
        engine_db,
        "get_latest_coverage_observation",
        lambda _conn, _ticker: {
            "ticker": "COHR",
            "analyst_count": 99,
            "data_status": "manual_required",
        },
    )

    result = get_financial_checklist_core(
        "COHR", checklist_getter=_checklist, connection_factory=_factory(db),
        sqlite_path=db, policy=_policy(8)
    )

    assert result["policy_view"]["coverage_status"] == "unknown"


def test_missing_sqlite_file_returns_readable_error_without_creation(tmp_path: Path) -> None:
    missing = tmp_path / "missing.db"

    result = get_financial_checklist_core(
        "COHR",
        checklist_getter=lambda ticker: (_ for _ in ()).throw(AssertionError()),
        connection_factory=lambda: (_ for _ in ()).throw(AssertionError()),
        sqlite_path=missing,
        policy=_policy(8),
    )

    assert result["engine_c_available"] is False
    assert "不存在" in result["note"]
    assert not missing.exists()


def test_graph_mcp_wrapper_serializes_core_result(monkeypatch) -> None:
    monkeypatch.setattr(
        graph_mcp,
        "get_financial_checklist_core",
        lambda ticker: {"ticker": ticker, "items": {}, "policy_view": {"policy_version": "v1"}},
    )

    result = json.loads(graph_mcp.get_financial_checklist("SIVE.ST"))

    assert result["ticker"] == "SIVE.ST"
    assert result["policy_view"]["policy_version"] == "v1"
