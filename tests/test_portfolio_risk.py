from __future__ import annotations

from copy import deepcopy

import pytest

from decision_lab.beta_policy import load_beta_policy
from decision_lab.portfolio_risk import (
    append_risk_snapshot,
    build_portfolio_components,
    event_search_requests,
    read_latest_risk_snapshot,
    risk_changes,
)


def _snapshot(*, tsmc: float) -> dict:
    return {
        "schema_version": "portfolio-risk-snapshot-v1",
        "as_of": "2026-07-29T00:00:00+00:00",
        "policy_version": "test",
        "etf_leverage": {"nominal_weight": 0.06, "effective_weight": 0.16},
        "loan_leverage_weight": 0.0,
        "combined_leverage_weight": 0.16,
        "alpha_total_weight": 0.02,
        "issuer_exposures": {
            "TSMC": {
                "direct_weight": 0.10,
                "indirect_weight": tsmc - 0.10,
                "total_weight": tsmc,
            }
        },
        "snapshot_digest": "x",
    }


def test_known_issuer_lookthrough_separates_direct_indirect_and_alpha() -> None:
    policy = load_beta_policy()
    rows = [
        {"ticker": "CASH", "bucket": "cash", "market_value_base": 10, "nav_base": 100, "base_currency": "USD"},
        {"ticker": "0050.TW", "market_value_base": 40, "nav_base": 100, "base_currency": "USD"},
        {"ticker": "2330.TW", "market_value_base": 10, "nav_base": 100, "base_currency": "USD"},
        {
            "ticker": "FRA:2DG",
            "company_id": "co:sivers_semiconductors",
            "market_value_base": 40,
            "nav_base": 100,
            "base_currency": "USD",
        },
    ]

    result = build_portfolio_components(rows, policy)

    assert result["alpha_total_base"] == 40
    assert result["issuer_direct_base"]["TSMC"] == 10
    assert result["issuer_indirect_base"]["TSMC"] == pytest.approx(23.476)
    assert result["issuer_direct_base"]["SIVE.ST"] == 40
    assert not any("mapping_unresolved" in item for item in result["blockers"])


def test_small_issuer_move_inside_same_band_stays_silent() -> None:
    policy = load_beta_policy()
    previous = _snapshot(tsmc=0.293)
    current = _snapshot(tsmc=0.295)

    changes = risk_changes(current, previous, policy)

    assert not any(item["metric"] == "issuer_exposure:TSMC" for item in changes)


def test_concentrated_issuer_price_drop_creates_ephemeral_search_packet() -> None:
    policy = load_beta_policy()
    snapshot = _snapshot(tsmc=0.30)
    current = {
        "data_status": "observed",
        "session_date": "2026-07-29",
        "return_1d": -0.05,
    }
    previous = deepcopy(current) | {"session_date": "2026-07-28", "return_1d": -0.01}

    requests = event_search_requests(
        snapshot,
        observations_by_benchmark={"tsmc": current},
        history_by_benchmark={"tsmc": [current, previous]},
        policy=policy,
    )

    assert len(requests) == 1
    assert requests[0]["issuer"] == "TSMC"
    assert requests[0]["verification_status"] == "unverified"
    assert requests[0]["persistence"] == "none"
    assert requests[0]["authority_effect"] == "none"


def test_private_risk_history_is_append_only_and_idempotent(tmp_path) -> None:
    path = tmp_path / "risk.jsonl"
    first = _snapshot(tsmc=0.293)
    second = _snapshot(tsmc=0.295) | {
        "as_of": "2026-07-30T00:00:00+00:00",
        "snapshot_digest": "y",
    }

    assert append_risk_snapshot(path, first) is True
    assert append_risk_snapshot(path, first) is False
    assert append_risk_snapshot(path, second) is True
    assert read_latest_risk_snapshot(path) == second
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2
