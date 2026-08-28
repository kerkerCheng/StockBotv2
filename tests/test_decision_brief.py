from __future__ import annotations

from pathlib import Path

import pytest

from decision_lab.brief import build_today_brief, render_today_markdown
from decision_lab.execution import apply_live_override, prepare_managed_action, record_live_choice
from tests.test_action_card import _decision
from tests.test_decision_execution import _store
from tests.test_decision_context import complete_inputs
from tests.test_operational_workflow import FixtureProvider


NOW = "2026-07-21T12:30:00+00:00"


def _new_store(tmp_path: Path, name: str):
    root = tmp_path / name
    root.mkdir()
    return _store(root)


# U7：四動作（NO ACTION／REVIEW／TRADE／HEDGE）已被兩態 `attention` 取代，所以
# 這裡改成參數化「情境 → 注意力」，而不是參數化動作名。三個情境刻意保留原本的
# 三種 setup——它們是真實會發生的狀態，改變的只是系統對它們的**說法**：
#   明確 skip           → MONITOR（舊 NO ACTION）
#   已記錄 live 但未成交 → REVIEW（舊 TRADE；系統不下單，只能請人回報）
#   投組曝險超限        → REVIEW（舊 HEDGE；系統不給尺寸，只能請人看一眼）
@pytest.mark.parametrize(
    ("scenario", "expected_attention"),
    [
        ("explicit_skip", "MONITOR"),
        ("live_choice_pending_fill", "REVIEW"),
        ("portfolio_over_cap", "REVIEW"),
    ],
)
def test_today_brief_covers_each_attention_scenario_with_field_contract(
    tmp_path: Path, scenario: str, expected_attention: str
) -> None:
    store = _new_store(tmp_path, scenario)
    try:
        decision = _decision(store, key=f"brief-{scenario}")
        cohort_id = store.get_decision(decision.decision_id)["cohort_id"]
        portfolio = {}
        if scenario == "explicit_skip":
            record_live_choice(
                store,
                decision.decision_id,
                selected_weight=0.0,
                decided_at="2026-07-21T12:10:00+00:00",
                explicit=True,
            )
        elif scenario == "live_choice_pending_fill":
            prepared = prepare_managed_action(
                store,
                action_type="live_override",
                target_id=decision.decision_id,
                payload={"selected_weight": 0.001, "reason": "明確接受探索部位"},
                prepared_at="2026-07-21T12:05:00+00:00",
                expires_at="2026-07-21T13:00:00+00:00",
            )
            apply_live_override(
                store,
                prepared.action_id,
                prepared.digest,
                native_approved=True,
                decided_at="2026-07-21T12:10:00+00:00",
            )
        elif scenario == "portfolio_over_cap":
            portfolio[cohort_id] = {
                "status": "over_cap",
                "factor": "photonics",
                "reason": "投組 photonics 曝險超過政策上限。",
            }

        before = {
            table: store.table_count(table)
            for table in (
                "decision_events",
                "context_bundles",
                "system_decisions",
                "paper_events",
                "live_choices",
            )
        }
        brief = build_today_brief(
            store,
            as_of=NOW,
            current_holdings={"status": "available", "rows": []},
            portfolio_context_by_cohort=portfolio,
        )
        after = {
            table: store.table_count(table)
            for table in before
        }

        assert brief["attention"] == expected_attention
        assert brief["action_needed"] is (expected_attention != "MONITOR")
        # `supported_sizing_range` 已隨資本表達層於 U7 移除，不再是欄位契約的一部分。
        for field in (
            "reason",
            "alpha_thesis_changes",
            "beta_portfolio_risk",
            "blockers",
            "next_review_at",
            "user_response_needed",
        ):
            assert field in brief
        assert "supported_sizing_range" not in brief
        assert before == after
        assert "今天需要動作嗎？" in render_today_markdown(brief)
    finally:
        store.close()


def test_today_finds_sheet_only_holding_without_creating_a_cohort(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        before = store.table_count("decision_cohorts")
        brief = build_today_brief(
            store,
            as_of=NOW,
            current_holdings={
                "status": "available",
                "rows": [
                    {
                        "ticker": "LEGACY",
                        "shares": 5.0,
                        "currency": "USD",
                        "market_value_base": 100.0,
                    }
                ],
            },
        )

        assert brief["attention"] == "REVIEW"
        assert "sheet_only_holding" in brief["blockers"]
        assert brief["items"][0]["ticker"] == "LEGACY"
        assert brief["items"][0]["sheet_only"] is True
        # 原本這裡還斷言 supported_sizing_range == [0, 0]；該欄位於 U7 隨資本
        # 表達層移除——sheet-only 持股要的是「有沒有人負責」，不是額度。
        assert "supported_sizing_range" not in brief["items"][0]
        assert store.table_count("decision_cohorts") == before
    finally:
        store.close()


def test_beta_covered_holding_is_visible_but_not_an_alpha_todo(tmp_path: Path) -> None:
    """QQQ 由 beta policy 涵蓋：仍要在 brief 現形，但不得每天配一個新 pq2 編號。"""
    store = _store(tmp_path)
    try:
        brief = build_today_brief(
            store,
            as_of=NOW,
            current_holdings={
                "status": "available",
                "rows": [
                    {
                        "ticker": "QQQ",
                        "shares": 87.0,
                        "currency": "USD",
                        "market_value_base": 58767.63,
                    }
                ],
            },
        )

        item = brief["items"][0]
        assert item["ticker"] == "QQQ"
        assert item["sheet_only"] is True
        assert item["coverage"] == "beta_policy"
        # MONITOR 是 collect_from_decisions 用來跳過 pq2 的唯一判準
        #（U7 之前是 `recommended_action != "NO ACTION"`）。
        assert item["attention"] == "MONITOR"
        assert item["blockers"] == []
        # 覆蓋事實不得冒泡成全域 blocker 噪音。
        assert "alpha_cohort_absent" not in brief["blockers"]
        assert "sheet_only_holding" not in brief["blockers"]
    finally:
        store.close()


def test_user_ignored_holding_is_not_an_alpha_todo(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        brief = build_today_brief(
            store,
            as_of=NOW,
            current_holdings={
                "status": "available",
                "rows": [
                    {
                        "ticker": "TYO:7803",
                        "shares": 400.0,
                        "currency": "USD",
                        "market_value_base": 849.59,
                    }
                ],
            },
        )

        item = brief["items"][0]
        assert item["coverage"] == "user_ignored"
        assert item["attention"] == "MONITOR"
        assert item["blockers"] == []
        # registry 無對應時，markdown 仍要顯示 ticker 而非 unresolved。
        assert "TYO:7803" in render_today_markdown(brief)
    finally:
        store.close()


def test_uncovered_holding_still_demands_review(tmp_path: Path) -> None:
    """回歸護欄：不在 beta policy／ignore 清單的持股必須維持 REVIEW。"""
    store = _store(tmp_path)
    try:
        brief = build_today_brief(
            store,
            as_of=NOW,
            current_holdings={
                "status": "available",
                "rows": [
                    {
                        "ticker": "SOMETHING_NEW",
                        "shares": 10.0,
                        "currency": "USD",
                        "market_value_base": 500.0,
                    }
                ],
            },
        )

        item = brief["items"][0]
        assert item["coverage"] == "uncovered"
        assert item["attention"] == "REVIEW"
        assert "sheet_only_holding" in item["blockers"]
        # U7：要求的動作改成「讓這檔進入瓶頸排序」，不再是配額度。
        assert "瓶頸排序" in item["user_response_needed"]
    finally:
        store.close()


def test_today_does_not_treat_beta_only_move_as_disproof(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        decision = _decision(store, key="brief-beta")
        cohort_id = store.get_decision(decision.decision_id)["cohort_id"]
        record_live_choice(
            store,
            decision.decision_id,
            selected_weight=0.0,
            decided_at="2026-07-21T12:10:00+00:00",
            explicit=True,
        )
        brief = build_today_brief(
            store,
            as_of=NOW,
            current_holdings={"status": "available", "rows": []},
            change_context_by_cohort={
                cohort_id: {
                    "security_return": -0.08,
                    "benchmark_return": -0.07,
                    "evidence_delta": "none",
                    "disproof_triggered": False,
                }
            },
        )

        assert brief["attention"] == "MONITOR"
        assert brief["alpha_thesis_changes"][0]["classification"] == "beta"
        assert brief["alpha_thesis_changes"][0]["thesis_changed"] is False
    finally:
        store.close()


def test_today_reads_current_market_fx_without_deriving_legacy_factor_hedge(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs(
        rows=[
            {
                "ticker": "FRA:2DG",
                "company_id": "co:sivers_semiconductors",
                "shares": 10.0,
                "currency": "EUR",
                "market_value_base": 200.0,
            }
        ]
    )
    inputs["holdings"].update({"nav_base": 1_000.0, "base_currency": "USD"})
    provider = FixtureProvider(inputs=inputs)
    try:
        _decision(store, key="brief-current-authorities")
        provider.inputs["market"]["price"] = 2.75
        provider.inputs["fx"]["rate"] = 0.11

        brief = build_today_brief(
            store,
            as_of=NOW,
            provider=provider,
        )

        # 純價格／匯率變動不產生注意力，也不得被推導成 legacy 的 factor hedge。
        # （U7 之前這裡是 REVIEW，但那個 REVIEW 來自 live lane 的資料缺口分支，
        # 與本測試要鎖的「不得從行情推導動作」無關；lane 移除後正確答案是 MONITOR。）
        assert brief["attention"] == "MONITOR"
        risk = brief["beta_portfolio_risk"][0]
        assert risk["portfolio_action"] == "none"
        assert risk["security_return"] == pytest.approx(0.1)
        assert risk["fx_return"] == pytest.approx(0.1)
    finally:
        store.close()


def test_identity_registration_pending_surfaces_structural_blocker() -> None:
    """2026-08-13：未上市公司的 cohort 缺 registry ticker 時，研究做再多都解不開。

    先前這件事只存在於 brief 作者寫的自然語言（[74] Agility）；作者換人或忘了寫就消失。
    """
    from decision_lab.brief import identity_registration_pending

    class _Registry:
        def company(self, company_id):
            class _C:
                research_ticker = "AAOI" if company_id == "co:applied_optoelectronics" else None
            return _C() if company_id.startswith("co:") else None

    summaries = [
        # 未上市：registry 有登記但沒有 ticker → 應列出
        {"cohort_id": "dc_a", "company_id": None,
         "company_id_hint": "co:agility_robotics",
         "research_ticker": None, "lifecycle_status": "active"},
        # 已終結：不再是待辦
        {"cohort_id": "dc_b", "company_id": None,
         "company_id_hint": "co:agility_robotics",
         "research_ticker": None, "lifecycle_status": "expired"},
        # 已有 ticker：正常
        {"cohort_id": "dc_c", "company_id": "co:applied_optoelectronics",
         "company_id_hint": None,
         "research_ticker": "AAOI", "lifecycle_status": "active"},
        # 連研究對象都不知道：屬 identity 完全未解析，不在本檢查範圍
        {"cohort_id": "dc_d", "company_id": None, "company_id_hint": None,
         "research_ticker": None, "lifecycle_status": "active"},
    ]

    rows = identity_registration_pending(summaries, _Registry())
    assert [r["cohort_id"] for r in rows] == ["dc_a"]
    assert rows[0]["company_id"] == "co:agility_robotics"
    assert rows[0]["registered"] is True
    assert "company_identity.json" in rows[0]["blocking_action"]


def test_blockers_travel_with_their_resolution_mode() -> None:
    """blocker code 必須附上「該由誰動手」，否則每個消費端都會自己再猜一份。

    事發（2026-08-26，一天內兩次）：brief 只給 code 不給 mode，於是
    `engine_b.todo` 手寫了一份 stale 清單去分類（立刻誤判 co:axt），
    同一天口頭也把 system_internal 的 blocker 說成「bug 要解」。
    分類本身早有 SSOT（config/decision_blockers.json 的 resolution_mode），
    缺的只是沒跟資料一起送出來。
    """

    from decision_lab.brief import _blockers_by_mode

    grouped = _blockers_by_mode([
        "holdings_stale",                              # system_internal
        "financial_resilience_corroboration_incomplete",  # user_decision
    ])

    assert grouped["user_decision"] == [
        "financial_resilience_corroboration_incomplete"
    ]
    assert "holdings_stale" in grouped["system_internal"]
    # 不得把三種 mode 混成一張清單——混了之後下游只能猜，而猜錯的方向
    # 永遠是「看起來需要更多研究」。
    assert set(grouped) <= {"user_decision", "system_internal", "awaiting_external"}


def test_blockers_by_mode_is_empty_not_missing_when_no_blockers() -> None:
    from decision_lab.brief import _blockers_by_mode

    assert _blockers_by_mode([]) == {}


def test_today_markdown_has_no_four_action_or_sizing_vocabulary(tmp_path: Path) -> None:
    """U7 驗收條件：首屏 markdown 不得再出現四動作字樣或部位百分比欄位名。

    這兩類字樣代表兩種宣稱：`TRADE`／`HEDGE` 宣稱一個系統做不到的授權（不給尺寸、
    不連 broker）；`supported_range`／`axis_ceiling`／`paper_target` 是已移除的資本
    欄位，若還出現在字串裡，代表某處又自己算了一份尺寸。
    """
    from tests.test_action_card import (
        FORBIDDEN_ACTION_WORDS,
        FORBIDDEN_SIZING_FIELDS,
    )

    store = _store(tmp_path)
    try:
        decision = _decision(store, key="brief-vocab")
        cohort_id = store.get_decision(decision.decision_id)["cohort_id"]
        brief = build_today_brief(
            store,
            as_of=NOW,
            current_holdings={
                "status": "available",
                "rows": [
                    {
                        "ticker": "SOMETHING_NEW",
                        "shares": 10.0,
                        "currency": "USD",
                        "market_value_base": 500.0,
                    }
                ],
            },
            portfolio_context_by_cohort={
                cohort_id: {"status": "over_cap", "factor": "photonics"}
            },
        )
        out = render_today_markdown(brief)

        for word in FORBIDDEN_ACTION_WORDS:
            assert word not in out, f"首屏仍含四動作字樣：{word}"
        for field in FORBIDDEN_SIZING_FIELDS:
            assert field not in out, f"首屏仍含資本欄位名：{field}"
        # 取代它們的兩個中文狀態必須真的在（否則上面的斷言可能只是因為沒渲染項目）。
        assert "注意力：需要複查" in out
        assert "需要複查 —" in out
    finally:
        store.close()
