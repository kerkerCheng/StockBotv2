from __future__ import annotations

from pathlib import Path

from decision_lab.intake import capture_signal
from decision_lab.models import MarketObservation, SignalInput
from decision_lab.store import DecisionStore
from storage.relational import initialize_private_root


class UnavailableMarket:
    def observe(self, *_args, **_kwargs) -> MarketObservation:
        return MarketObservation(status="unavailable")


class LaterMarket:
    def observe(self, *_args, **_kwargs) -> MarketObservation:
        return MarketObservation(
            status="observed",
            ticker="SIVE.ST",
            price=99.0,
            currency="SEK",
            source="fixture://later",
            as_of="2026-07-22T00:00:00+00:00",
            fetched_at="2026-07-22T00:01:00+00:00",
        )


def _signal(observed_at: str) -> SignalInput:
    return SignalInput(
        raw_text="raw lead",
        source_id="aleabitoreddit",
        source_uri="https://example.test/post",
        origin_event=observed_at,
        observed_at=observed_at,
        company_id="co:sivers_semiconductors",
        research_ticker="SIVE.ST",
        atomic_claim="CW laser bottleneck",
        direction="long",
        expiry="2026-10-21T00:00:00+00:00",
        disproof="qualified alternative",
        evidence_tier=4,
    )


def test_unavailable_inception_is_immutable_and_never_hindsight_backfilled(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    private_root = repo / "library" / "private"
    initialize_private_root(private_root, repo_root=repo)
    store = DecisionStore.open(
        private_root / "decision_lab" / "decision_lab.db",
        private_root=private_root,
        repo_root=repo,
    )
    try:
        first = capture_signal(
            store,
            _signal("2026-07-21T00:00:00+00:00"),
            market=UnavailableMarket(),
        )
        original = store.get_shadow(first.cohort_id)
        retry = capture_signal(
            store,
            _signal("2026-07-22T00:00:00+00:00"),
            market=LaterMarket(),
        )
        after = store.get_shadow(retry.cohort_id)

        assert original.status == "unavailable"
        assert original.price is None
        assert original.market_return_status == "unknown"
        assert after == original
        assert retry.shadow_created is False
    finally:
        store.close()
