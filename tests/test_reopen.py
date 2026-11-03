"""等回落的重開條件——**舊紀錄照讀**（2026-11-01 failure log #124 加上；2026-11-03 盲點修法第 18＋16 條隨等回落退役）。

2026-11-03 起新紀錄寫不出等回落（寫入端 ④⁰，見 test_open_two_gates），重開條件不再叫醒、不再印、不再比對；但帶著它的舊紀錄是
append-only 的一部分，每天照讀。這裡只守讀的那一半：
①合約：只有等回落能帶；至少一個可機械比對的值，或 text 以「不適用：」開頭；沒寫就不進 payload（舊紀錄 brief_id 不變）；
  70 與 70.0 算出同一個 id；
②判斷鍵：舊紀錄加上或改重開條件算改判（當時寫的字，INV-6）；滯留天數與正文版不動。
叫醒、計數、短版標記、⑤ 兩種種類的測試隨機制一起拿掉。
"""
from __future__ import annotations

import pytest

from alpha.candidates import body_version, judgment_version, stall_version
from alpha.errors import ContractViolation
from alpha.narrative import parse_brief_record
from alpha.narrative.contracts import CandidateState, Reopen
from test_priced_since import REOPEN, _at, _chain, _rec


def _with_reopen(reopen) -> list:
    """_chain 之後**只加**重開條件的一版（10-21，理由與正文都不變）——用來看判斷鍵、滯留與正文版各自怎麼走。"""
    a, b, c = _chain()
    d = parse_brief_record(_rec(at=_at(10, 21), reason="寫入時第 87 百分位", supersedes=c.brief_id, reopen=reopen))
    return [a, b, c, d]


# ---- ① 合約（舊紀錄照讀） ----

def test_only_a_wait_can_carry_it_and_it_must_be_checkable_or_say_why_not() -> None:
    with pytest.raises(ContractViolation, match="只有 candidate_state=priced_wait"):
        CandidateState(state="missing", watch_id="ew_x", reason="r", reopen=Reopen(text="x", price_at_or_below=1.0))
    with pytest.raises(ContractViolation, match="至少要一個可機械比對的值"):
        Reopen(text="等便宜一點")
    with pytest.raises(ContractViolation, match="0–100"):
        Reopen(text="x", own_pctile_at_or_below=120)
    for bad in (0, -5, True, float("nan")):
        with pytest.raises(ContractViolation):
            Reopen(text="x", price_at_or_below=bad)
    assert not Reopen(text="不適用：剛上市，沒有三年歷史、也沒有參考價").machine_checkable


def test_old_records_keep_their_id_and_the_number_form_does_not_split_ids() -> None:
    old = _rec(at=_at(10, 5))
    assert "reopen" not in old["candidate_state"] and parse_brief_record(old).brief_id == old["brief_id"]
    as_int = _rec(at=_at(10, 5), reopen={"text": "x", "price_at_or_below": 70})
    as_float = _rec(at=_at(10, 5), reopen={"text": "x", "price_at_or_below": 70.0})
    assert as_int["brief_id"] == as_float["brief_id"]
    parsed = parse_brief_record(as_int)
    assert parsed.candidate_state.reopen.as_dict()["price_at_or_below"] == 70.0
    assert parsed.candidate_state.effective == "open"                                # 讀法：舊的等回落是可開
    with pytest.raises(ContractViolation, match="不認得的鍵"):
        parse_brief_record({**as_int, "candidate_state": {**as_int["candidate_state"],
                                                          "reopen": {"text": "x", "price": 70}}})


# ---- ② 判斷鍵、滯留、正文（舊紀錄） ----

def test_adding_a_condition_is_a_new_judgment_but_not_a_new_stall_or_body() -> None:
    records = _with_reopen(REOPEN)
    current = records[-1]
    assert judgment_version(records, current).brief_id == current.brief_id          # 加上重開條件＝改判（當時寫的字）
    assert stall_version(records, current).brief_id == records[0].brief_id         # 同一段（讀成可開），滯留不歸零
    assert body_version(records, current).brief_id == records[1].brief_id         # 正文自 10-15 沒改
