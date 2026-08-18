from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from decision_lab.context import build_context_bundle, holdings_digest
from decision_lab.coverage import assess_coverage
from decision_lab.execution import (
    ExecutionError,
    apply_live_override,
    apply_paper_amendment,
    assess_probe,
    prepare_managed_action,
    record_live_choice,
    record_live_fill,
)
from decision_lab.store import DecisionStore, _assert_user_sized_within_capital_caps
from paper_portfolio.ledger import replay_decision_store_events
from storage.relational import initialize_private_root
from tests.test_decision_context import NOW, complete_inputs
from tests.test_probe_sizing import _assessment
from thesis.investment_policy import load_policy


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


def _bundle(store: DecisionStore, key: str = "execution", *, inputs=None):
    payload = deepcopy(inputs or complete_inputs())
    identity = payload["identity"]
    cohort_id = store.ensure_cohort(
        dedupe_key=key,
        company_id=identity["company_id"],
        research_ticker=identity["research_ticker"],
    ).cohort_id
    store.record_holdings_confirmation(
        holdings_digest(payload["holdings"]["rows"]),
        confirmed_at="2026-07-21T09:00:00+00:00",
    )
    bundle = build_context_bundle(
        store,
        cohort_id=cohort_id,
        evaluation_at=NOW,
        policy_version=load_policy()["policy_version"],
        **payload,
    )
    stored = store.record_coverage_assessment(
        cohort_id=cohort_id,
        context_digest=bundle.digest,
        status="analyzable",
        blockers=(),
        paper_blockers=(),
        live_blockers=("holdings_unconfirmed",),
        catalyst="next filing",
        disproof="commercial evidence fails",
        expiry="2026-08-21T00:00:00+00:00",
        decision_relevance=8,
        falsifiability=8,
        information_value=7,
    )
    coverage = store.get_coverage_result(str(stored["assessment_id"]))
    return bundle, coverage


def test_eligible_assess_is_atomic_and_retry_creates_one_paper_event(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store)
        first = assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="assess:one",
            effective_at=NOW,
        )
        retry = assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="assess:one",
            effective_at=NOW,
        )

        assert first == retry
        assert first.paper_funded is True
        assert store.table_count("system_decisions") == 1
        assert store.table_count("paper_events") == 1
        assert store.paper_position("co:sivers_semiconductors") == pytest.approx(0.0035)
    finally:
        store.close()


def test_same_idempotency_key_with_different_request_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store)
        assess_probe(
            store, bundle, coverage, _assessment(),
            idempotency_key="assess:conflict", effective_at=NOW,
        )
        changed = _assessment(commercial="bounded_hypothesis")

        with pytest.raises(ExecutionError, match="idempotency"):
            assess_probe(
                store, bundle, coverage, changed,
                idempotency_key="assess:conflict", effective_at=NOW,
            )
    finally:
        store.close()


@pytest.mark.parametrize(
    "intent,paper_blocker,live_blocker",
    [
        ("research", "execution_intent_research_only", "execution_intent_research_only"),
        ("paper", None, "execution_intent_paper_only"),
        ("live", None, None),
    ],
)
def test_execution_intent_is_an_existing_coverage_lane_permission(
    tmp_path: Path,
    intent: str,
    paper_blocker: str | None,
    live_blocker: str | None,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, _ = _bundle(store, f"intent:{intent}")
        coverage = assess_coverage(
            store,
            bundle,
            catalyst="next filing",
            disproof="commercial evidence fails",
            expiry="2026-08-21T00:00:00+00:00",
            decision_relevance=8,
            falsifiability=8,
            information_value=7,
            execution_intent=intent,
        )

        assert (paper_blocker in coverage.paper_blockers) is (paper_blocker is not None)
        assert (live_blocker in coverage.live_blockers) is (live_blocker is not None)
    finally:
        store.close()


def test_pending_coverage_persists_missing_catalyst_and_disproof_as_blockers(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, _ = _bundle(store, "missing-semantic-fields")

        coverage = assess_coverage(
            store,
            bundle,
            catalyst="",
            disproof="",
            expiry="2026-08-21T00:00:00+00:00",
            decision_relevance=0,
            falsifiability=0,
            information_value=0,
        )

        assert coverage.status == "coverage_pending"
        assert {"catalyst_missing", "disproof_missing"} <= set(coverage.blockers)
        assert store.get_coverage_result(coverage.assessment_id) == coverage
    finally:
        store.close()


def test_research_intent_is_in_assessment_request_and_cannot_fund_paper(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store, "research-intent")
        result = assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="assess:research-intent",
            effective_at=NOW,
            execution_intent="research",
        )

        decision = store.get_decision(result.decision_id)
        assert result.paper_funded is False
        assert decision["payload"]["request"]["execution_intent"] == "research"
        assert "execution_intent_research_only" in decision["payload"]["sizing"][
            "paper_blockers"
        ]
    finally:
        store.close()


def test_unresolved_context_can_record_only_a_zero_size_decision(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        cohort_id = store.ensure_cohort(
            dedupe_key="unresolved-decision",
            company_id=None,
            research_ticker=None,
        ).cohort_id
        inputs = complete_inputs(rows=[])
        inputs.update(
            {
                "identity": {},
                "evidence": {
                    "focus_company": None,
                    "sources": [],
                    "causal_paths": [],
                    "counter_paths": [],
                },
                "financial": {"status": "missing"},
                "market": {"status": "missing"},
                "fx": {"status": "missing"},
                "holdings": {"status": "missing"},
            }
        )
        bundle = build_context_bundle(
            store,
            cohort_id=cohort_id,
            evaluation_at=NOW,
            policy_version=load_policy()["policy_version"],
            **inputs,
        )
        coverage = assess_coverage(
            store,
            bundle,
            catalyst="resolve identity",
            disproof="claim cannot be attributed",
            expiry="2026-08-21T00:00:00+00:00",
            decision_relevance=8,
            falsifiability=8,
            information_value=7,
        )
        unknown = _assessment()
        for value in unknown.values():
            value.update(level="unknown", evidence_refs=[], missing_data=["identity"])

        result = assess_probe(
            store,
            bundle,
            coverage,
            unknown,
            idempotency_key="assess:unresolved",
            effective_at=NOW,
        )

        assert result.paper_funded is False
        assert result.paper_max_supported_position == 0.0
        assert store.table_count("system_decisions") == 1
        assert store.table_count("paper_events") == 0
    finally:
        store.close()


def test_equivalent_effective_time_offsets_are_one_idempotent_decision(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store, "offset-retry")
        first = assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="assess:offset-retry",
            effective_at="2026-07-21T13:00:00+00:00",
        )
        retry = assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="assess:offset-retry",
            effective_at="2026-07-21T09:00:00-04:00",
        )

        assert retry == first
        assert store.table_count("system_decisions") == 1
    finally:
        store.close()


@pytest.mark.parametrize(
    "failure_at",
    ["after_capacity", "after_decision", "after_paper_event", "after_projection"],
)
def test_failure_injection_rolls_back_decision_and_paper(
    tmp_path: Path, failure_at: str
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store)
        with pytest.raises(RuntimeError, match="injected"):
            assess_probe(
                store,
                bundle,
                coverage,
                _assessment(),
                idempotency_key=f"assess:{failure_at}",
                effective_at=NOW,
                _failure_at=failure_at,
            )

        assert store.table_count("system_decisions") == 0
        assert store.table_count("paper_events") == 0
        assert store.paper_position("co:sivers_semiconductors") == 0.0
    finally:
        store.close()


def test_forged_coverage_cannot_bypass_stored_pending_gate(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store)
        stored = store.record_coverage_assessment(
            cohort_id=bundle.cohort_id,
            context_digest=bundle.digest,
            status="coverage_pending",
            blockers=("catalyst_missing",),
            paper_blockers=("catalyst_missing",),
            live_blockers=("catalyst_missing",),
            catalyst="unknown",
            disproof="commercial evidence fails",
            expiry="2026-08-21T00:00:00+00:00",
            decision_relevance=8,
            falsifiability=8,
            information_value=7,
        )
        pending = store.get_coverage_result(str(stored["assessment_id"]))
        forged = replace(
            pending,
            status="analyzable",
            blockers=(),
            paper_blockers=(),
            paper_context_ready=True,
        )
        result = assess_probe(
            store, bundle, forged, _assessment(),
            idempotency_key="assess:pending", effective_at=NOW,
        )

        assert result.paper_funded is False
        assert store.table_count("system_decisions") == 1
        assert store.table_count("paper_events") == 0
    finally:
        store.close()


def test_transaction_recomputes_current_paper_capacity_instead_of_stale_context(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    policy = deepcopy(load_policy())
    policy["probe_lane"]["probe_book_nav_cap"] = 0.005
    axt_inputs = complete_inputs(rows=[])
    axt_inputs["identity"] = {
        "company_id": "co:axt",
        "research_ticker": "AXTI",
        "execution_symbol": "AXTI",
        "market_currency": "USD",
        "execution_currency": "USD",
        "execution_venue": "NASDAQ",
    }
    axt_inputs["evidence"] = deepcopy(axt_inputs["evidence"])
    axt_inputs["evidence"]["focus_company"] = {"id": "co:axt"}
    axt_inputs["evidence"]["subject_origin_entity"] = "AXT"
    axt_inputs["financial"] = deepcopy(axt_inputs["financial"])
    axt_inputs["financial"]["ticker"] = "AXTI"
    axt_inputs["market"] = deepcopy(axt_inputs["market"])
    axt_inputs["market"].update({"ticker": "AXTI", "currency": "USD"})
    axt_inputs["fx"] = deepcopy(axt_inputs["fx"])
    axt_inputs["fx"].update({"pair": "USD/USD", "rate": 1.0})
    try:
        first_bundle, first_coverage = _bundle(store, "capacity-1")
        second_bundle, second_coverage = _bundle(
            store, "capacity-2", inputs=axt_inputs
        )
        first = assess_probe(
            store, first_bundle, first_coverage, _assessment(),
            idempotency_key="capacity:1", effective_at=NOW, policy=policy,
        )
        second = assess_probe(
            store, second_bundle, second_coverage, _assessment(),
            idempotency_key="capacity:2", effective_at="2026-07-21T12:01:00+00:00",
            policy=policy,
        )

        assert first.paper_target == pytest.approx(0.0035)
        assert second.paper_target == pytest.approx(0.0015)
        assert store.paper_position("co:sivers_semiconductors") == pytest.approx(0.0035)
        assert store.paper_position("co:axt") == pytest.approx(0.0015)
        assert second.paper_target != pytest.approx(0.0035)
    finally:
        store.close()


def test_backdated_assess_cannot_diverge_projection_from_event_replay(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store, "paper-order")
        assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="assess:paper-order:first",
            effective_at="2026-07-21T13:00:00+00:00",
        )
        with pytest.raises(ValueError, match="causal timeline|follow"):
            assess_probe(
                store,
                bundle,
                coverage,
                _assessment(commercial="bounded_hypothesis"),
                idempotency_key="assess:paper-order:backdated",
                effective_at="2026-07-21T12:30:00+00:00",
            )

        events = store.list_paper_events(bundle.cohort_id)
        assert len(events) == 1
        assert store.paper_position("co:sivers_semiconductors") == pytest.approx(0.0035)
        assert replay_decision_store_events(events)["company_weights"][
            "co:sivers_semiconductors"
        ] == pytest.approx(0.0035)
    finally:
        store.close()


def test_live_choice_and_fill_require_explicit_user_facts_and_do_not_rewrite_system(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store)
        decision = assess_probe(
            store, bundle, coverage, _assessment(),
            idempotency_key="assess:live", effective_at=NOW,
        )
        original_digest = store.get_decision(decision.decision_id)["decision_digest"]

        with pytest.raises(ExecutionError, match="explicit"):
            record_live_choice(
                store, decision.decision_id, selected_weight=0.0,
                decided_at=NOW, explicit=False,
            )
        choice_id = record_live_choice(
            store,
            decision.decision_id,
            selected_weight=0.0,
            decided_at=NOW,
            explicit=True,
        )
        with pytest.raises(ExecutionError, match="explicit"):
            record_live_fill(
                store,
                decision.decision_id,
                execution_ref="manual:broker-1",
                shares=10,
                price=2.0,
                currency="EUR",
                executed_at=NOW,
                explicit=False,
            )

        assert choice_id
        assert store.get_decision(decision.decision_id)["decision_digest"] == original_digest
        assert store.table_count("live_execution_reports") == 0
    finally:
        store.close()


def test_user_sized_choice_bypasses_supported_range_but_not_capital_caps(
    tmp_path: Path,
) -> None:
    """驗收條件 1–3（`2026-08-18-alpha-live-user-sized-requirements` §4）。

    `user_sized` 的尺寸來源是使用者，不與 `live_supported_range` 比較——因為
    2026-08-15 起系統已不對使用者呈現尺寸。但這**不是**放寬：分開之後兩邊各自更嚴
    （L12），單筆 NAV 上限與 ETF 槓桿 cap 照樣硬擋。
    """

    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store, "user-sized")
        decision = assess_probe(
            store, bundle, coverage, _assessment(),
            idempotency_key="assess:user-sized", effective_at=NOW,
        )
        sizing = store.get_decision(decision.decision_id)["payload"]["sizing"]
        supported_upper = float(sizing["live_supported_range"][1])
        single_position_cap = next(
            e["cap_weight"]
            for e in sizing["constraint_trace"]
            if e["lane"] == "live" and e["constraint"] == "single_position_cap"
        )

        # 驗收 3：研究完整度／lane blocker 讓系統區間歸零，user_sized 仍可記錄。
        # 這一筆若被擋，就代表 gate 又在用研究進度否決資本（D2 要修掉的正是這個）。
        assert supported_upper < single_position_cap
        chosen = single_position_cap / 2.0
        assert chosen > supported_upper

        with pytest.raises(ExecutionError, match="reason"):
            record_live_choice(
                store, decision.decision_id, selected_weight=chosen,
                decided_at=NOW, explicit=True, user_sized=True,
            )

        choice_id = record_live_choice(
            store,
            decision.decision_id,
            selected_weight=chosen,
            decided_at=NOW,
            explicit=True,
            user_sized=True,
            reason="thesis 已成立，依自己的判斷定尺寸",
        )
        assert choice_id

        row = store._conn.execute(
            "SELECT choice_type, selected_weight, system_supported_upper "
            "FROM live_choices WHERE choice_id = ?",
            (choice_id,),
        ).fetchone()
        assert row["choice_type"] == "user_sized"
        # 系統當時的意見必須被保存下來，否則日後無法比較「人 vs 系統」。
        assert row["system_supported_upper"] == pytest.approx(supported_upper)
        assert row["selected_weight"] > row["system_supported_upper"]

        # 驗收 2：剛好等於單筆上限可以，超過不行。
        record_live_choice(
            store, decision.decision_id, selected_weight=single_position_cap,
            decided_at="2026-07-21T12:06:00+00:00", explicit=True, user_sized=True,
            reason="押到單筆上限",
        )
        with pytest.raises(ExecutionError, match="single position cap"):
            record_live_choice(
                store, decision.decision_id,
                selected_weight=single_position_cap + 0.001,
                decided_at="2026-07-21T12:07:00+00:00", explicit=True, user_sized=True,
                reason="想超過上限",
            )

        # user_sized 與 override 是兩條互斥路徑，不得疊用來繞過彼此的要求。
        with pytest.raises(ValueError, match="mutually exclusive"):
            store.record_live_choice(
                decision_id=decision.decision_id, selected_weight=chosen,
                decided_at="2026-07-21T12:08:00+00:00", user_sized=True,
                force_override=True, reason="兩個都要", approved_action_id="pa_x",
            )
    finally:
        store.close()


def test_user_sized_cap_counts_existing_position_and_rejects_stale_decisions(
    tmp_path: Path,
) -> None:
    """兩個 2026-08-18 紅隊審查抓到的資本安全洞。

    (1) 上限管的是**部位總量**不是單次買入量——首版只比 `selected_weight`，於是已持有
        4% 的標的還能再買 5%。
    (2) 凍結快照有時效——沒有上界時，三個月前的 decision 仍會說「未觸頂」，而期間
        持股早已變動。
    """

    from decision_lab.store import USER_SIZED_MAX_DECISION_AGE_DAYS

    sizing = {
        "live_blockers": [],
        "live_current_position": 0.04,
        "constraint_trace": [
            {"lane": "live", "constraint": "single_position_cap", "cap_weight": 0.05},
        ],
    }

    # 已持有 4%，再買 2% 會超過 5% 上限——即使 2% 本身遠低於上限。
    with pytest.raises(ValueError, match="exceeds single position cap"):
        _assert_user_sized_within_capital_caps(sizing, 0.02)
    # 剛好補到上限可以。
    _assert_user_sized_within_capital_caps(sizing, 0.01)

    fresh = "2026-07-21T12:00:00+00:00"
    stale_days = USER_SIZED_MAX_DECISION_AGE_DAYS + 1
    with pytest.raises(ValueError, match="frozen within"):
        _assert_user_sized_within_capital_caps(
            sizing,
            0.001,
            decision_effective_at=fresh,
            decided_at=f"2026-07-{21 + stale_days:02d}T12:00:00+00:00",
        )
    # 期限內不擋。
    _assert_user_sized_within_capital_caps(
        sizing, 0.001, decision_effective_at=fresh, decided_at="2026-07-25T12:00:00+00:00"
    )


def test_user_sized_choice_is_still_blocked_by_real_capital_caps(tmp_path: Path) -> None:
    """槓桿／單筆上限已觸頂時，`user_sized` 必須被擋——那才是真正的風控。

    對照組是上一個測試：研究完整度 blocker 擋不住 user_sized，資本上限擋得住。
    兩者都成立，`user_sized` 才算「分開之後兩邊更嚴」而不是整體放寬。
    """

    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store, "user-sized-capped")
        decision = assess_probe(
            store, bundle, coverage, _assessment(),
            idempotency_key="assess:user-sized-capped", effective_at=NOW,
        )
        stored = store.get_decision(decision.decision_id)
        sizing = deepcopy(stored["payload"]["sizing"])

        for blocker in (
            "single_position_nav_cap_reached",
            "etf_leverage_nominal_cap_reached",
            "etf_leverage_effective_cap_reached",
        ):
            capped = deepcopy(sizing)
            capped["live_blockers"] = [blocker]
            with pytest.raises(ValueError, match="capital caps"):
                _assert_user_sized_within_capital_caps(capped, 0.01)

        # `portfolio_leverage_unavailable` 雖標 fatal，但**不得**擋 user_sized。
        # 它在每一筆真實 decision 上都亮（恆亮＝零鑑別力），且說不出「亮起時標的更可能
        # 變壞」的機制——那是管線狀態不是風險判斷（D3）。這一行鎖住那個判斷，
        # 若未來有人想把它加回 _HARD_CAP_BLOCKERS，會先撞到這裡並被迫重讀理由。
        unavailable = deepcopy(sizing)
        unavailable["live_blockers"] = ["portfolio_leverage_unavailable"]
        _assert_user_sized_within_capital_caps(unavailable, 0.01)

        # 沒有資本上限 blocker 時，同一筆權重就通得過——證明擋下來的是那四碼，
        # 不是別的東西順帶擋掉的。
        clean = deepcopy(sizing)
        clean["live_blockers"] = ["execution_intent_paper_only", "holdings_unconfirmed"]
        _assert_user_sized_within_capital_caps(clean, 0.01)

        # 凍結的 trace 缺 single_position_cap 時 fail closed：無法驗證的上限
        # 不得被當成已通過。
        no_cap = deepcopy(clean)
        no_cap["constraint_trace"] = [
            e for e in no_cap["constraint_trace"] if e["constraint"] != "single_position_cap"
        ]
        with pytest.raises(ValueError, match="frozen single_position_cap"):
            _assert_user_sized_within_capital_caps(no_cap, 0.01)
    finally:
        store.close()


def test_above_cap_live_override_requires_prepared_exact_native_approval(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store)
        decision = assess_probe(
            store, bundle, coverage, _assessment(),
            idempotency_key="assess:override", effective_at=NOW,
        )
        prepared = prepare_managed_action(
            store,
            action_type="live_override",
            target_id=decision.decision_id,
            payload={"selected_weight": 0.01, "reason": "我接受超額探索風險"},
            prepared_at=NOW,
            expires_at="2026-07-21T13:00:00+00:00",
        )

        assert store.table_count("live_choices") == 0
        with pytest.raises(ExecutionError, match="approval"):
            apply_live_override(
                store, prepared.action_id, prepared.digest,
                native_approved=False, decided_at="2026-07-21T12:05:00+00:00",
            )
        with pytest.raises(ExecutionError, match="digest"):
            apply_live_override(
                store, prepared.action_id, "0" * 64,
                native_approved=True, decided_at="2026-07-21T12:05:00+00:00",
            )
        choice_id = apply_live_override(
            store,
            prepared.action_id,
            prepared.digest,
            native_approved=True,
            decided_at="2026-07-21T12:05:00+00:00",
        )
        fill_id = record_live_fill(
            store,
            decision.decision_id,
            execution_ref="manual:broker-override",
            shares=10,
            price=2.0,
            currency="EUR",
            executed_at="2026-07-21T12:10:00+00:00",
            explicit=True,
        )

        with pytest.raises(ExecutionError, match="currency"):
            record_live_fill(
                store,
                decision.decision_id,
                execution_ref="manual:wrong-currency",
                shares=10,
                price=2.0,
                currency="JPY",
                executed_at="2026-07-21T12:11:00+00:00",
                explicit=True,
            )

        assert choice_id
        assert fill_id
        assert store.table_count("live_choices") == 1
        assert store.table_count("live_execution_reports") == 1

        assert record_live_fill(
            store,
            decision.decision_id,
            execution_ref="manual:broker-override",
            shares=10,
            price=2.0,
            currency="EUR",
            executed_at="2026-07-21T12:10:00+00:00",
            explicit=True,
        ) == fill_id
        with pytest.raises(ExecutionError, match="different fill"):
            record_live_fill(
                store,
                decision.decision_id,
                execution_ref="manual:broker-override",
                shares=11,
                price=2.0,
                currency="EUR",
                executed_at="2026-07-21T12:10:00+00:00",
                explicit=True,
            )
    finally:
        store.close()


@pytest.mark.parametrize("action_type,target", [("paper_correction", 0.002), ("paper_reversal", 0.0)])
def test_paper_amendment_preserves_original_and_requires_approval(
    tmp_path: Path, action_type: str, target: float
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store)
        decision = assess_probe(
            store, bundle, coverage, _assessment(),
            idempotency_key=f"assess:{action_type}", effective_at=NOW,
        )
        assert decision.paper_event_id is not None
        prepared = prepare_managed_action(
            store,
            action_type=action_type,
            target_id=decision.paper_event_id,
            payload={"target_weight": target, "reason": "修正紙上紀錄"},
            prepared_at=NOW,
            expires_at="2026-07-21T13:00:00+00:00",
        )

        with pytest.raises(ExecutionError, match="follow"):
            apply_paper_amendment(
                store,
                prepared.action_id,
                prepared.digest,
                native_approved=True,
                effective_at="2026-07-21T11:59:00+00:00",
            )

        amendment_id = apply_paper_amendment(
            store,
            prepared.action_id,
            prepared.digest,
            native_approved=True,
            effective_at="2026-07-21T12:05:00+00:00",
        )

        events = store.list_paper_events(bundle.cohort_id)
        assert len(events) == 2
        assert events[0]["paper_event_id"] == decision.paper_event_id
        assert events[1]["paper_event_id"] == amendment_id
        assert events[1]["corrects_paper_event_id"] == decision.paper_event_id
        assert store.paper_position("co:sivers_semiconductors") == pytest.approx(target)
        replayed = replay_decision_store_events(events)
        assert replayed["company_weights"].get("co:sivers_semiconductors", 0.0) == pytest.approx(
            target
        )
        assert replayed["event_count"] == 2
    finally:
        store.close()
