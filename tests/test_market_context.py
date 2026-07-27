from __future__ import annotations

from datetime import datetime, timezone
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from engine_c.market_data import build_tradeability_snapshot, get_tradeability_snapshot


def test_tradeability_snapshot_uses_actual_latest_history_timestamp_and_adv20() -> None:
    rows = [
        {
            "as_of": f"2026-07-{day:02d}T16:00:00+00:00",
            "close": float(day),
            "volume": float(day * 100),
        }
        for day in range(1, 22)
    ]

    result = build_tradeability_snapshot(
        ticker="FRA:2DG",
        currency="EUR",
        rows=rows,
        fetched_at="2026-07-21T17:00:00+00:00",
        source="fixture://history",
    )

    assert result["status"] == "observed"
    assert result["as_of"] == "2026-07-21T16:00:00+00:00"
    assert result["price"] == 21.0
    assert result["adv20"] == pytest.approx(sum(day * 100 for day in range(2, 22)) / 20)


@pytest.mark.parametrize(
    "rows",
    [
        [{"as_of": "not-a-time", "close": 10.0, "volume": 100.0}],
        [{"as_of": "2026-07-21T16:00:00+00:00", "close": float("nan"), "volume": 1.0}],
        [{"as_of": "2026-07-21T16:00:00+00:00", "close": 10.0, "volume": -1.0}],
    ],
)
def test_tradeability_snapshot_quarantines_invalid_history(rows) -> None:
    result = build_tradeability_snapshot(
        ticker="FRA:2DG",
        currency="EUR",
        rows=rows,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        source="fixture://history",
    )

    assert result["status"] == "quarantined"
    assert result["blockers"]


def test_tradeability_snapshot_requires_twenty_unique_sessions() -> None:
    rows = [
        {
            "as_of": f"2026-07-{day:02d}T16:00:00+00:00",
            "close": 10.0,
            "volume": 100.0,
        }
        for day in range(1, 20)
    ]
    rows.append(dict(rows[-1]))

    result = build_tradeability_snapshot(
        ticker="FRA:2DG",
        currency="EUR",
        rows=rows,
        fetched_at="2026-07-21T17:00:00+00:00",
        source="fixture://history",
    )

    assert result["status"] == "quarantined"
    assert "market_history_insufficient_sessions" in result["blockers"]


def test_execution_symbol_uses_yahoo_alias_but_preserves_canonical_ticker(
    monkeypatch,
) -> None:
    requested = []
    index = pd.date_range("2026-06-01", periods=25, freq="B", tz="Europe/Berlin")
    history = pd.DataFrame({
        "Close": [2.0 + i / 100 for i in range(25)],
        "Volume": [1000 + i for i in range(25)],
    }, index=index)

    class FakeTicker:
        def __init__(self, symbol):
            requested.append(symbol)

        def history(self, **_kwargs):
            return history

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=FakeTicker))

    result = get_tradeability_snapshot("FRA:2DG", "EUR")

    assert requested == ["2DG.F"]
    assert result["status"] == "observed"
    assert result["ticker"] == "FRA:2DG"
    assert result["source"] == "yfinance://history/2DG.F"
