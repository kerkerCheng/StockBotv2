"""Coverage blocker 嚴重度分類——唯一權威。

這份分類刻意住在一個不依賴 store／coverage 的模組裡，因為它有三個消費者，
而它們分屬不同層：

- ``sizing.calculate_probe_limits``：決定 ``coverage_cap`` 要不要歸零。
- ``coverage.assess_coverage`` 與 ``coverage.apply_execution_intent``：決定 lane 的
  ``context_ready``。
- ``store.get_coverage_result``：從持久化狀態重建同一個 ``context_ready``。
- ``action_card.build_action_card``：決定要不要強制 ``REVIEW``。

先前它只住在 ``coverage.py``，而 ``coverage`` 依賴 ``store``，於是 store 想用就會
循環 import——結果是只有 sizing 真的套用了分類，其餘三處各自用
``status == "analyzable"``（⟺ 零 blocker）這個更粗的判準，把 2026-08-02 的放寬在
下游完整抵銷掉。分類本身沒錯，錯在它沒有一個所有層都拿得到的家。

⚠ ``status`` 的 ``analyzable`` ⟺ 零 blocker 是持久化 invariant（見
``store.record_coverage_assessment``），不得為了放行研究不完整的案例而鬆動；
需要嚴重度時一律呼叫本模組，不要拿 ``status`` 當代理指標。

新增 blocker 時 ``tests/test_coverage_severity.py`` 會失敗，強迫做出分類決定，
而不是靠預設安靜放行。
"""
from __future__ import annotations


CHECKLIST_ITEMS = (
    "gross_margin_trend",
    "customer_concentration",
    "backlog",
    "dilution",
    "valuation_pressure",
)

# Coverage blocker 分兩類，因為它們擋的是完全不同的東西。
#
# 「研究還不完整」＝知道在講哪家公司、也有可稽核的骨架，只是功課沒做完。這類
# 不該歸零資本，該讓 Confidence 的 axis_ceiling 生效——證據不完備就只能小注，
# 但不是不能參與。等到每一項都補齊，alpha 通常也已經被市場定價完畢。
#
# 「連在講什麼都不確定」＝身分無法解析、圖裡沒有這家公司、一份來源都沒有、
# 財務 authority 掛掉、沒有證偽條件、決策沒有有效期。這類仍然歸零：它們不是
# 「還沒被證實的好消息」，而是讓整筆決策無法被稽核或事後檢驗的缺陷。
#
# 未列入本集合的一律當致命處理（fail closed）。
INCOMPLETE_COVERAGE_BLOCKERS = frozenset(
    {
        # 只有當事人來源；證據弱，但主張本身是明確的。
        "independent_source_missing",
        # 圖裡還沒有反面路徑。
        "counter_path_missing",
        # Engine C 算不出 runway（yfinance 在財報後常暫時缺 FCF）。
        "financial_runway_manual_required",
        # 還沒寫催化劑。disproof 是硬性的（L7），catalyst 不是。
        "catalyst_missing",
    }
)


def is_incomplete_research(blocker: str) -> bool:
    if blocker in INCOMPLETE_COVERAGE_BLOCKERS:
        return True
    # 財務核驗清單五項的各種缺漏：功課沒做完，不是不知道在講誰。
    return any(blocker.startswith(f"financial_{item}_") for item in CHECKLIST_ITEMS)


def fatal_blockers(blockers: tuple[str, ...]) -> tuple[str, ...]:
    """回傳應使資本歸零的 blocker；研究不完整的項目不在其中。"""

    return tuple(b for b in blockers if not is_incomplete_research(b))


__all__ = [
    "CHECKLIST_ITEMS",
    "INCOMPLETE_COVERAGE_BLOCKERS",
    "fatal_blockers",
    "is_incomplete_research",
]
