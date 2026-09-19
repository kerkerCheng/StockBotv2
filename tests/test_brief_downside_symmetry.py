"""首屏短評必須講得出「判斷錯了值多少」（2026-09-19，七缺陷之 4）。

D2（2026-09-16）逐字：「那把尺多一端：**判斷錯了值多少**」、「賭注與判斷錯了值多少**對稱**」。
但 `PLACEHOLDERS` 只有 `bet_target`／`payoff`，**沒有 downside 端**，而同一格的 `do_not` 又寫著
「目標價與報酬一律 placeholder」——**兩條合起來讓首屏結構上講不出下檔數字**。
值早就存在（`brief_scale` 的 `downside_target`／`downside_return`），只是沒跟著資料走到那一格（L16）。

⚠ 缺席不得被壓成 0：實測 16 檔只有 LITE 與 AXTI 有 downside scenario，其餘填不出來時
印 `（尚無）` 並標 partial——「**還沒做**」與「**做了，結論是跌幅有限**」是兩件不同的事。
"""
from __future__ import annotations

import pytest

from alpha.errors import ContractViolation
from alpha.narrative import ABSENT, PLACEHOLDERS, fill_brief
from alpha.narrative.contracts import BRIEF_FRAME, SLOT_KEYS, brief_record, parse_brief_record


def _brief(text: str):
    slots = []
    for key in SLOT_KEYS:
        slots.append({"key": key, "text": (text if key == "if_right_if_wrong" else "一句話。"),
                      "evidence_refs": ["engine_c://financial_snapshot/LITE"]})
    return parse_brief_record(brief_record(
        ticker="LITE", company_id="co:lumentum", slots=slots, note="test"))


def test_downside_placeholders_are_registered() -> None:
    assert "downside_target" in PLACEHOLDERS and "downside_return" in PLACEHOLDERS


def test_a_slot_may_now_say_what_being_wrong_costs() -> None:
    brief = _brief("賭對了值 {bet_target}，判斷錯了值 {downside_target}（{downside_return}）。")
    filled, absent = fill_brief(brief, {"bet_target": "984 USD", "downside_target": "804.21 USD",
                                        "downside_return": "−13.6%"})
    assert "804.21 USD" in filled["if_right_if_wrong"] and "−13.6%" in filled["if_right_if_wrong"]
    assert not absent.get("if_right_if_wrong")


def test_missing_downside_prints_absent_not_zero() -> None:
    """沒有 downside scenario 的 14 檔：印「（尚無）」並現形，**不補 0**。"""
    brief = _brief("賭對了值 {bet_target}，判斷錯了值 {downside_target}。")
    filled, absent = fill_brief(brief, {"bet_target": "244 USD", "downside_target": None})
    assert ABSENT in filled["if_right_if_wrong"]
    assert "0" not in filled["if_right_if_wrong"].replace("244", "")   # 沒有被補成 0
    assert "{downside_target}" in absent["if_right_if_wrong"]


def test_unregistered_placeholder_is_still_rejected() -> None:
    """開的是兩個具名 placeholder，**不是把封閉字彙打開**。"""
    with pytest.raises(ContractViolation):
        _brief("判斷錯了值 {downside_price}。")


def test_the_slot_spec_asks_for_both_ends() -> None:
    spec = BRIEF_FRAME["if_right_if_wrong"]
    assert "downside_target" in spec["look_at"]
    assert "對稱" in spec["do_not"]
    # 2026-09-19 實測教訓：在 placeholder 旁邊寫「兩邊差不多大」當場就錯了。
    assert "依賴那個數字大小的結論" in spec["do_not"]
