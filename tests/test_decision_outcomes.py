from __future__ import annotations

from pathlib import Path

import pytest

from decision_lab.intake import capture_signal
from decision_lab.models import MarketObservation, SignalInput
from decision_lab.outcomes import (
    OutcomeError,
    close_probe,
    current_lifecycle,
    trigger_review_required,
)
from tests.test_decision_execution import _bundle, _store
from tests.test_probe_sizing import _assessment
from decision_lab.execution import assess_probe, record_live_choice
from risk.policy import load_policy


class FixedMarket:
    def __init__(self, observation: MarketObservation):
        self.observation = observation

    def observe(self, *_args) -> MarketObservation:
        return self.observation


def _captured(store, *, status="observed"):
    observation = (
        MarketObservation(
            status="observed",
            ticker="SIVE.ST",
            price=10.0,
            currency="SEK",
            source="fixture://market",
            as_of="2026-07-01T10:00:00+00:00",
            fetched_at="2026-07-01T10:01:00+00:00",
        )
        if status == "observed"
        else MarketObservation(status=status)
    )
    return capture_signal(
        store,
        SignalInput(
            raw_text="Sivers CW laser claim",
            source_id="aleabitoreddit",
            source_uri="https://example.test/post/1",
            origin_event="post:1",
            observed_at="2026-07-01T10:00:00+00:00",
            atomic_claim="Sivers controls a critical CW laser bottleneck",
            direction="long",
            expiry="2026-12-31T00:00:00+00:00",
            disproof="Named customer qualification fails",
            evidence_tier=4,
            company_id="co:sivers_semiconductors",
            research_ticker="SIVE.ST",
            source_traced=False,
        ),
        market=FixedMarket(observation),
    )


def test_claim_correctness_is_separate_from_market_and_benchmark_return(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        captured = _captured(store)
        result = close_probe(
            store,
            captured.cohort_id,
            terminal_status="expired",
            claim_correctness="unknown",
            current_market={
                "status": "observed",
                "ticker": "SIVE.ST",
                "price": 12.0,
                "currency": "SEK",
                "as_of": "2026-12-31T10:00:00+00:00",
                "source": "fixture://market-end",
            },
            benchmark={
                "status": "observed",
                "ticker": "OMXSPI",
                "start_price": 100.0,
                "end_price": 110.0,
                "source": "fixture://benchmark",
                "start_as_of": "2026-07-01T10:00:00+00:00",
                "as_of": "2026-12-31T10:00:00+00:00",
            },
            reason="Claim expiry reached without decisive proof",
            evidence_refs=["fixture://outcome-review"],
            effective_at="2026-12-31T12:00:00+00:00",
        )

        assert result.claim_correctness == "unknown"
        assert result.absolute_return == pytest.approx(0.20)
        assert result.benchmark_adjusted_return == pytest.approx(0.10)
        assert result.claim_correctness != "true"
    finally:
        store.close()


@pytest.mark.parametrize(
    "market, message",
    [
        (
            {
                "status": "observed",
                "ticker": "ERIC-B.ST",
                "price": 12.0,
                "currency": "SEK",
                "as_of": "2026-08-01T10:00:00+00:00",
                "source": "fixture://wrong-security",
            },
            "ticker",
        ),
        (
            {
                "status": "observed",
                "ticker": "SIVE.ST",
                "price": 12.0,
                "currency": "SEK",
                "as_of": "2026-06-30T10:00:00+00:00",
                "source": "fixture://pre-inception",
            },
            "predates",
        ),
    ],
)
def test_outcome_market_is_bound_to_cohort_identity_and_shadow_window(
    tmp_path: Path,
    market: dict,
    message: str,
) -> None:
    store = _store(tmp_path)
    try:
        captured = _captured(store)
        with pytest.raises(OutcomeError, match=message):
            close_probe(
                store,
                captured.cohort_id,
                terminal_status="expired",
                claim_correctness="unknown",
                current_market=market,
                benchmark={"status": "missing"},
                reason="Window validation",
                evidence_refs=["fixture://review"],
                effective_at="2026-08-01T12:00:00+00:00",
            )
        assert store.table_count("outcome_envelopes") == 0
    finally:
        store.close()


def test_outcome_secret_in_reason_never_enters_store(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        captured = _captured(store)
        with pytest.raises(OutcomeError, match="secret-bearing"):
            close_probe(
                store,
                captured.cohort_id,
                terminal_status="expired",
                claim_correctness="unknown",
                current_market={"status": "missing"},
                benchmark={"status": "missing"},
                reason="Authorization: Bearer CANARY-DO-NOT-LEAK",
                evidence_refs=["fixture://review"],
                effective_at="2026-08-01T12:00:00+00:00",
            )
        assert store.table_count("outcome_envelopes") == 0
    finally:
        store.close()


@pytest.mark.parametrize("inception_status", ["missing", "unavailable"])
def test_missing_inception_never_hindsight_backfills_market_return(
    tmp_path: Path, inception_status: str
) -> None:
    store = _store(tmp_path)
    try:
        captured = _captured(store, status=inception_status)
        result = close_probe(
            store,
            captured.cohort_id,
            terminal_status="rejected",
            claim_correctness="false",
            current_market={
                "status": "observed",
                "ticker": "SIVE.ST",
                "price": 12.0,
                "currency": "SEK",
                "as_of": "2026-08-01T10:00:00+00:00",
                "source": "fixture://market-end",
            },
            benchmark={"status": "missing"},
            reason="Counter-evidence rejected the claim",
            evidence_refs=["fixture://counter-evidence"],
            effective_at="2026-08-01T12:00:00+00:00",
        )

        assert result.market_return_status == "unknown"
        assert result.absolute_return is None
        assert result.benchmark_adjusted_return is None
    finally:
        store.close()


def test_disproof_enters_review_required_with_48h_due_before_terminal_state(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        captured = _captured(store)
        review = trigger_review_required(
            store,
            captured.cohort_id,
            reason="Named qualification failed",
            evidence_refs=["fixture://customer"],
            effective_at="2026-07-21T12:00:00+00:00",
        )

        assert review.status == "review_required"
        assert review.review_due_at == "2026-07-23T12:00:00+00:00"
        assert current_lifecycle(store, captured.cohort_id).status == "review_required"
    finally:
        store.close()


@pytest.mark.parametrize("failure_at", ["after_terminal", "after_outcome"])
def test_terminal_transition_and_outcome_roll_back_together(
    tmp_path: Path, failure_at: str
) -> None:
    store = _store(tmp_path)
    try:
        captured = _captured(store)
        with pytest.raises(RuntimeError, match="injected"):
            close_probe(
                store,
                captured.cohort_id,
                terminal_status="rejected",
                claim_correctness="false",
                current_market={"status": "missing"},
                benchmark={"status": "missing"},
                reason="Rejected",
                evidence_refs=["fixture://counter"],
                effective_at="2026-07-21T12:00:00+00:00",
                _failure_at=failure_at,
            )

        assert store.table_count("outcome_envelopes") == 0
        assert current_lifecycle(store, captured.cohort_id).status == "active"
    finally:
        store.close()


def test_terminal_retry_is_exactly_once_and_conflicting_outcome_fails(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    kwargs = dict(
        terminal_status="rejected",
        claim_correctness="false",
        current_market={"status": "missing"},
        benchmark={"status": "missing"},
        reason="Rejected",
        evidence_refs=["fixture://counter"],
        effective_at="2026-07-21T12:00:00+00:00",
    )
    try:
        captured = _captured(store)
        first = close_probe(store, captured.cohort_id, **kwargs)
        retry = close_probe(store, captured.cohort_id, **kwargs)

        assert first == retry
        assert store.table_count("outcome_envelopes") == 1
        with pytest.raises(OutcomeError, match="terminal"):
            close_probe(
                store,
                captured.cohort_id,
                **{**kwargs, "claim_correctness": "true"},
            )
    finally:
        store.close()


def test_outcome_freezes_system_vs_user_choice_and_calculator_trace(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store, "outcome-decision")
        decision = assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="outcome:decision",
            effective_at="2026-07-21T12:00:00+00:00",
        )
        record_live_choice(
            store,
            decision.decision_id,
            selected_weight=0.0,
            decided_at="2026-07-21T12:05:00+00:00",
            explicit=True,
        )

        result = close_probe(
            store,
            bundle.cohort_id,
            terminal_status="expired",
            claim_correctness="mixed",
            current_market={"status": "missing"},
            benchmark={"status": "missing"},
            reason="Review horizon ended",
            evidence_refs=["fixture://review"],
            effective_at="2026-10-21T12:00:00+00:00",
        )
        frozen = store.get_outcome(result.outcome_id)

        # 系統給的額度欄位已隨資本表達層移除（R9）：outcome 回答的是「排序準不準」，
        # 那需要報酬率，不需要系統曾建議投多少。
        assert "system_paper_target" not in frozen["decision_attribution"]
        # user_live_weight 保留——那是**使用者實際做了什麼**的事實，不是系統建議。
        assert frozen["decision_attribution"]["user_live_weight"] == 0.0
        assert frozen["decision_attribution"]["user_choice_type"] == "skipped"
        # 讀 policy 而非寫死版本字串：這裡要守的是「凍結值等於當時 policy 說的值」，
        # 不是某個特定版本號。寫死會讓每次 calculator 語意變更都被迫改測試，
        # 而那正是 2026-08-14 差點漏掉的事（改了 sizing 語意卻沒 bump 版本）。
        assert frozen["calculator_version"] == load_policy()["probe_lane"]["calculator_version"]
        # `constraint_trace`（資本上限鏈）已隨 U7 移除；事後檢討要問的是「當時這檔卡在
        # 哪一軸、研究做到什麼程度」，不是「當時額度被誰擋住」。
        assert "constraint_trace" not in frozen
        assert frozen["weakest_axis"] == "source_reliability"
        assert frozen["research_status"] == "READY"
    finally:
        store.close()


def test_outcome_attributes_the_latest_decision_and_has_no_paper_book_left(
    tmp_path: Path,
) -> None:
    """U7 之後 outcome 只歸因到「當時最新的那筆研究判斷」。

    原本這裡守的是「歸因到真正**資助**的那個 decision，不是最新的被擋建議」——
    那個區別由 paper book（`paper_position_state`）撐起來，而 paper 部位已隨資本
    表達層移除，`atomic_assess_probe` 不再寫任何 paper event。於是
    `paper_source_decision_id` 對新 decision 恆為 None，欄位保留只為了讀得回 U7
    之前的歷史（L10 append-only）。
    """

    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store, "outcome-book")
        ready = assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="outcome:ready",
            effective_at="2026-07-21T12:00:00+00:00",
        )
        incomplete = assess_probe(
            store,
            bundle,
            coverage,
            _assessment(commercial="unknown"),
            idempotency_key="outcome:incomplete",
            effective_at="2026-07-22T12:00:00+00:00",
        )
        assert ready.research_status == "READY"
        assert incomplete.research_status == "INCOMPLETE"
        assert store.paper_position("co:sivers_semiconductors") == 0.0
        assert store.table_count("paper_events") == 0

        result = close_probe(
            store,
            bundle.cohort_id,
            terminal_status="expired",
            claim_correctness="mixed",
            current_market={"status": "missing"},
            benchmark={"status": "missing"},
            reason="Review horizon ended",
            evidence_refs=["fixture://review"],
            effective_at="2026-10-21T12:00:00+00:00",
        )
        outcome = store.get_outcome(result.outcome_id)
        attribution = outcome["decision_attribution"]

        assert attribution["decision_id"] == incomplete.decision_id
        assert attribution["paper_source_decision_id"] is None
        # 系統額度欄位確實不見了，不是改名躲起來。
        assert "system_paper_target" not in attribution
        assert "latest_recommendation_target" not in attribution
        assert "system_paper_max" not in attribution
        # 取而代之凍下來的是「當時卡在哪一軸、研究做到什麼程度」。
        assert outcome["weakest_axis"] == "commercial_maturity"
        assert outcome["research_status"] == "INCOMPLETE"
    finally:
        store.close()


def test_revised_closes_old_epoch_and_opens_new_active_epoch(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        captured = _captured(store)
        first = close_probe(
            store,
            captured.cohort_id,
            terminal_status="revised",
            claim_correctness="mixed",
            current_market={"status": "missing"},
            benchmark={"status": "missing"},
            reason="Narrowed claim scope",
            evidence_refs=["fixture://revision"],
            effective_at="2026-07-21T12:00:00+00:00",
        )
        retry = close_probe(
            store,
            captured.cohort_id,
            terminal_status="revised",
            claim_correctness="mixed",
            current_market={"status": "missing"},
            benchmark={"status": "missing"},
            reason="Narrowed claim scope",
            evidence_refs=["fixture://revision"],
            effective_at="2026-07-21T12:00:00+00:00",
        )

        lifecycle = current_lifecycle(store, captured.cohort_id)
        assert retry == first
        assert lifecycle.epoch == 2
        assert lifecycle.status == "active"
        assert store.table_count("outcome_envelopes") == 1
        assert store.lifecycle_invariant_violations() == []
    finally:
        store.close()
