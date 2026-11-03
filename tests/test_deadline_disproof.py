"""逾期型反證（盲點修法 plan 2026-11-02-001 §7 第 10 條②，2026-11-03；審查 strategy-4：事件型反證要等一份新文件才醒，
輸家常常什麼都不發）。

守的事：
①契約：`NarrativeDisproof.deadline` 只是宣告——沒寫＝false、只收 true／false（字串、數字、null 都拒收）；as_dict 只在 true 時寫，
  舊紀錄的 brief_id 一位不動；
②候選板：每列帶這一版敘事的逾期型反證條數（沒有 v2 敘事＝None）；`counts.no_deadline`＝可開與已持有裡一條都沒有的檔數
  （持股讀不到＝None，不是 0）；
③心跳段 2 與短版 ④ 每天印一行（0 也印；舊板＝未算、讀不到照說）；
④`alpha brief --add` 宣告可開（或候選板上是已持有）而一條都沒有時印一行提醒——只印、不擋。
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from alpha.candidates import assemble_board, deadline_line, no_deadline_rows
from alpha.errors import ContractViolation
from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record
from alpha.narrative.contracts import new_brief_id
from alpha.providers.candidates import deadline_reminder, derive_row

from test_open_two_gates import CO, DISPROOF, EDGE, HELD_NONE, READ, T, TODAY, _rows, _slots, _tq

DEADLINE = {**DISPROOF, "condition": "若 2027-02-28 前客戶仍未具名第二供應來源以外的量產訂單，量的賭注不成立",
            "deadline": True}


def _record(disproof=(DISPROOF,), *, state="open", watch_id=None, reason=None) -> dict:
    return brief_record(company_id=CO, ticker=T, slots=_slots(), record_version=RECORD_VERSION_V2,
                        rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}], disproof=list(disproof),
                        answers={"priced_in": "yes", "in_numbers": "yes"},
                        candidate_state={"state": state, "watch_id": watch_id, "reason": reason},
                        created_at=datetime(2026, 11, 2, 3, tzinfo=timezone.utc))


# ---------------------------------------------------------------------------
# ① 契約
# ---------------------------------------------------------------------------

def test_deadline_is_written_only_when_true_and_old_ids_do_not_move() -> None:
    plain = _record()
    assert "deadline" not in plain["disproof"][0]                              # 沒寫＝false，不進 payload
    assert plain["brief_id"] == new_brief_id({k: v for k, v in plain.items() if k != "brief_id"})
    flagged = _record([DEADLINE])
    assert flagged["disproof"][0]["deadline"] is True
    assert parse_brief_record(flagged).disproof[0].deadline is True
    assert parse_brief_record(plain).disproof[0].deadline is False
    explicit_false = _record([{**DISPROOF, "deadline": False}])
    assert explicit_false["brief_id"] == plain["brief_id"]                     # 寫 false 與不寫同一份


@pytest.mark.parametrize("value", ["true", 1, None, "yes"])
def test_deadline_takes_only_true_or_false(value) -> None:
    with pytest.raises(ContractViolation, match="deadline"):
        _record([{**DISPROOF, "deadline": value}])


# ---------------------------------------------------------------------------
# ② 候選板
# ---------------------------------------------------------------------------

HELD = {"status": "ok", "by_company": {CO: {"symbols": ["AXTI"]}}, "unresolved": [], "beta_excluded": 0, "zero_shares": 0}


def _row(record, *, held=HELD_NONE):
    return derive_row(T, CO, records=[parse_brief_record(record)], today=TODAY, reading_rows=_rows(), watches=[],
                      lifecycle={}, edge=EDGE, three_questions=_tq(), held=held)


def test_each_row_carries_its_deadline_count_and_the_board_counts_open_and_held_without_one() -> None:
    plain, flagged = _row(_record()), _row(_record([DISPROOF, DEADLINE]))
    assert plain["deadline_disproof"] == 0 and flagged["deadline_disproof"] == 1
    held_plain = _row(_record(state="pass", reason="非倍率持股"), held=HELD)
    assert held_plain["group"] == "held" and held_plain["deadline_disproof"] == 0
    no_narrative = derive_row(T, CO, records=[], today=TODAY, reading_rows=_rows(), watches=[], lifecycle={},
                              edge=EDGE, three_questions=_tq(), held=HELD)
    assert no_narrative["deadline_disproof"] is None                            # 沒有敘事不是「0 條」
    missing = dict(plain, group="missing", ticker="MMM")
    groups = {"open": [dict(plain, ticker="AAA"), dict(flagged, ticker="BBB")],
              "held": [dict(held_plain, ticker="CCC"), dict(no_narrative, ticker="DDD")], "missing": [missing]}
    assert [r["ticker"] for r in no_deadline_rows(groups)] == ["AAA", "CCC"]    # 缺 X 不數；沒有敘事另算


def test_the_count_is_none_when_holdings_were_not_read() -> None:
    row = dict(_row(_record()), ticker="AAA")
    ok = assemble_board([row], universe=["AAA"], held=HELD_NONE, narrative_rewrite=[])
    assert ok["counts"]["no_deadline"] == 1
    unread = assemble_board([row], universe=["AAA"], held={"status": "unavailable", "reason": "Sheet 讀不到"},
                            narrative_rewrite=[])
    assert unread["counts"]["no_deadline"] is None


# ---------------------------------------------------------------------------
# ③ 狀態行
# ---------------------------------------------------------------------------

def test_the_status_line_prints_zero_unread_and_old_boards_honestly() -> None:
    row = dict(_row(_record()), ticker="AAA")
    board = assemble_board([row], universe=["AAA"], held=HELD_NONE, narrative_rewrite=[])
    assert deadline_line(board) == "逾期型反證 0 條的持有／可開敘事 1：AAA"
    none = assemble_board([dict(_row(_record([DEADLINE])), ticker="AAA")], universe=["AAA"], held=HELD_NONE,
                          narrative_rewrite=[])
    assert deadline_line(none) == "逾期型反證 0 條的持有／可開敘事 0"
    unread = assemble_board([row], universe=["AAA"], held={"status": "unavailable"}, narrative_rewrite=[])
    assert "持股沒讀到" in deadline_line(unread)
    old = {"counts": {"open": 1}, "groups": {"open": [{"ticker": "AAA"}]}, "holdings": {"status": "ok"}}
    assert "未算" in deadline_line(old)


def test_the_heartbeat_and_the_short_brief_both_print_the_line(monkeypatch, tmp_path) -> None:
    """產出要到消費者手上（L13）：心跳段 2 與短版 ④ 都印同一句（整句由候選板給，L16）。"""
    from crons import daily_brief
    from crons import heartbeat as hb

    board = assemble_board([dict(_row(_record()), ticker="AAA")], universe=["AAA"], held=HELD_NONE, narrative_rewrite=[])
    monkeypatch.setattr(hb, "_load_state", lambda state_dir, kind: (board, None))
    assert "逾期型反證 0 條的持有／可開敘事 1：AAA" in hb._candidate_lines(tmp_path)
    assert "- 逾期型反證 0 條的持有／可開敘事 1：AAA" in daily_brief.candidate_short_lines(tmp_path)


# ---------------------------------------------------------------------------
# ④ 寫入時的提醒
# ---------------------------------------------------------------------------

def test_the_writer_reminds_open_or_held_narratives_without_one_and_never_blocks() -> None:
    assert deadline_reminder(_record(), held=False) is not None                 # 宣告可開、沒有
    assert deadline_reminder(_record([DEADLINE]), held=False) is None
    assert deadline_reminder(_record(state="pass", reason="非倍率"), held=True) is not None   # 候選板上已持有
    assert deadline_reminder(_record(state="pass", reason="非倍率"), held=False) is None
    assert deadline_reminder(_record(state="pass", reason="非倍率"), held=None) is None      # 候選板讀不到：每天的計數器會點名
