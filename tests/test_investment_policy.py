"""Investment policy is numeric SSOT and is evaluated at query time."""
from __future__ import annotations

import json

import pytest

from thesis.investment_policy import (
    PolicyError,
    calculate_position_limit,
    check_factor_exposure,
    holding_action,
    load_policy,
)


def _policy(**overrides):
    policy = {
        "policy_version": "test-v1",
        "single_position_nav_cap": 0.05,
        "minimum_open_conviction": 3,
        "conviction_coefficients": {"3": 0.08, "4": 0.10, "5": 0.15},
        "analyst_coverage_threshold": 8,
        "analyst_coverage_discount_levels": 1,
        "factor_exposure_caps": {"semiconductor": 0.25},
        "minimum_holding_days": 90,
    }
    policy.update(overrides)
    return policy


def test_repository_policy_loads_and_returns_version() -> None:
    policy = load_policy()
    result = calculate_position_limit(
        total_nav=100,
        high_risk_budget=20,
        conviction=5,
        analyst_coverage_count=9,
        policy=policy,
    )

    assert result["policy_version"] == policy["policy_version"]
    assert result["effective_conviction"] == 4
    assert result["conviction_coefficient"] == 0.10
    assert result["maximum_position"] == 2.0


def test_coverage_threshold_changes_view_without_data_migration() -> None:
    observation = 9

    crowded = calculate_position_limit(
        total_nav=100,
        high_risk_budget=100,
        conviction=5,
        analyst_coverage_count=observation,
        policy=_policy(analyst_coverage_threshold=8),
    )
    not_crowded = calculate_position_limit(
        total_nav=100,
        high_risk_budget=100,
        conviction=5,
        analyst_coverage_count=observation,
        policy=_policy(analyst_coverage_threshold=12),
    )

    assert crowded["conviction_coefficient"] == 0.10
    assert not_crowded["conviction_coefficient"] == 0.15
    assert crowded["coverage_view"]["analyst_coverage_count"] == observation
    assert not_crowded["coverage_view"]["analyst_coverage_count"] == observation


def test_missing_coverage_is_unknown_and_not_persisted() -> None:
    result = calculate_position_limit(
        total_nav=100,
        high_risk_budget=20,
        conviction=5,
        analyst_coverage_count=None,
        policy=_policy(),
    )

    assert result["coverage_view"]["coverage_status"] == "unknown"
    assert "crowding" not in result
    assert result["effective_conviction"] == 5


@pytest.mark.parametrize(
    "override",
    [
        {"single_position_nav_cap": 1.1},
        {"analyst_coverage_threshold": "8"},
        {"conviction_coefficients": {"3": 0.08, "4": 0.10}},
        {"factor_exposure_caps": {"semiconductor": -0.1}},
    ],
)
def test_invalid_policy_fails_closed(tmp_path, override) -> None:
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(_policy(**override)), encoding="utf-8")

    with pytest.raises(PolicyError):
        load_policy(path)


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_policy_numbers_fail_closed(tmp_path, invalid) -> None:
    path = tmp_path / "policy.json"
    path.write_text(
        json.dumps(_policy(single_position_nav_cap=invalid)), encoding="utf-8"
    )

    with pytest.raises(PolicyError, match="finite"):
        load_policy(path)


def test_missing_policy_key_fails_closed(tmp_path) -> None:
    policy = _policy()
    policy.pop("minimum_holding_days")
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy), encoding="utf-8")

    with pytest.raises(PolicyError, match="missing required keys"):
        load_policy(path)


def test_factor_cap_and_exit_override_are_machine_checked() -> None:
    exposure = check_factor_exposure(
        "semiconductor",
        current_exposure=0.20,
        proposed_addition=0.06,
        policy=_policy(),
    )
    exit_action = holding_action(days_held=10, exit_triggered=True, policy=_policy())

    assert exposure["within_cap"] is False
    assert exit_action["action"] == "review_exit_now"
