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
    """無上限仍然不合法——但**「無上限」現在是負數與 >20，不再是 0**。

    ⚠ 2026-09-17（Phase 2 Step 2.2／D12）改了這一條的 0 那一格，理由寫在
    `engine_b/routine_config.py` 的註解：0 原本被拒絕是因為「0 會被讀成無上限」，
    而那是一個表示承載兩種語意（L12）。修法是先分開——0＝研究層關閉、1..20＝每輪上限、
    其餘仍拒絕。**原斷言守的東西（0 不得被讀成無上限）沒有被刪，是被換成更強的那條**：
    `tests/test_engine_b_cli.py::test_drain_limit_zero_selects_nothing_of_every_kind`
    直接證明 limit=0 選不出任何一種工作——原斷言只擋得住寫下 0，擋不住任何一個
    把 limit 當「沒有上限」用的消費端。
    """
    path = tmp_path / "daily.json"
    for bad in (-1, 21, True, 2.5, "5"):
        _write(path, {
            "schema_version": "1",
            "pq1": {
                "drain_limit_per_run": bad,
                "tracked_ticker_sources": {
                    "thesis_lifecycle": True,
                    "decision_cohorts": True,
                },
            },
        })
        with pytest.raises(ValueError, match=r"0\.\.20"):
            routine_config.load_config(path)


def test_zero_means_research_disabled_not_unbounded(tmp_path) -> None:
    """0 合法且逐字讀得回來——D12：研究只在互動 session 做，daily 的研究層關閉。"""
    path = tmp_path / "daily.json"
    _write(path, {
        "schema_version": "1",
        "pq1": {
            "drain_limit_per_run": 0,
            "tracked_ticker_sources": {
                "thesis_lifecycle": True,
                "decision_cohorts": True,
                "theme_core_companies": False,
            },
        },
    })

    assert routine_config.load_config(path)["pq1"]["drain_limit_per_run"] == 0


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


def test_edgar_watch_narrative_and_wait_derivations_each_behind_its_own_flag() -> None:
    """#133（2026-11-07）：現行敘事的美股、還在盯的等待所等的美股各自一個開關併入；外國發行人照舊排除。"""
    from engine_b.routine_config import edgar_watch_tickers

    sources = dict(narratives=frozenset({"MXL", "5801.T"}), waits=frozenset({"GLW", "300308.SZ"}))
    base = {"tickers": ["AMAT"]}
    assert edgar_watch_tickers({**base, "derive_from_narratives": True, "derive_from_waits": True},
                               **sources) == ["AMAT", "GLW", "MXL"]
    assert edgar_watch_tickers({**base, "derive_from_narratives": True}, **sources) == ["AMAT", "MXL"]
    assert edgar_watch_tickers({**base, "derive_from_waits": True}, **sources) == ["AMAT", "GLW"]
    assert edgar_watch_tickers(base, **sources) == ["AMAT"]


def test_edgar_watch_scope_each_derivation_fails_alone(monkeypatch) -> None:
    """一個推導來源讀不到只少它那一份：其他來源與手動清單不跟著縮小，而且回報少了哪一份（INV-3）。"""

    def boom(*_args):
        raise OSError("讀不到")

    watch = {"tickers": ["AMAT"], "derive_from_tracked": True, "derive_from_narratives": True,
             "derive_from_waits": True}
    monkeypatch.setattr(routine_config, "discover_tracked_tickers", lambda config: frozenset({"COHU"}))
    monkeypatch.setattr(routine_config, "narrative_tickers", boom)
    monkeypatch.setattr(routine_config, "waiting_tickers", lambda: frozenset({"GLW"}))
    tickers, failures = routine_config.edgar_watch_scope(watch)
    assert tickers == ["AMAT", "COHU", "GLW"]
    assert [f.split("：")[0] for f in failures] == ["derive_from_narratives"]

    monkeypatch.setattr(routine_config, "discover_tracked_tickers", boom)
    monkeypatch.setattr(routine_config, "narrative_tickers", lambda: frozenset({"MXL"}))
    tickers, failures = routine_config.edgar_watch_scope(watch)
    assert tickers == ["AMAT", "GLW", "MXL"]
    assert [f.split("：")[0] for f in failures] == ["derive_from_tracked"]


def test_waiting_tickers_reads_the_same_watches_semantic_unreachable_counts(monkeypatch) -> None:
    """語意、active／fired 才算（與 `semantic_unreachable` 同一群）；實體查不到名冊不算（INV-1：不憑名字猜）。"""
    from engine_b import event_watch as ew
    from identity.registry import get_registry

    listed = [c for c in get_registry().companies if str(c.research_ticker or "").strip()][:3]
    a, b, c = (str(x.company_id) for x in listed)
    watches = [
        {"kind": ew.SEMANTIC_KIND, "status": "active", "entities": [a]},
        {"kind": ew.SEMANTIC_KIND, "status": "fired", "entities": [b, "co:not_in_registry"]},
        {"kind": ew.SEMANTIC_KIND, "status": "consumed", "entities": [c]},
        {"kind": "date", "status": "active", "entities": [c]},
    ]
    monkeypatch.setattr(ew, "load_watches", lambda path=None: {"watches": watches})
    expected = {str(x.research_ticker).strip().upper() for x in listed[:2]}
    assert routine_config.waiting_tickers() == frozenset(expected)


def test_primary_coverage_reads_the_same_scope_as_harvest(monkeypatch) -> None:
    """#133：叫不叫得醒（`primary_coverage`）與 harvest 抓什麼是同一個定義——repo 的設定開著敘事推導，
    推導進來的公司（含它的 `co:*`）涵蓋面也看得到；推導沒給它就不在。"""
    from engine_b import event_watch as ew
    from identity.registry import get_registry

    company_id = get_registry().company_id_for_ticker("MXL")
    assert company_id, "MXL 有現行敘事，名冊必須有它"
    monkeypatch.setattr(routine_config, "discover_tracked_tickers", lambda config: frozenset())
    monkeypatch.setattr(routine_config, "waiting_tickers", lambda: frozenset())
    monkeypatch.setattr(routine_config, "narrative_tickers", lambda: frozenset())
    assert "MXL" not in ew.primary_coverage()
    monkeypatch.setattr(routine_config, "narrative_tickers", lambda: frozenset({"MXL"}))
    coverage = ew.primary_coverage()
    assert {"MXL", company_id} <= coverage
