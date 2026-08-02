from __future__ import annotations

from pathlib import Path

import pytest

from decision_lab.context import build_context_bundle, holdings_digest
from decision_lab.store import DecisionStore
from storage.relational import initialize_private_root


NOW = "2026-07-21T12:00:00+00:00"


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


def _cohort(store: DecisionStore, key: str) -> str:
    return store.ensure_cohort(
        dedupe_key=key,
        company_id="co:sivers_semiconductors",
        research_ticker="SIVE.ST",
    ).cohort_id


def complete_inputs(rows=None):
    rows = rows if rows is not None else [
        {"ticker": "FRA:2DG", "shares": 10.0, "currency": "EUR"}
    ]
    return {
        "identity": {
            "company_id": "co:sivers_semiconductors",
            "research_ticker": "SIVE.ST",
            "execution_symbol": "FRA:2DG",
            "market_currency": "SEK",
            "execution_currency": "EUR",
            "execution_venue": "FRA",
        },
        "evidence": {
            "focus_company": {"id": "co:sivers_semiconductors"},
            "subject_origin_entity": "Sivers",
            "sources": [
                {"id": "src:gf", "origin_entity": "GlobalFoundries", "evidence_tier": 2}
            ],
            "causal_paths": ["edge:cw-laser"],
            "counter_paths": ["edge:alternative"],
        },
        "financial": {
            "status": "observed",
            "ticker": "SIVE.ST",
            "as_of": "2026-07-15T00:00:00+00:00",
            "fetched_at": "2026-07-15T01:00:00+00:00",
            "source": "fixture://filing",
            "cash_and_equivalents": 120.0,
            "total_debt": 20.0,
            "free_cash_flow_ttm": -60.0,
            "checklist": {
                "gross_margin_trend": {"status": "ok"},
                "customer_concentration": {
                    "status": "manual_reviewed",
                    "value": "top customers disclosed",
                    "source": "fixture://filing",
                },
                "backlog": {
                    "status": "manual_reviewed",
                    "value": "backlog disclosed",
                    "source": "fixture://filing",
                },
                "dilution": {"status": "ok"},
                "valuation_pressure": {"status": "ok"},
            },
        },
        "market": {
            "status": "observed",
            "ticker": "SIVE.ST",
            "price": 2.5,
            "currency": "SEK",
            "adv20": 1_000_000.0,
            "as_of": "2026-07-21T10:00:00+00:00",
            "fetched_at": "2026-07-21T10:01:00+00:00",
            "unit_status": "ok",
            "source": "fixture://market",
        },
        "fx": {
            "status": "observed",
            "pair": "SEK/USD",
            "rate": 0.1,
            "as_of": "2026-07-21T10:00:00+00:00",
            "fetched_at": "2026-07-21T10:01:00+00:00",
            "source": "fixture://fx",
        },
        "holdings": {
            "status": "available",
            "rows": rows,
            "fetched_at": "2026-07-21T11:00:00+00:00",
        },
        "paper_exposure": {"nav": 100.0, "total_weight": 0.0},
    }


def test_holdings_confirmation_is_digest_bound_and_retrieval_is_not_confirmation(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs()
    try:
        cohort_id = _cohort(store, "fixture")
        unconfirmed = build_context_bundle(
            store,
            cohort_id=cohort_id,
            evaluation_at=NOW,
            policy_version="probe-v1",
            **inputs,
        )
        digest = holdings_digest(inputs["holdings"]["rows"])
        store.record_holdings_confirmation(digest, confirmed_at="2026-07-21T09:00:00+00:00")
        confirmed = build_context_bundle(
            store,
            cohort_id=cohort_id,
            evaluation_at=NOW,
            policy_version="probe-v1",
            **inputs,
        )
        changed = complete_inputs(rows=[
            {"ticker": "FRA:2DG", "shares": 11.0, "currency": "EUR"}
        ])
        changed_bundle = build_context_bundle(
            store,
            cohort_id=cohort_id,
            evaluation_at=NOW,
            policy_version="probe-v1",
            **changed,
        )

        assert unconfirmed.payload["holdings"]["status"] == "unconfirmed"
        assert confirmed.payload["holdings"]["status"] == "confirmed"
        assert changed_bundle.payload["holdings"]["status"] == "unconfirmed"
        assert confirmed.digest != changed_bundle.digest
    finally:
        store.close()


def test_secret_in_benign_external_value_is_rejected_before_persistence(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs()
    inputs["market"]["source"] = "postgresql://user:canary-password@example/db"
    try:
        with pytest.raises(ValueError, match="secret-bearing"):
            build_context_bundle(
                store,
                cohort_id=_cohort(store, "secret-value"),
                evaluation_at=NOW,
                policy_version="probe-v1",
                **inputs,
            )
        assert store.table_count("context_bundles") == 0
    finally:
        store.close()


def test_future_manual_runway_cannot_complete_current_financial_context(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs()
    inputs["financial"].update(
        {
            "cash_and_equivalents": None,
            "total_debt": None,
            "free_cash_flow_ttm": None,
            "manual_runway": {
                "cash_and_equivalents": 100.0,
                "total_debt": 0.0,
                "free_cash_flow_ttm": -50.0,
                "source": "fixture://future-filing",
                "as_of": "2027-01-01T00:00:00+00:00",
            },
        }
    )
    try:
        bundle = build_context_bundle(
            store,
            cohort_id=_cohort(store, "future-runway"),
            evaluation_at=NOW,
            policy_version="probe-v1",
            **inputs,
        )

        assert bundle.payload["financial"]["runway"]["status"] == "manual_required"
        assert "financial_runway_timestamp_future" in bundle.payload["financial"][
            "blockers"
        ]
    finally:
        store.close()


def test_context_identity_cannot_cross_fund_a_different_cohort(tmp_path: Path) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs()
    inputs["identity"].update(
        {
            "company_id": "co:axt",
            "research_ticker": "AXTI",
            "execution_symbol": "AXTI",
            "market_currency": "USD",
            "execution_currency": "USD",
            "execution_venue": "NASDAQ",
        }
    )
    try:
        with pytest.raises(ValueError, match="cohort authority"):
            build_context_bundle(
                store,
                cohort_id=_cohort(store, "cross-company"),
                evaluation_at=NOW,
                policy_version="probe-v1",
                **inputs,
            )
        assert store.table_count("context_bundles") == 0
    finally:
        store.close()


def test_confirmed_empty_malformed_missing_and_unavailable_are_distinct(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        empty_inputs = complete_inputs(rows=[])
        store.record_holdings_confirmation(
            holdings_digest([]), confirmed_at="2026-07-21T09:00:00+00:00"
        )
        empty = build_context_bundle(
            store, cohort_id=_cohort(store, "empty"), evaluation_at=NOW,
            policy_version="probe-v1", **empty_inputs
        )

        statuses = [empty.payload["holdings"]["status"]]
        for upstream_status in ("malformed", "missing", "unavailable"):
            inputs = complete_inputs()
            inputs["holdings"] = {"status": upstream_status, "rows": []}
            bundle = build_context_bundle(
                store, cohort_id=_cohort(store, upstream_status), evaluation_at=NOW,
                policy_version="probe-v1", **inputs
            )
            statuses.append(bundle.payload["holdings"]["status"])

        assert statuses == ["confirmed_empty", "malformed", "missing", "unavailable"]
    finally:
        store.close()


def test_context_bundle_is_content_addressed_and_frozen(tmp_path: Path) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs()
    try:
        store.record_holdings_confirmation(
            holdings_digest(inputs["holdings"]["rows"]),
            confirmed_at="2026-07-21T09:00:00+00:00",
        )
        cohort_id = _cohort(store, "fixture")
        first = build_context_bundle(
            store, cohort_id=cohort_id, evaluation_at=NOW,
            policy_version="probe-v1", **inputs
        )
        retry = build_context_bundle(
            store, cohort_id=cohort_id, evaluation_at=NOW,
            policy_version="probe-v1", **inputs
        )

        assert first == retry
        assert len(first.digest) == 64
        assert store.table_count("context_bundles") == 1
    finally:
        store.close()


def test_context_builds_canonical_reference_index_from_frozen_authorities(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs()
    try:
        bundle = build_context_bundle(
            store,
            cohort_id=_cohort(store, "reference-index"),
            evaluation_at=NOW,
            policy_version="probe-v1",
            **inputs,
        )

        index = bundle.payload["reference_index"]
        assert index["src:gf"]["authorities"] == ["graph_source_assertion"]
        assert index["edge:cw-laser"]["authorities"] == ["graph_causal"]
        assert "engine_c_financial" in index["fixture://filing"]["authorities"]
        assert "engine_c_customer" in index["fixture://filing"]["authorities"]
        assert index["fixture://market"]["authorities"] == ["market"]
        assert index["policy:probe-v1"]["authorities"] == ["policy"]
        assert any(
            item["authorities"] == ["holdings"]
            for item in index.values()
        )
    finally:
        store.close()


def test_non_gate_manual_observations_reach_the_reference_index(
    tmp_path: Path,
) -> None:
    """非 gate 的人工觀測必須傳到凍結 context，否則寫了也沒有軸能引用。

    _normalize_financial 曾漏傳 observations，使 Engine C 的或有請求權、監管依賴等
    欄位靜默無法被 Confidence 軸引用——寫入成功、reference index 卻沒有它。
    """
    store = _store(tmp_path)
    inputs = complete_inputs()
    inputs["financial"]["observations"] = {
        "contingent_liquidity_claims": {
            "status": "manual_reviewed",
            "value": "redemption right disclosed",
            "source": "fixture://contingent-claims",
            "authorities": ["engine_c_financial", "engine_c_manual"],
        },
    }
    try:
        bundle = build_context_bundle(
            store,
            cohort_id=_cohort(store, "extended-observations"),
            evaluation_at=NOW,
            policy_version="probe-v1",
            **inputs,
        )

        financial = bundle.payload["financial"]
        assert "contingent_liquidity_claims" in financial["observations"]

        entry = bundle.payload["reference_index"]["fixture://contingent-claims"]
        assert entry["authorities"] == ["engine_c_financial", "engine_c_manual"]
    finally:
        store.close()


def test_secret_bearing_external_payload_is_rejected_before_persistence(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs()
    inputs["market"]["api_token"] = "canary-secret"
    try:
        with pytest.raises(ValueError, match="secret-bearing"):
            build_context_bundle(
                store,
                cohort_id=_cohort(store, "secret"),
                evaluation_at=NOW,
                policy_version="probe-v1",
                **inputs,
            )
        assert store.table_count("context_bundles") == 0
    finally:
        store.close()
