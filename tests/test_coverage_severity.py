"""Coverage blocker 的嚴重度分類：研究不完整不該和「不知道在講什麼」同罰。

等到每一項 coverage 都補齊，alpha 通常已經被市場定價完畢（AXT 2026-07：
簽約到財報三天內股價 +63%，而系統的決策此時仍是 DATA_NEEDED）。因此
「功課沒做完」只降低可承受的部位，「連在講什麼都不確定」才歸零。
"""
from __future__ import annotations

from decision_lab.coverage import _CHECKLIST_ITEMS, fatal_blockers


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
