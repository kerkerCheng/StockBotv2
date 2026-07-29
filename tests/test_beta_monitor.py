"""Engine D beta monitor separates timing from hard contribution capacity。"""
from __future__ import annotations

from copy import deepcopy

import pytest

from decision_lab.beta_monitor import build_beta_monitor, render_beta_monitor_markdown, signal_state
from decision_lab.beta_policy import load_beta_policy, unique_benchmarks


NOW = "2026-07-28T00:00:00+00:00"


def _observation(
    key: str,
    *,
    drawdown: float = -0.25,
    rsi: float = 35.0,
    histogram_slope: float = 0.1,
    distance_200: float = 0.02,
    slope_50: float = 0.01,
):
    return {
        "benchmark_key": key,
        "data_status": "observed",
        "fetched_at": NOW,
        "session_date": "2026-07-27",
        "return_1d": -0.01,
        "return_5d": -0.03,
        "return_20d": -0.08,
        "rsi_14": rsi,
        "drawdown_252": drawdown,
        "macd_histogram": -0.2,
        "macd_histogram_slope": histogram_slope,
        "distance_sma_20": -0.03,
        "distance_sma_50": -0.05,
        "distance_sma_200": distance_200,
        "sma_50_slope_5": slope_50,
        "realized_vol_20": 0.3,
        "realized_vol_60": 0.25,
        "blockers": [],
    }


def _observations(policy, **kwargs):
    return {
        item["benchmark_key"]: _observation(item["benchmark_key"], **kwargs)
        for item in unique_benchmarks(policy)
    }


def _holdings(*, cash: float = 10.0, tqqq: float = 0.0, other: list[dict] | None = None):
    other_rows = list(other or [])
    residual = 100.0 - cash - tqqq - sum(float(row["market_value_base"]) for row in other_rows)
    rows = [
        {
            "ticker": "CASH",
            "bucket": "cash",
            "market_value_base": cash,
            "nav_base": 100.0,
            "base_currency": "USD",
        },
        {
            "ticker": "TQQQ",
            "bucket": "槓桿",
            "market_value_base": tqqq,
            "nav_base": 100.0,
            "base_currency": "USD",
        },
    ]
    if residual > 0:
        rows.append(
            {
                "ticker": "LON:VWRA",
                "bucket": "大盤",
                "market_value_base": residual,
                "nav_base": 100.0,
                "base_currency": "USD",
            }
        )
    rows.extend(other_rows)
    return rows


def _capital_rows(*, credit_limit: str = "1000") -> list[dict]:
    common = {
        "as_of": "2026-07-28",
        "confirmation_status": "user_confirmed",
        "currency": "USD",
    }
    return [
        {
            **common,
            "record_id": "portfolio_cash_authority_01",
            "capital_type": "portfolio_cash_authority",
            "amount": "",
            "amount_source": "Portfolio.cash_twd+Portfolio.cash_usd",
        },
        {
            **common,
            "record_id": "operating_floor_01",
            "capital_type": "operating_floor",
            "amount": "1",
        },
        {
            **common,
            "record_id": "planned_outflows_24m_01",
            "capital_type": "planned_outflows_reserve_24m",
            "amount": "0",
        },
        {
            **common,
            "record_id": "credit_facility_01",
            "capital_type": "contingent_liquidity_credit_facility",
            "confirmation_status": "user_confirmed_partial",
            "limit_amount": credit_limit,
            "drawn_amount": "0",
            "annual_rate_pct": "3.1",
            "interest_accrual": "daily",
            "availability": "on_demand",
            "facility_term_years": "30",
            "repayment_structure": "revolving_draw_repay",
            "minimum_payment_status": "exists_unverified",
            "minimum_payment_terms": "",
            "deployment_mode": "manual_review_only",
            "automatic_deployment": "FALSE",
            "include_in_net_investable_capital": "FALSE",
            "include_in_deployable_cash": "FALSE",
        },
    ]


def test_signal_state_uses_macd_and_ma_as_pace_guard_not_extra_votes() -> None:
    policy = load_beta_policy()

    bullish = signal_state(_observation("qqq"), policy)
    bearish = signal_state(
        _observation("qqq", histogram_slope=0.1, distance_200=-0.1, slope_50=-0.02),
        policy,
    )

    assert bullish["tier"] == "deep"
    assert bullish["pace"] == 0.5
    assert bearish["tier"] == "deep"
    assert bearish["pace"] == 0.25


def test_ranges_share_one_frozen_deployable_cash_budget() -> None:
    policy = load_beta_policy()
    observations = _observations(policy)
    histories = {key: [value] for key, value in observations.items()}

    report = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=histories,
        holdings_rows=_holdings(cash=10.0),
        as_of=NOW,
        policy=policy,
    )

    reviews = [item for item in report["items"] if item["action"] == "CONTRIBUTE REVIEW"]
    assert report["portfolio"]["deployable_cash_base"] == pytest.approx(2.0)
    assert sum(item["supported_order_range_base"][1] for item in reviews) <= 2.0
    assert report["portfolio"]["allocated_review_base"] == pytest.approx(
        sum(item["supported_order_range_base"][1] for item in reviews)
    )
    assert report["capital_scope"] == "sheet_conservative"
    assert report["policy_mode"] == "paper_observation"


def test_household_cash_runs_a_separate_range_without_using_credit() -> None:
    policy = load_beta_policy()
    observations = _observations(policy)
    histories = {key: [value] for key, value in observations.items()}

    report = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=histories,
        holdings_rows=_holdings(cash=10.0),
        capital_authority_rows=_capital_rows(),
        as_of=NOW,
        policy=policy,
    )
    larger_credit = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=histories,
        holdings_rows=_holdings(cash=10.0),
        capital_authority_rows=_capital_rows(credit_limit="999999"),
        as_of=NOW,
        policy=policy,
    )

    assert report["sheet_conservative_range"][1] <= 2.0
    assert report["household_cash_supported_range"][1] <= 6.0
    assert report["household_cash_supported_range"][1] >= report["sheet_conservative_range"][1]
    assert report["household_cash_supported_range"] == larger_credit["household_cash_supported_range"]
    assert report["contingent_credit_available"]["undrawn_amount_base"] == 1000.0
    assert report["loan_funded_supported_range"]["status"] == "manual_review_required"
    assert all(
        item["supported_order_range_base"] == item["sheet_conservative_order_range_base"]
        for item in report["items"]
    )


def test_missing_household_authority_does_not_zero_phase_one_range() -> None:
    policy = load_beta_policy()
    observations = _observations(policy)
    histories = {key: [value] for key, value in observations.items()}

    report = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=histories,
        holdings_rows=_holdings(cash=10.0),
        capital_authority_rows=None,
        as_of=NOW,
        policy=policy,
    )

    assert report["sheet_conservative_range"][1] > 0
    assert report["household_cash_supported_range"] == [0.0, 0.0]
    assert "capital_authority_unavailable" in report["blockers"]
    rendered = render_beta_monitor_markdown(report)
    assert "Household cash 可部署" in rendered
    assert "LON:VWRA — observed｜" not in rendered


def test_leverage_effective_cap_binds_even_when_signal_is_extreme() -> None:
    policy = load_beta_policy()
    observations = _observations(policy, drawdown=-0.5, rsi=15.0)
    histories = {key: [value] for key, value in observations.items()}
    # 8 nominal TQQQ already equals 24 effective, beyond the 20 effective cap.
    report = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=histories,
        holdings_rows=_holdings(cash=50.0, tqqq=8.0),
        as_of=NOW,
        policy=policy,
    )

    tqqq = next(item for item in report["items"] if item["ticker"] == "TQQQ")
    assert tqqq["signal_pace"] == 1.0
    assert tqqq["action"] == "PAUSE CONTRIBUTION"
    assert tqqq["supported_order_range_base"] == [0.0, 0.0]
    assert "leveraged_effective_capacity" in tqqq["binding_constraints"]


def test_sequential_allocations_also_share_the_technology_capacity() -> None:
    policy = load_beta_policy()
    observations = _observations(policy)
    histories = {key: [value] for key, value in observations.items()}
    rows = _holdings(
        cash=35.0,
        other=[
            {
                "ticker": "UNMAPPED",
                "bucket": "觀察",
                "market_value_base": 65.0,
                "nav_base": 100.0,
                "base_currency": "USD",
            }
        ],
    )

    report = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=histories,
        holdings_rows=rows,
        as_of=NOW,
        policy=policy,
    )
    by_ticker = {item["ticker"]: item for item in policy["instruments"]}
    technology_addition = sum(
        item["supported_order_range_base"][1]
        * by_ticker[item["ticker"]]["leverage_multiple"]
        * by_ticker[item["ticker"]]["technology_proxy_load"]
        for item in report["items"]
    )

    assert technology_addition <= 5.000001


def test_missing_sheet_or_partial_technical_data_returns_zero_ranges() -> None:
    policy = load_beta_policy()
    observations = _observations(policy)
    observations["dram"] = {
        "data_status": "insufficient_history",
        "fetched_at": NOW,
        "blockers": ["technical_history_insufficient_252_sessions"],
    }

    no_sheet = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark={},
        holdings_rows=None,
        as_of=NOW,
        policy=policy,
    )
    with_sheet = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark={key: [value] for key, value in observations.items()},
        holdings_rows=_holdings(),
        as_of=NOW,
        policy=policy,
    )

    assert no_sheet["status"] == "degraded"
    assert all(item["supported_order_range_base"] == [0.0, 0.0] for item in no_sheet["items"])
    dram = next(item for item in with_sheet["items"] if item["ticker"] == "DRAM")
    assert dram["action"] == "PAUSE CONTRIBUTION"
    assert "technical_history_insufficient_252_sessions" in dram["blockers"]


def test_same_signal_respects_repeat_cadence() -> None:
    policy = load_beta_policy()
    observation = _observation("qqq")
    observations = _observations(policy)
    histories = {key: [value] for key, value in observations.items()}
    histories["qqq"] = [deepcopy(observation) for _ in range(2)]

    report = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=histories,
        holdings_rows=_holdings(cash=20.0),
        as_of=NOW,
        policy=policy,
    )

    qqq = next(item for item in report["items"] if item["ticker"] == "QQQ")
    tqqq = next(item for item in report["items"] if item["ticker"] == "TQQQ")
    assert qqq["review_cadence"]["reason"] == "cooldown"
    assert qqq["action"] == "HOLD"
    assert tqqq["action"] == "HOLD"


def test_known_tsmc_lower_bound_pauses_taiwan_related_additions() -> None:
    policy = load_beta_policy()
    observations = _observations(policy)
    histories = {key: [value] for key, value in observations.items()}
    rows = _holdings(
        cash=50.0,
        other=[
            {
                "ticker": "2330.TW",
                "bucket": "觀察",
                "market_value_base": 36.0,
                "nav_base": 100.0,
                "base_currency": "USD",
            }
        ],
    )

    report = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark=histories,
        holdings_rows=rows,
        as_of=NOW,
        policy=policy,
    )

    taiwan = [
        item
        for item in report["items"]
        if item["ticker"] in {"0050.TW", "006208.TW", "00631L.TW", "2330.TW"}
    ]
    assert all(item["supported_order_range_base"][1] == 0 for item in taiwan)
    assert any("single_company_capacity:TSMC" in item["binding_constraints"] for item in taiwan)


def test_markdown_is_aggregate_and_preserves_human_boundary() -> None:
    policy = load_beta_policy()
    observations = _observations(policy)
    report = build_beta_monitor(
        observations_by_benchmark=observations,
        history_by_benchmark={key: [value] for key, value in observations.items()},
        holdings_rows=_holdings(),
        as_of=NOW,
        policy=policy,
    )

    rendered = render_beta_monitor_markdown(report)

    assert "Sheet-only conservative" in rendered
    assert "## TL;DR" in rendered
    assert "退休淨終值" in rendered
    assert "technical signal 只決定新增的 timing／pace" in rendered
    assert "月息不得依賴被迫賣出 beta" in rendered
    assert "1日 -1.0%｜5日 -3.0%｜20日 -8.0%" in rendered
    assert "## 主力 ETF／權值" in rendered
    assert rendered.index("QQQ") < rendered.index("TQQQ")
    assert "不代表已核准、已下單或已寫回" in rendered
    assert "shares" not in rendered
