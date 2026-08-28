from __future__ import annotations

from pathlib import Path

import pytest

from decision_lab.action_card import RedactionError, build_action_card, render_markdown
from decision_lab.execution import assess_probe
from decision_lab.execution import (
    apply_live_override,
    prepare_managed_action,
    record_live_fill,
)
from decision_lab.models import ATTENTION_STATES, RESEARCH_STATUSES
from decision_lab.outcomes import close_probe, trigger_review_required
from tests.test_decision_context import NOW
from tests.test_decision_execution import _bundle, _store
from tests.test_probe_sizing import _assessment


def _decision(store, *, key="card"):
    bundle, coverage = _bundle(store, key)
    return assess_probe(
        store,
        bundle,
        coverage,
        _assessment(),
        idempotency_key=f"assess:{key}",
        effective_at="2026-07-21T12:00:00+00:00",
    )


def test_action_card_leads_with_attention_and_reports_research_completeness(
    tmp_path: Path,
) -> None:
    """U7：card 首欄由四動作 `action` 改為兩態 `attention`，資本 lane 由研究完整度取代。

    原測試（`..._keeps_paper_live_separate`）斷言 paper.target／live.supported_shares
    這兩個「系統給的尺寸」欄位；資本表達層已於 U7 移除，改為斷言仍存在的三件事：
    注意力狀態、研究完整度、以及 live 只記錄使用者做了什麼。

    ⚠ 這份 fixture 的 attention 由 REVIEW 變成 MONITOR，而且是**正確的**：舊值來自
    「live lane 的必要輸入不完整（holdings_unconfirmed／execution_market_missing）」
    這條分支。live lane 已不存在——系統不判定 live 資格，那些 code 只剩診斷用途，
    留在 `blockers` 裡但不再要求使用者做任何事。
    """
    store = _store(tmp_path)
    try:
        decision = _decision(store)
        # 錨定 as_of 到 fixture 參考時間；不傳則走 wall-clock，fixture 市場時戳
        # （2026-07-21）過 36h freshness 窗後會誤判 data_refresh。
        card = build_action_card(store, decision.decision_id, as_of=NOW)

        assert card["attention"] in ATTENTION_STATES
        assert card["attention"] == "MONITOR"
        assert card["urgency"] == "routine"
        assert card["research"]["status"] in RESEARCH_STATUSES
        assert card["research"]["status"] == "READY"
        assert card["research"]["data_stale"] is False
        # live 不再有系統判定的資格或區間，只剩「使用者做了什麼」。
        assert card["live"] == {"user_choice": None, "fill_reported": False}
        assert card["weakest_link"]["axis"]
        assert card["disproof_condition"]
        assert "Disproof condition" in render_markdown(card)
        assert card["next_action"]
    finally:
        store.close()


def test_coverage_blocker_that_drives_review_appears_in_card_blockers(
    tmp_path: Path,
) -> None:
    """把 attention 判成 REVIEW 的 core blocker 必須出現在 card 自己的 blockers 裡。

    事發（2026-08-05）：co:axt 的唯一實質缺口是 coverage 的
    financial_runway_manual_required，但 card blockers 只放 assessment_blockers，
    所以下游只看得到 lane blocker（全屬 system_internal），待辦池因此推導出
    「僅剩系統內部狀態，重新 reassess 即可」——與真正的缺口完全無關，而且會
    誘導使用者去跑一個不會改變任何東西的 reassess。

    U7 補強：本測試原本的 REVIEW 其實來自 live lane 的 DATA_NEEDED 分支，而不是
    coverage blocker 本身（`financial_runway_manual_required` 是 `sizing` 嚴重度，
    不阻擋）。live lane 移除後那個假來源沒了，所以這裡改為同時放一個**真正致命**的
    coverage blocker，讓「驅動 REVIEW」與「出現在 blockers」是同一件事；不阻擋的
    那一個仍必須帶著自己的嚴重度分類出現（L16：分類要跟著資料走）。
    """

    from copy import deepcopy

    from decision_lab.context import build_context_bundle, holdings_digest
    from tests.test_decision_context import complete_inputs
    from thesis.investment_policy import load_policy

    store = _store(tmp_path)
    try:
        payload = deepcopy(complete_inputs())
        identity = payload["identity"]
        cohort_id = store.ensure_cohort(
            dedupe_key="coverage-blocker",
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
            # 有 core blocker 時 coverage 依契約就是 coverage_pending，不可能是
            # analyzable——這正是 co:axt 的真實狀態。
            status="coverage_pending",
            blockers=("financial_runway_manual_required", "best_source_missing"),
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
        decision = assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="assess:coverage-blocker",
            effective_at="2026-07-21T12:00:00+00:00",
        )

        card = build_action_card(store, decision.decision_id, as_of=NOW)

        assert card["attention"] == "REVIEW"
        assert "best_source_missing" in card["blockers"]
        assert "financial_runway_manual_required" in card["blockers"]
        # 不阻擋的那一個仍要現形，並且明確標成「不阻擋、只影響排序」。
        assert "financial_runway_manual_required" in card["research_incomplete_blockers"]
        assert "best_source_missing" not in card["research_incomplete_blockers"]
    finally:
        store.close()


def test_beta_move_without_evidence_delta_is_not_called_thesis_disproof(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="beta")
        card = build_action_card(
            store,
            decision.decision_id,
            change_context={
                "security_return": -0.08,
                "benchmark_return": -0.07,
                "evidence_delta": "none",
                "disproof_triggered": False,
            },
        )

        assert card["alpha_beta"]["classification"] == "beta"
        assert card["alpha_beta"]["thesis_changed"] is False
        assert "disproof" not in card["reason"].lower()
    finally:
        store.close()


def test_portfolio_factor_breach_asks_for_review_without_fake_units(
    tmp_path: Path,
) -> None:
    """投組曝險超限仍要指名「該降哪一項」，但它是複查請求而非 HEDGE 授權。

    U7：`HEDGE` 這個動作字樣已移除——系統不給尺寸也不連 broker，說 HEDGE 等於宣稱
    一個它做不到的授權。原本承載資訊的 `scope.portfolio` 完全保留，不得因為改名
    而把「要降低哪一項曝險」弄丟。
    """
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="hedge")
        card = build_action_card(
            store,
            decision.decision_id,
            as_of=NOW,  # 錨定，避免 wall-clock 使 fixture 資料過期而搶先 data_refresh
            portfolio_context={
                "status": "over_cap",
                "factor": "photonics",
                "reason": "portfolio factor exposure exceeded",
            },
        )

        assert card["attention"] == "REVIEW"
        assert card["scope"]["portfolio"] == "reduce_or_hedge:photonics"
        assert card["scope"]["single_name"] == "hold_pending_portfolio_action"
        assert "shares" not in card["scope"]
    finally:
        store.close()


def test_card_is_pure_read_and_markdown_preserves_first_screen_contract(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="pure")
        before = {
            table: store.table_count(table)
            for table in ("system_decisions", "paper_events", "live_choices")
        }
        card = build_action_card(store, decision.decision_id)
        markdown = render_markdown(card)
        after = {
            table: store.table_count(table)
            for table in ("system_decisions", "paper_events", "live_choices")
        }

        assert before == after
        # 標題不再是動作，而是注意力狀態。
        assert markdown.splitlines()[0].startswith("# 需要複查")
        assert "Weakest link" in markdown
        assert "研究完整度" in markdown
        assert "Live" in markdown
        assert "下一步" in markdown
    finally:
        store.close()


def test_secret_bearing_optional_context_is_rejected_before_render(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="secret")
        with pytest.raises(RedactionError, match="secret"):
            build_action_card(
                store,
                decision.decision_id,
                change_context={"api_token": "CANARY-DO-NOT-LEAK"},
            )
        with pytest.raises(RedactionError, match="secret"):
            build_action_card(
                store,
                decision.decision_id,
                change_context={"notes": "Authorization: Bearer CANARY-DO-NOT-LEAK"},
            )
    finally:
        store.close()


def test_markdown_renderer_escapes_research_text_and_terminal_controls(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle, coverage = _bundle(store, "markdown-escape")
        assessment = _assessment()
        assessment["source_reliability"]["reason"] = "*injected*\n# heading\x1b[31m"
        decision = assess_probe(
            store,
            bundle,
            coverage,
            assessment,
            idempotency_key="card:markdown-escape",
            effective_at="2026-07-21T12:00:00+00:00",
        )
        markdown = render_markdown(build_action_card(store, decision.decision_id))

        assert "\x1b" not in markdown
        assert "\n# heading" not in markdown
        assert r"\*injected\*" in markdown
    finally:
        store.close()


def test_card_respects_explicit_live_fill_instead_of_asking_again(
    tmp_path: Path,
) -> None:
    """已回報成交後，card 只監控，不再要求任何動作。"""
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="filled")
        prepared = prepare_managed_action(
            store,
            action_type="live_override",
            target_id=decision.decision_id,
            payload={"selected_weight": 0.01, "reason": "我接受額外探索風險"},
            prepared_at="2026-07-21T12:00:00+00:00",
            expires_at="2026-07-21T13:00:00+00:00",
        )
        apply_live_override(
            store,
            prepared.action_id,
            prepared.digest,
            native_approved=True,
            decided_at="2026-07-21T12:05:00+00:00",
        )
        record_live_fill(
            store,
            decision.decision_id,
            execution_ref="manual:card-fill",
            shares=10,
            price=2.0,
            currency="EUR",
            executed_at="2026-07-21T12:10:00+00:00",
            explicit=True,
        )

        card = build_action_card(store, decision.decision_id, as_of=NOW)

        assert card["attention"] == "MONITOR"
        assert card["live"]["fill_reported"] is True
        assert card["scope"]["single_name"] == "monitor_confirmed_live_execution"
    finally:
        store.close()


def test_review_required_lifecycle_forces_48h_review_without_optional_context(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="lifecycle-review")
        cohort_id = store.get_decision(decision.decision_id)["cohort_id"]
        trigger_review_required(
            store,
            cohort_id,
            reason="Customer qualification failed",
            evidence_refs=["fixture://customer"],
            effective_at="2026-07-21T12:10:00+00:00",
        )

        card = build_action_card(store, decision.decision_id)

        assert card["attention"] == "REVIEW"
        assert card["urgency"] == "within_48h"
        assert card["lifecycle"]["status"] == "review_required"
        assert card["lifecycle"]["review_due_at"] == "2026-07-23T12:10:00+00:00"
    finally:
        store.close()


def test_action_card_rechecks_frozen_freshness_at_render_time(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="stale-card")
        card = build_action_card(
            store,
            decision.decision_id,
            as_of="2026-08-10T12:00:00+00:00",
        )

        assert card["attention"] == "REVIEW"
        assert card["urgency"] == "data_refresh"
        # 資料過期不再表現成 paper lane 失格，而是研究完整度降級。
        assert card["research"]["status"] == "DATA_NEEDED"
        assert card["research"]["data_stale"] is True
        assert any("stale_since_decision" in item for item in card["blockers"])
    finally:
        store.close()


def test_terminal_probe_never_reuses_old_decision_to_open_position(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="terminal-card")
        cohort_id = store.get_decision(decision.decision_id)["cohort_id"]
        close_probe(
            store,
            cohort_id,
            terminal_status="rejected",
            claim_correctness="false",
            current_market={"status": "missing"},
            benchmark={"status": "missing"},
            reason="Claim disproved",
            evidence_refs=["fixture://counter"],
            effective_at="2026-07-21T13:00:00+00:00",
        )

        card = build_action_card(
            store, decision.decision_id, as_of="2026-07-21T13:05:00+00:00"
        )
        assert card["attention"] == "REVIEW"
        assert card["scope"]["single_name"] == "terminal_unwind_review"
    finally:
        store.close()


def test_disproof_review_remains_primary_when_portfolio_is_over_cap(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="review-and-hedge")
        cohort_id = store.get_decision(decision.decision_id)["cohort_id"]
        trigger_review_required(
            store,
            cohort_id,
            reason="Customer qualification failed",
            evidence_refs=["fixture://customer"],
            effective_at="2026-07-21T12:10:00+00:00",
        )
        card = build_action_card(
            store,
            decision.decision_id,
            as_of="2026-07-21T12:20:00+00:00",
            portfolio_context={"status": "over_cap", "factor": "photonics"},
        )

        assert card["attention"] == "REVIEW"
        assert card["urgency"] == "within_48h"
        assert card["scope"]["portfolio"] == "reduce_or_hedge:photonics"
    finally:
        store.close()


def test_new_live_choice_requires_its_own_fill(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="choice-link")
        first = prepare_managed_action(
            store,
            action_type="live_override",
            target_id=decision.decision_id,
            payload={"selected_weight": 0.01, "reason": "first"},
            prepared_at="2026-07-21T12:00:00+00:00",
            expires_at="2026-07-21T13:00:00+00:00",
        )
        apply_live_override(
            store,
            first.action_id,
            first.digest,
            native_approved=True,
            decided_at="2026-07-21T12:05:00+00:00",
        )
        record_live_fill(
            store,
            decision.decision_id,
            execution_ref="manual:first-fill",
            shares=10,
            price=2.0,
            currency="EUR",
            executed_at="2026-07-21T12:10:00+00:00",
            explicit=True,
        )
        second = prepare_managed_action(
            store,
            action_type="live_override",
            target_id=decision.decision_id,
            payload={"selected_weight": 0.02, "reason": "second"},
            prepared_at="2026-07-21T12:15:00+00:00",
            expires_at="2026-07-21T13:00:00+00:00",
        )
        apply_live_override(
            store,
            second.action_id,
            second.digest,
            native_approved=True,
            decided_at="2026-07-21T12:20:00+00:00",
        )

        card = build_action_card(
            store, decision.decision_id, as_of="2026-07-21T12:25:00+00:00"
        )
        assert card["live"]["fill_reported"] is False
        # U7：舊 `TRADE` 的 `execute_confirmed_live_choice` 改為 `report_manual_fill`
        # ——系統不下單，能請使用者做的只有回報自己手動下的那一筆。
        assert card["attention"] == "REVIEW"
        assert card["urgency"] == "awaiting_manual_execution"
        assert card["scope"]["single_name"] == "report_manual_fill"
    finally:
        store.close()


def _synthetic_card() -> dict:
    """最小的 card DTO：只給 renderer 需要的欄位，不經過 store。"""

    return {
        "attention": "REVIEW",
        "company_id": "co:test",
        "urgency": "next_review",
        "reason": "r",
        "alpha_beta": {"classification": "alpha"},
        "disproof_condition": "d",
        "weakest_link": {
            "axis": "source_reliability",
            "level": "bounded_hypothesis",
            "reason": "w",
        },
        "execution_intent": "paper",
        "research": {"status": "INCOMPLETE", "data_stale": False},
        "live": {"user_choice": None, "fill_reported": False},
        "blockers": [],
        "research_incomplete_blockers": [],
        "next_action": "n",
    }


def test_markdown_does_not_present_a_recommended_size() -> None:
    """Alpha 呈現契約（2026-08-15）：不對人輸出建議尺寸。

    事發：6 個 ELIGIBLE cohort 的 target 全是同一個 0.1% NAV（合計 0.6%，以可部署
    現金計每檔約 30 美元）。那個數字來自從未被 outcome 驗證的 axis_ceiling
    （measured_outcomes 0/8），是常數、不帶資訊，卻讓人讀成系統在建議部位。
    使用者的話：「繞了這麼久只得到我很早就看到的幾間公司、都等於 0.2%。」

    U7 把這條契約從「呈現層不顯示」推進到「底層根本不算」：paper target 與
    live supported range 已隨資本表達層一起移除，所以這裡不再有數值可藏。
    保留本測試是因為它鎖的另一半仍然成立——**狀態與診斷必須留著**。
    """

    import re
    from decision_lab.action_card import render_markdown

    out = render_markdown(_synthetic_card())

    assert not re.search(r"\d+\.\d+%", out), "不得把尺寸當行動指引呈現"
    assert not re.search(r"target=", out)
    # 但狀態與診斷必須留著——今天整天就是靠 blockers 找到問題的。
    assert "INCOMPLETE" in out
    assert "Blockers" in out
    assert "人工決定" in out


# U7 驗收條件：四動作字樣與部位百分比欄位名都不得再出現在人看得到的輸出裡。
# 這不是風格檢查——說出 `TRADE`／`HEDGE` 等於宣稱一個系統做不到的授權，而
# `supported_range`／`axis_ceiling`／`paper_target` 是已被移除的資本欄位，
# 它們若還在字串裡出現，代表某處還在自己算一份尺寸（L16：分類已有 SSOT 時
# 不要在下游重造）。
FORBIDDEN_ACTION_WORDS = ("NO_ACTION", "NO ACTION", "TRADE", "HEDGE")
FORBIDDEN_SIZING_FIELDS = ("supported_range", "axis_ceiling", "paper_target")


def test_action_card_markdown_has_no_four_action_or_sizing_vocabulary(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="vocab")
        for context in (
            None,
            {"status": "over_cap", "factor": "photonics"},
        ):
            card = build_action_card(
                store, decision.decision_id, as_of=NOW, portfolio_context=context
            )
            out = render_markdown(card)
            for word in FORBIDDEN_ACTION_WORDS:
                assert word not in out, f"markdown 仍含四動作字樣：{word}"
            for field in FORBIDDEN_SIZING_FIELDS:
                assert field not in out, f"markdown 仍含資本欄位名：{field}"
        # `reduce_or_hedge:<factor>` 只活在 JSON 的 scope 裡（小寫、機器讀），
        # 不會以動作字樣出現在人看的 markdown 上。
        assert "HEDGE" not in render_markdown(_synthetic_card())
    finally:
        store.close()
