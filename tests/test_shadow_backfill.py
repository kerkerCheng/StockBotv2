"""Shadow 錨點的修復路徑：可重建，但不得用事後價格。

Shadow 記的是某個已知時刻的最後一個完整交易日收盤價——那是可重建的事實，
不是只有當下才有的真相。因此一次瞬時故障造成的空錨點應該可以修復（2026-08-08
實測 9 個 cohort 有 7 個沒有價格，其中包含股價隨後 +100% 以上的 co:axt）。

但修復不得變成挑價格：``tests/test_shadow_baseline.py`` 已鎖住 intake 路徑不做
事後回填，這裡是明確的修復路徑，同一條紀律必須成立。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from decision_lab.intake import capture_signal
from decision_lab.models import MarketObservation, SignalInput
from decision_lab.store import DecisionStore
from storage.relational import initialize_private_root


INCEPTION = "2026-07-29T00:59:55+00:00"


class UnavailableMarket:
    def observe(self, *_args, **_kwargs) -> MarketObservation:
        return MarketObservation(status="unavailable")


def _store(tmp_path: Path) -> DecisionStore:
    repo = tmp_path / "repo"
    repo.mkdir()
    private_root = repo / "library" / "private"
    initialize_private_root(private_root, repo_root=repo)
    return DecisionStore.open(
        private_root / "decision_lab" / "decision_lab.db",
        private_root=private_root,
        repo_root=repo,
    )


def _signal() -> SignalInput:
    return SignalInput(
        raw_text="raw lead",
        source_id="aleabitoreddit",
        source_uri="https://example.test/post",
        origin_event=INCEPTION,
        observed_at=INCEPTION,
        company_id="co:axt",
        research_ticker="AXTI",
        atomic_claim="InP substrate bottleneck",
        direction="long",
        expiry="2026-10-21T00:00:00+00:00",
        disproof="second qualified supplier announced",
        evidence_tier=4,
    )


def _snapshot(as_of: str, price: float = 42.76) -> dict:
    return {
        "status": "observed",
        "ticker": "AXTI",
        "price": price,
        "currency": "USD",
        "source": "backfill://yfinance/AXTI@2026-07-29",
        "as_of": as_of,
        "fetched_at": INCEPTION,
    }


def test_missing_anchor_can_be_rebuilt_from_a_pre_inception_close(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        captured = capture_signal(store, _signal(), market=UnavailableMarket())
        assert store.get_shadow(captured.cohort_id).status == "unavailable"

        rebuilt = store.backfill_shadow(
            captured.cohort_id,
            _snapshot("2026-07-28T00:00:00+00:00"),
            inception_at=INCEPTION,
            backfilled_at="2026-08-08T00:00:00+00:00",
            reason="inception 當時行情不可用",
        )

        assert rebuilt.status == "observed"
        assert rebuilt.price == pytest.approx(42.76)
        # 來源必須看得出這是重建而非即時觀測——它是可辯護的重建，不是重播。
        assert str(rebuilt.source).startswith("backfill://")
        events = [
            event
            for event in store.list_events(cohort_id=captured.cohort_id)
            if event.event_type == "shadow_backfilled"
        ]
        assert len(events) == 1
    finally:
        store.close()


def test_backfill_refuses_a_post_inception_price(tmp_path: Path) -> None:
    """Hindsight 防線：用 inception 之後的價格會把基準點往有利方向偷移。"""

    store = _store(tmp_path)
    try:
        captured = capture_signal(store, _signal(), market=UnavailableMarket())

        with pytest.raises(ValueError, match="hindsight"):
            store.backfill_shadow(
                captured.cohort_id,
                _snapshot("2026-07-31T00:00:00+00:00", price=60.43),
                inception_at=INCEPTION,
                backfilled_at="2026-08-08T00:00:00+00:00",
                reason="事後挑一個更低的基準",
            )

        assert store.get_shadow(captured.cohort_id).status == "unavailable"
    finally:
        store.close()


def test_backfill_never_overwrites_an_observed_anchor(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        captured = capture_signal(store, _signal(), market=UnavailableMarket())
        store.backfill_shadow(
            captured.cohort_id,
            _snapshot("2026-07-28T00:00:00+00:00"),
            inception_at=INCEPTION,
            backfilled_at="2026-08-08T00:00:00+00:00",
            reason="第一次修復",
        )

        with pytest.raises(ValueError, match="already observed"):
            store.backfill_shadow(
                captured.cohort_id,
                _snapshot("2026-07-27T00:00:00+00:00", price=47.88),
                inception_at=INCEPTION,
                backfilled_at="2026-08-08T01:00:00+00:00",
                reason="再修一次",
            )

        assert store.get_shadow(captured.cohort_id).price == pytest.approx(42.76)
    finally:
        store.close()
