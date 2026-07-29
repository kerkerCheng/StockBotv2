from __future__ import annotations

from pathlib import Path

import pytest

from decision_lab.brief import build_today_brief, render_today_markdown
from decision_lab.execution import apply_live_override, prepare_managed_action, record_live_choice
from tests.test_action_card import _decision
from tests.test_decision_execution import _store
from tests.test_decision_context import complete_inputs
from tests.test_operational_workflow import FixtureProvider


NOW = "2026-07-21T12:30:00+00:00"


def _new_store(tmp_path: Path, name: str):
    root = tmp_path / name
    root.mkdir()
    return _store(root)


@pytest.mark.parametrize("expected", ["NO ACTION", "REVIEW", "TRADE", "HEDGE"])
def test_today_brief_emits_all_action_classes_with_nine_field_contract(
    tmp_path: Path, expected: str
) -> None:
    store = _new_store(tmp_path, expected.replace(" ", "_").lower())
    try:
        decision = _decision(store, key=f"brief-{expected}")
        cohort_id = store.get_decision(decision.decision_id)["cohort_id"]
        portfolio = {}
        if expected == "NO ACTION":
            record_live_choice(
                store,
                decision.decision_id,
                selected_weight=0.0,
                decided_at="2026-07-21T12:10:00+00:00",
                explicit=True,
            )
        elif expected == "TRADE":
            prepared = prepare_managed_action(
                store,
                action_type="live_override",
                target_id=decision.decision_id,
                payload={"selected_weight": 0.001, "reason": "明確接受探索部位"},
                prepared_at="2026-07-21T12:05:00+00:00",
                expires_at="2026-07-21T13:00:00+00:00",
            )
            apply_live_override(
                store,
                prepared.action_id,
                prepared.digest,
                native_approved=True,
                decided_at="2026-07-21T12:10:00+00:00",
            )
        elif expected == "HEDGE":
            portfolio[cohort_id] = {
                "status": "over_cap",
                "factor": "photonics",
                "reason": "投組 photonics 曝險超過政策上限。",
            }

        before = {
            table: store.table_count(table)
            for table in (
                "decision_events",
                "context_bundles",
                "system_decisions",
                "paper_events",
                "live_choices",
            )
        }
        brief = build_today_brief(
            store,
            as_of=NOW,
            current_holdings={"status": "available", "rows": []},
            portfolio_context_by_cohort=portfolio,
        )
        after = {
            table: store.table_count(table)
            for table in before
        }

        assert brief["recommended_action"] == expected
        assert brief["action_needed"] is (expected != "NO ACTION")
        for field in (
            "reason",
            "alpha_thesis_changes",
            "beta_portfolio_risk",
            "supported_sizing_range",
            "blockers",
            "next_review_at",
            "user_response_needed",
        ):
            assert field in brief
        assert before == after
        assert "今天需要動作嗎？" in render_today_markdown(brief)
    finally:
        store.close()


def test_today_finds_sheet_only_holding_without_creating_a_cohort(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        before = store.table_count("decision_cohorts")
        brief = build_today_brief(
            store,
            as_of=NOW,
            current_holdings={
                "status": "available",
                "rows": [
                    {
                        "ticker": "LEGACY",
                        "shares": 5.0,
                        "currency": "USD",
                        "market_value_base": 100.0,
                    }
                ],
            },
        )

        assert brief["recommended_action"] == "REVIEW"
        assert "sheet_only_holding" in brief["blockers"]
        assert brief["items"][0]["ticker"] == "LEGACY"
        assert brief["items"][0]["sheet_only"] is True
        assert brief["items"][0]["supported_sizing_range"] == [0.0, 0.0]
        assert store.table_count("decision_cohorts") == before
    finally:
        store.close()


def test_beta_covered_holding_is_visible_but_not_an_alpha_todo(tmp_path: Path) -> None:
    """QQQ 由 beta policy 涵蓋：仍要在 brief 現形，但不得每天配一個新 pq2 編號。"""
    store = _store(tmp_path)
    try:
        brief = build_today_brief(
            store,
            as_of=NOW,
            current_holdings={
                "status": "available",
                "rows": [
                    {
                        "ticker": "QQQ",
                        "shares": 87.0,
                        "currency": "USD",
                        "market_value_base": 58767.63,
                    }
                ],
            },
        )

        item = brief["items"][0]
        assert item["ticker"] == "QQQ"
        assert item["sheet_only"] is True
        assert item["coverage"] == "beta_policy"
        # NO ACTION 是 collect_from_decisions 用來跳過 pq2 的唯一判準。
        assert item["recommended_action"] == "NO ACTION"
        assert item["blockers"] == []
        assert item["supported_sizing_range"] == [0.0, 0.0]
        # 覆蓋事實不得冒泡成全域 blocker 噪音。
        assert "alpha_cohort_absent" not in brief["blockers"]
        assert "sheet_only_holding" not in brief["blockers"]
    finally:
        store.close()


def test_user_ignored_holding_is_not_an_alpha_todo(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        brief = build_today_brief(
            store,
            as_of=NOW,
            current_holdings={
                "status": "available",
                "rows": [
                    {
                        "ticker": "TYO:7803",
                        "shares": 400.0,
                        "currency": "USD",
                        "market_value_base": 849.59,
                    }
                ],
            },
        )

        item = brief["items"][0]
        assert item["coverage"] == "user_ignored"
        assert item["recommended_action"] == "NO ACTION"
        assert item["blockers"] == []
        # registry 無對應時，markdown 仍要顯示 ticker 而非 unresolved。
        assert "TYO:7803" in render_today_markdown(brief)
    finally:
        store.close()


def test_uncovered_holding_still_demands_review(tmp_path: Path) -> None:
    """回歸護欄：不在 beta policy／ignore 清單的持股必須維持 REVIEW。"""
    store = _store(tmp_path)
    try:
        brief = build_today_brief(
            store,
            as_of=NOW,
            current_holdings={
                "status": "available",
                "rows": [
                    {
                        "ticker": "SOMETHING_NEW",
                        "shares": 10.0,
                        "currency": "USD",
                        "market_value_base": 500.0,
                    }
                ],
            },
        )

        item = brief["items"][0]
        assert item["coverage"] == "uncovered"
        assert item["recommended_action"] == "REVIEW"
        assert "sheet_only_holding" in item["blockers"]
    finally:
        store.close()


def test_today_does_not_treat_beta_only_move_as_disproof(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="brief-beta")
        cohort_id = store.get_decision(decision.decision_id)["cohort_id"]
        record_live_choice(
            store,
            decision.decision_id,
            selected_weight=0.0,
            decided_at="2026-07-21T12:10:00+00:00",
            explicit=True,
        )
        brief = build_today_brief(
            store,
            as_of=NOW,
            current_holdings={"status": "available", "rows": []},
            change_context_by_cohort={
                cohort_id: {
                    "security_return": -0.08,
                    "benchmark_return": -0.07,
                    "evidence_delta": "none",
                    "disproof_triggered": False,
                }
            },
        )

        assert brief["recommended_action"] == "NO ACTION"
        assert brief["alpha_thesis_changes"][0]["classification"] == "beta"
        assert brief["alpha_thesis_changes"][0]["thesis_changed"] is False
    finally:
        store.close()


def test_today_reads_current_market_fx_and_derives_factor_hedge_from_sheet(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs(
        rows=[
            {
                "ticker": "FRA:2DG",
                "company_id": "co:sivers_semiconductors",
                "shares": 10.0,
                "currency": "EUR",
                "market_value_base": 200.0,
            }
        ]
    )
    inputs["holdings"].update({"nav_base": 1_000.0, "base_currency": "USD"})
    provider = FixtureProvider(inputs=inputs)
    try:
        _decision(store, key="brief-current-authorities")
        provider.inputs["market"]["price"] = 2.75
        provider.inputs["fx"]["rate"] = 0.11

        brief = build_today_brief(
            store,
            as_of=NOW,
            provider=provider,
        )

        assert brief["recommended_action"] == "HEDGE"
        risk = brief["beta_portfolio_risk"][0]
        assert risk["portfolio_action"] == "reduce_or_hedge:photonics"
        assert risk["security_return"] == pytest.approx(0.1)
        assert risk["fx_return"] == pytest.approx(0.1)
    finally:
        store.close()
