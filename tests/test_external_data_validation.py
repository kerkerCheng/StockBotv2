from __future__ import annotations

import math

import pytest

from decision_lab.adapters.market import normalize_fx_snapshot, normalize_market_snapshot
from decision_lab.context import derive_runway


NOW = "2026-07-21T12:00:00+00:00"


def _market(**overrides):
    payload = {
        "status": "observed",
        "ticker": "SIVE.ST",
        "price": 2.5,
        "currency": "SEK",
        "adv20": 1_000_000.0,
        "as_of": "2026-07-21T10:00:00+00:00",
        "fetched_at": "2026-07-21T10:01:00+00:00",
        "unit_status": "ok",
        "source": "fixture://market",
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    ("overrides", "blocker"),
    [
        ({"price": math.nan}, "market_price_invalid"),
        ({"price": math.inf}, "market_price_invalid"),
        ({"price": -1}, "market_price_invalid"),
        ({"ticker": "COHR"}, "market_ticker_mismatch"),
        ({"currency": "USD"}, "market_currency_mismatch"),
        ({"unit_status": "corporate_action_stale"}, "market_unit_unverified"),
        ({"price": 1e12}, "market_price_anomaly"),
        ({"as_of": "2026-07-22T00:00:00+00:00"}, "market_timestamp_future"),
    ],
)
def test_market_anomalies_are_quarantined(overrides, blocker) -> None:
    normalized = normalize_market_snapshot(
        _market(**overrides),
        expected_ticker="SIVE.ST",
        expected_currency="SEK",
        evaluation_at=NOW,
    )

    assert normalized["status"] == "quarantined"
    assert blocker in normalized["blockers"]
    assert normalized.get("price") is None


def test_market_and_fx_staleness_use_observation_time_not_fetch_time() -> None:
    market = normalize_market_snapshot(
        _market(
            as_of="2026-07-18T00:00:00+00:00",
            fetched_at="2026-07-21T11:59:00+00:00",
        ),
        expected_ticker="SIVE.ST",
        expected_currency="SEK",
        evaluation_at=NOW,
    )
    fx = normalize_fx_snapshot(
        {
            "status": "observed",
            "pair": "SEK/USD",
            "rate": 0.1,
            "as_of": "2026-07-18T00:00:00+00:00",
            "fetched_at": "2026-07-21T11:59:00+00:00",
            "source": "fixture://fx",
        },
        expected_pair="SEK/USD",
        evaluation_at=NOW,
    )

    assert market["status"] == "stale"
    assert fx["status"] == "stale"


def test_market_access_block_survives_normalization_as_retry_required() -> None:
    normalized = normalize_market_snapshot(
        {
            "status": "unavailable",
            "blockers": ["market_history_unavailable"],
            "failure_class": "access_blocked",
        },
        expected_ticker="AXTI",
        expected_currency="USD",
        evaluation_at=NOW,
    )

    assert normalized["status"] == "unavailable"
    assert normalized["failure_class"] == "access_blocked"
    assert "market_access_blocked_retry_required" in normalized["blockers"]


def test_runway_self_funding_negative_fcf_and_manual_required_paths() -> None:
    self_funding = derive_runway(
        {
            "cash_and_equivalents": 120.0,
            "total_debt": 20.0,
            "free_cash_flow_ttm": 1.0,
            "source": "fixture://filing",
            "as_of": "2026-06-30T00:00:00+00:00",
        }
    )
    burning = derive_runway(
        {
            "cash_and_equivalents": 120.0,
            "total_debt": 20.0,
            "free_cash_flow_ttm": -60.0,
            "source": "fixture://filing",
            "as_of": "2026-06-30T00:00:00+00:00",
        }
    )
    missing = derive_runway(
        {
            "cash_and_equivalents": None,
            "total_debt": 20.0,
            "free_cash_flow_ttm": -60.0,
        }
    )

    assert self_funding["status"] == "self_funding"
    assert burning["status"] == "calculated"
    assert burning["runway_months"] == pytest.approx(24.0)
    assert missing == {"status": "manual_required", "runway_months": None}


def test_manual_runway_requires_source_and_as_of() -> None:
    with pytest.raises(ValueError, match="source"):
        derive_runway(
            {"cash_and_equivalents": None},
            manual_observation={
                "cash_and_equivalents": 10.0,
                "total_debt": 1.0,
                "free_cash_flow_ttm": -5.0,
            },
        )
