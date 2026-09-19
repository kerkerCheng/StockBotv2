"""催化劑那一格的四種「沒有」必須分得開（2026-09-19，七缺陷之 1）。

事發：`no_catalyst_in_horizon` 在 16 檔裡亮 15 檔（**93.75%**），清除率 **0**——
那不是 gate，那是牆（L14-4 的前兩個免 outcome 測試）。但第三個測試它過了：
**因果機制講得出**（沒有裁決點的賭注不知道何時認錯，與 L7 同源），所以它是**問錯問題**，
不是該拆掉——它問「一個可選欄位填了沒」，而不是「這個賭注有沒有裁決點」（L15-1）。

成因是四種形狀被壓成同一句話（L12）：
**A** 有日期、只差 `resolves`（4 檔）｜**B** 有散文沒日期（6 檔）｜
**C** 日期晚於目標價日（1 檔，GFS——**判準正確運作的唯一實例**）｜**D** 根本沒有催化劑（4 檔）。

⚠ **拆開不是放寬**：四個理由全部仍然 filtered。不得直接把 `resolves` 改必填
（104 條全沒填，62 個判斷檔會整片無法通過契約驗證），也不得讓沒有 `resolves` 的算進射程
（那是「為了讓籃子非空而放寬篩選條件」，AGENTS.md 明文禁止）。
"""
from __future__ import annotations

from webapp.basket import CATALYST_REASONS, FILTER_REASONS, _catalyst_reason

VALUE_DATE = "2027-06-27"


def _shape(**over):
    base = {"total": 0, "linked": 0, "unlinked": 0, "unlinked_dated": 0,
            "unlinked_undated": 0, "earliest_unlinked_date": None}
    base.update(over)
    return base


def _ripeness(*links):
    return {"counts": {"linked": len(links)}, "links": list(links)}


def test_every_catalyst_reason_is_in_the_closed_vocabulary() -> None:
    assert set(CATALYST_REASONS) <= set(FILTER_REASONS)
    assert "no_catalyst_in_horizon" not in FILTER_REASONS      # 舊的一表兩義 key 已移除


def test_a_catalyst_in_horizon_passes() -> None:
    ripeness = _ripeness({"state": "pending", "expected_at": "2027-01-31"})
    assert _catalyst_reason(ripeness, _shape(total=1, linked=1), VALUE_DATE) is None


def test_shape_a_only_missing_resolves_is_our_todo_not_the_target_s_fault() -> None:
    """A：有日期、也落在目標價日之前，**只差沒填 resolves**——攔錯的那一種。"""
    reason = _catalyst_reason(
        None, _shape(total=3, linked=0, unlinked=3, unlinked_dated=2,
                     earliest_unlinked_date="2027-02-15"), VALUE_DATE)
    assert reason == "catalyst_missing_resolves"
    assert "待辦" in FILTER_REASONS[reason]


def test_shape_b_undated_prose() -> None:
    reason = _catalyst_reason(
        None, _shape(total=2, linked=0, unlinked=2, unlinked_undated=2), VALUE_DATE)
    assert reason == "catalyst_undated"


def test_shape_c_linked_but_too_late_is_the_gate_actually_working() -> None:
    """C：GFS 的形狀——有指名假設的催化劑，但日期晚於目標價日。"""
    ripeness = _ripeness({"state": "pending", "expected_at": "2028-03-31"})
    assert _catalyst_reason(ripeness, _shape(total=1, linked=1), VALUE_DATE) == "catalyst_after_value_date"


def test_shape_c_also_covers_an_undated_link_that_is_simply_too_late() -> None:
    reason = _catalyst_reason(
        None, _shape(total=1, linked=0, unlinked=1, unlinked_dated=1,
                     earliest_unlinked_date="2028-09-30"), VALUE_DATE)
    assert reason == "catalyst_after_value_date"


def test_shape_d_nothing_recorded() -> None:
    assert _catalyst_reason(None, _shape(), VALUE_DATE) == "no_catalyst_recorded"
    assert _catalyst_reason(None, None, VALUE_DATE) == "no_catalyst_recorded"


def test_splitting_did_not_loosen_anything() -> None:
    """四種形狀**全部仍然是 filtered**——拆開只是讓理由分得開。"""
    for shape in (_shape(), _shape(total=2, linked=0, unlinked=2, unlinked_undated=2),
                  _shape(total=1, linked=0, unlinked=1, unlinked_dated=1,
                         earliest_unlinked_date="2027-01-01")):
        assert _catalyst_reason(None, shape, VALUE_DATE) in CATALYST_REASONS
