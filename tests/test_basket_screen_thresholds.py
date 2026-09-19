"""D11 的兩條機械條件接進籃子 filter（2026-09-19，Phase 4a）。

使用者核准 amendment 後，Phase 4 拆成 4a／4b：**4a 是不依賴估值儀器的那幾條**。
市值上限與覆蓋家數上限都只要 Engine C 的快照就算得出來——它們不需要目標倍數、
不需要 payoff，所以不必等 Phase 7。

⚠ **接上去的當天籃子就從「通過 1」變成「通過 0」**（LITE 市值 83.5B／覆蓋 25 被擋）。
那是**合法結果**：`AGENTS.md`「籃子空就空，不得為了非空放寬條件」，而 LITE 從來就不是
「邊緣小公司」。`scripts/alpha_screen_check.py` 早在 2026-09-19 上午就預告了這件事。

⚠ 缺值**各自成一類**（INV-3）：「它太大」與「我們不知道它多大」是兩個結論，
而**沒有量過**又是第三個——三者不得同形。
"""
from __future__ import annotations

from webapp.basket import FILTER_REASONS, _screen_reasons

THRESHOLDS = {"market_cap_max_usd": 10_000_000_000, "analyst_count_max": 12}


def _entry(cap: float | None, count: int | None, absence: str | None = None):
    return {"market_cap_usd": cap, "analyst_count": count, "market_cap_absence": absence}


def test_the_four_reasons_are_registered() -> None:
    for key in ("market_cap_above_max", "analyst_count_above_max",
                "market_cap_unknown", "analyst_count_unknown"):
        assert key in FILTER_REASONS


def test_a_small_well_under_covered_name_passes_both() -> None:
    """IQE.L 的形狀：0.76B／3 位——**這正是要找的那一類**。"""
    assert _screen_reasons(_entry(0.76e9, 3), THRESHOLDS) == []


def test_market_cap_over_the_cap_is_filtered() -> None:
    """LITE 的形狀：83.5B／25——接上去當天就把唯一的 top_pick 擋掉了。"""
    reasons = _screen_reasons(_entry(83.5e9, 25), THRESHOLDS)
    assert "market_cap_above_max" in reasons and "analyst_count_above_max" in reasons


def test_the_two_conditions_are_independent() -> None:
    """TSEM：市值超標但覆蓋只有 7；MP：市值 8.4B 在範圍內但覆蓋 15 超標。"""
    assert _screen_reasons(_entry(25.3e9, 7), THRESHOLDS) == ["market_cap_above_max"]
    assert _screen_reasons(_entry(8.4e9, 15), THRESHOLDS) == ["analyst_count_above_max"]


def test_unknown_is_its_own_reason_not_a_silent_pass() -> None:
    """**「我們不知道它多大」不得被讀成「它夠小」**——那會讓一次取數失敗靜默放行。"""
    assert _screen_reasons(_entry(None, 3, "取不到 GBP/USD 匯率"), THRESHOLDS) == ["market_cap_unknown"]
    assert _screen_reasons(_entry(0.76e9, None), THRESHOLDS) == ["analyst_count_unknown"]


def test_no_screen_means_the_conditions_are_simply_not_applied() -> None:
    """⚠ **「這一輪沒有量」與「量過而且合格」是兩件事。**

    沒有 screen 時一條都不套——把它當成通過，等於讓取數失敗靜默放行整個籃子。
    """
    assert _screen_reasons(None, THRESHOLDS) == []
    assert _screen_reasons(_entry(83.5e9, 25), None) == []      # 沒有門檻也一樣
