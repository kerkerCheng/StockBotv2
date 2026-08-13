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
                "theme_core_companies": True,
            },
        },
    })

    assert routine_config.load_config(path)["pq1"]["drain_limit_per_run"] == 2


def test_config_fails_closed_on_incomplete_tracked_ticker_sources(tmp_path) -> None:
    """tracked_ticker_sources 的每個來源都必須明示 boolean，不得靠預設值靜默關閉。

    這條先前被 Windows tmp_path 權限問題遮住：整個檔案在 setup 階段就 error，
    於是 2026-08-12 新增 theme_core_companies 時，沒有任何測試指出缺鍵的 config 會失效。
    """
    path = tmp_path / "daily.json"
    _write(path, {
        "schema_version": "1",
        "pq1": {
            "drain_limit_per_run": 2,
            "tracked_ticker_sources": {"thesis_lifecycle": True},
        },
    })

    with pytest.raises(ValueError, match="decision_cohorts"):
        routine_config.load_config(path)


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


def test_us_edgar_candidates_excludes_foreign_issuers() -> None:
    """EDGAR 只有美國註冊人；外國發行人放進 watch 只會每天產生找不到 CIK 的失敗。"""
    from engine_b.routine_config import us_edgar_candidates

    got = us_edgar_candidates(
        {"AAOI", "NVDA", "IQE.L", "SIVE.ST", "2330.TW", "", "  "}
    )
    assert got == frozenset({"AAOI", "NVDA"})


def test_edgar_watch_manual_list_is_a_floor_not_a_replacement() -> None:
    """derivation 只補「已追蹤卻沒 watcher」，不得縮減既有監看。

    上游（lifecycle／Decision store／themes.txt）任一暫時讀不到都會讓 tracked 縮小；
    若採取代語意就會靜默停止監看既有標的，而漏掉的 filing 沒有人會發現。
    """
    from engine_b.routine_config import edgar_watch_tickers

    watch = {"tickers": ["AMAT", "GFS"], "derive_from_tracked": True}

    # 正常：手動 ∪ 導出（外國發行人被排除）
    assert edgar_watch_tickers(
        watch, tracked=frozenset({"NVDA", "SIVE.ST"})
    ) == ["AMAT", "GFS", "NVDA"]

    # 上游全空：不得縮減
    assert edgar_watch_tickers(watch, tracked=frozenset()) == ["AMAT", "GFS"]

    # 未開啟 derivation：維持手動清單
    assert edgar_watch_tickers(
        {"tickers": ["AMAT", "GFS"]}, tracked=frozenset({"NVDA"})
    ) == ["AMAT", "GFS"]
