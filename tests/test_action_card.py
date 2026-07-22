from __future__ import annotations

from pathlib import Path

import pytest

from decision_lab.action_card import RedactionError, build_action_card, render_markdown
from decision_lab.execution import assess_probe
from decision_lab.execution import (
    apply_live_override,
    prepare_managed_action,
    record_live_fill,
)
from decision_lab.outcomes import close_probe, trigger_review_required
from tests.test_decision_execution import _bundle, _store
from tests.test_probe_sizing import _assessment


def _decision(store, *, key="card"):
    bundle, coverage = _bundle(store, key)
    return assess_probe(
        store,
        bundle,
        coverage,
        _assessment(),
        idempotency_key=f"assess:{key}",
        effective_at="2026-07-21T12:00:00+00:00",
    )


def test_action_card_leads_with_action_and_keeps_paper_live_separate(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store)
        card = build_action_card(store, decision.decision_id)

        assert card["action"] == "REVIEW"
        assert card["urgency"] == "next_review"
        assert card["paper"]["funded"] is True
        assert card["paper"]["target"] == pytest.approx(0.0035)
        assert card["live"]["status"] == "DATA_NEEDED"
        assert card["live"]["supported_shares"] is None
        assert card["weakest_link"]["axis"]
        assert card["next_action"]
    finally:
        store.close()


def test_beta_move_without_evidence_delta_is_not_called_thesis_disproof(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="beta")
        card = build_action_card(
            store,
            decision.decision_id,
            change_context={
                "security_return": -0.08,
                "benchmark_return": -0.07,
                "evidence_delta": "none",
                "disproof_triggered": False,
            },
        )

        assert card["alpha_beta"]["classification"] == "beta"
        assert card["alpha_beta"]["thesis_changed"] is False
        assert "disproof" not in card["reason"].lower()
    finally:
        store.close()


def test_portfolio_factor_breach_can_request_hedge_without_fake_units(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="hedge")
        card = build_action_card(
            store,
            decision.decision_id,
            portfolio_context={
                "status": "over_cap",
                "factor": "photonics",
                "reason": "portfolio factor exposure exceeded",
            },
        )

        assert card["action"] == "HEDGE"
        assert card["scope"]["portfolio"] == "reduce_or_hedge:photonics"
        assert "shares" not in card["scope"]
    finally:
        store.close()


def test_card_is_pure_read_and_markdown_preserves_first_screen_contract(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="pure")
        before = {
            table: store.table_count(table)
            for table in ("system_decisions", "paper_events", "live_choices")
        }
        card = build_action_card(store, decision.decision_id)
        markdown = render_markdown(card)
        after = {
            table: store.table_count(table)
            for table in ("system_decisions", "paper_events", "live_choices")
        }

        assert before == after
        assert markdown.splitlines()[0].startswith("# REVIEW")
        assert "Weakest link" in markdown
        assert "Live" in markdown
        assert "下一步" in markdown
    finally:
        store.close()


def test_secret_bearing_optional_context_is_rejected_before_render(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="secret")
        with pytest.raises(RedactionError, match="secret"):
            build_action_card(
                store,
                decision.decision_id,
                change_context={"api_token": "CANARY-DO-NOT-LEAK"},
            )
        with pytest.raises(RedactionError, match="secret"):
            build_action_card(
                store,
                decision.decision_id,
                change_context={"notes": "Authorization: Bearer CANARY-DO-NOT-LEAK"},
            )
    finally:
        store.close()


def test_markdown_renderer_escapes_research_text_and_terminal_controls(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store, "markdown-escape")
        assessment = _assessment()
        assessment["source_reliability"]["reason"] = "*injected*\n# heading\x1b[31m"
        decision = assess_probe(
            store,
            bundle,
            coverage,
            assessment,
            idempotency_key="card:markdown-escape",
            effective_at="2026-07-21T12:00:00+00:00",
        )
        markdown = render_markdown(build_action_card(store, decision.decision_id))

        assert "\x1b" not in markdown
        assert "\n# heading" not in markdown
        assert r"\*injected\*" in markdown
    finally:
        store.close()


def test_card_respects_explicit_live_fill_instead_of_recommending_duplicate_trade(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="filled")
        prepared = prepare_managed_action(
            store,
            action_type="live_override",
            target_id=decision.decision_id,
            payload={"selected_weight": 0.01, "reason": "我接受額外探索風險"},
            prepared_at="2026-07-21T12:00:00+00:00",
            expires_at="2026-07-21T13:00:00+00:00",
        )
        apply_live_override(
            store,
            prepared.action_id,
            prepared.digest,
            native_approved=True,
            decided_at="2026-07-21T12:05:00+00:00",
        )
        record_live_fill(
            store,
            decision.decision_id,
            execution_ref="manual:card-fill",
            shares=10,
            price=2.0,
            currency="EUR",
            executed_at="2026-07-21T12:10:00+00:00",
            explicit=True,
        )

        card = build_action_card(store, decision.decision_id)

        assert card["action"] == "NO_ACTION"
        assert card["live"]["fill_reported"] is True
        assert card["scope"]["single_name"] == "monitor_confirmed_live_execution"
    finally:
        store.close()


def test_review_required_lifecycle_forces_48h_review_without_optional_context(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="lifecycle-review")
        cohort_id = store.get_decision(decision.decision_id)["cohort_id"]
        trigger_review_required(
            store,
            cohort_id,
            reason="Customer qualification failed",
            evidence_refs=["fixture://customer"],
            effective_at="2026-07-21T12:10:00+00:00",
        )

        card = build_action_card(store, decision.decision_id)

        assert card["action"] == "REVIEW"
        assert card["urgency"] == "within_48h"
        assert card["lifecycle"]["status"] == "review_required"
        assert card["lifecycle"]["review_due_at"] == "2026-07-23T12:10:00+00:00"
    finally:
        store.close()


def test_action_card_rechecks_frozen_freshness_at_render_time(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="stale-card")
        card = build_action_card(
            store,
            decision.decision_id,
            as_of="2026-08-10T12:00:00+00:00",
        )

        assert card["action"] == "REVIEW"
        assert card["urgency"] == "data_refresh"
        assert card["paper"]["status"] == "DATA_NEEDED"
        assert card["live"]["supported_shares"] is None
        assert any("stale_since_decision" in item for item in card["blockers"])
    finally:
        store.close()


def test_terminal_probe_never_reuses_old_decision_to_open_position(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="terminal-card")
        cohort_id = store.get_decision(decision.decision_id)["cohort_id"]
        close_probe(
            store,
            cohort_id,
            terminal_status="rejected",
            claim_correctness="false",
            current_market={"status": "missing"},
            benchmark={"status": "missing"},
            reason="Claim disproved",
            evidence_refs=["fixture://counter"],
            effective_at="2026-07-21T13:00:00+00:00",
        )

        card = build_action_card(
            store, decision.decision_id, as_of="2026-07-21T13:05:00+00:00"
        )
        assert card["action"] == "REVIEW"
        assert card["scope"]["single_name"] == "terminal_unwind_review"
    finally:
        store.close()


def test_disproof_review_remains_primary_when_portfolio_is_over_cap(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="review-and-hedge")
        cohort_id = store.get_decision(decision.decision_id)["cohort_id"]
        trigger_review_required(
            store,
            cohort_id,
            reason="Customer qualification failed",
            evidence_refs=["fixture://customer"],
            effective_at="2026-07-21T12:10:00+00:00",
        )
        card = build_action_card(
            store,
            decision.decision_id,
            as_of="2026-07-21T12:20:00+00:00",
            portfolio_context={"status": "over_cap", "factor": "photonics"},
        )

        assert card["action"] == "REVIEW"
        assert card["urgency"] == "within_48h"
        assert card["scope"]["portfolio"] == "reduce_or_hedge:photonics"
    finally:
        store.close()


def test_new_live_choice_requires_its_own_fill(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="choice-link")
        first = prepare_managed_action(
            store,
            action_type="live_override",
            target_id=decision.decision_id,
            payload={"selected_weight": 0.01, "reason": "first"},
            prepared_at="2026-07-21T12:00:00+00:00",
            expires_at="2026-07-21T13:00:00+00:00",
        )
        apply_live_override(
            store,
            first.action_id,
            first.digest,
            native_approved=True,
            decided_at="2026-07-21T12:05:00+00:00",
        )
        record_live_fill(
            store,
            decision.decision_id,
            execution_ref="manual:first-fill",
            shares=10,
            price=2.0,
            currency="EUR",
            executed_at="2026-07-21T12:10:00+00:00",
            explicit=True,
        )
        second = prepare_managed_action(
            store,
            action_type="live_override",
            target_id=decision.decision_id,
            payload={"selected_weight": 0.02, "reason": "second"},
            prepared_at="2026-07-21T12:15:00+00:00",
            expires_at="2026-07-21T13:00:00+00:00",
        )
        apply_live_override(
            store,
            second.action_id,
            second.digest,
            native_approved=True,
            decided_at="2026-07-21T12:20:00+00:00",
        )

        card = build_action_card(
            store, decision.decision_id, as_of="2026-07-21T12:25:00+00:00"
        )
        assert card["live"]["fill_reported"] is False
        assert card["scope"]["single_name"] == "execute_confirmed_live_choice"
    finally:
        store.close()
