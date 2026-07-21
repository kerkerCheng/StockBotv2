from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sqlite3

import pytest

from decision_lab.action_card import build_action_card
from decision_lab.backup import create_private_backup, restore_private_backup
from decision_lab.bootstrap import open_default_store
from decision_lab.context import build_context_bundle, holdings_snapshot_digest
from decision_lab.coverage import assess_coverage
from decision_lab.execution import assess_probe
from decision_lab.intake import capture_signal
from decision_lab.models import MarketObservation, SignalInput
from decision_lab.outcomes import close_probe
from decision_lab.sizing import calculate_probe_limits
from decision_lab.store import DecisionStore
from engine_c.db import _ensure_sqlite_schema, upsert_snapshot
from engine_c.manual_observations import append_manual_observation
from paper_portfolio.ledger import replay_decision_store_events
from thesis.investment_policy import load_policy


FIXTURES = Path(__file__).parent / "fixtures" / "decision_lab"


class FixedMarket:
    def __init__(self, payload: dict):
        self._observation = MarketObservation(**payload)

    def observe(self, *_args) -> MarketObservation:
        return self._observation


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _store(tmp_path: Path) -> tuple[DecisionStore, Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    private = repo / "library" / "private"
    return open_default_store(repo), repo, private


def _freeze_fixture_context(
    store: DecisionStore,
    fixture: dict,
    cohort_id: str,
    *,
    with_execution: bool = False,
):
    context = deepcopy(fixture["context"])
    holdings = context["holdings"]
    store.record_holdings_confirmation(
        holdings_snapshot_digest(
            holdings["rows"],
            nav_base=holdings.get("nav_base"),
            base_currency=holdings.get("base_currency"),
        ),
        confirmed_at=fixture["holdings_confirmed_at"],
    )
    return build_context_bundle(
        store,
        cohort_id=cohort_id,
        evaluation_at=fixture["evaluation_at"],
        policy_version=load_policy()["policy_version"],
        execution_market=fixture.get("execution_market") if with_execution else None,
        execution_fx=fixture.get("execution_fx") if with_execution else None,
        **context,
    )


def _run_sive(store: DecisionStore) -> tuple[dict, object, object, object]:
    fixture = _fixture("sive_reference_design.json")
    captured = capture_signal(
        store,
        SignalInput(**fixture["signal"]),
        market=FixedMarket(fixture["shadow_market"]),
    )
    bundle = _freeze_fixture_context(store, fixture, captured.cohort_id)
    coverage = assess_coverage(store, bundle, **fixture["coverage"])
    decision = assess_probe(
        store,
        bundle,
        coverage,
        fixture["assessment"],
        idempotency_key="e2e:sive:initial",
        effective_at=fixture["evaluation_at"],
    )
    return fixture, captured, bundle, decision


def test_sive_signal_funds_bounded_paper_but_never_auto_adds_live(
    tmp_path: Path,
) -> None:
    store, _, _ = _store(tmp_path)
    try:
        fixture, captured, _, decision = _run_sive(store)
        card = build_action_card(store, decision.decision_id)

        assert captured.company_id == "co:sivers_semiconductors"
        assert captured.research_ticker == "SIVE.ST"
        assert captured.execution_symbol == "FRA:2DG"
        assert store.get_shadow(captured.cohort_id).price == pytest.approx(2.5)
        assert store.get_probe(captured.cohort_id).evidence_admission_status == "lead_only"
        assert decision.paper_funded is True
        assert decision.paper_target == pytest.approx(0.001)
        assert card["weakest_link"]["axis"] == "commercial_maturity"
        assert any(
            "production order" in item
            for item in card["weakest_link"]["missing_data"]
        )
        assert card["paper"]["funded"] is True
        assert card["live"]["status"] == "DATA_NEEDED"
        assert card["live"]["supported_shares"] is None
        assert store.table_count("live_choices") == 0
        assert store.table_count("live_execution_reports") == 0

        complete = deepcopy(fixture)
        complete["context"]["paper_exposure"].update(
            {
                "total_weight": decision.paper_target,
                "company_weights": {
                    "co:sivers_semiconductors": decision.paper_target
                },
                "factor_weights": {
                    "photonics": decision.paper_target,
                    "small_cap": decision.paper_target,
                },
            }
        )
        live_bundle = _freeze_fixture_context(
            store, complete, captured.cohort_id, with_execution=True
        )
        live_coverage = assess_coverage(store, live_bundle, **fixture["coverage"])
        live_sizing = calculate_probe_limits(
            live_bundle, live_coverage, fixture["assessment"]
        )

        assert live_sizing.live_status == "ELIGIBLE"
        assert live_sizing.live_supported_shares is not None
        assert live_sizing.live_current_position == pytest.approx(0.003)
        assert live_sizing.live_supported_range[1] == pytest.approx(0.002)
        assert any(
            item["constraint"] == "execution_adv_1pct"
            and item["authority"] == "execution_market+execution_fx"
            for item in live_sizing.constraint_trace
        )
        assert store.table_count("live_choices") == 0
    finally:
        store.close()


def test_empty_graph_company_stays_shadow_only_with_bounded_research_work(
    tmp_path: Path,
) -> None:
    store, _, _ = _store(tmp_path)
    fixture = _fixture("empty_graph_company.json")
    try:
        captured = capture_signal(
            store,
            SignalInput(**fixture["signal"]),
            market=FixedMarket(fixture["shadow_market"]),
        )
        bundle = _freeze_fixture_context(store, fixture, captured.cohort_id)
        coverage = assess_coverage(store, bundle, **fixture["coverage"])
        decision = assess_probe(
            store,
            bundle,
            coverage,
            fixture["assessment"],
            idempotency_key="e2e:empty-graph",
            effective_at=fixture["evaluation_at"],
        )
        frozen = store.get_decision(decision.decision_id)["payload"]["sizing"]
        card = build_action_card(store, decision.decision_id)

        assert store.count_shadows(captured.cohort_id) == 1
        assert coverage.status == "coverage_pending"
        assert coverage.work_order_id is not None
        assert "graph_company_missing" in coverage.blockers
        assert "causal_path_missing" in coverage.blockers
        assert decision.paper_funded is False
        assert frozen["paper_max_supported_position"] == 0.0
        assert frozen["live_supported_range"] == [0.0, 0.0]
        assert store.table_count("paper_events") == 0
        assert store.table_count("research_work_orders") == 1
        assert card["action"] == "REVIEW"
        assert card["live"]["supported_shares"] is None
    finally:
        store.close()


def test_engine_c_rebuild_and_private_restore_preserve_frozen_decision_audit(
    tmp_path: Path,
) -> None:
    store, repo, private = _store(tmp_path)
    fixture, captured, bundle, decision = _run_sive(store)
    outcome = close_probe(
        store,
        captured.cohort_id,
        terminal_status="expired",
        claim_correctness="unknown",
        current_market={"status": "missing"},
        benchmark={"status": "missing"},
        reason="Fixture horizon ended without production-order confirmation.",
        evidence_refs=["fixture://sive/outcome-review"],
        effective_at="2026-10-21T12:00:00+00:00",
    )
    original = {
        "decision_digest": store.get_decision(decision.decision_id)["decision_digest"],
        "context_digest": bundle.digest,
        "outcome": store.get_outcome(outcome.outcome_id),
        "paper": replay_decision_store_events(
            store.list_paper_events(captured.cohort_id)
        ),
    }

    engine_path = private / "engine_c" / "rebuild-fixture.db"
    engine_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "ticker": "SIVE.ST",
        "snapshot_date": "2026-07-21",
        "gross_margin": 0.4,
        "operating_margin": -0.1,
        "revenue_ttm": 100,
        "shares_outstanding": 100,
        "cash_and_equivalents": 120.0,
        "total_debt": 20.0,
        "free_cash_flow_ttm": -60.0,
        "ev_revenue": 2.0,
        "pe_trailing": None,
        "pe_forward": None,
        "price": 2.5,
        "analyst_target_mean": None,
        "analyst_target_high": None,
        "analyst_target_low": None,
        "analyst_target_count": None,
        "fetched_at": "2026-07-21T10:00:00+00:00",
    }
    manual = {
        "ticker": "SIVE.ST",
        "field_name": "backlog",
        "value": "no named production order",
        "source_ref": "fixture://sivers/filing",
        "as_of": "2026-07-15T00:00:00+00:00",
        "author": "fixture",
    }
    engine = sqlite3.connect(engine_path)
    engine.row_factory = sqlite3.Row
    _ensure_sqlite_schema(engine)
    upsert_snapshot(engine, snapshot)
    append_manual_observation(engine, **manual)
    assert engine.execute("SELECT COUNT(*) FROM financial_snapshots").fetchone()[0] == 1
    assert engine.execute("SELECT COUNT(*) FROM manual_observations").fetchone()[0] == 1
    engine.close()

    # Rebuild Engine C from explicit ETL + manual-ledger inputs without touching
    # the frozen Decision Store. Production deletion still requires a recovery backup.
    engine_path.unlink()
    rebuilt = sqlite3.connect(engine_path)
    rebuilt.row_factory = sqlite3.Row
    _ensure_sqlite_schema(rebuilt)
    upsert_snapshot(rebuilt, snapshot)
    append_manual_observation(rebuilt, **manual)
    rebuilt_counts = (
        rebuilt.execute("SELECT COUNT(*) FROM financial_snapshots").fetchone()[0],
        rebuilt.execute("SELECT COUNT(*) FROM manual_observations").fetchone()[0],
        rebuilt.execute("SELECT COUNT(*) FROM manual_fields").fetchone()[0],
    )
    rebuilt_manual = rebuilt.execute(
        "SELECT value, source_note, updated_at FROM manual_fields"
    ).fetchone()
    rebuilt.close()
    assert rebuilt_counts == (1, 1, 1)
    assert tuple(rebuilt_manual) == (
        manual["value"],
        manual["source_ref"],
        manual["as_of"],
    )
    assert store.get_decision(decision.decision_id)["decision_digest"] == original[
        "decision_digest"
    ]

    store.close()
    backup = create_private_backup(
        sources={
            "decision_lab": private / "decision_lab" / "decision_lab.db",
            "engine_c": engine_path,
        },
        backup_id="20260721T120000Z",
        private_root=private,
        repo_root=repo,
    )
    mutated = open_default_store(repo)
    mutated.ensure_cohort(
        dedupe_key="post-backup-mutation",
        company_id="co:axt",
        research_ticker="AXTI",
    )
    mutated.close()
    engine_path.unlink()
    restore_private_backup(
        backup,
        targets={
            "decision_lab": private / "decision_lab" / "decision_lab.db",
            "engine_c": engine_path,
        },
        private_root=private,
        repo_root=repo,
    )
    restored = open_default_store(repo)
    try:
        recovered_engine = sqlite3.connect(engine_path)
        try:
            assert recovered_engine.execute(
                "SELECT COUNT(*) FROM manual_observations"
            ).fetchone()[0] == 1
        finally:
            recovered_engine.close()
        assert restored.get_decision(decision.decision_id)["decision_digest"] == original[
            "decision_digest"
        ]
        assert restored.get_context_bundle(original["context_digest"]).digest == original[
            "context_digest"
        ]
        assert restored.get_outcome(outcome.outcome_id) == original["outcome"]
        assert replay_decision_store_events(
            restored.list_paper_events(captured.cohort_id)
        ) == original["paper"]
        assert restored.lifecycle_invariant_violations() == []
        assert restored.table_count("decision_cohorts") == 1
    finally:
        restored.close()
