"""Alpha Investment View 的消費端：Daily Brief 接線、CLI 派工、取數層的 fail-soft。"""
from __future__ import annotations

import argparse
import types
from datetime import date
from pathlib import Path

import pytest

from briefing.render import render_today_markdown
from briefing.today import build_today_brief
from tests.test_decision_execution import _store

NOW = "2026-09-05T02:00:00+00:00"


def _card(ticker: str = "COHR") -> dict:
    return {
        "ticker": ticker, "company_id": "co:coherent", "company_label": f"co:coherent（{ticker}）",
        "scores": {"structural": {"status": "available", "basis": "deterministic", "effective": 0.85,
                                  "session_level": None, "reason": None},
                   "value_capture": {"status": "available", "basis": "session_judgment",
                                     "effective": 0.75, "session_level": "strong", "reason": None},
                   "earnings_exposure": {"status": "missing", "basis": "none", "effective": None,
                                         "session_level": None, "reason": "unknown"},
                   "expectation_gap": {"status": "stale", "basis": "session_judgment",
                                       "effective": 0.25, "session_level": "weak", "reason": None},
                   "catalyst": {"status": "missing", "basis": "none", "effective": None,
                                "session_level": None, "reason": "unknown"}},
        "signal": {"has_signal": True, "context_matches": False, "weakest_axis": "expectation_gap",
                   "reason": "舊 context"},
        "market_implied_eps_growth": {"value": 2.39, "status": "available", "basis": "heuristic_proxy",
                                      "reason": None},
        "consensus_revenue_growth": {"value": 0.382, "status": "available", "basis": "observation",
                                     "analyst_count": 22},
        "catalyst": {"state": "watch", "state_label": "🟢 監控中", "days_to_expiry": 176,
                     "next_checkpoint": "2026-12-01", "next_checkpoint_confidence": "estimated",
                     "structured_count": 0, "checkpoint_count": 1, "reason": None},
        "disproof": {"condition_count": 3, "narrative_present": True, "problems": []},
        "research_status": "READY", "point_in_time_mode": "current",
        "not_modeled": ["internal_fundamentals", "earnings_bridge", "expected_return", "downside",
                        "entry_logic"],
        "warnings": [],
    }


def test_today_brief_passes_alpha_cards_through_and_keeps_none_distinct(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        holdings = {"status": "available", "rows": []}
        absent = build_today_brief(store, as_of=NOW, current_holdings=holdings)
        assert "alpha_cards" in absent and absent["alpha_cards"] is None
        assert "未提供 Alpha Card" in render_today_markdown(absent)

        empty = build_today_brief(store, as_of=NOW, current_holdings=holdings, alpha_cards=[])
        assert empty["alpha_cards"] == []
        text = render_today_markdown(empty)
        assert "無候選可摘要" in text and "未提供 Alpha Card" not in text

        loaded = build_today_brief(store, as_of=NOW, current_holdings=holdings, alpha_cards=[_card()])
        text = render_today_markdown(loaded)
        assert "Alpha Card 摘要" in text
        assert "co:coherent（COHR）（判斷過期⌛）" in text
        assert "+239.0%（proxy）" in text
        assert "python -m briefing alpha-card" in text
    finally:
        store.close()


def test_alpha_cards_sit_between_ranking_and_nav(tmp_path: Path) -> None:
    """首屏順序：排序 → Alpha Card 摘要 → NAV。摘要是排序的補充，不是替代。"""
    store = _store(tmp_path)
    try:
        brief = build_today_brief(store, as_of=NOW, current_holdings={"status": "available", "rows": []},
                                  alpha_cards=[_card()])
        keys = list(brief)
        assert keys.index("ready_not_ranked") < keys.index("alpha_cards") < keys.index("nav_exposure")
        text = render_today_markdown(brief)
        assert text.index("瓶頸排序") < text.index("Alpha Card 摘要") < text.index("持股 NAV 比例")
    finally:
        store.close()


def test_tickers_from_ranking_preserves_authority_order_and_dedupes() -> None:
    from briefing.alpha_view.sources import tickers_from_ranking

    ranking = {"actionable": [{"ticker": "COHR"}, {"ticker": "COHR"}, {"ticker": "LITE"},
                              {"ticker": None}, {"ticker": "AXTI"}]}
    assert tickers_from_ranking(ranking) == ["COHR", "LITE", "AXTI"]
    assert tickers_from_ranking(ranking, limit=2) == ["COHR", "LITE"]
    assert tickers_from_ranking(None) == []


def test_fetch_alpha_cards_degrades_per_ticker_not_whole_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    from briefing.alpha_view import sources

    def fake_fetch(ticker: str, **kwargs):
        if ticker == "BAD":
            raise TimeoutError("neo4j")
        from tests.test_alpha_investment_view import _view

        return _view()

    monkeypatch.setattr(sources, "fetch_alpha_investment_view", fake_fetch)
    cards = sources.fetch_alpha_cards(["COHR", "BAD"])
    assert [c["ticker"] for c in cards] == ["COHR", "BAD"]
    assert cards[1]["status"] == "unavailable" and cards[1]["reason"] == "TimeoutError"
    assert cards[0]["scores"]["structural"]["basis"] == "deterministic"


def test_fetch_view_with_injected_providers_and_no_private_authorities(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """取數層在沒有 Decision Store／判斷檔／thesis 檔時仍組得出 view，且每個缺席都帶原因。"""
    from alpha.testing import FakeGraphResearchProvider
    from briefing.alpha_view import sources
    from tests.test_alpha_investment_view import COMPANY, _FakeFundamentals

    monkeypatch.setattr(sources, "DECISION_DB", tmp_path / "nope.db")
    monkeypatch.setattr(sources, "LIFECYCLE_PATH", tmp_path / "nope.json")
    monkeypatch.setattr(sources, "JUDGMENT_DIR", tmp_path / "judgments")
    monkeypatch.setattr(sources, "LEGACY_JUDGMENT_DIR", tmp_path / "legacy")
    import engine_c.checklist as checklist_mod

    monkeypatch.setattr(checklist_mod, "get_checklist",
                        lambda ticker: {"engine_c_available": False, "note": "測試：無 Engine C"})
    view = sources.fetch_alpha_investment_view(
        "COHR", today=date(2026, 9, 5),
        graph_provider=FakeGraphResearchProvider(company_id=COMPANY),
        fundamentals_provider=_FakeFundamentals(),
    )
    assert view.identity.ticker == "COHR" and view.identity.company_id == "co:coherent"
    assert view.identity.signal.has_signal is False
    assert "找不到 session 判斷檔" in (view.identity.signal.reason or "")
    assert "沒有 Decision Store" in (view.identity.lifecycle.reason or "")
    assert view.catalysts.narrative.status == "missing"
    assert view.fundamentals.checklist[0].status == "missing"
    assert view.structural_thesis.structural_score.is_known         # Q1 仍算得出
    ranking = {d.key: d for d in view.structural_thesis.ranking}
    assert ranking["actionable_rank"].value == 1
    # FakeGraphResearchProvider 的 get_structural_changes_since 會回一個事件 → 二階影響也接得上
    assert view.causal_paths.meta.status == "available"


def test_briefing_cli_handlers_are_named_functions() -> None:
    """同 `test_alpha_cli_dispatch`：handler 不得是延後 import 的 lambda。"""
    from briefing import cli

    parser = cli.build_parser()
    subparsers = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))  # noqa: SLF001
    for name, sub in subparsers.choices.items():
        func = sub.get_default("func")
        assert isinstance(func, types.FunctionType) and func.__name__ != "<lambda>", name
        assert func.__module__ == cli.__name__, name
    assert "alpha-card" in subparsers.choices


def test_briefing_cli_reports_unknown_ticker_without_traceback(capsys: pytest.CaptureFixture[str]) -> None:
    from briefing import cli

    rc = cli.main(["alpha-card", "NOT_A_TICKER_XYZ", "--no-causal"])
    assert rc == 2
    assert "registry 找不到" in capsys.readouterr().err


def test_company_decision_facts_reads_only_research_fields_from_a_real_store(tmp_path: Path) -> None:
    """Engine D 自己的唯讀查詢：對真實 schema 的 store 建一筆 decision，再用 `mode=ro` 連線讀。
    回傳裡不得出現任何部位／NAV／cap 欄位。"""
    import sqlite3

    from decision_lab.coverage_queries import company_decision_facts
    from tests.test_action_card import _decision

    store = _store(tmp_path)
    try:
        decision = _decision(store, key="facts-ro")
        cohort_id = store.get_decision(decision.decision_id)["cohort_id"]
        company_id = store._conn.execute(  # noqa: SLF001 — 只為取測試 fixture 的 company_id
            "SELECT company_id FROM decision_cohorts WHERE cohort_id = ?", (cohort_id,)
        ).fetchone()["company_id"]
        db_path = Path(store.path)
    finally:
        store.close()

    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        facts = company_decision_facts(conn, str(company_id))
    finally:
        conn.close()
    assert facts is not None
    assert facts["cohort_id"] == cohort_id
    assert facts["cohort_count"] == 1
    assert facts["selection_rule"]
    assert "research_status" in facts and "legacy_axis_levels" in facts
    banned = {"live_current_position", "single_position_nav_cap", "live_blockers", "paper_blockers",
              "nav", "selected_weight", "shares"}
    assert not (set(facts) & banned), set(facts) & banned
    # 沒有這家公司 → None（不是空 dict）
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        assert company_decision_facts(conn, "co:nobody_here") is None
    finally:
        conn.close()


def test_fetch_alpha_cards_shares_one_provider_across_tickers(monkeypatch: pytest.MonkeyPatch) -> None:
    """整批共用 provider：不得每檔各開一次 Neo4j／重算一次排序。"""
    from briefing.alpha_view import sources

    seen: list[object] = []

    def fake_fetch(ticker: str, **kwargs):
        seen.append(kwargs.get("graph_provider"))
        from tests.test_alpha_investment_view import _view

        return _view()

    monkeypatch.setattr(sources, "fetch_alpha_investment_view", fake_fetch)
    sentinel = object()
    sources.fetch_alpha_cards(["COHR", "LITE", "AXTI"], graph_provider=sentinel,
                              fundamentals_provider=object())
    assert seen == [sentinel, sentinel, sentinel]


def test_alpha_cards_render_unknown_condition_count_as_unknown_not_zero() -> None:
    from briefing.alpha_view import render_alpha_cards

    card = _card()
    card["signal"]["has_signal"] = False
    card["disproof"]["condition_count"] = None
    row = next(line for line in render_alpha_cards([card]) if line.startswith("| co:coherent"))
    assert "結構化：未知" in row and "0 條" not in row


def test_company_decision_facts_filters_history_by_as_of(tmp_path: Path) -> None:
    """Decision Store 有時間戳，所以 as-of 是**真正的過濾**：decision 生效日（2026-07-21）之前
    問 → None；之後問 → 事實帶 `point_in_time.as_of`。"""
    import sqlite3

    from decision_lab.coverage_queries import company_decision_facts
    from tests.test_action_card import _decision

    store = _store(tmp_path)
    try:
        decision = _decision(store, key="facts-asof")
        cohort_id = store.get_decision(decision.decision_id)["cohort_id"]
        company_id = store._conn.execute(  # noqa: SLF001
            "SELECT company_id FROM decision_cohorts WHERE cohort_id = ?", (cohort_id,)
        ).fetchone()["company_id"]
        db_path = Path(store.path)
    finally:
        store.close()

    from datetime import date as _date, timedelta

    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        # fixture 的 cohort `created_at` 是真實寫入時間（今天），decision `effective_at` 是固定的
        # 2026-07-21；截止日以 cohort 建立日為錨，前一天問 → 什麼都不知道。
        created = _date.fromisoformat(str(conn.execute(
            "SELECT created_at FROM decision_cohorts WHERE cohort_id = ?", (cohort_id,)
        ).fetchone()["created_at"])[:10])
        before = company_decision_facts(conn, str(company_id), as_of=(created - timedelta(days=1)).isoformat())
        on_day = company_decision_facts(conn, str(company_id), as_of=created.isoformat())
        current = company_decision_facts(conn, str(company_id))
    finally:
        conn.close()
    assert before is None, "cohort 建立前一天，Engine D 對這家公司什麼都不知道"
    assert on_day is not None and on_day["point_in_time"] == {"mode": "as_of", "as_of": created.isoformat()}
    assert on_day["decision_effective_at"].startswith("2026-07-21")
    assert current["point_in_time"] == {"mode": "current", "as_of": None}
    assert current["decision_effective_at"] == on_day["decision_effective_at"]


def test_sources_pass_as_of_into_decision_store_query(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """取數層在 as-of 模式下把 as_of 交給 Engine D 的唯讀查詢，並把回報的時點標記帶進 DecisionFacts。"""
    from briefing.alpha_view import sources

    calls: list[tuple[str, str | None]] = []

    def fake_facts(conn, company_id, *, as_of=None):
        calls.append((company_id, as_of))
        return {"cohort_id": "dc_x", "cohort_count": 1, "selection_rule": "r",
                "point_in_time": {"mode": "as_of" if as_of else "current", "as_of": as_of},
                "catalyst": "x", "disproof": "y", "expiry": "2026-11-30T00:00:00+00:00",
                "coverage_created_at": "2026-08-15 03:06:02"}

    db = tmp_path / "decision_lab.db"
    db.write_bytes(b"")
    monkeypatch.setattr(sources, "DECISION_DB", db)
    import decision_lab.coverage_queries as cq

    monkeypatch.setattr(cq, "company_decision_facts", fake_facts)
    facts, reason = sources._decision_facts("co:coherent", as_of=date(2026, 8, 15))  # noqa: SLF001
    assert reason is None and facts is not None
    assert calls == [("co:coherent", "2026-08-15")]
    assert facts.point_in_time_as_of == "2026-08-15" and facts.point_in_time_mode == "as_of"
    facts_now, _ = sources._decision_facts("co:coherent", as_of=None)  # noqa: SLF001
    assert facts_now.point_in_time_as_of is None and facts_now.point_in_time_mode == "current"
