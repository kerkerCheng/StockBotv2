"""Household capital authority stays point-in-time, cash-only and fail-closed。"""
from __future__ import annotations

import copy

import pytest

from decision_lab.capital_authority import build_household_capital_view


NOW = "2026-07-28T00:00:00+00:00"


def _rows(*, currency: str = "USD", drawn: str = "0") -> list[dict]:
    common = {
        "as_of": "2026-07-28",
        "confirmation_status": "user_confirmed",
        "currency": currency,
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
            "amount": "10",
        },
        {
            **common,
            "record_id": "planned_outflows_24m_01",
            "capital_type": "planned_outflows_reserve_24m",
            "amount": "5",
        },
        {
            **common,
            "record_id": "credit_facility_01",
            "capital_type": "contingent_liquidity_credit_facility",
            "confirmation_status": "user_confirmed_partial",
            "limit_amount": "1000",
            "drawn_amount": drawn,
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


def _fx(pair: str, evaluation_at: str) -> dict:
    return {
        "status": "observed",
        "pair": pair,
        "rate": 1.0,
        "as_of": evaluation_at,
        "fetched_at": evaluation_at,
        "source": f"fixture://{pair}",
    }


def _build(rows=None, **kwargs):
    return build_household_capital_view(
        authority_rows=_rows() if rows is None else rows,
        portfolio_cash_base=100.0,
        portfolio_nav_base=1000.0,
        base_currency="USD",
        evaluation_at=NOW,
        alpha_reserve_nav_fraction=0.03,
        max_authority_age_days=90,
        max_fx_age_hours=96,
        fx_fetcher=_fx,
        **kwargs,
    )


def test_capital_view_uses_portfolio_cash_once_and_keeps_credit_contingent() -> None:
    view = _build()

    assert view["status"] == "partial"
    assert view["household_cash"]["status"] == "available"
    assert view["household_cash"]["deployable_cash_base"] == pytest.approx(55.0)
    assert view["contingent_credit_available"]["undrawn_amount_base"] == 1000.0
    assert view["contingent_credit_available"]["terms_status"] == "incomplete"
    assert view["loan_funded_supported_range"]["status"] == "manual_review_required"
    assert view["loan_funded_supported_range"]["range_base"] is None
    assert view["fx"]["USD/USD"]["source"] == "identity://same-currency"


def test_capital_view_digest_changes_with_authority_scalar() -> None:
    first = _build()
    changed = _rows()
    changed[1]["amount"] = "11"
    second = _build(changed)

    assert len(first["digest"]) == 64
    assert first["digest"] != second["digest"]


def test_duplicate_or_stale_authority_fails_household_cash_closed() -> None:
    duplicate = _rows()
    duplicate.append(copy.deepcopy(duplicate[1]))
    stale = _rows()
    for row in stale:
        row["as_of"] = "2025-01-01"

    duplicate_view = _build(duplicate)
    stale_view = _build(stale)

    assert duplicate_view["household_cash"]["deployable_cash_base"] == 0.0
    assert "capital_authority_record_id_invalid" in duplicate_view["blockers"]
    assert stale_view["household_cash"]["deployable_cash_base"] == 0.0
    assert "capital_authority_stale" in stale_view["blockers"]


def test_wrong_direction_fx_fails_but_valid_drawn_debt_is_telemetry() -> None:
    rows = _rows(currency="TWD")

    def wrong_fx(_pair: str, evaluation_at: str) -> dict:
        return {
            "status": "observed",
            "pair": "USD/TWD",
            "rate": 32.0,
            "as_of": evaluation_at,
            "fetched_at": evaluation_at,
            "source": "fixture://wrong",
        }

    fx_view = build_household_capital_view(
        authority_rows=rows,
        portfolio_cash_base=100.0,
        portfolio_nav_base=1000.0,
        base_currency="USD",
        evaluation_at=NOW,
        alpha_reserve_nav_fraction=0.03,
        max_authority_age_days=90,
        max_fx_age_hours=96,
        fx_fetcher=wrong_fx,
    )
    drawn_view = _build(_rows(drawn="1"))

    assert fx_view["household_cash"]["deployable_cash_base"] == 0.0
    assert "operating_floor_fx_unavailable" in fx_view["blockers"]
    assert drawn_view["household_cash"]["deployable_cash_base"] == pytest.approx(55.0)
    assert drawn_view["drawn_debt_base"] == pytest.approx(1.0)
    assert "drawn_debt_present" in drawn_view["warnings"]


def test_drawn_balance_with_missing_fx_does_not_invent_loan_leverage() -> None:
    rows = _rows()
    rows[-1]["currency"] = "EUR"
    rows[-1]["drawn_amount"] = "1"

    view = build_household_capital_view(
        authority_rows=rows,
        portfolio_cash_base=100.0,
        portfolio_nav_base=1000.0,
        base_currency="USD",
        evaluation_at=NOW,
        alpha_reserve_nav_fraction=0.03,
        max_authority_age_days=90,
        max_fx_age_hours=96,
        fx_fetcher=None,
    )

    assert view["household_cash"]["deployable_cash_base"] == pytest.approx(55.0)
    assert view["drawn_debt_base"] is None
    assert "credit_fx_unavailable" in view["contingent_credit_available"]["blockers"]


def test_credit_limit_never_changes_household_cash() -> None:
    original = _build()
    larger = _rows()
    larger[-1]["limit_amount"] = "999999"
    changed = _build(larger)

    assert original["household_cash"]["deployable_cash_base"] == changed["household_cash"]["deployable_cash_base"]
