from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from decision_lab.action_card import build_action_card
from decision_lab.context import build_context_bundle, holdings_digest
from decision_lab.coverage import assess_coverage
from decision_lab.execution import (
    ExecutionError,
    apply_live_override,
    assess_probe,
    prepare_managed_action,
    record_live_choice,
    record_live_fill,
)
from decision_lab.models import ATTENTION_STATES
from decision_lab.store import (
    DecisionStore,
    _assert_user_sized_within_capital_caps,
    _canonical_json,
    _digest,
)
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


def test_assess_is_atomic_and_retry_creates_one_decision_without_paper_event(
    tmp_path: Path,
) -> None:
    """同一個 idempotency key 重跑只留下一筆 decision，而且不寫任何 paper 部位。

    U7（2026-08-28）起 `atomic_assess_probe` 不再建立 paper event——paper 部位是
    資本表達，已隨資本表達層一起移除。既有 `paper_events`／`paper_position_projection`
    是 append-only 歷史，保持可讀但不再增長，所以這裡連帶鎖住「新決策一筆都不寫」。
    """

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
        assert first.research_status == "READY"
        assert store.table_count("system_decisions") == 1
        assert store.table_count("paper_events") == 0
        assert store.paper_position("co:sivers_semiconductors") == 0.0
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


def test_research_intent_is_in_assessment_request_and_blocks_the_paper_lane(
    tmp_path: Path,
) -> None:
    """`execution_intent` 進入凍結 request，並在 paper lane 留下對應 blocker。

    U7 之後 `paper_blockers` 的語意是「研究資料齊不齊」而不是「能不能配資本」，
    所以斷言改看 `research_status`：有 paper blocker ⇒ `DATA_NEEDED`。
    """

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
        assert result.research_status == "DATA_NEEDED"
        assert decision["payload"]["request"]["execution_intent"] == "research"
        assert "execution_intent_research_only" in decision["payload"]["sizing"][
            "paper_blockers"
        ]
    finally:
        store.close()


def test_unresolved_context_can_record_only_a_data_needed_decision(
    tmp_path: Path,
) -> None:
    """身分未解析時仍可留下一筆決策紀錄，但研究完整度必須誠實標成 `DATA_NEEDED`。

    U7 之前這裡斷言的是「額度歸零」（`paper_max_supported_position == 0`）；
    額度已移除，剩下的同一件事是研究完整度。
    """

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

        assert result.research_status == "DATA_NEEDED"
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


# ⚠ `after_paper_event` 與 `after_projection` 兩個注入點已隨 U7 移除：
# `atomic_assess_probe` 不再寫 paper event／projection，那兩行程式不存在了。
@pytest.mark.parametrize("failure_at", ["after_capacity", "after_decision"])
def test_failure_injection_rolls_back_the_whole_decision(
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

        # 偽造的 coverage 不算數：store 重讀 authoritative coverage，於是 pending 的
        # `catalyst_missing` 仍然落進 paper lane，研究完整度誠實降級。
        assert result.research_status == "DATA_NEEDED"
        assert store.table_count("system_decisions") == 1
        assert store.table_count("paper_events") == 0
    finally:
        store.close()


# ⚠ `test_transaction_recomputes_current_paper_capacity_instead_of_stale_context`
# 於 U7（2026-08-28）隨資本表達層一起移除：它唯一斷言的是 probe book 額度
# （`probe_book_nav_cap` → `paper_target`）會在交易中依當下 paper 部位重算。
# `probe_book_nav_cap` 已從 `config/investment_policy.json` 移除，`paper_target`
# 已從 `ProbeSizingResult` 移除，也不再有 paper event 會佔用書額。


def test_backdated_assess_is_rejected_by_the_cohort_causal_timeline(
    tmp_path: Path,
) -> None:
    """晚於既有事件的因果時序仍然硬擋——只是不再有 paper projection 要保護。

    原本的驗收對象是「projection 不得與 event replay 分歧」；U7 之後沒有新的 paper
    event，剩下的同一道保護是 decision 本身不得回填到既有時間線之前。
    """

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

        assert store.table_count("system_decisions") == 1
        assert store.list_paper_events(bundle.cohort_id) == []
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


def test_every_nonzero_live_choice_is_user_sized_and_still_hits_capital_caps(
    tmp_path: Path,
) -> None:
    """U7 之後系統不再輸出 `live_supported_range`，尺寸一律由使用者決定。

    `choice_type` 因此只剩 `override`／`skipped`／`user_sized`——「接受系統區間」
    （`accepted`）與「低於區間下緣」（`below_range`）兩個相對於系統意見定義的分類
    已無所指。但這**不是**放寬：分開之後兩邊各自更嚴（L12），每一筆非零、非 override
    的選擇都必須走同一道資本上限檢查，單筆 5% NAV 上限照樣硬擋。
    """

    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store, "user-sized")
        decision = assess_probe(
            store, bundle, coverage, _assessment(),
            idempotency_key="assess:user-sized", effective_at=NOW,
        )
        sizing = store.get_decision(decision.decision_id)["payload"]["sizing"]
        single_position_cap = float(sizing["single_position_nav_cap"])
        chosen = single_position_cap / 2.0

        # 研究完整度／lane blocker 不得否決使用者的尺寸——那些是研究進度，不是風險
        # 判斷（D2／D3）。這一筆若被擋，就代表 gate 又在用研究進度否決資本。
        assert sizing["live_blockers"]

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
        # 新 decision 沒有系統區間，欄位必須是 NULL——「系統沒給過意見」與
        # 「系統給的意見是 0」不是同一件事（L12）。舊 decision 的值仍保留在
        # 同一欄，見 `test_legacy_capital_expression_decision_stays_readable`。
        assert row["system_supported_upper"] is None

        # 沒有 `user_sized` 旗標也一樣：非零選擇一律走同一道檢查、記成 user_sized。
        implicit_id = record_live_choice(
            store, decision.decision_id, selected_weight=chosen,
            decided_at="2026-07-21T12:05:00+00:00", explicit=True,
        )
        assert store._conn.execute(
            "SELECT choice_type FROM live_choices WHERE choice_id = ?", (implicit_id,)
        ).fetchone()["choice_type"] == "user_sized"

        # 剛好等於單筆上限可以，超過不行。
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

        # skip（0%）不新增曝險，仍是獨立的 `skipped` 分類，且不受上限檢查影響。
        skip_id = record_live_choice(
            store, decision.decision_id, selected_weight=0.0,
            decided_at="2026-07-21T12:08:00+00:00", explicit=True,
        )
        assert store._conn.execute(
            "SELECT choice_type FROM live_choices WHERE choice_id = ?", (skip_id,)
        ).fetchone()["choice_type"] == "skipped"

        # user_sized 與 override 是兩條互斥路徑，不得疊用來繞過彼此的要求。
        with pytest.raises(ValueError, match="mutually exclusive"):
            store.record_live_choice(
                decision_id=decision.decision_id, selected_weight=chosen,
                decided_at="2026-07-21T12:09:00+00:00", user_sized=True,
                force_override=True, reason="兩個都要", approved_action_id="pa_x",
            )
    finally:
        store.close()


@pytest.mark.parametrize("cap_shape", ["frozen_field", "legacy_constraint_trace"])
def test_user_sized_cap_counts_existing_position_and_rejects_stale_decisions(
    cap_shape: str,
) -> None:
    """兩個 2026-08-18 紅隊審查抓到的資本安全洞。

    (1) 上限管的是**部位總量**不是單次買入量——首版只比 `selected_weight`，於是已持有
        4% 的標的還能再買 5%。
    (2) 凍結快照有時效——沒有上界時，三個月前的 decision 仍會說「未觸頂」，而期間
        持股早已變動。

    兩種 sizing 形狀都必須成立：U7 之後直接凍 `single_position_nav_cap`，
    U7 之前凍在 `constraint_trace` 的 `single_position_cap` 條目裡。Decision Store
    是 append-only 的 private authority，舊 decision 不回寫（L10）。
    """

    from decision_lab.store import USER_SIZED_MAX_DECISION_AGE_DAYS

    sizing: dict = {
        "live_blockers": [],
        "live_current_position": 0.04,
    }
    if cap_shape == "frozen_field":
        sizing["single_position_nav_cap"] = 0.05
    else:
        sizing["constraint_trace"] = [
            {"lane": "live", "constraint": "single_position_cap", "cap_weight": 0.05},
        ]

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

        # 沒有資本上限 blocker 時，同一筆權重就通得過——證明擋下來的是那三碼，
        # 不是別的東西順帶擋掉的。
        clean = deepcopy(sizing)
        clean["live_blockers"] = ["execution_intent_paper_only", "holdings_unconfirmed"]
        _assert_user_sized_within_capital_caps(clean, 0.01)

        # 凍結的 sizing 缺 single_position_nav_cap 時 fail closed：無法驗證的上限
        # 不得被當成已通過。
        no_cap = deepcopy(clean)
        no_cap.pop("single_position_nav_cap")
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


# ⚠ `test_paper_amendment_preserves_original_and_requires_approval` 於 U7
# （2026-08-28）隨資本表達層一起移除：它的前提是 `assess_probe` 會產生一個
# `paper_event_id` 供 correction／reversal 修正，而 `atomic_assess_probe` 已不再
# 建立 paper event，公開路徑上不存在可被修正的新事件。
# `apply_paper_amendment` 仍留在 production，唯一用途是修正 U7 之前的歷史事件。


def test_new_decision_sizing_has_no_capital_expression_fields(tmp_path: Path) -> None:
    """U7 的驗收條件：新凍結的 `sizing` 一個資本欄位都不許有。

    這是 L14 要的那種驗收——不是「這一步回傳成功」，而是「payload 裡真的沒有那些
    key 了」。留一個帶 `axis_ceiling` 的殘骸比整組沒拔還糟：下游會繼續讀它。
    """

    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store, "no-capital-fields")
        decision = assess_probe(
            store, bundle, coverage, _assessment(),
            idempotency_key="assess:no-capital-fields", effective_at=NOW,
        )
        sizing = store.get_decision(decision.decision_id)["payload"]["sizing"]

        for removed in (
            "axis_ceiling",
            "paper_target",
            "paper_max_supported_position",
            "paper_status",
            "live_status",
            "live_supported_range",
            "live_supported_shares",
            "constraint_trace",
        ):
            assert removed not in sizing, f"{removed} 應已隨 U7 移除"

        assert set(sizing) == {
            "cohort_id",
            "context_digest",
            "policy_version",
            "rubric_version",
            "calculator_version",
            "identity_registry_version",
            "weakest_axis",
            "axis_results",
            "assessment_blockers",
            "research_status",
            "paper_blockers",
            "live_blockers",
            "live_current_position",
            "single_position_nav_cap",
        }
        assert sizing["research_status"] in {"READY", "INCOMPLETE", "DATA_NEEDED"}
        # 逐軸結果也不得留下額度殘骸——`ceiling` 是 axis_ceiling 的來源。
        for axis_result in sizing["axis_results"].values():
            assert "ceiling" not in axis_result

        # DecisionExecutionResult 同樣只剩三個欄位。
        assert set(vars(decision)) == {
            "decision_id",
            "decision_digest",
            "research_status",
        }
    finally:
        store.close()


def _insert_legacy_decision(store: DecisionStore, template_decision_id: str) -> str:
    """把一筆 U7 之前形狀的 decision 直接寫進 store，沿用既有 context／coverage。

    刻意繞過 `atomic_assess_probe`：現行 calculator 已經產不出舊 payload，而 store
    裡真的躺著 128 筆這種資料。characterization test 要驗的就是「讀得回來」。
    """

    template = store.get_decision(template_decision_id)
    payload = deepcopy(template["payload"])
    legacy_sizing = deepcopy(payload["sizing"])
    for key in ("research_status", "single_position_nav_cap"):
        legacy_sizing.pop(key, None)
    legacy_sizing.update(
        {
            "paper_status": "ELIGIBLE",
            "live_status": "ELIGIBLE",
            "axis_ceiling": 0.0035,
            "paper_target": 0.0035,
            "paper_max_supported_position": 0.0035,
            "live_supported_range": [0.0, 0.002],
            "live_supported_shares": 80,
            "constraint_trace": [
                {
                    "lane": "live",
                    "constraint": "single_position_cap",
                    "cap_weight": 0.05,
                    "authority": "investment_policy",
                }
            ],
        }
    )
    payload["sizing"] = legacy_sizing
    payload_json = _canonical_json(payload)
    decision_digest = _digest(payload_json)
    decision_id = "pd_" + _digest("legacy:capital-expression")[:32]
    effective_at = "2026-07-21T12:30:00+00:00"
    store._conn.execute(
        """
        INSERT INTO system_decisions (
            decision_id, cohort_id, idempotency_key, request_digest,
            decision_digest, context_digest, coverage_assessment_id,
            policy_version, calculator_version, payload_json, effective_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            decision_id,
            template["cohort_id"],
            "legacy:capital-expression",
            template["request_digest"],
            decision_digest,
            template["context_digest"],
            payload["request"]["coverage"]["assessment_id"],
            "2026-08-13.1",
            "probe-envelope-v3",
            payload_json,
            effective_at,
        ),
    )
    store._conn.commit()
    return decision_id


def test_legacy_capital_expression_decision_stays_readable(tmp_path: Path) -> None:
    """Characterization：U7 之前的 decision 必須照樣讀得回來，且不被回寫。

    Decision Store 是 append-only 的 private authority（L10）——舊 payload 帶著
    `paper_status`／`live_supported_range`／`constraint_trace`／
    `paper_max_supported_position` 永遠留在庫裡。三個讀取端都必須容忍它：
    計數器、Action Card 與 live choice 的資本上限檢查。
    """

    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store, "legacy-shape")
        current = assess_probe(
            store, bundle, coverage, _assessment(),
            idempotency_key="assess:legacy-shape", effective_at=NOW,
        )
        legacy_id = _insert_legacy_decision(store, current.decision_id)
        legacy_sizing = store.get_decision(legacy_id)["payload"]["sizing"]
        assert legacy_sizing["paper_status"] == "ELIGIBLE"

        # 1) 計數器：`live_range_nonzero` 是歷史欄位，只有舊 decision 會貢獻；
        #    `eligible_cohorts` 對舊 decision 退回讀 `paper_status == "ELIGIBLE"`。
        counters = store.capital_expression_counters()
        assert counters["decisions"] == 2
        assert counters["live_range_nonzero"] == 1
        assert counters["eligible_cohorts"] == 1
        assert counters["total_cohorts"] == 1

        # 2) Action Card：舊 payload 沒有 `research_status`，讀取端由 `paper_status`
        #    還原成 READY，不回寫。
        card = build_action_card(store, legacy_id, as_of="2026-07-21T12:31:00+00:00")
        assert card["attention"] in ATTENTION_STATES
        assert card["research"]["status"] == "READY"
        assert card["live"] == {"user_choice": None, "fill_reported": False}

        # 3) live choice：上限來源退回舊 `constraint_trace`，而舊的
        #    `live_supported_range` 上界仍寫進 `system_supported_upper` 供稽核。
        choice_id = record_live_choice(
            store,
            legacy_id,
            selected_weight=0.01,
            decided_at="2026-07-21T12:31:00+00:00",
            explicit=True,
            user_sized=True,
            reason="沿用舊 decision 的凍結上限",
        )
        row = store._conn.execute(
            "SELECT choice_type, system_supported_upper FROM live_choices"
            " WHERE choice_id = ?",
            (choice_id,),
        ).fetchone()
        assert row["choice_type"] == "user_sized"
        assert row["system_supported_upper"] == pytest.approx(0.002)

        # 舊的凍結上限照樣硬擋：容忍舊格式不等於放行。
        with pytest.raises(ExecutionError, match="single position cap"):
            record_live_choice(
                store, legacy_id, selected_weight=0.051,
                decided_at="2026-07-21T12:32:00+00:00", explicit=True,
                user_sized=True, reason="想超過舊上限",
            )

        # 舊 payload 未被任何讀取路徑改寫。
        assert store.get_decision(legacy_id)["payload"]["sizing"] == legacy_sizing
    finally:
        store.close()
