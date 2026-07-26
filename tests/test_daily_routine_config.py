from __future__ import annotations

import json

import pytest

from engine_b import routine_config


def _write(path, payload) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_config_owns_daily_drain_limit(tmp_path) -> None:
    path = tmp_path / "daily.json"
    _write(path, {
        "schema_version": "1",
        "pq1": {
            "drain_limit_per_run": 2,
            "tracked_ticker_sources": {
                "thesis_lifecycle": True,
                "decision_cohorts": True,
            },
        },
    })

    assert routine_config.load_config(path)["pq1"]["drain_limit_per_run"] == 2


def test_config_rejects_unbounded_daily_drain(tmp_path) -> None:
    path = tmp_path / "daily.json"
    _write(path, {
        "schema_version": "1",
        "pq1": {
            "drain_limit_per_run": 0,
            "tracked_ticker_sources": {
                "thesis_lifecycle": True,
                "decision_cohorts": True,
            },
        },
    })

    with pytest.raises(ValueError, match="1..20"):
        routine_config.load_config(path)


def test_tracked_tickers_merge_lifecycle_and_nonterminal_cohorts(tmp_path) -> None:
    lifecycle = tmp_path / "lifecycle.json"
    _write(lifecycle, {
        "a": {"status": "active", "ticker": "COHR"},
        "b": {"status": "retired", "ticker": "OLD"},
    })
    rows = [
        {"research_ticker": "NVDA", "lifecycle_status": "shadow"},
        {"research_ticker": "DONE", "lifecycle_status": "promoted"},
    ]

    assert routine_config.lifecycle_tickers(lifecycle) == frozenset({"COHR"})
    assert routine_config.cohort_tickers(rows) == frozenset({"NVDA"})
