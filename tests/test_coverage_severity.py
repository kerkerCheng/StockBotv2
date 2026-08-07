"""Coverage blocker 的嚴重度分類：研究不完整不該和「不知道在講什麼」同罰。

等到每一項 coverage 都補齊，alpha 通常已經被市場定價完畢（AXT 2026-07：
簽約到財報三天內股價 +63%，而系統的決策此時仍是 DATA_NEEDED）。因此
「功課沒做完」只降低可承受的部位，「連在講什麼都不確定」才歸零。
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from decision_lab.action_card import build_action_card
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
    "graph_company_missing",
    "best_source_missing",
    "causal_path_missing",
    "financial_missing",
    "financial_unavailable",
    "financial_quarantined",
    "disproof_missing",
    "expiry_invalid",
)

# 只降尺寸：知道在講哪家公司、骨架可稽核，只是研究還沒做完。
INCOMPLETE = (
    "independent_source_missing",
    "counter_path_missing",
    "financial_runway_manual_required",
    "catalyst_missing",
)


def test_fatal_blockers_zero_out_capital() -> None:
    for blocker in FATAL:
        assert fatal_blockers((blocker,)) == (blocker,), f"{blocker} 應歸零"


def test_incomplete_research_does_not_zero_out_capital() -> None:
    for blocker in INCOMPLETE:
        assert fatal_blockers((blocker,)) == (), f"{blocker} 不應歸零，應只降尺寸"


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
    known = set(FATAL) | set(INCOMPLETE) | {
        f"financial_{item}_{suffix}"
        for item in _CHECKLIST_ITEMS
        for suffix in ("missing", "manual_required", "manual_source_missing")
    }
    classified_fatal = {b for b in known if fatal_blockers((b,))}

    assert classified_fatal == set(FATAL)


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
