"""固定 beta universe、數值 policy 與目標配置在使用前一律先驗證。"""
from __future__ import annotations

import copy

import pytest

from portfolio.policy import (
    BetaPolicyError,
    TargetAllocationError,
    instrument_price_key,
    load_beta_policy,
    load_target_allocation,
    unique_benchmarks,
    unique_technical_targets,
    validate_beta_policy,
    validate_target_allocation,
)


def test_repository_beta_policy_has_fourteen_instruments_and_eleven_series() -> None:
    policy = load_beta_policy()

    assert policy["mode"] == "paper_observation"
    assert policy["schema_version"] == "beta-policy-v3"
    assert policy["capital_scope"] == "shared_cash_pool"
    assert set(policy["capital"]) == {
        "cash_bucket_aliases",
        "authority_max_age_days",
        "fx_max_age_hours",
    }
    assert len(policy["instruments"]) == 14
    assert len(unique_benchmarks(policy)) == 11
    assert len(unique_technical_targets(policy)) == 14
    by_ticker = {item["ticker"]: item for item in policy["instruments"]}
    assert by_ticker["TQQQ"]["benchmark_key"] == by_ticker["QQQ"]["benchmark_key"]
    assert instrument_price_key(by_ticker["TQQQ"]) == "price:tqqq"
    assert instrument_price_key(by_ticker["QQQ"]) == "qqq"
    assert by_ticker["TQQQ"]["leverage_multiple"] == 3.0
    assert {
        by_ticker[ticker]["benchmark_key"]
        for ticker in ("0050.TW", "006208.TW", "00631L.TW")
    } == {"tw50"}
    assert by_ticker["00631L.TW"]["leverage_multiple"] == 2.0
    assert instrument_price_key(by_ticker["00631L.TW"]) == "price:00631l.tw"
    assert "technology_proxy_load" not in by_ticker["QQQ"]
    assert "issuer_concentration_warning" in policy["risk"]
    assert "technology_effective_cap" not in policy["risk"]


def test_signal_and_campaign_budget_are_gone_but_freshness_and_risk_remain() -> None:
    """2026-08-29 拔除技術訊號後，設定裡不得再有 pace／tier；風控 cap 全數保留。

    行情鮮度不是訊號，它是「這份價格還能不能顯示」的資料品質門檻，
    因此從 signal 區塊搬到獨立的 market_data。
    """
    policy = load_beta_policy()

    assert "signal" not in policy
    assert "campaign_budget_fraction_by_sleeve" not in policy
    assert policy["market_data"]["max_refresh_age_hours"] == 96
    for key in (
        "leveraged_nominal_warning",
        "leveraged_nominal_cap",
        "leveraged_effective_warning",
        "leveraged_effective_cap",
        "total_exposure_warning",
        "total_exposure_cap",
        "issuer_concentration_warning",
        "alpha_total_warning",
    ):
        assert key in policy["risk"], key
    assert "event_monitor" in policy["risk"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(mode="live"),
        # warning 必須 <= cap；取 cap 之上的值以避免寫死數字
        lambda p: p["risk"].update(
            leveraged_nominal_warning=p["risk"]["leveraged_nominal_cap"] + 0.01
        ),
        lambda p: p["market_data"].update(max_refresh_age_hours=1),
        # 訊號已拔除：把它加回來必須被 top-level 欄位比對擋下
        lambda p: p.update(signal={"baseline_pace": 0.25}),
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


def test_repository_target_allocation_covers_every_sleeve_and_sums_to_one() -> None:
    target = load_target_allocation()
    policy = load_beta_policy()

    assert target["schema_version"] == "target-allocation-v1"
    assert target["basis"] == "invested_non_cash"
    beta_sleeves = {str(item["sleeve"]) for item in policy["instruments"]}
    assert beta_sleeves < set(target["sleeves"]), "每個 beta sleeve 都必須有目標比例"
    assert set(target["sleeves"]) - beta_sleeves == {"alpha"}
    assert sum(item["target"] for item in target["sleeves"].values()) == pytest.approx(1.0)
    assert all(item["band"] > 0 for item in target["sleeves"].values())
    # 兩條相關性警告是輸出的一部分，不得被移除
    names = {item["name"] for item in target["correlation_warnings"]}
    assert len(names) == 2
    assert target["rebalancing"] == {
        "method": "new_money_only",
        "loan_tranche_excluded": True,
    }


@pytest.mark.parametrize(
    "mutate",
    [
        # 少一格 sleeve：不能安靜當成 0%，必須 fail closed
        lambda t: t["sleeves"].pop("alpha"),
        lambda t: t["sleeves"]["beta_core"].update(target=0.9),
        lambda t: t.update(basis="nav"),
        lambda t: t.update(correlation_warnings=[]),
        lambda t: t["rebalancing"].update(method="sell_to_rebalance"),
        lambda t: t["rebalancing"].update(loan_tranche_excluded=False),
    ],
)
def test_invalid_target_allocation_fails_closed(mutate) -> None:
    target = load_target_allocation()
    mutate(target)

    with pytest.raises(TargetAllocationError):
        validate_target_allocation(target)
