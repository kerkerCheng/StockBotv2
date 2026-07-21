from __future__ import annotations

from datetime import datetime, timezone

import pytest

from engine_c.market_data import build_tradeability_snapshot


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
