from __future__ import annotations

from pathlib import Path

from decision_lab.context import build_context_bundle, holdings_snapshot_digest
from decision_lab.coverage import assess_coverage
from decision_lab.store import DecisionStore
from storage.relational import initialize_private_root
from tests.test_decision_context import NOW, complete_inputs


def _store(tmp_path: Path) -> DecisionStore:
    repo = tmp_path / "repo"
    repo.mkdir()
    private_root = repo / "library" / "private"
    initialize_private_root(private_root, repo_root=repo)
    store = DecisionStore.open(
        private_root / "decision_lab" / "decision_lab.db",
        private_root=private_root,
        repo_root=repo,
    )
    store.ensure_cohort(
        dedupe_key="fixture",
        company_id="co:sivers_semiconductors",
        research_ticker="SIVE.ST",
    )
    return store


def _bundle(
    store: DecisionStore,
    *,
    evidence=None,
    financial=None,
    holdings=None,
    execution_market=None,
    execution_fx=None,
):
    inputs = complete_inputs()
    if evidence is not None:
        inputs["evidence"] = evidence
    if financial is not None:
        inputs["financial"] = financial
    if holdings is not None:
        inputs["holdings"] = holdings
    store.record_holdings_confirmation(
        holdings_snapshot_digest(
            inputs["holdings"]["rows"],
            nav_base=inputs["holdings"].get("nav_base"),
            base_currency=inputs["holdings"].get("base_currency"),
        ),
        confirmed_at="2026-07-21T09:00:00+00:00",
    )
    cohort_id = store.ensure_cohort(
        dedupe_key="fixture",
        company_id="co:sivers_semiconductors",
        research_ticker="SIVE.ST",
    ).cohort_id
    return build_context_bundle(
        store, cohort_id=cohort_id, evaluation_at=NOW,
        policy_version="probe-v1",
        execution_market=execution_market,
        execution_fx=execution_fx,
        **inputs,
    )


def _assess(store: DecisionStore, bundle, **overrides):
    kwargs = {
        "catalyst": "customer production order",
        "disproof": "qualified alternative wins socket",
        "expiry": "2026-10-21T00:00:00+00:00",
        "decision_relevance": 5,
        "falsifiability": 5,
        "information_value": 5,
    }
    kwargs.update(overrides)
    return assess_coverage(store, bundle, **kwargs)


def test_empty_graph_stays_shadow_only_and_gets_bounded_work_order(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        bundle = _bundle(
            store,
            evidence={
                "focus_company": None,
                "subject_origin_entity": "Unknown",
                "sources": [],
                "causal_paths": [],
                "counter_paths": [],
            },
        )
        result = _assess(store, bundle)

        assert result.status == "coverage_pending"
        assert result.paper_supported_position == 0.0
        assert result.live_supported_range == (0.0, 0.0)
        assert result.work_order_id is not None
        assert "graph_company_missing" in result.blockers
        assert store.table_count("research_work_orders") == 1
    finally:
        store.close()


def test_complete_packet_becomes_analyzable_without_overwriting_old_event(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        pending = _assess(
            store,
            _bundle(
                store,
                evidence={
                    "focus_company": None,
                    "subject_origin_entity": "Unknown",
                    "sources": [],
                    "causal_paths": [],
                    "counter_paths": [],
                },
            ),
        )
        analyzable = _assess(store, _bundle(store))

        assert pending.status == "coverage_pending"
        assert analyzable.status == "analyzable"
        assert analyzable.blockers == ()
        assert store.table_count("coverage_assessments") == 2
    finally:
        store.close()


def test_supplier_only_source_and_manual_financial_items_are_explicit_blockers(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs()
    inputs["evidence"]["sources"] = [
        {"id": "src:self", "origin_entity": "Sivers", "evidence_tier": 1}
    ]
    inputs["financial"]["checklist"]["backlog"] = {
        "status": "manual_required", "value": ""
    }
    try:
        result = _assess(
            store,
            _bundle(
                store,
                evidence=inputs["evidence"],
                financial=inputs["financial"],
            ),
        )

        assert "independent_source_missing" in result.blockers
        assert "financial_backlog_manual_required" in result.blockers
    finally:
        store.close()


def test_live_stale_does_not_destroy_paper_research_analyzability(tmp_path: Path) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs()
    inputs["holdings"] = {"status": "available", "rows": inputs["holdings"]["rows"]}
    cohort_id = store.ensure_cohort(
        dedupe_key="fixture",
        company_id="co:sivers_semiconductors",
        research_ticker="SIVE.ST",
    ).cohort_id
    try:
        bundle = build_context_bundle(
            store, cohort_id=cohort_id, evaluation_at=NOW,
            policy_version="probe-v1", **inputs
        )
        result = _assess(store, bundle)

        assert result.status == "analyzable"
        assert result.paper_context_ready is True
        assert result.live_context_ready is False
        assert "holdings_unconfirmed" in result.live_blockers
    finally:
        store.close()


def test_stale_financial_snapshot_blocks_paper_lane_but_keeps_research_state(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs()
    inputs["financial"]["as_of"] = "2026-06-01T00:00:00+00:00"
    inputs["holdings"].update({"nav_base": 10_000.0, "base_currency": "USD"})
    try:
        result = _assess(
            store,
            _bundle(
                store,
                financial=inputs["financial"],
                holdings=inputs["holdings"],
                execution_market={
                    "status": "observed",
                    "ticker": "FRA:2DG",
                    "price": 10.0,
                    "currency": "EUR",
                    "adv20": 100.0,
                    "as_of": "2026-07-21T10:00:00+00:00",
                    "fetched_at": "2026-07-21T10:01:00+00:00",
                    "unit_status": "ok",
                    "source": "fixture://fra-market",
                },
                execution_fx={
                    "status": "observed",
                    "pair": "EUR/USD",
                    "rate": 1.2,
                    "as_of": "2026-07-21T10:00:00+00:00",
                    "fetched_at": "2026-07-21T10:01:00+00:00",
                    "source": "fixture://eur-usd",
                },
            ),
        )

        assert result.status == "analyzable"
        assert result.paper_context_ready is False
        assert result.live_context_ready is True
        assert "financial_stale" in result.paper_blockers
    finally:
        store.close()


def test_queue_capacity_preserves_backlog_and_stable_ranking(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        results = []
        for index in range(7):
            cohort = store.ensure_cohort(
                dedupe_key=f"empty-{index}",
                company_id="co:sivers_semiconductors",
                research_ticker="SIVE.ST",
            )
            inputs = complete_inputs()
            inputs["evidence"] = {
                "focus_company": None,
                "subject_origin_entity": "Unknown",
                "sources": [],
                "causal_paths": [],
                "counter_paths": [],
            }
            bundle = build_context_bundle(
                store, cohort_id=cohort.cohort_id, evaluation_at=NOW,
                policy_version="probe-v1", **inputs
            )
            results.append(
                _assess(store, bundle, decision_relevance=7 - index)
            )

        ranked_once = store.rank_work_orders(capacity=5)
        ranked_twice = store.rank_work_orders(capacity=5)
        assert ranked_once == ranked_twice
        assert len(ranked_once["selected"]) == 5
        assert len(ranked_once["backlog"]) == 2
        assert store.table_count("research_work_orders") == 7
        assert all(result.work_order_id for result in results)
    finally:
        store.close()
