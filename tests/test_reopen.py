"""等回落的重開條件（2026-11-01 使用者「兩點都照你建議吧」；failure log #124；plan 2026-11-01-002 P1）。

10-31 四檔等回落被價格叫醒、重寫四次、狀態一次都沒變；使用者 10-22 兩次問「回落多少才變可開」。
守的事：
①合約：只有等回落能帶；至少一個可機械比對的值，或 text 以「不適用：」開頭；沒寫就不進 payload（舊紀錄 brief_id 不變）；
  70 與 70.0 算出同一個 id；
②寫入端：新寫的等回落沒帶就拒收；只改字面值的重述（restates）不擋；
③叫醒（Q1 換成）：寫了可比對條件的列，達成才進 rewrite[]，回落本身不再叫醒、也不出 kind=pulled_back；
  沒寫的舊紀錄照 #116 回落叫醒，另進一次「沒寫重開條件」；「不適用：」照 #116；量不到＝None，不是沒達成；
④判斷鍵：加上或改重開條件算改判；滯留天數與正文版不動；
⑤心跳與短版：計數、標記、圖例，沒算印「未算」；短版不出現「該／燈／買／賣」；
⑥待做清單：兩種新種類都算進「敘事該重寫」並點名公司。
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from alpha.candidates import (
    NO_REOPEN_REASON, PULLED_BACK_PREFIX, REOPEN_MET_PREFIX, assemble_board, body_version, judgment_version,
    pullback_counts, reopen_counts, reopen_status, stall_version,
)
from alpha.errors import ContractViolation
from alpha.narrative import parse_brief_record
from alpha.narrative.contracts import CandidateState, Reopen
from alpha.providers.briefs import read_brief_records, write_brief
from alpha.providers.candidates import board_rewrite
from engine_b import event_watch as ew
from test_priced_since import CO, REOPEN, TODAY, _artifact, _at, _chain, _ctx, _derive, _fresh, _rec

BARS = [(date(2026, 9, 28), 100.0), (date(2026, 10, 14), 90.0), (date(2026, 10, 20), 77.85)]   # 10-20 收 77.85


def _with_reopen(reopen) -> list:
    """_chain 之後**只加**重開條件的一版（10-21，理由與正文都不變）——用來看判斷鍵、滯留與正文版各自怎麼走。"""
    a, b, c = _chain()
    d = parse_brief_record(_rec(at=_at(10, 21), reason="寫入時第 87 百分位", supersedes=c.brief_id, reopen=reopen))
    return [a, b, c, d]


def _chain_with(reopen) -> list:
    """同 _chain，但 10-15 那次改判起就帶重開條件：判斷日停在 10-15（收 90），10-20 收 77.85——舊規則會叫醒的那一刻。"""
    a = _rec(at=_at(9, 29), reason="寫入時第 90 百分位")
    b = _rec(at=_at(10, 15), reason="寫入時第 87 百分位", supersedes=a["brief_id"], reopen=reopen)
    c = _rec(at=_at(10, 20), reason="寫入時第 87 百分位", supersedes=b["brief_id"], evidence="graph://y", reopen=reopen)
    return [parse_brief_record(r) for r in (a, b, c)]


# ---- ① 合約 ----

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
    assert parse_brief_record(as_int).candidate_state.reopen.as_dict()["price_at_or_below"] == 70.0
    with pytest.raises(ContractViolation, match="不認得的鍵"):
        parse_brief_record({**as_int, "candidate_state": {**as_int["candidate_state"],
                                                          "reopen": {"text": "x", "price": 70}}})


# ---- ② 寫入端 ----

def test_a_new_wait_without_a_reopen_condition_is_refused(tmp_path: Path) -> None:
    ctx, wid = _ctx()
    with pytest.raises(ContractViolation, match="等回落要寫重開條件"):
        write_brief(_fresh(wid, reopen=None), ctx=ctx, directory=tmp_path / "b", watches_path=tmp_path / "w.json")
    out = write_brief(_fresh(wid), ctx=ctx, directory=tmp_path / "b", watches_path=tmp_path / "w.json")
    (saved,), _ = read_brief_records("AXTI", directory=tmp_path / "b")
    assert saved.brief_id == out["brief_id"] and saved.candidate_state.reopen.price_at_or_below == 70.0


# ---- ③ 叫醒 ----

def test_a_checkable_condition_replaces_the_pullback_wake() -> None:
    """10-20 收 77.85 低於判斷日：舊規則會叫醒。寫了「收盤 ≤ 70」→ 還沒到 → 不叫醒、不出 kind=pulled_back、不算已回落。"""
    row, _ = _derive(_chain_with({"text": "回到 70 以下", "price_at_or_below": 70.0}), bars=BARS)
    assert row["wake_by"] == "reopen" and row["reopen"]["met"] is False and row["reopen_missing"] is False
    assert row["pulled_back"] is True                                  # 事實照算
    assert not any(r.startswith(PULLED_BACK_PREFIX) for r in row["rewrite"])
    assert not any(r.startswith(REOPEN_MET_PREFIX) for r in row["rewrite"])
    kinds = [b["kind"] for b in board_rewrite([row], [])]
    assert "pulled_back" not in kinds and "reopen_met" not in kinds and "no_reopen" not in kinds
    assert pullback_counts([row]) == {"pulled_back": 0, "unknown": 0}
    assert "收盤 ≤ 70（今 77.85，差 −10.1%）" in row["reopen"]["line"]


@pytest.mark.parametrize("reopen", [{"text": "回到 80 以下", "price_at_or_below": 80.0},
                                    {"text": "百分位回到 90 以下", "own_pctile_at_or_below": 90.0}])
def test_reaching_either_value_wakes_with_the_condition_only(reopen) -> None:
    row, _ = _derive(_chain_with(reopen), bars=BARS)
    assert row["reopen"]["met"] is True
    reasons = [r for r in row["rewrite"] if r.startswith(REOPEN_MET_PREFIX)]
    assert len(reasons) == 1 and "今" not in reasons[0] and "%" not in reasons[0]     # 不帶每天變的數字
    assert "重開達成" in row["rewrite_words"]
    listed = [b for b in board_rewrite([row], []) if b["kind"] == "reopen_met"]
    assert len(listed) == 1 and listed[0]["condition"] == reasons[0]
    board = assemble_board([row], universe=["AXTI"], held={"status": "ok", "by_company": {}}, narrative_rewrite=listed)
    assert board["counts"]["priced_wait_reopen_met"] == 1 and board["counts"]["priced_wait_pulled_back"] == 0


def test_an_unmeasurable_input_is_not_a_miss() -> None:
    row, _ = _derive(_chain_with({"text": "百分位回到 50 以下", "own_pctile_at_or_below": 50.0}), now=None, bars=BARS)
    assert row["reopen"]["met"] is None and "今天量不到" in row["reopen"]["line"]
    assert reopen_counts([row])["reopen_unknown"] == 1


def test_an_old_record_keeps_the_pullback_wake_and_is_asked_to_add_a_condition_once() -> None:
    row, _ = _derive(_chain(), bars=BARS)
    assert row["wake_by"] == "pulled_back" and row["reopen"] is None and row["reopen_missing"] is True
    assert any(r.startswith(PULLED_BACK_PREFIX) for r in row["rewrite"]) and NO_REOPEN_REASON in row["rewrite"]
    kinds = [b["kind"] for b in board_rewrite([row], [])]
    assert kinds.count("pulled_back") == 1 and kinds.count("no_reopen") == 1
    assert "沒寫重開" in row["rewrite_words"]


def test_not_applicable_keeps_the_pullback_wake() -> None:
    row, _ = _derive(_chain_with({"text": "不適用：剛重估，三年區間沒有參考意義"}), bars=BARS)
    assert row["wake_by"] == "pulled_back" and row["reopen"]["machine"] is False and row["reopen_missing"] is False
    assert any(r.startswith(PULLED_BACK_PREFIX) for r in row["rewrite"]) and NO_REOPEN_REASON not in row["rewrite"]


@pytest.mark.parametrize("state", ["missing", "pass", "open"])
def test_rows_that_are_not_waiting_carry_none(state) -> None:
    row, _ = _derive([parse_brief_record(_rec(at=_at(10, 15), state=state, reason="理由"))], bars=BARS)
    assert (row["reopen"], row["reopen_missing"], row["wake_by"]) == (None, None, None)
    assert NO_REOPEN_REASON not in row["rewrite"]


# ---- ④ 判斷鍵、滯留、正文 ----

def test_adding_a_condition_is_a_new_judgment_but_not_a_new_stall_or_body() -> None:
    records = _with_reopen(REOPEN)
    current = records[-1]
    assert judgment_version(records, current).brief_id == current.brief_id          # 加上重開條件＝改判
    assert stall_version(records, current).brief_id == records[0].brief_id         # 同一筆等待，滯留不歸零
    assert body_version(records, current).brief_id == records[1].brief_id         # 正文自 10-15 沒改


def test_a_restating_version_cannot_change_the_condition() -> None:
    """重開條件進判斷鍵：改它就是改判，不能宣告 restates 包裝成只改字面值（L12）；條件相同的重述照過。"""
    from alpha.narrative import RECORD_VERSION_V2, brief_record
    from alpha.providers.briefs import restates_problems
    from test_priced_since import READ, _slots

    def build(at, *, reopen, supersedes=None, restates=None):
        return parse_brief_record(brief_record(
            company_id=CO, ticker="AXTI", slots=_slots(), record_version=RECORD_VERSION_V2,
            rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}],
            answers={"priced_in": "yes", "in_numbers": "yes"},
            candidate_state={"state": "priced_wait", "watch_id": "ew_wait", "reason": "寫入時第 88 百分位", "reopen": reopen},
            supersedes_id=supersedes, restates=restates, created_at=at))

    a = build(_at(10, 15), reopen=REOPEN)
    same = build(_at(10, 20), reopen=REOPEN, supersedes=a.brief_id, restates=a.brief_id)
    moved = build(_at(10, 20), reopen={**REOPEN, "price_at_or_below": 60.0}, supersedes=a.brief_id, restates=a.brief_id)
    assert restates_problems(same, [a]) == []
    assert any("候選狀態" in p for p in restates_problems(moved, [a]))


# ---- ⑤ 心跳 ----

def test_the_status_block_counts_and_never_turns_not_computed_into_zero() -> None:
    from crons import heartbeat as hb

    base = {"open": 0, "missing": 0, "priced_wait": 3, "pass": 0, "held": 0, "oldest": {}, "pulled_back": 0,
            "priced_only": 0, "priced_only_unknown": 0}
    text = hb.candidate_states_text({**base, "reopen_met": 1, "no_reopen": 2, "reopen_unknown": 0,
                                     "reopen_not_computed": 0})
    assert "重開達成 1｜沒寫重開 2" in text
    assert "重開達成 未算" in hb.candidate_states_text(base)                        # 舊計數沒有這幾格
    assert "重開達成 未算" in hb.candidate_states_text({**base, "reopen_met": 0, "reopen_not_computed": 3})


def test_the_short_block_marks_each_row_without_action_words(tmp_path, monkeypatch) -> None:
    from crons import heartbeat as hb

    monkeypatch.setattr(hb, "_load_state", lambda state_dir, kind: (__import__("json").loads(
        (state_dir / "candidates.json").read_text(encoding="utf-8")), None))
    monkeypatch.setattr(ew, "load_watches", lambda: {"watches": []})
    waiting, _ = _derive(_chain_with({"text": "回到 70 以下", "price_at_or_below": 70.0}), bars=BARS)
    met, _ = _derive(_chain_with({"text": "回到 80 以下", "price_at_or_below": 80.0}), bars=BARS)
    short = hb.priced_wait_short_lines(_artifact(tmp_path / "a", [waiting]), today=TODAY)
    assert "｜重開：收盤 ≤ 70（今 77.85，差 −10.1%）" in short[1] and "已回落" not in short[1]
    assert "重開＝敘事寫的「到哪裡就重開」" in short[-1]
    short = hb.priced_wait_short_lines(_artifact(tmp_path / "b", [met]), today=TODAY)
    assert "｜**重開條件達成**" in short[1]
    for word in ("該", "燈", "買", "賣"):
        assert word not in "\n".join(short)


# ---- ⑥ 待做清單 ----

def test_both_new_kinds_reach_the_narrative_rewrite_counter() -> None:
    """INV-4：叫醒要指得出 consumer——候選板清單的兩種新種類，⑤「敘事該重寫」計數並點名（drain 照名字去改）。"""
    from test_todo_ledger import _board, _collect

    met = {"kind": "reopen_met", "ticker": "A", "company_id": "co:a", "brief_id": "ib_1", "condition": "重開條件達成：收盤 ≤ 70，重問已定價"}
    missing = {"kind": "no_reopen", "ticker": "B", "company_id": "co:b", "brief_id": "ib_2"}
    row = _collect(candidates=_board(met, missing))["todo.narrative"]
    assert row.count == 2 and "重開達成 1（A）" in row.work and "沒寫重開 1（B）" in row.work
    assert reopen_status(None, None) is None                                         # 沒寫＝None，不是空條件
