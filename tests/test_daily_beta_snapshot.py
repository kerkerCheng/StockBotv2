"""The scheduled beta entry is narrow, degraded-safe and public-output only。"""
from __future__ import annotations

import io
import json
import sqlite3

from decision_lab.beta_policy import load_beta_policy, unique_technical_targets
from engine_c.technical import ensure_technical_schema
from scripts.daily_beta_snapshot import run


NOW = "2026-07-28T00:00:00+00:00"


class NonClosingConnection:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        ensure_technical_schema(self.conn)

    def __getattr__(self, name):
        if name == "close":
            return lambda: None
        return getattr(self.conn, name)


def _observed(key: str, symbol: str):
    return {
        "benchmark_key": key,
        "provider_symbol": symbol,
        "session_date": "2026-07-27",
        "session_count": 300,
        "data_status": "observed",
        "close_raw": 100.0,
        "close_adjusted": 100.0,
        "return_1d": -0.01,
        "return_5d": -0.03,
        "return_20d": -0.08,
        "drawdown_252": -0.25,
        "rsi_14": 35.0,
        "macd_line": -1.0,
        "macd_signal": -1.1,
        "macd_histogram": 0.1,
        "macd_histogram_slope": 0.05,
        "sma_20": 102.0,
        "sma_50": 105.0,
        "sma_200": 98.0,
        "distance_sma_20": -0.02,
        "distance_sma_50": -0.05,
        "distance_sma_200": 0.02,
        "sma_50_slope_5": 0.01,
        "realized_vol_20": 0.3,
        "realized_vol_60": 0.25,
        "source": f"fixture://{key}",
        "series_digest": "a" * 64,
        "fetched_at": NOW,
        "blockers": [],
        "warnings": [],
    }


def _refresh(*, policy, conn):
    from engine_c.technical import append_technical_observation

    items = []
    for target in unique_technical_targets(policy):
        observation = _observed(target["benchmark_key"], target["benchmark_symbol"])
        observation_id = append_technical_observation(conn, observation)
        items.append(
            {
                "benchmark_key": target["benchmark_key"],
                "observation_id": observation_id,
                "data_status": "observed",
            }
        )
    return {
        "status": "ok",
        "observed_count": len(items),
        "total_count": len(items),
        "items": items,
    }


def _holdings():
    return [
        {
            "ticker": "CASH",
            "bucket": "cash",
            "market_value_base": 10.0,
            "nav_base": 100.0,
            "base_currency": "USD",
        },
        {
            "ticker": "LON:VWRA",
            "bucket": "大盤",
            "market_value_base": 90.0,
            "nav_base": 100.0,
            "base_currency": "USD",
        }
    ]


def _capital():
    common = {"as_of": "2026-07-28", "currency": "USD"}
    return [
        {
            **common,
            "record_id": "cash_floor_01",
            "capital_type": "cash_floor",
            "amount": "1",
        },
        {
            **common,
            "record_id": "credit_facility_01",
            "capital_type": "credit_facility",
            "limit_amount": "1000",
            "drawn_amount": "0",
            "annual_rate_pct": "3.1",
            "interest_accrual": "daily",
            "facility_term_years": "30",
            "repayment_structure": "interest_only_bullet_principal_at_maturity",
        },
    ]


def test_fixed_entry_runs_refresh_and_outputs_public_json() -> None:
    holder = NonClosingConnection()
    output = io.StringIO()

    code = run(
        ["--format", "json", "--as-of", NOW, "--no-record-risk"],
        stdout=output,
        policy=load_beta_policy(),
        conn_factory=lambda: holder,
        holdings_fetcher=_holdings,
        capital_fetcher=_capital,
        refresh_fn=_refresh,
    )
    payload = json.loads(output.getvalue())

    assert code == 0
    assert payload["refresh"]["status"] == "ok"
    assert payload["capital_scope"] == "shared_cash_pool"
    assert "self_funded_supported_range" in payload
    assert "sheet_conservative_range" not in payload
    assert "household_cash_supported_range" not in payload
    assert "contingent_credit_available" in payload
    assert payload["loan_funded_supported_range"]["status"] == "manual_review_required"
    assert len(payload["items"]) == 14
    assert "shares" not in output.getvalue()
    assert "private" not in output.getvalue()
    holder.conn.close()


def test_sheet_failure_keeps_technical_health_but_zeroes_ranges() -> None:
    holder = NonClosingConnection()
    output = io.StringIO()

    def broken_sheet():
        raise RuntimeError("secret path should not escape")

    code = run(
        ["--format", "json", "--as-of", NOW, "--no-record-risk"],
        stdout=output,
        policy=load_beta_policy(),
        conn_factory=lambda: holder,
        holdings_fetcher=broken_sheet,
        capital_fetcher=_capital,
        refresh_fn=_refresh,
    )
    payload = json.loads(output.getvalue())

    assert code == 0
    assert payload["status"] == "degraded"
    assert "holdings_unavailable" in payload["blockers"]
    assert all(item["supported_order_range_base"] == [0.0, 0.0] for item in payload["items"])
    assert "secret path" not in output.getvalue()
    holder.conn.close()
