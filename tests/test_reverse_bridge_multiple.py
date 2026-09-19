"""「五倍要什麼為真」＝同一條橋，只換起點（2026-09-19，Phase 7 Step 7.1）。

現行主流程問的是「明年的盈餘，市場給錯價了嗎」——那把尺量的是 20% 等級的錯價。
目標要的是「這家公司如果賭對了，幾年後會不會變五倍」，**而那件事的分子今天幾乎不存在**。

`build_reverse_bridge` 本來就是對的形狀：走一次真正的 `build_bridge`（正向算不出來的，
反解也算不出來）、不單調時回 `no_sign_change` 而不猜。**它與「五倍要什麼為真」的差別
只有起點價格**——所以 Step 7.1 是一個參數，不是一個新模組。

⚠ **問五倍時，`no_sign_change` 才是我們要的答案**：「即使把這個 driver 拉到合法極限也撐不起
五倍」是一個結論，比「需要成長 340%」這個數字有用得多。
"""
from __future__ import annotations

import pytest

from alpha.errors import ContractViolation
from tests.test_reverse_bridge import _actuals, _full_set, TARGET
from alpha.reverse import build_reverse_bridge


def _reverse(price: float, multiple: float, *, multiple_of_return: float = 1.0,
             growth: float = 0.10, margin_delta: float = 0.0):
    return build_reverse_bridge(
        company_id="co:test", ticker="TEST", as_of=None, target_period=TARGET,
        actuals=_actuals(), assumptions=_full_set(growth, margin_delta), current_price=price,
        target_multiple=multiple, our_eps=1.60, consensus_eps=None,
        target_return_multiple=multiple_of_return)


def test_default_is_exactly_the_old_behaviour() -> None:
    """倍率預設 1.0＝原本的「市場隱含」問法。**既有消費者一筆都不該壞**（L11-6）。"""
    result = _reverse(price=40.0, multiple=20.0)
    assert result.target_return_multiple == 1.0
    assert result.market_implied_eps == pytest.approx(2.0)
    assert result.required_eps == pytest.approx(2.0)      # 倍率 1 時兩者相同


def test_asking_for_five_times_moves_only_the_starting_price() -> None:
    result = _reverse(price=40.0, multiple=20.0, multiple_of_return=5.0)
    assert result.required_eps == pytest.approx(10.0)     # 40 × 5 ÷ 20
    # ⚠ 市場隱含那一格**不跟著動**——它回答的是另一個問題（L12：一個表示不承載兩種語意）
    assert result.market_implied_eps == pytest.approx(2.0)


def test_the_two_gaps_answer_two_different_questions() -> None:
    result = _reverse(price=40.0, multiple=20.0, multiple_of_return=5.0)
    assert result.eps_gap == pytest.approx(2.0 / 1.60 - 1)        # 市場比我們樂觀多少
    assert result.required_gap == pytest.approx(10.0 / 1.60 - 1)  # 要五倍還差多少


def test_an_unreachable_target_names_itself_instead_of_guessing() -> None:
    """五倍在一年內做不到時，**每個 driver 都該說「拉到極限也做不到」**，而不是給一個假數字。"""
    result = _reverse(price=40.0, multiple=20.0, multiple_of_return=50.0)
    assert result.required_eps == pytest.approx(100.0)
    assert result.unreachable_drivers, "拉到極限也達不到時必須有 no_sign_change，不得靜默給值"
    for solution in result.unreachable_drivers:
        assert solution.implied_value is None      # 不猜
        assert solution.reason                     # 說得出兩端的值
    assert result.status in ("partial", "missing")


def test_a_reachable_target_still_solves() -> None:
    """**這個機制必須會滅**（L14-4）：倍率小到做得到時，照樣解得出來。"""
    result = _reverse(price=40.0, multiple=20.0, multiple_of_return=1.05)
    assert [s for s in result.solutions if s.status in ("solved", "already_equal")]


def test_zero_or_negative_multiple_is_refused_not_defaulted() -> None:
    """「零倍」「負倍」沒有定義——**不得靠預設值把它變成 1**。"""
    for bad in (0.0, -2.0):
        with pytest.raises(ContractViolation):
            _reverse(price=40.0, multiple=20.0, multiple_of_return=bad)


def test_method_says_which_question_it_answered() -> None:
    result = _reverse(price=40.0, multiple=20.0, multiple_of_return=5.0)
    assert "倍率" in result.method
