from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from decision_lab.context import build_context_bundle, holdings_digest
from decision_lab.coverage import assess_coverage
from decision_lab.execution import (
    ExecutionError,
    apply_live_override,
    apply_paper_amendment,
    assess_probe,
    prepare_managed_action,
    record_live_choice,
    record_live_fill,
)
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
    stored = store.record_coverage_assessment(
        cohort_id=cohort_id,
        context_digest=bundle.digest,
        status="analyzable",
        blockers=(),
        paper_blockers=(),
        live_blockers=("holdings_unconfirmed",),
        catalyst="next filing",
        disproof="commercial evidence fails",
        expiry="2026-08-21T00:00:00+00:00",
        decision_relevance=8,
        falsifiability=8,
        information_value=7,
    )
    coverage = store.get_coverage_result(str(stored["assessment_id"]))
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
    "intent,paper_blocker,live_blocker",
    [
        ("research", "execution_intent_research_only", "execution_intent_research_only"),
        ("paper", None, "execution_intent_paper_only"),
        ("live", None, None),
    ],
)
def test_execution_intent_is_an_existing_coverage_lane_permission(
    tmp_path: Path,
    intent: str,
    paper_blocker: str | None,
    live_blocker: str | None,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, _ = _bundle(store, f"intent:{intent}")
        coverage = assess_coverage(
            store,
            bundle,
            catalyst="next filing",
            disproof="commercial evidence fails",
            expiry="2026-08-21T00:00:00+00:00",
            decision_relevance=8,
            falsifiability=8,
            information_value=7,
            execution_intent=intent,
        )

        assert (paper_blocker in coverage.paper_blockers) is (paper_blocker is not None)
        assert (live_blocker in coverage.live_blockers) is (live_blocker is not None)
    finally:
        store.close()


def test_pending_coverage_persists_missing_catalyst_and_disproof_as_blockers(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, _ = _bundle(store, "missing-semantic-fields")

        coverage = assess_coverage(
            store,
            bundle,
            catalyst="",
            disproof="",
            expiry="2026-08-21T00:00:00+00:00",
            decision_relevance=0,
            falsifiability=0,
            information_value=0,
        )

        assert coverage.status == "coverage_pending"
        assert {"catalyst_missing", "disproof_missing"} <= set(coverage.blockers)
        assert store.get_coverage_result(coverage.assessment_id) == coverage
    finally:
        store.close()


def test_research_intent_is_in_assessment_request_and_cannot_fund_paper(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store, "research-intent")
        result = assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="assess:research-intent",
            effective_at=NOW,
            execution_intent="research",
        )

        decision = store.get_decision(result.decision_id)
        assert result.paper_funded is False
        assert decision["payload"]["request"]["execution_intent"] == "research"
        assert "execution_intent_research_only" in decision["payload"]["sizing"][
            "paper_blockers"
        ]
    finally:
        store.close()


def test_unresolved_context_can_record_only_a_zero_size_decision(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        cohort_id = store.ensure_cohort(
            dedupe_key="unresolved-decision",
            company_id=None,
            research_ticker=None,
        ).cohort_id
        inputs = complete_inputs(rows=[])
        inputs.update(
            {
                "identity": {},
                "evidence": {
                    "focus_company": None,
                    "sources": [],
                    "causal_paths": [],
                    "counter_paths": [],
                },
                "financial": {"status": "missing"},
                "market": {"status": "missing"},
                "fx": {"status": "missing"},
                "holdings": {"status": "missing"},
            }
        )
        bundle = build_context_bundle(
            store,
            cohort_id=cohort_id,
            evaluation_at=NOW,
            policy_version=load_policy()["policy_version"],
            **inputs,
        )
        coverage = assess_coverage(
            store,
            bundle,
            catalyst="resolve identity",
            disproof="claim cannot be attributed",
            expiry="2026-08-21T00:00:00+00:00",
            decision_relevance=8,
            falsifiability=8,
            information_value=7,
        )
        unknown = _assessment()
        for value in unknown.values():
            value.update(level="unknown", evidence_refs=[], missing_data=["identity"])

        result = assess_probe(
            store,
            bundle,
            coverage,
            unknown,
            idempotency_key="assess:unresolved",
            effective_at=NOW,
        )

        assert result.paper_funded is False
        assert result.paper_max_supported_position == 0.0
        assert store.table_count("system_decisions") == 1
        assert store.table_count("paper_events") == 0
    finally:
        store.close()


def test_equivalent_effective_time_offsets_are_one_idempotent_decision(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store, "offset-retry")
        first = assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="assess:offset-retry",
            effective_at="2026-07-21T13:00:00+00:00",
        )
        retry = assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="assess:offset-retry",
            effective_at="2026-07-21T09:00:00-04:00",
        )

        assert retry == first
        assert store.table_count("system_decisions") == 1
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


def test_forged_coverage_cannot_bypass_stored_pending_gate(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store)
        stored = store.record_coverage_assessment(
            cohort_id=bundle.cohort_id,
            context_digest=bundle.digest,
            status="coverage_pending",
            blockers=("catalyst_missing",),
            paper_blockers=("catalyst_missing",),
            live_blockers=("catalyst_missing",),
            catalyst="unknown",
            disproof="commercial evidence fails",
            expiry="2026-08-21T00:00:00+00:00",
            decision_relevance=8,
            falsifiability=8,
            information_value=7,
        )
        pending = store.get_coverage_result(str(stored["assessment_id"]))
        forged = replace(
            pending,
            status="analyzable",
            blockers=(),
            paper_blockers=(),
            paper_context_ready=True,
        )
        result = assess_probe(
            store, bundle, forged, _assessment(),
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


def test_backdated_assess_cannot_diverge_projection_from_event_replay(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store, "paper-order")
        assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="assess:paper-order:first",
            effective_at="2026-07-21T13:00:00+00:00",
        )
        with pytest.raises(ValueError, match="causal timeline|follow"):
            assess_probe(
                store,
                bundle,
                coverage,
                _assessment(commercial="bounded_hypothesis"),
                idempotency_key="assess:paper-order:backdated",
                effective_at="2026-07-21T12:30:00+00:00",
            )

        events = store.list_paper_events(bundle.cohort_id)
        assert len(events) == 1
        assert store.paper_position("co:sivers_semiconductors") == pytest.approx(0.0035)
        assert replay_decision_store_events(events)["company_weights"][
            "co:sivers_semiconductors"
        ] == pytest.approx(0.0035)
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

        with pytest.raises(ExecutionError, match="currency"):
            record_live_fill(
                store,
                decision.decision_id,
                execution_ref="manual:wrong-currency",
                shares=10,
                price=2.0,
                currency="JPY",
                executed_at="2026-07-21T12:11:00+00:00",
                explicit=True,
            )

        assert choice_id
        assert fill_id
        assert store.table_count("live_choices") == 1
        assert store.table_count("live_execution_reports") == 1

        assert record_live_fill(
            store,
            decision.decision_id,
            execution_ref="manual:broker-override",
            shares=10,
            price=2.0,
            currency="EUR",
            executed_at="2026-07-21T12:10:00+00:00",
            explicit=True,
        ) == fill_id
        with pytest.raises(ExecutionError, match="different fill"):
            record_live_fill(
                store,
                decision.decision_id,
                execution_ref="manual:broker-override",
                shares=11,
                price=2.0,
                currency="EUR",
                executed_at="2026-07-21T12:10:00+00:00",
                explicit=True,
            )
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

        with pytest.raises(ExecutionError, match="follow"):
            apply_paper_amendment(
                store,
                prepared.action_id,
                prepared.digest,
                native_approved=True,
                effective_at="2026-07-21T11:59:00+00:00",
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
