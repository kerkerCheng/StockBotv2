"""Fixed beta universe and numeric policy are validated before runtime use。"""
from __future__ import annotations

import copy

import pytest

from decision_lab.beta_policy import (
    BetaPolicyError,
    load_beta_policy,
    unique_benchmarks,
    validate_beta_policy,
)


def test_repository_beta_policy_has_fourteen_instruments_and_eleven_series() -> None:
    policy = load_beta_policy()

    assert policy["mode"] == "paper_observation"
    assert policy["schema_version"] == "beta-policy-v2"
    assert policy["capital_scope"] == "shared_cash_pool"
    assert set(policy["capital"]) == {
        "cash_bucket_aliases",
        "authority_max_age_days",
        "fx_max_age_hours",
    }
    assert len(policy["instruments"]) == 14
    assert len(unique_benchmarks(policy)) == 11
    by_ticker = {item["ticker"]: item for item in policy["instruments"]}
    assert by_ticker["TQQQ"]["benchmark_key"] == by_ticker["QQQ"]["benchmark_key"]
    assert by_ticker["TQQQ"]["leverage_multiple"] == 3.0
    assert {
        by_ticker[ticker]["benchmark_key"]
        for ticker in ("0050.TW", "006208.TW", "00631L.TW")
    } == {"tw50"}
    assert by_ticker["00631L.TW"]["leverage_multiple"] == 2.0
    assert "technology_proxy_load" not in by_ticker["QQQ"]
    assert "issuer_concentration_warning" in policy["risk"]
    assert "technology_effective_cap" not in policy["risk"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(mode="live"),
        lambda p: p["risk"].update(leveraged_nominal_warning=0.09),
        lambda p: p["signal"].update(allowed_paces=[0, 0.5, 1]),
        lambda p: p["instruments"].append(copy.deepcopy(p["instruments"][0])),
        lambda p: p["instruments"][0].update(leverage_multiple=3.0),
        lambda p: p["instruments"][1].update(benchmark_symbol="WRONG"),
    ],
)
def test_invalid_beta_policy_fails_closed(mutate) -> None:
    policy = load_beta_policy()
    mutate(policy)

    with pytest.raises(BetaPolicyError):
        validate_beta_policy(policy)


def test_policy_returns_detached_sorted_view() -> None:
    policy = load_beta_policy()
    reversed_policy = copy.deepcopy(policy)
    reversed_policy["instruments"].reverse()

    normalized = validate_beta_policy(reversed_policy)

    assert [item["priority"] for item in normalized["instruments"]] == sorted(
        item["priority"] for item in policy["instruments"]
    )
