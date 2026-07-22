from __future__ import annotations

from engine_c.market_data import build_fx_snapshot


def test_build_fx_snapshot_preserves_exact_direction_and_latest_rate() -> None:
    result = build_fx_snapshot(
        pair="SEK/USD",
        rows=[
            {"as_of": "2026-07-20T00:00:00+00:00", "rate": 0.10},
            {"as_of": "2026-07-21T00:00:00+00:00", "rate": 0.11},
        ],
        fetched_at="2026-07-21T01:00:00+00:00",
        source="fixture://fx",
    )

    assert result["status"] == "observed"
    assert result["pair"] == "SEK/USD"
    assert result["rate"] == 0.11
    assert result["source"] == "fixture://fx"


def test_build_fx_snapshot_rejects_malformed_or_empty_observations() -> None:
    malformed = build_fx_snapshot(
        pair="USDSEK",
        rows=[],
        fetched_at="2026-07-21T01:00:00+00:00",
        source="fixture://fx",
    )
    missing = build_fx_snapshot(
        pair="SEK/USD",
        rows=[{"as_of": "bad", "rate": 0}],
        fetched_at="2026-07-21T01:00:00+00:00",
        source="fixture://fx",
    )

    assert malformed["status"] == "malformed"
    assert missing["status"] == "missing"
