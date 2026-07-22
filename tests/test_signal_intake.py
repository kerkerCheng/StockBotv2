from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from decision_lab.intake import (
    SignalSourceRegistry,
    SourcePolicy,
    capture_signal,
)
from decision_lab.models import MarketObservation, SignalInput
from decision_lab.store import DecisionStore
from storage.relational import initialize_private_root


class FixedMarket:
    def observe(self, *_args, **_kwargs) -> MarketObservation:
        return MarketObservation(
            status="observed",
            ticker="SIVE.ST",
            price=2.5,
            currency="SEK",
            source="fixture://market/sive",
            as_of="2026-07-21T08:00:00+00:00",
            fetched_at="2026-07-21T08:01:00+00:00",
        )


class UnexpectedMarket:
    def observe(self, *_args, **_kwargs) -> MarketObservation:
        raise AssertionError("unresolved identity must not query market data")


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


def _signal(**overrides) -> SignalInput:
    base = SignalInput(
        raw_text="Sivers controls a key CW laser bottleneck",
        source_id="aleabitoreddit",
        source_uri="https://example.test/post/1",
        origin_event="post-1",
        observed_at="2026-07-21T08:00:00+00:00",
        company_id="co:sivers_semiconductors",
        research_ticker="SIVE.ST",
        atomic_claim="Sivers controls a key CW laser bottleneck",
        direction="long",
        expiry="2026-10-21T00:00:00+00:00",
        disproof="A qualified alternative wins the same production socket",
        evidence_tier=4,
    )
    return replace(base, **overrides)


def test_repeated_thesis_has_one_probe_shadow_and_three_signal_observations(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        results = [
            capture_signal(
                store,
                _signal(
                    raw_text=f"restatement {index}",
                    source_uri=f"https://example.test/post/{index}",
                    origin_event=f"post-{index}",
                    observed_at=f"2026-07-{20 + index:02d}T08:00:00+00:00",
                ),
                market=FixedMarket(),
            )
            for index in range(1, 4)
        ]

        cohort_id = results[0].cohort_id
        assert {result.cohort_id for result in results} == {cohort_id}
        assert [result.shadow_created for result in results] == [True, False, False]
        assert len(store.list_events(cohort_id, event_type="qualified_signal")) == 3
        assert store.count_shadows(cohort_id) == 1
        assert store.get_probe(cohort_id).status == "active"
    finally:
        store.close()


def test_claim_or_expiry_changes_create_distinct_probe(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        first = capture_signal(store, _signal(), market=FixedMarket())
        different_claim = capture_signal(
            store,
            _signal(
                atomic_claim="Sivers has a named production order",
                origin_event="post-2",
            ),
            market=FixedMarket(),
        )
        different_expiry = capture_signal(
            store,
            _signal(expiry="2027-01-01T00:00:00+00:00", origin_event="post-3"),
            market=FixedMarket(),
        )

        assert len({first.cohort_id, different_claim.cohort_id, different_expiry.cohort_id}) == 3
    finally:
        store.close()


def test_equivalent_expiry_offsets_share_one_probe_and_shadow(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        first = capture_signal(store, _signal(), market=FixedMarket())
        retry = capture_signal(
            store,
            _signal(
                expiry="2026-10-20T20:00:00-04:00",
                origin_event="post-offset",
            ),
            market=FixedMarket(),
        )

        assert retry.cohort_id == first.cohort_id
        assert retry.shadow_created is False
        assert store.count_shadows(first.cohort_id) == 1
    finally:
        store.close()


def test_registry_status_never_upgrades_raw_evidence_or_graph_admission(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        result = capture_signal(store, _signal(), market=FixedMarket())
        probe = store.get_probe(result.cohort_id)

        assert result.source_status == "active"
        assert result.evidence_tier == 4
        assert probe.evidence_admission_status == "lead_only"
        assert store.table_count("paper_events") == 0
    finally:
        store.close()


def test_later_untraced_restatement_does_not_downgrade_traced_admission(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        first = capture_signal(
            store,
            _signal(source_traced=True, evidence_tier=3),
            market=FixedMarket(),
        )
        capture_signal(
            store,
            _signal(
                source_traced=False,
                evidence_tier=4,
                observed_at="2026-07-22T08:00:00+00:00",
                origin_event="post-2",
            ),
            market=FixedMarket(),
        )

        assert store.get_probe(first.cohort_id).evidence_admission_status == "eligible_for_review"
    finally:
        store.close()


def test_probe_gate_and_automatic_capture_permission_fail_before_write(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    candidate_registry = SignalSourceRegistry(
        version=1,
        policies=(
            SourcePolicy(
                source_id="aleabitoreddit",
                status="candidate",
                research_priority=1,
                auto_capture=False,
            ),
        ),
    )
    try:
        with pytest.raises(ValueError, match="disproof"):
            capture_signal(store, _signal(disproof=""), market=FixedMarket())
        with pytest.raises(ValueError, match="automatic capture"):
            capture_signal(
                store,
                _signal(capture_mode="automatic"),
                market=FixedMarket(),
                source_registry=candidate_registry,
            )

        assert store.table_count("decision_cohorts") == 0
        assert store.table_count("shadow_observations") == 0
    finally:
        store.close()


def test_opt_in_incomplete_unresolved_signal_still_captures_cohort_and_shadow(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    signal = _signal(
        atomic_claim="",
        disproof="",
        company_id=None,
        research_ticker=None,
        source_uri="signal:7a86d75b5c0f",
    )
    try:
        first = capture_signal(
            store,
            signal,
            market=UnexpectedMarket(),
            allow_incomplete=True,
            allow_unresolved=True,
        )
        retry = capture_signal(
            store,
            signal,
            market=UnexpectedMarket(),
            allow_incomplete=True,
            allow_unresolved=True,
        )

        assert first.company_id is None
        assert first.research_ticker is None
        assert first.execution_symbol is None
        assert retry.cohort_id == first.cohort_id
        assert [first.shadow_created, retry.shadow_created] == [True, False]
        assert store.get_shadow(first.cohort_id).status == "unavailable"
        assert len(store.list_events(first.cohort_id, event_type="qualified_signal")) == 1
    finally:
        store.close()


def test_unresolved_cohort_identity_binding_is_monotonic_and_audited(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        captured = capture_signal(
            store,
            _signal(company_id=None, research_ticker=None),
            market=UnexpectedMarket(),
            allow_unresolved=True,
        )

        bound = store.bind_cohort_identity(
            captured.cohort_id,
            company_id="co:sivers_semiconductors",
            research_ticker="SIVE.ST",
            resolved_at="2026-07-21T08:05:00+00:00",
        )
        retry = store.bind_cohort_identity(
            captured.cohort_id,
            company_id="co:sivers_semiconductors",
            research_ticker="SIVE.ST",
            resolved_at="2026-07-21T08:06:00+00:00",
        )

        assert bound == retry
        assert bound.company_id == "co:sivers_semiconductors"
        assert bound.research_ticker == "SIVE.ST"
        assert len(store.list_events(captured.cohort_id, event_type="identity_resolved")) == 1
        with pytest.raises(ValueError, match="remap"):
            store.bind_cohort_identity(
                captured.cohort_id,
                company_id="co:axt",
                research_ticker="AXTI",
                resolved_at="2026-07-21T08:07:00+00:00",
            )
    finally:
        store.close()


def test_future_market_price_never_becomes_shadow_inception(tmp_path: Path) -> None:
    store = _store(tmp_path)

    class FutureMarket(FixedMarket):
        def observe(self, *_args, **_kwargs) -> MarketObservation:
            return replace(
                super().observe(),
                as_of="2026-07-22T08:00:00+00:00",
                fetched_at="2026-07-22T08:01:00+00:00",
            )

    try:
        result = capture_signal(store, _signal(), market=FutureMarket())
        shadow = store.get_shadow(result.cohort_id)

        assert shadow.status == "unavailable"
        assert shadow.price is None
    finally:
        store.close()


@pytest.mark.parametrize(
    "changes",
    [
        {"ticker": "ERIC-B.ST"},
        {
            "as_of": "2020-07-21T08:00:00+00:00",
            "fetched_at": "2026-07-21T08:01:00+00:00",
        },
        {
            "as_of": "2026-07-21T08:00:00+00:00",
            "fetched_at": "2026-07-21T07:59:00+00:00",
        },
    ],
)
def test_wrong_security_stale_or_causally_invalid_shadow_price_is_unavailable(
    tmp_path: Path,
    changes: dict,
) -> None:
    store = _store(tmp_path)

    class InvalidMarket(FixedMarket):
        def observe(self, *_args, **_kwargs) -> MarketObservation:
            return replace(super().observe(), **changes)

    try:
        result = capture_signal(store, _signal(), market=InvalidMarket())
        assert store.get_shadow(result.cohort_id).status == "unavailable"
    finally:
        store.close()


@pytest.mark.parametrize(
    "overrides",
    [
        {"source_uri": "https://user:password@example.test/post/1"},
        {"source_uri": "https://example.test/post/1?api_key=CANARY123456789"},
        {"raw_text": "Authorization: Bearer CANARY-DO-NOT-LEAK"},
    ],
)
def test_signal_credentials_never_enter_store(
    tmp_path: Path,
    overrides: dict,
) -> None:
    store = _store(tmp_path)
    try:
        with pytest.raises(ValueError, match="credential|secret-bearing"):
            capture_signal(store, _signal(**overrides), market=FixedMarket())
        assert store.table_count("decision_events") == 0
    finally:
        store.close()
