from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from decision_lab.context import build_context_bundle, holdings_snapshot_digest
from decision_lab.models import CoverageResult
from decision_lab.sizing import AXES, AssessmentError, calculate_probe_limits
from decision_lab.store import DecisionStore
from storage.relational import initialize_private_root
from tests.test_decision_context import NOW, complete_inputs
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


def _assessment(*, commercial: str = "corroborated") -> dict:
    levels = {axis: "corroborated" for axis in AXES}
    levels["commercial_maturity"] = commercial
    refs = {
        "source_reliability": ["src:gf"],
        "technical_causal_link": ["edge:cw-laser"],
        "commercial_maturity": ["fixture://filing"],
        "financial_resilience": ["fixture://filing"],
        "valuation_payoff": ["fixture://market"],
    }
    return {
        axis: {
            "level": level,
            "evidence_refs": refs[axis],
            "reason": f"{axis} fixture assessment",
            "missing_data": [] if level == "corroborated" else ["named production order"],
        }
        for axis, level in levels.items()
    }


def _bundle(
    store: DecisionStore,
    *,
    inputs: dict | None = None,
    execution_market: dict | None = None,
    execution_fx: dict | None = None,
):
    payload = deepcopy(inputs or complete_inputs())
    cohort_id = store.ensure_cohort(
        dedupe_key="probe-sizing",
        company_id="co:sivers_semiconductors",
        research_ticker="SIVE.ST",
    ).cohort_id
    store.record_holdings_confirmation(
        holdings_snapshot_digest(
            payload["holdings"]["rows"],
            nav_base=payload["holdings"].get("nav_base"),
            base_currency=payload["holdings"].get("base_currency"),
        ),
        confirmed_at="2026-07-21T09:00:00+00:00",
    )
    return build_context_bundle(
        store,
        cohort_id=cohort_id,
        evaluation_at=NOW,
        policy_version=load_policy()["policy_version"],
        execution_market=execution_market,
        execution_fx=execution_fx,
        **payload,
    )


def _coverage(bundle, *, paper=True, live=True) -> CoverageResult:
    return CoverageResult(
        assessment_id="assessment:fixture",
        cohort_id=bundle.cohort_id,
        context_digest=bundle.digest,
        status="analyzable",
        blockers=(),
        paper_blockers=() if paper else ("market_stale",),
        live_blockers=() if live else ("holdings_unconfirmed",),
        paper_context_ready=paper,
        live_context_ready=live,
        paper_supported_position=0.0,
        live_supported_range=(0.0, 0.0),
        work_order_id=None,
    )


def test_multiple_positive_events_do_not_add_and_weakest_axis_caps_position(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle = _bundle(store)
        assessment = _assessment(commercial="bounded_hypothesis")
        assessment["technical_causal_link"]["evidence_refs"] = [
            "co:sivers_semiconductors",
            "edge:cw-laser",
            "edge:alternative",
        ]

        result = calculate_probe_limits(bundle, _coverage(bundle), assessment)

        assert result.weakest_axis == "commercial_maturity"
        assert result.axis_ceiling == 0.002
        assert result.paper_max_supported_position == 0.002
        assert result.paper_target == 0.001
        assert result.axis_results["technical_causal_link"]["ceiling"] == 0.005
    finally:
        store.close()


@pytest.mark.parametrize("failure", ["unknown", "missing_ref"])
def test_unknown_or_unreferenced_required_axis_fails_closed(
    tmp_path: Path, failure: str
) -> None:
    store = _store(tmp_path)
    try:
        bundle = _bundle(store)
        assessment = _assessment()
        if failure == "unknown":
            assessment["financial_resilience"]["level"] = "unknown"
            assessment["financial_resilience"]["evidence_refs"] = []
            assessment["financial_resilience"]["missing_data"] = ["runway source"]
        else:
            assessment["valuation_payoff"]["evidence_refs"] = []

        result = calculate_probe_limits(bundle, _coverage(bundle), assessment)

        assert result.paper_max_supported_position == 0.0
        assert result.live_supported_range == (0.0, 0.0)
        assert result.action == "SHADOW_ONLY"
        assert result.assessment_blockers
    finally:
        store.close()


@pytest.mark.parametrize(
    "axis,invalid_ref",
    [
        ("source_reliability", "fixture://not-in-this-context"),
        ("valuation_payoff", "edge:cw-laser"),
    ],
)
def test_cross_context_or_wrong_authority_ref_fails_closed(
    tmp_path: Path, axis: str, invalid_ref: str
) -> None:
    store = _store(tmp_path)
    try:
        bundle = _bundle(store)
        assessment = _assessment()
        assessment[axis]["evidence_refs"] = [invalid_ref]

        result = calculate_probe_limits(bundle, _coverage(bundle), assessment)

        assert result.axis_results[axis]["level"] == "unknown"
        assert f"assessment_context_mismatch:{axis}" in result.assessment_blockers
        assert result.paper_max_supported_position == 0.0
        assert result.live_supported_range == (0.0, 0.0)
    finally:
        store.close()


def test_coverage_gate_cannot_be_overridden_by_high_axis_levels(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        bundle = _bundle(store)
        pending = _coverage(bundle)
        pending = CoverageResult(**{**pending.__dict__, "status": "coverage_pending"})

        result = calculate_probe_limits(bundle, pending, _assessment())

        assert result.paper_max_supported_position == 0.0
        assert result.live_supported_range == (0.0, 0.0)
        assert any(
            item["constraint"] == "coverage_gate" and item["cap_weight"] == 0.0
            for item in result.constraint_trace
        )
    finally:
        store.close()


def test_paper_book_and_factor_remaining_can_bind_below_axis_ceiling(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs()
    inputs["paper_exposure"] = {
        "nav": 100.0,
        "total_weight": 0.019,
        "company_weights": {},
        "factor_weights": {"photonics": 0.099, "small_cap": 0.01},
    }
    try:
        bundle = _bundle(store, inputs=inputs)

        result = calculate_probe_limits(bundle, _coverage(bundle), _assessment())

        assert result.axis_ceiling == 0.005
        assert result.paper_max_supported_position == pytest.approx(0.001)
        binding = {
            item["constraint"]
            for item in result.constraint_trace
            if item["lane"] == "paper" and item["binding"]
        }
        assert "probe_book_remaining" in binding
        assert "factor:photonics" in binding
    finally:
        store.close()


def test_paper_and_live_use_separate_nav_factor_and_execution_liquidity(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs(
        rows=[
            {
                "ticker": "FRA:2DG",
                "shares": 10.0,
                "currency": "EUR",
                "company_id": "co:sivers_semiconductors",
                "market_value_base": 10.0,
            },
            {
                "ticker": "SIVE.ST",
                "shares": 20.0,
                "currency": "SEK",
                "company_id": "co:sivers_semiconductors",
                "market_value_base": 20.0,
            },
        ]
    )
    inputs["holdings"].update({"nav_base": 10_000.0, "base_currency": "USD"})
    execution_market = {
        "status": "observed",
        "ticker": "FRA:2DG",
        "price": 10.0,
        "currency": "EUR",
        "adv20": 100.0,
        "as_of": "2026-07-21T10:00:00+00:00",
        "fetched_at": "2026-07-21T10:01:00+00:00",
        "unit_status": "ok",
        "source": "fixture://fra-market",
    }
    execution_fx = {
        "status": "observed",
        "pair": "EUR/USD",
        "rate": 1.2,
        "as_of": "2026-07-21T10:00:00+00:00",
        "fetched_at": "2026-07-21T10:01:00+00:00",
        "source": "fixture://eur-usd",
    }
    try:
        bundle = _bundle(
            store,
            inputs=inputs,
            execution_market=execution_market,
            execution_fx=execution_fx,
        )

        result = calculate_probe_limits(bundle, _coverage(bundle), _assessment())

        assert result.paper_max_supported_position == 0.005
        assert result.live_current_position == pytest.approx(0.003)
        # 1% * 100 ADV = 1 股；10 EUR * 1.2 = USD 12，僅增加 0.12% NAV。
        assert result.live_supported_range[1] == pytest.approx(0.0042)
        assert result.live_supported_shares[1] == pytest.approx(3.5)
        assert any(
            item["lane"] == "live" and item["constraint"] == "execution_adv_1pct"
            and item["binding"]
            for item in result.constraint_trace
        )
    finally:
        store.close()


def test_cash_rows_do_not_block_live_sizing_as_unmapped_holdings(
    tmp_path: Path,
) -> None:
    """Sheet 現金列計入 NAV，但沒有 company／factor 可解析，不得 fail closed。"""
    store = _store(tmp_path)
    inputs = complete_inputs(
        rows=[
            {
                "ticker": "—",
                "shares": 0.0,
                "currency": "USD",
                "market_value_base": 31_700.0,
                "is_cash": True,
            },
            {
                "ticker": "FRA:2DG",
                "shares": 10.0,
                "currency": "EUR",
                "company_id": "co:sivers_semiconductors",
                "market_value_base": 10.0,
            },
        ]
    )
    inputs["holdings"].update({"nav_base": 10_000.0, "base_currency": "USD"})
    try:
        bundle = _bundle(store, inputs=inputs)

        result = calculate_probe_limits(bundle, _coverage(bundle), _assessment())

        assert not any(
            blocker.startswith("holdings_company_mapping_unresolved")
            for blocker in result.live_blockers
        )
        # 現金不得計入任何 factor 曝險。
        assert result.live_current_position == pytest.approx(0.001)
    finally:
        store.close()


def test_unmapped_non_cash_holding_still_blocks_live_sizing(tmp_path: Path) -> None:
    """回歸護欄：真正對應不到公司的持股仍要擋住 live sizing。"""
    store = _store(tmp_path)
    inputs = complete_inputs(
        rows=[
            {
                "ticker": "MYSTERY",
                "shares": 5.0,
                "currency": "USD",
                "market_value_base": 500.0,
            },
        ]
    )
    inputs["holdings"].update({"nav_base": 10_000.0, "base_currency": "USD"})
    try:
        bundle = _bundle(store, inputs=inputs)

        result = calculate_probe_limits(bundle, _coverage(bundle), _assessment())

        assert "holdings_company_mapping_unresolved:MYSTERY" in result.live_blockers
    finally:
        store.close()


def test_research_listing_market_data_cannot_substitute_for_execution_listing_adv(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs(rows=[])
    inputs["holdings"].update({"nav_base": 10_000.0, "base_currency": "USD"})
    try:
        bundle = _bundle(store, inputs=inputs)

        result = calculate_probe_limits(bundle, _coverage(bundle), _assessment())

        assert result.paper_max_supported_position == 0.005
        assert result.live_status == "DATA_NEEDED"
        assert result.live_supported_range == (0.0, 0.0)
        assert "execution_market_missing" in result.live_blockers
    finally:
        store.close()


def test_live_fx_must_translate_execution_currency_into_holdings_base(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs(rows=[])
    inputs["holdings"].update({"nav_base": 10_000.0, "base_currency": "TWD"})
    execution_market = {
        "status": "observed",
        "ticker": "FRA:2DG",
        "price": 10.0,
        "currency": "EUR",
        "adv20": 100.0,
        "as_of": "2026-07-21T10:00:00+00:00",
        "fetched_at": "2026-07-21T10:01:00+00:00",
        "unit_status": "ok",
        "source": "fixture://fra-market",
    }
    wrong_fx = {
        "status": "observed",
        "pair": "EUR/USD",
        "rate": 1.2,
        "as_of": "2026-07-21T10:00:00+00:00",
        "fetched_at": "2026-07-21T10:01:00+00:00",
        "source": "fixture://eur-usd",
    }
    try:
        bundle = _bundle(
            store,
            inputs=inputs,
            execution_market=execution_market,
            execution_fx=wrong_fx,
        )
        result = calculate_probe_limits(bundle, _coverage(bundle), _assessment())

        assert result.live_status == "DATA_NEEDED"
        assert result.live_supported_shares is None
        assert "execution_fx_pair_mismatch" in result.live_blockers
    finally:
        store.close()


def test_sizing_is_content_deterministic_and_rejects_context_mismatch(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle = _bundle(store)
        result_a = calculate_probe_limits(bundle, _coverage(bundle), _assessment())
        result_b = calculate_probe_limits(bundle, _coverage(bundle), _assessment())
        assert result_a == result_b

        mismatched = _coverage(bundle)
        mismatched = CoverageResult(
            **{**mismatched.__dict__, "context_digest": "different"}
        )
        with pytest.raises(AssessmentError, match="context"):
            calculate_probe_limits(bundle, mismatched, _assessment())
    finally:
        store.close()
