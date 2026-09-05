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
        "attention": None, "research_status": "READY",
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
