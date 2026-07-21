from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sqlite3

import pytest

from decision_lab.context import build_context_bundle, holdings_digest
from decision_lab.execution import (
    ExecutionError,
    apply_live_override,
    apply_paper_amendment,
    assess_probe,
    prepare_managed_action,
    record_live_choice,
    record_live_fill,
)
from decision_lab.models import CoverageResult
from decision_lab.store import DecisionStore
from paper_portfolio.ledger import replay_decision_store_events
from storage.relational import initialize_private_root
from tests.test_decision_context import NOW, complete_inputs
from tests.test_probe_sizing import _assessment
from thesis.investment_policy import load_policy


def _store(tmp_path: Path) -> DecisionStore:
    repo = tmp_path / "repo"
    repo.mkdir()
    private_root = repo / "library" / "private"
    initialize_private_root(private_root, repo_root=repo)
    return DecisionStore.open(
        private_root / "decision_lab" / "decision_lab.db",
        private_root=private_root,
        repo_root=repo,
    )


def test_existing_pre_execution_store_adds_nullable_link_columns(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    private_root = repo / "library" / "private"
    initialize_private_root(private_root, repo_root=repo)
    path = private_root / "decision_lab" / "decision_lab.db"
    path.parent.mkdir(parents=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE paper_events (
            paper_event_id TEXT PRIMARY KEY,
            cohort_id TEXT NOT NULL,
            decision_event_id TEXT,
            event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_digest TEXT NOT NULL,
            effective_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (decision_event_id, payload_digest)
        )
        """
    )
    conn.commit()
    conn.close()

    store = DecisionStore.open(path, private_root=private_root, repo_root=repo)
    try:
        columns = store.table_columns("paper_events")
        assert {"decision_id", "corrects_paper_event_id", "approved_action_id"} <= columns
    finally:
        store.close()


def _bundle(store: DecisionStore, key: str = "execution", *, inputs=None):
    payload = deepcopy(inputs or complete_inputs())
    identity = payload["identity"]
    cohort_id = store.ensure_cohort(
        dedupe_key=key,
        company_id=identity["company_id"],
        research_ticker=identity["research_ticker"],
    ).cohort_id
    store.record_holdings_confirmation(
        holdings_digest(payload["holdings"]["rows"]),
        confirmed_at="2026-07-21T09:00:00+00:00",
    )
    bundle = build_context_bundle(
        store,
        cohort_id=cohort_id,
        evaluation_at=NOW,
        policy_version=load_policy()["policy_version"],
        **payload,
    )
    coverage = CoverageResult(
        assessment_id=f"assessment:{key}",
        cohort_id=cohort_id,
        context_digest=bundle.digest,
        status="analyzable",
        blockers=(),
        paper_blockers=(),
        live_blockers=("holdings_unconfirmed",),
        paper_context_ready=True,
        live_context_ready=False,
        paper_supported_position=0.0,
        live_supported_range=(0.0, 0.0),
        work_order_id=None,
    )
    return bundle, coverage


def test_eligible_assess_is_atomic_and_retry_creates_one_paper_event(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store)
        first = assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="assess:one",
            effective_at=NOW,
        )
        retry = assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="assess:one",
            effective_at=NOW,
        )

        assert first == retry
        assert first.paper_funded is True
        assert store.table_count("system_decisions") == 1
        assert store.table_count("paper_events") == 1
        assert store.paper_position("co:sivers_semiconductors") == pytest.approx(0.0035)
    finally:
        store.close()


def test_same_idempotency_key_with_different_request_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store)
        assess_probe(
            store, bundle, coverage, _assessment(),
            idempotency_key="assess:conflict", effective_at=NOW,
        )
        changed = _assessment(commercial="bounded_hypothesis")

        with pytest.raises(ExecutionError, match="idempotency"):
            assess_probe(
                store, bundle, coverage, changed,
                idempotency_key="assess:conflict", effective_at=NOW,
            )
    finally:
        store.close()


@pytest.mark.parametrize(
    "failure_at",
    ["after_capacity", "after_decision", "after_paper_event", "after_projection"],
)
def test_failure_injection_rolls_back_decision_and_paper(
    tmp_path: Path, failure_at: str
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store)
        with pytest.raises(RuntimeError, match="injected"):
            assess_probe(
                store,
                bundle,
                coverage,
                _assessment(),
                idempotency_key=f"assess:{failure_at}",
                effective_at=NOW,
                _failure_at=failure_at,
            )

        assert store.table_count("system_decisions") == 0
        assert store.table_count("paper_events") == 0
        assert store.paper_position("co:sivers_semiconductors") == 0.0
    finally:
        store.close()


def test_gate_or_stale_paper_context_records_decision_but_never_funds(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store)
        pending = CoverageResult(**{**coverage.__dict__, "status": "coverage_pending"})
        result = assess_probe(
            store, bundle, pending, _assessment(),
            idempotency_key="assess:pending", effective_at=NOW,
        )

        assert result.paper_funded is False
        assert store.table_count("system_decisions") == 1
        assert store.table_count("paper_events") == 0
    finally:
        store.close()


def test_transaction_recomputes_current_paper_capacity_instead_of_stale_context(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    policy = deepcopy(load_policy())
    policy["probe_lane"]["probe_book_nav_cap"] = 0.005
    axt_inputs = complete_inputs(rows=[])
    axt_inputs["identity"] = {
        "company_id": "co:axt",
        "research_ticker": "AXTI",
        "execution_symbol": "AXTI",
        "market_currency": "USD",
        "execution_currency": "USD",
        "execution_venue": "NASDAQ",
    }
    axt_inputs["evidence"] = deepcopy(axt_inputs["evidence"])
    axt_inputs["evidence"]["focus_company"] = {"id": "co:axt"}
    axt_inputs["evidence"]["subject_origin_entity"] = "AXT"
    axt_inputs["financial"] = deepcopy(axt_inputs["financial"])
    axt_inputs["financial"]["ticker"] = "AXTI"
    axt_inputs["market"] = deepcopy(axt_inputs["market"])
    axt_inputs["market"].update({"ticker": "AXTI", "currency": "USD"})
    axt_inputs["fx"] = deepcopy(axt_inputs["fx"])
    axt_inputs["fx"].update({"pair": "USD/USD", "rate": 1.0})
    try:
        first_bundle, first_coverage = _bundle(store, "capacity-1")
        second_bundle, second_coverage = _bundle(
            store, "capacity-2", inputs=axt_inputs
        )
        first = assess_probe(
            store, first_bundle, first_coverage, _assessment(),
            idempotency_key="capacity:1", effective_at=NOW, policy=policy,
        )
        second = assess_probe(
            store, second_bundle, second_coverage, _assessment(),
            idempotency_key="capacity:2", effective_at="2026-07-21T12:01:00+00:00",
            policy=policy,
        )

        assert first.paper_target == pytest.approx(0.0035)
        assert second.paper_target == pytest.approx(0.0015)
        assert store.paper_position("co:sivers_semiconductors") == pytest.approx(0.0035)
        assert store.paper_position("co:axt") == pytest.approx(0.0015)
        assert second.paper_target != pytest.approx(0.0035)
    finally:
        store.close()


def test_live_choice_and_fill_require_explicit_user_facts_and_do_not_rewrite_system(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store)
        decision = assess_probe(
            store, bundle, coverage, _assessment(),
            idempotency_key="assess:live", effective_at=NOW,
        )
        original_digest = store.get_decision(decision.decision_id)["decision_digest"]

        with pytest.raises(ExecutionError, match="explicit"):
            record_live_choice(
                store, decision.decision_id, selected_weight=0.0,
                decided_at=NOW, explicit=False,
            )
        choice_id = record_live_choice(
            store,
            decision.decision_id,
            selected_weight=0.0,
            decided_at=NOW,
            explicit=True,
        )
        with pytest.raises(ExecutionError, match="explicit"):
            record_live_fill(
                store,
                decision.decision_id,
                execution_ref="manual:broker-1",
                shares=10,
                price=2.0,
                currency="EUR",
                executed_at=NOW,
                explicit=False,
            )

        assert choice_id
        assert store.get_decision(decision.decision_id)["decision_digest"] == original_digest
        assert store.table_count("live_execution_reports") == 0
    finally:
        store.close()


def test_above_cap_live_override_requires_prepared_exact_native_approval(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store)
        decision = assess_probe(
            store, bundle, coverage, _assessment(),
            idempotency_key="assess:override", effective_at=NOW,
        )
        prepared = prepare_managed_action(
            store,
            action_type="live_override",
            target_id=decision.decision_id,
            payload={"selected_weight": 0.01, "reason": "我接受超額探索風險"},
            prepared_at=NOW,
            expires_at="2026-07-21T13:00:00+00:00",
        )

        assert store.table_count("live_choices") == 0
        with pytest.raises(ExecutionError, match="approval"):
            apply_live_override(
                store, prepared.action_id, prepared.digest,
                native_approved=False, decided_at="2026-07-21T12:05:00+00:00",
            )
        with pytest.raises(ExecutionError, match="digest"):
            apply_live_override(
                store, prepared.action_id, "0" * 64,
                native_approved=True, decided_at="2026-07-21T12:05:00+00:00",
            )
        choice_id = apply_live_override(
            store,
            prepared.action_id,
            prepared.digest,
            native_approved=True,
            decided_at="2026-07-21T12:05:00+00:00",
        )
        fill_id = record_live_fill(
            store,
            decision.decision_id,
            execution_ref="manual:broker-override",
            shares=10,
            price=2.0,
            currency="EUR",
            executed_at="2026-07-21T12:10:00+00:00",
            explicit=True,
        )

        assert choice_id
        assert fill_id
        assert store.table_count("live_choices") == 1
        assert store.table_count("live_execution_reports") == 1
    finally:
        store.close()


@pytest.mark.parametrize("action_type,target", [("paper_correction", 0.002), ("paper_reversal", 0.0)])
def test_paper_amendment_preserves_original_and_requires_approval(
    tmp_path: Path, action_type: str, target: float
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store)
        decision = assess_probe(
            store, bundle, coverage, _assessment(),
            idempotency_key=f"assess:{action_type}", effective_at=NOW,
        )
        assert decision.paper_event_id is not None
        prepared = prepare_managed_action(
            store,
            action_type=action_type,
            target_id=decision.paper_event_id,
            payload={"target_weight": target, "reason": "修正紙上紀錄"},
            prepared_at=NOW,
            expires_at="2026-07-21T13:00:00+00:00",
        )

        amendment_id = apply_paper_amendment(
            store,
            prepared.action_id,
            prepared.digest,
            native_approved=True,
            effective_at="2026-07-21T12:05:00+00:00",
        )

        events = store.list_paper_events(bundle.cohort_id)
        assert len(events) == 2
        assert events[0]["paper_event_id"] == decision.paper_event_id
        assert events[1]["paper_event_id"] == amendment_id
        assert events[1]["corrects_paper_event_id"] == decision.paper_event_id
        assert store.paper_position("co:sivers_semiconductors") == pytest.approx(target)
        replayed = replay_decision_store_events(events)
        assert replayed["company_weights"].get("co:sivers_semiconductors", 0.0) == pytest.approx(
            target
        )
        assert replayed["event_count"] == 2
    finally:
        store.close()
