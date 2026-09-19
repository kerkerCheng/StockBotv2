"""「欠一個答案」拆成兩格：沒人看過 vs 觀點已在 base 裡（2026-09-19，七缺陷之 5）。

事發：籃子對 SOI.PA／LYC.AX／6324.T 印「還沒寫賭注」，但它們 base 的 derivation 是
`independent`／`company_guidance`——**差異看法整個住在 base 裡**，overlay 只剩那個來源本身的
寬度（LITE 實測賭注空間只有 +0.5pp）。硬要把格子填滿，寫出來的會是「隨便樂觀一點」，
正是 `ASSUMPTION_SCENARIOS` 註解要擋的 bull case。

⚠ **但不得因此自動算成有賭注**：COHR 是 `independent` **且**寫得出 variant（錨在指引上緣）。
所以這一格分的是**欠的是什麼**，不是**欠不欠**——兩者都還欠一個答案（L12：先分開再各自定規則）。
"""
from __future__ import annotations

from webapp.basket import BET_STATES, OPINION_IN_BASE_STANCES, _bet_state


def test_four_states_and_only_two_are_terminal() -> None:
    assert set(BET_STATES) == {"bet", "abstained", "opinion_in_base", "unanswered"}
    assert "不是終局" in BET_STATES["opinion_in_base"] or "仍欠" in BET_STATES["opinion_in_base"]


def test_opinion_in_base_only_for_the_two_stances() -> None:
    assert OPINION_IN_BASE_STANCES == frozenset({"independent", "company_guidance"})
    assert _bet_state(None, abstained=False, stance="independent") == "opinion_in_base"
    assert _bet_state(None, abstained=False, stance="company_guidance") == "opinion_in_base"
    # 共識反解的 base **結構上不可能**與共識不同——那才是真正的「沒人看過」。
    assert _bet_state(None, abstained=False, stance="consensus_inverted") == "unanswered"
    assert _bet_state(None, abstained=False, stance="no_opinion_bearing_assumptions") == "unanswered"
    assert _bet_state(None, abstained=False, stance="undeclared") == "unanswered"
    assert _bet_state(None, abstained=False, stance=None) == "unanswered"


def test_having_a_payoff_still_wins() -> None:
    """COHR 的形狀：base 有觀點**而且**寫得出 overlay——那是 `bet`，不是新格。"""
    assert _bet_state(0.23, abstained=False, stance="independent") == "bet"
    assert _bet_state(-0.31, abstained=False, stance="company_guidance") == "bet"


def test_declared_abstention_beats_opinion_in_base() -> None:
    """宣告不主張是**終局**（已研究、附 revisit_when），不得被降級成「待決定」。"""
    assert _bet_state(None, abstained=True, stance="independent") == "abstained"
