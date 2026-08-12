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


def test_theme_core_companies_join_tracked_universe() -> None:
    """2026-08-12 迴歸：COHR／LITE 已列為 cpo 主題核心公司、EDGAR watch 也在抓它們的
    filing，卻因為沒有 active cohort 而在 pq1 排序上等於未追蹤——harvest 花錢抓進來、
    排序又把它壓下去，是兩個 authority 互相矛盾。
    """
    from engine_b.routine_config import theme_core_tickers

    core = theme_core_tickers()
    assert {"COHR", "LITE"} <= core, "themes.txt 的核心公司必須進入 tracked universe"
