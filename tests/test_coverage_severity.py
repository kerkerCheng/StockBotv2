"""Coverage blocker 的嚴重度分類：研究不完整不該和「不知道在講什麼」同罰。

等到每一項 coverage 都補齊，alpha 通常已經被市場定價完畢（AXT 2026-07：
簽約到財報三天內股價 +63%，而系統的決策此時仍是 DATA_NEEDED）。因此
「功課沒做完」只降低可承受的部位，「連在講什麼都不確定」才歸零。
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from decision_lab.action_card import build_action_card
from decision_lab.blocker_severity import (
    diagnostic_blockers,
    registered_keys,
    severity_of,
)
from decision_lab.context import build_context_bundle, holdings_digest
from decision_lab.coverage import _CHECKLIST_ITEMS, fatal_blockers
from decision_lab.execution import assess_probe
from tests.test_decision_context import NOW, complete_inputs
from tests.test_decision_execution import _store
from tests.test_probe_sizing import _assessment
from thesis.investment_policy import load_policy


# 讓資本歸零：這些缺陷使決策無法稽核或事後檢驗，不是「還沒被證實的好消息」。
FATAL = (
    "identity_unresolved",
    "best_source_missing",
    "causal_path_missing",
    "disproof_missing",
    "expiry_invalid",
    # 報價單位未登記會差 100 倍（IQE.L 2026-08-13 實例）——猜單位比不算更危險。
    "market_quote_unit_unregistered",
    # 抓到別的標的／單位不明／價格損毀：不是「還沒查」，是「查到的東西是錯的」。
    "market_ticker_mismatch",
    "market_unit_unverified",
    "market_price_invalid",
    # 缺幣別無法換算成 NAV 計價，與 unit_unverified 同族。
    "market_currency_missing",
    # quarantined ＝ 已知壞掉，不是還沒查。沿用 beta technical 的既有先例
    # （AGENTS.md 2026-08-01：資料不足／stale／quarantined 時誠實歸零）。
    "financial_quarantined",
)

# 只降尺寸：知道在講哪家公司、骨架可稽核，只是研究還沒做完或資料還沒到。
INCOMPLETE = (
    "independent_source_missing",
    "counter_path_missing",
    "financial_runway_manual_required",
    "catalyst_missing",
    # ↓ 2026-08-13 由 fatal 降級，各有明確理由：
    # graph_company_missing 清除率 0%，且 config 自承「名稱誤導，可能只是 identity
    # 未綁定」——拿可能是假訊號的東西歸零。要恢復 fatal 必須先能區分「圖裡真的
    # 沒有」與「identity 沒綁對」。
    "graph_company_missing",
    # financial_missing／unavailable：financial_resilience 軸的 authority 就是
    # Engine C，缺了那一軸自然變 unknown → ceiling 0。再讓 blocker 歸零是同一件事
    # 罰兩次，且把「這家公司沒資料」誤當成「這家公司有問題」。
    "financial_missing",
    "financial_unavailable",
    # 過期不等於錯，只降尺寸。
    "market_stale",
    "financial_stale",
    "fx_stale",
    # ADV 只影響 live 執行尺寸，由 execution_adv_1pct 單獨處理。
    "market_adv_invalid",
)

# 完全不影響資本，只出現在報表：請求參數、由其他 blocker 導出、或系統自身作業狀態。
# 這一級是 2026-08-13 新增的，因為前兩名觸發者（80.6% 與 66.7%）都屬於此類，
# 而它們在舊制下把 live lane 擋掉 71/72 次。
DIAGNOSTIC = (
    "execution_intent_research_only",
    "execution_intent_paper_only",
    "paper_context_not_ready",
    "live_context_not_ready",
    "coverage_pending",
    "technical_history_insufficient",
    "sheet_only_holding",
)

# 只對 live 致命：live 需要 NAV 與執行 context，paper 在 probe 尺度不需要。
LIVE_ONLY_FATAL = (
    "holdings_unavailable",
    "execution_fx_missing",
    "portfolio_leverage_unavailable",
    "execution_quote_unit_unregistered",
    # 2026-08-13：曾一度誤判為 diagnostic，被 test_live_lane_reachable 抓到。
    # config 原文「只有真的要 size live 部位時才需要 --confirm-holdings」講的是
    # 「live 需要」——沒有經確認的持倉就沒有 NAV，live 區間算不出來。
    # 對 paper／research 它才是必然結果而非缺口。
    "holdings_unconfirmed",
)


def test_fatal_blockers_zero_out_capital() -> None:
    for blocker in FATAL:
        assert fatal_blockers((blocker,)) == (blocker,), f"{blocker} 應歸零"


def test_incomplete_research_does_not_zero_out_capital() -> None:
    for blocker in INCOMPLETE:
        assert fatal_blockers((blocker,)) == (), f"{blocker} 不應歸零，應只降尺寸"


def test_diagnostic_blockers_never_zero_any_lane() -> None:
    """診斷級永遠不得歸零——它們不是關於標的的事實。

    `execution_intent_research_only` 是請求參數（config 自述「此項不是缺口」），
    `holdings_unconfirmed` 是我的試算表狀態（自述「對研究用途是必然結果」）。
    這兩者在 2026-08-13 之前把 live lane 擋掉 71/72 次。
    """
    for blocker in DIAGNOSTIC:
        assert severity_of(blocker) == "diagnostic", f"{blocker} 應為 diagnostic"
        for lane in (None, "paper", "live"):
            assert fatal_blockers((blocker,), lane=lane) == (), f"{blocker} 不得擋 {lane}"
    assert set(diagnostic_blockers(DIAGNOSTIC)) == set(DIAGNOSTIC)


def test_live_only_fatal_does_not_block_paper() -> None:
    """持股與執行 context 缺失只擋 live；paper 在 0.2% 尺度不需要 NAV 與執行市場。"""
    for blocker in LIVE_ONLY_FATAL:
        assert fatal_blockers((blocker,), lane="live") == (blocker,), f"{blocker} 應擋 live"
        assert fatal_blockers((blocker,), lane="paper") == (), f"{blocker} 不應擋 paper"
        # lane=None 沿用舊語意「在任一 lane 致命即算」，供非 lane-scoped 清單使用。
        assert fatal_blockers((blocker,)) == (blocker,)


def test_registry_is_the_single_source_of_severity() -> None:
    """分類只有一份，住在 config/decision_blockers.json。

    先前這裡是硬編碼 frozenset，而 config 另有一套 51 項的 resolution_mode 分類——
    兩套互不知道，一套給人看、一套決定資本（L12）。
    """
    keys = registered_keys()
    assert len(keys) == len(set(keys)), "登記表不得有重複 key"
    for blocker in FATAL + INCOMPLETE + DIAGNOSTIC + LIVE_ONLY_FATAL:
        assert severity_of(blocker) in {"fatal", "sizing", "diagnostic"}


def test_financial_checklist_gaps_only_reduce_size() -> None:
    """五項核驗清單沒填是功課問題，不是身分不明。"""
    for item in _CHECKLIST_ITEMS:
        for suffix in ("missing", "manual_required", "manual_source_missing"):
            blocker = f"financial_{item}_{suffix}"
            assert fatal_blockers((blocker,)) == (), f"{blocker} 不應歸零"


def test_axt_shaped_gap_set_stays_investable_at_reduced_size() -> None:
    """AXT 2026-08-02 的實際 blocker 組合：全是研究不完整，不該被打成零。"""
    axt = (
        "financial_runway_manual_required",
        "independent_source_missing",
        "counter_path_missing",
    )

    assert fatal_blockers(axt) == ()


def test_one_fatal_blocker_dominates_a_pile_of_incomplete_ones() -> None:
    mixed = ("financial_runway_manual_required", "disproof_missing", "catalyst_missing")

    assert fatal_blockers(mixed) == ("disproof_missing",)


def test_unrecognised_blocker_fails_closed() -> None:
    """新增 blocker 若沒分類，預設歸零而不是預設放行。"""
    assert fatal_blockers(("some_future_blocker",)) == ("some_future_blocker",)


def test_every_known_blocker_has_a_deliberate_classification() -> None:
    """coverage.assess_coverage 產得出的每個 blocker 都必須已被分類。

    這是那道剎車：新增一種 blocker 時，這個測試會逼人明確決定它屬於
    「歸零」還是「降尺寸」，而不是靠 fail-closed 預設安靜地擋掉資本。
    """
    known = set(FATAL) | set(INCOMPLETE) | set(DIAGNOSTIC) | {
        f"financial_{item}_{suffix}"
        for item in _CHECKLIST_ITEMS
        for suffix in ("missing", "manual_required", "manual_source_missing")
    }
    classified_fatal = {b for b in known if fatal_blockers((b,))}

    assert classified_fatal == set(FATAL)

    # 每一個都必須是**明確登記**的，不能靠 fail-closed 預設落進 fatal。
    # 判準是「有沒有在 config 命中一條規則」：命中 diagnostic/sizing 顯然是明確的；
    # 命中 fatal 也必須來自登記，而不是未登記的預設。
    from decision_lab.blocker_severity import _match  # noqa: PLC0415 — 僅測試用

    for blocker in sorted(known | set(LIVE_ONLY_FATAL)):
        assert _match(blocker) is not None, f"{blocker} 未登記於 config/decision_blockers.json"


def _decision_with_coverage_blockers(store, blockers: tuple[str, ...], *, key: str):
    """建一筆只有指定 coverage blocker、lane 資料齊全的決策。"""

    payload = deepcopy(complete_inputs())
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
        # 有 blocker 時 status 依 store invariant 必為 coverage_pending；
        # 嚴重度不改寫這個持久化標籤，只改下游怎麼解讀它。
        status="coverage_pending",
        blockers=blockers,
        paper_blockers=(),
        live_blockers=(),
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
        idempotency_key=f"assess:{key}",
        effective_at="2026-07-21T12:00:00+00:00",
    )
    return coverage, decision


# AXT 2026-08-02 的實際缺口組合：全部是研究不完整。
_AXT_SHAPED = (
    "financial_runway_manual_required",
    "independent_source_missing",
    "counter_path_missing",
)


def test_every_consumer_applies_the_same_severity_classification(
    tmp_path: Path,
) -> None:
    """分類正確不夠，四個消費者都必須真的套用它。

    事發（2026-08-08）：2026-08-02 把 counter_path_missing 等分類成「研究不完整」，
    sizing 的 coverage_cap 確實照做了，但其餘三處沒有——
    store.get_coverage_result、coverage.assess_coverage 與 coverage.apply_execution_intent
    都用 `status == "analyzable"`（⟺ 零 blocker）決定 lane readiness，action_card 則用
    整個 core_blockers 決定要不要 REVIEW。於是放寬在下游被完整抵銷：supported range
    仍是 0，card 仍叫使用者「去把研究做完」，而那份分類看起來是生效的。
    這個測試鎖住「所有消費者共用同一份分類」。
    """

    store = _store(tmp_path)
    try:
        coverage, decision = _decision_with_coverage_blockers(
            store, _AXT_SHAPED, key="severity-incomplete"
        )

        # 消費者一：store 的 lane readiness 不因非致命 blocker 而關閉。
        assert coverage.paper_context_ready is True
        assert coverage.live_context_ready is True

        # 消費者二：sizing 不把資本歸零——這是整條鏈唯一真正重要的輸出。
        assert decision.paper_max_supported_position > 0

        # 消費者三：card 不因研究不完整就強制 REVIEW／叫人補研究。
        card = build_action_card(store, decision.decision_id, as_of=NOW)
        assert card["scope"]["single_name"] != "complete_research_work_order"

        # 但它們仍必須看得見：會改變輸出的輸入要出現在輸出自己的證據欄位。
        assert set(_AXT_SHAPED) <= set(card["blockers"])
        assert set(card["research_incomplete_blockers"]) == set(_AXT_SHAPED)
    finally:
        store.close()


def test_one_fatal_blocker_still_forces_research_completion(tmp_path: Path) -> None:
    """放寬只針對研究不完整；致命缺口仍必須擋下並要求補齊。"""

    store = _store(tmp_path)
    try:
        coverage, decision = _decision_with_coverage_blockers(
            store,
            _AXT_SHAPED + ("disproof_missing",),
            key="severity-fatal",
        )

        assert coverage.paper_context_ready is False
        card = build_action_card(store, decision.decision_id, as_of=NOW)
        assert card["action"] == "REVIEW"
        assert card["scope"]["single_name"] == "complete_research_work_order"
        assert "disproof_missing" in card["blockers"]
        # 致命的那個不得被歸進「不阻擋」那一欄。
        assert "disproof_missing" not in card["research_incomplete_blockers"]
    finally:
        store.close()


def test_daily_brief_carries_the_two_standing_counters(tmp_path: Path) -> None:
    """兩個常駐計數器必須出現在 brief，且為 0 時要有警語。

    它們存在的理由不是報表好看：2026-08-13 的 audit 發現同一個診斷被正確寫下四次
    卻從未改到 binding constraint，成因是判準住在要人主動想起來去讀的文件裡
    （D16：入口是使用者的一次動作，出口不該也要求使用者記得）。計數器讓開發迴圈
    的進展每天自己出現，不需要任何人記得回去看 brainstorm。
    """
    from decision_lab.brief import build_today_brief, render_today_markdown

    store = _store(tmp_path)
    try:
        counters = store.capital_expression_counters()
        assert set(counters) == {
            "decisions",
            "live_range_nonzero",
            "outcomes",
            "measured_outcomes",
        }

        brief = build_today_brief(store, as_of=NOW)
        assert brief["capital_expression"] == counters

        # 全新 store：沒有 decision 也沒有 outcome，不該喊警語（沒東西可喊）。
        assert "資本表達" in render_today_markdown(brief)

        primed = dict(brief)
        primed["capital_expression"] = {
            "decisions": 73,
            "live_range_nonzero": 0,
            "outcomes": 8,
            "measured_outcomes": 0,
        }
        text = render_today_markdown(primed)
        assert "非零 live 區間 0/73" in text
        assert "已量測 outcome 0/8" in text
        assert "系統至今從未輸出過可入場區間" in text
        assert "判斷準不準仍無法用證據回答" in text

        # 一旦有產出就不再喊——警語要刺眼到不被略過，但不該每天喊。
        primed["capital_expression"] = {
            "decisions": 73,
            "live_range_nonzero": 8,
            "outcomes": 8,
            "measured_outcomes": 7,
        }
        quiet = render_today_markdown(primed)
        assert "⚠" not in quiet.split("資本表達")[1].split("\n")[0]
    finally:
        store.close()
