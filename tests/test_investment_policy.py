"""Investment policy is numeric SSOT and is evaluated at query time."""
from __future__ import annotations

import json

import pytest

from risk.policy import (
    POLICY_PATH,
    PolicyError,
    calculate_position_limit,
    holding_action,
    load_policy,
    validate_policy,
)


def _policy(**overrides):
    policy = {
        "policy_version": "test-v1",
        "single_position_nav_cap": 0.05,
        "minimum_open_conviction": 3,
        "conviction_coefficients": {"3": 0.08, "4": 0.10, "5": 0.15},
        "analyst_coverage_threshold": 8,
        "analyst_coverage_discount_levels": 1,
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


def test_exit_override_is_machine_checked_without_legacy_factor_caps() -> None:
    exit_action = holding_action(days_held=10, exit_triggered=True, policy=_policy())

    assert exit_action["action"] == "review_exit_now"
    assert "factor_exposure_caps" not in validate_policy(_policy())


def test_repository_policy_has_versioned_probe_lane_defaults() -> None:
    probe = load_policy()["probe_lane"]

    assert probe["paper_nav"] == 100.0
    assert probe["review_hours"] == 72
    assert probe["rubric_version"]
    assert probe["calculator_version"]


def test_probe_lane_no_longer_carries_capital_expression_keys() -> None:
    """U7 把 alpha 的資本表達層整組移除，這四個鍵不得偷偷長回來。

    ⚠ 刻意讀 raw JSON，不讀 `load_policy()`：`_validate_probe_lane` 只挑已知鍵做
    normalize，加回設定檔的鍵根本不會出現在回傳值裡——斷言正規化結果等於斷言一個
    恆真命題。要驗的是「真的被加回來時會變的那個東西」。
    """

    raw = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    removed = {
        "single_probe_nav_cap",
        "probe_book_nav_cap",
        "axis_ceilings",
        "live_adv_fraction_cap",
    }

    assert removed.isdisjoint(raw["probe_lane"])
    # 對照組：真實風控不在移除之列，單筆 5% NAV 上限仍是 top-level 的 SSOT。
    assert raw["single_position_nav_cap"] == 0.05


@pytest.mark.parametrize(
    "probe_override",
    [
        {"review_hours": 96},
        {"paper_nav": 0.0},
        {"rubric_version": ""},
        {"evidence_hops": -1},
    ],
)
def test_invalid_probe_lane_fails_closed_without_changing_formal_policy(
    probe_override,
) -> None:
    repository_probe = load_policy()["probe_lane"]
    invalid_probe = dict(repository_probe)
    invalid_probe.update(probe_override)

    with pytest.raises(PolicyError):
        validate_policy(_policy(probe_lane=invalid_probe))

    # 沒有 probe_lane 的舊 formal policy 仍維持相容。
    assert validate_policy(_policy())["single_position_nav_cap"] == 0.05
