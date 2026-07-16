"""Versioned investment-policy loading and query-time derived decisions.

The JSON file is the numeric source of truth. Engine C stores observations only;
coverage thresholds and position sizing are applied here at query time.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "config" / "investment_policy.json"

_REQUIRED_KEYS = {
    "policy_version",
    "single_position_nav_cap",
    "minimum_open_conviction",
    "conviction_coefficients",
    "analyst_coverage_threshold",
    "analyst_coverage_discount_levels",
    "factor_exposure_caps",
    "minimum_holding_days",
}


class PolicyError(ValueError):
    """Raised when policy configuration is missing or unsafe."""


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PolicyError(f"{name} must be numeric")
    return float(value)


def _ratio(value: Any, name: str, *, allow_zero: bool = False) -> float:
    result = _number(value, name)
    lower_ok = result >= 0 if allow_zero else result > 0
    if not lower_ok or result > 1:
        raise PolicyError(f"{name} must be {'between 0 and 1' if allow_zero else 'in (0, 1]'}")
    return result


def validate_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a policy mapping, failing closed on drift."""

    if not isinstance(policy, Mapping):
        raise PolicyError("policy must be a JSON object")
    missing = sorted(_REQUIRED_KEYS - set(policy))
    if missing:
        raise PolicyError(f"policy missing required keys: {', '.join(missing)}")

    version = policy["policy_version"]
    if not isinstance(version, str) or not version.strip():
        raise PolicyError("policy_version must be a non-empty string")

    minimum = policy["minimum_open_conviction"]
    if isinstance(minimum, bool) or not isinstance(minimum, int) or not 1 <= minimum <= 5:
        raise PolicyError("minimum_open_conviction must be an integer from 1 to 5")

    coefficients = policy["conviction_coefficients"]
    if not isinstance(coefficients, Mapping):
        raise PolicyError("conviction_coefficients must be an object")
    required_levels = {str(level) for level in range(minimum, 6)}
    if set(coefficients) != required_levels:
        raise PolicyError(
            "conviction_coefficients must contain exactly levels "
            + ", ".join(sorted(required_levels))
        )
    normalized_coefficients = {
        key: _ratio(value, f"conviction_coefficients.{key}")
        for key, value in coefficients.items()
    }
    ordered = [normalized_coefficients[str(level)] for level in range(minimum, 6)]
    if ordered != sorted(ordered):
        raise PolicyError("conviction coefficients must not decrease as conviction rises")

    threshold = policy["analyst_coverage_threshold"]
    discount = policy["analyst_coverage_discount_levels"]
    minimum_days = policy["minimum_holding_days"]
    for name, value, lower in (
        ("analyst_coverage_threshold", threshold, 1),
        ("analyst_coverage_discount_levels", discount, 0),
        ("minimum_holding_days", minimum_days, 0),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < lower:
            raise PolicyError(f"{name} must be an integer >= {lower}")
    if discount > 4:
        raise PolicyError("analyst_coverage_discount_levels must be <= 4")

    caps = policy["factor_exposure_caps"]
    if not isinstance(caps, Mapping) or not caps:
        raise PolicyError("factor_exposure_caps must be a non-empty object")
    normalized_caps: dict[str, float] = {}
    for factor, cap in caps.items():
        if not isinstance(factor, str) or not factor.strip():
            raise PolicyError("factor exposure names must be non-empty strings")
        normalized_caps[factor] = _ratio(cap, f"factor_exposure_caps.{factor}")

    return {
        "policy_version": version.strip(),
        "single_position_nav_cap": _ratio(
            policy["single_position_nav_cap"], "single_position_nav_cap"
        ),
        "minimum_open_conviction": minimum,
        "conviction_coefficients": normalized_coefficients,
        "analyst_coverage_threshold": threshold,
        "analyst_coverage_discount_levels": discount,
        "factor_exposure_caps": normalized_caps,
        "minimum_holding_days": minimum_days,
    }


def load_policy(path: str | Path = POLICY_PATH) -> dict[str, Any]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"cannot load investment policy: {exc}") from exc
    return validate_policy(raw)


def coverage_policy_view(
    analyst_coverage_count: int | None,
    *,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    current = validate_policy(policy) if policy is not None else load_policy()
    if analyst_coverage_count is None:
        status = "unknown"
        discount = 0
    else:
        if isinstance(analyst_coverage_count, bool) or not isinstance(
            analyst_coverage_count, int
        ) or analyst_coverage_count < 0:
            raise PolicyError("analyst_coverage_count must be a non-negative integer or null")
        threshold_met = analyst_coverage_count >= current["analyst_coverage_threshold"]
        status = "threshold_met" if threshold_met else "below_threshold"
        discount = current["analyst_coverage_discount_levels"] if threshold_met else 0
    return {
        "policy_version": current["policy_version"],
        "analyst_coverage_count": analyst_coverage_count,
        "coverage_status": status,
        "coverage_threshold": current["analyst_coverage_threshold"],
        "conviction_discount_levels": discount,
    }


def calculate_position_limit(
    *,
    total_nav: float,
    high_risk_budget: float,
    conviction: int,
    analyst_coverage_count: int | None,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the maximum position without persisting any derived category."""

    current = validate_policy(policy) if policy is not None else load_policy()
    nav = _number(total_nav, "total_nav")
    budget = _number(high_risk_budget, "high_risk_budget")
    if nav < 0 or budget < 0:
        raise PolicyError("total_nav and high_risk_budget must be non-negative")
    if isinstance(conviction, bool) or not isinstance(conviction, int) or not 1 <= conviction <= 5:
        raise PolicyError("conviction must be an integer from 1 to 5")

    coverage = coverage_policy_view(analyst_coverage_count, policy=current)
    effective_conviction = conviction - coverage["conviction_discount_levels"]
    eligible = effective_conviction >= current["minimum_open_conviction"]
    coefficient = (
        current["conviction_coefficients"][str(effective_conviction)] if eligible else 0.0
    )
    nav_limit = nav * current["single_position_nav_cap"]
    budget_limit = budget * coefficient
    maximum = min(nav_limit, budget_limit) if eligible else 0.0
    return {
        "policy_version": current["policy_version"],
        "eligible_to_open": eligible,
        "input_conviction": conviction,
        "effective_conviction": effective_conviction,
        "conviction_coefficient": coefficient,
        "nav_limit": nav_limit,
        "high_risk_budget_limit": budget_limit,
        "maximum_position": maximum,
        "coverage_view": coverage,
    }


def check_factor_exposure(
    factor: str,
    *,
    current_exposure: float,
    proposed_addition: float,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    current = validate_policy(policy) if policy is not None else load_policy()
    if factor not in current["factor_exposure_caps"]:
        raise PolicyError(f"unknown factor exposure: {factor}")
    existing = _ratio(current_exposure, "current_exposure", allow_zero=True)
    addition = _ratio(proposed_addition, "proposed_addition", allow_zero=True)
    projected = existing + addition
    cap = current["factor_exposure_caps"][factor]
    return {
        "policy_version": current["policy_version"],
        "factor": factor,
        "cap": cap,
        "projected_exposure": projected,
        "within_cap": projected <= cap,
    }


def holding_action(*, days_held: int, exit_triggered: bool,
                   policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    current = validate_policy(policy) if policy is not None else load_policy()
    if isinstance(days_held, bool) or not isinstance(days_held, int) or days_held < 0:
        raise PolicyError("days_held must be a non-negative integer")
    if not isinstance(exit_triggered, bool):
        raise PolicyError("exit_triggered must be boolean")
    return {
        "policy_version": current["policy_version"],
        "action": (
            "review_exit_now"
            if exit_triggered
            else "minimum_holding_period"
            if days_held < current["minimum_holding_days"]
            else "normal_review"
        ),
        "minimum_holding_days": current["minimum_holding_days"],
    }
