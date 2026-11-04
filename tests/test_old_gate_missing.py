"""舊門寫的缺 X 重判一次（2026-11-04 整體盲點審查複查）。

起始門 2026-11-03 改了（讀到邊與十項深挖搬去加碼門、已定價改成脈絡），但候選板上的缺 X 都是舊門下寫的——它們只在各自的
watch 醒來或到期才重寫，Q3 財報季剛重寫的那幾份等的是 2027 的年報。決定紀錄 §10.1 選了 (a)「門設計太嚴」；不把舊的缺 X 在
新門下重判一次，這個答案到 12-22 都驗不出來。⑤ 多一格「缺 X 還是舊門寫的」：一次性的母體，研究 session 逐檔重判，清完恆為 0。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from alpha.candidates import START_GATE_SINCE, assemble_board
from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record
from alpha.providers.candidates import derive_row
from engine_b import todo_ledger as tl

TODAY = date(2026, 11, 4)
CO, T = "co:axt", "AXTI"
READ, READ2 = "sr_" + "a" * 16, "sr_" + "b" * 16
EDGE = {"state": "edge", "label": "邊緣", "reasons": ["within_edge"], "market_cap_usd": 4.8e9, "analyst_count": 5}
NOT_HELD = {"status": "ok", "by_company": {}, "unresolved": [], "beta_excluded": 0, "zero_shares": 0}
DISPROOF = {"condition": "若 JX 在 2026-12-31 前宣布新產能投產則供給缺口消失，量的賭注不成立", "check_frequency": "每季",
            "action_48h": "重寫", "entities": [CO], "expires": "2027-03-01", "source": "self", "link_source_ref": None}
BEFORE = START_GATE_SINCE - timedelta(hours=2)
AFTER = START_GATE_SINCE + timedelta(hours=2)


def _slots() -> dict:
    ev = ["graph://x"]
    return {"demand": {"text": "客戶預付產能。", "evidence_refs": ev},
            "position": {"text": "坐在基板層，年增 {in_numbers_latest}（{in_numbers_as_of}）。", "evidence_refs": ev},
            "bottleneck": {"text": "三家供應。", "evidence_refs": ev},
            "priced_in": {"text": "自家三年 {own_history_basis} 第 {own_history_pctile} 百分位。", "evidence_refs": ev},
            "our_bet": {"text": "賭層的量。", "evidence_refs": ev},
            "what_must_be_true": {"text": "擴產沒提前。", "evidence_refs": ev},
            "when": {"text": "{next_checkpoint_date} 財報。", "evidence_refs": ev}}


def _record(*, at: datetime, state: str = "missing", reason: str = "缺客戶具名", read: str = READ,
            supersedes: str | None = None) -> dict:
    return brief_record(company_id=CO, ticker=T, slots=_slots(), record_version=RECORD_VERSION_V2,
                        rides=[{"node": "tech:x", "unit": "layer", "reading_id": read}], disproof=[DISPROOF],
                        answers={"priced_in": "yes", "in_numbers": "yes"},
                        candidate_state={"state": state, "watch_id": "ew_1" if state == "missing" else None,
                                         "reason": reason if state in ("missing", "pass") else None},
                        supersedes_id=supersedes, created_at=at)


def _derive(records) -> dict:
    rows = {("tech:x", "layer"): {"node": "tech:x", "unit": "layer", "reading_id": READ2, "status": "current",
                                  "kind": "volume"}}
    tq = {"priced_in": [{"key": "own_history_pctile", "value": 88.0, "absence_kind": None}],
          "in_numbers": [{"key": "in_numbers_series", "value": 1.0, "absence_kind": None}],
          "will_it_die": [{"key": "wipeout_debt", "value": "green", "absence_kind": None}]}
    return derive_row(T, CO, records=[parse_brief_record(r) for r in records], today=TODAY, reading_rows=rows,
                      watches=[], lifecycle={}, edge=EDGE, three_questions=tq, held=NOT_HELD)


def test_a_missing_x_written_before_the_writer_changed_gates_is_flagged() -> None:
    old = _record(at=BEFORE)
    assert _derive([old])["declared_before_start_gate"] is True
    assert _derive([_record(at=AFTER)])["declared_before_start_gate"] is False


def test_a_re_ride_after_the_change_does_not_count_as_a_re_judgment_but_a_new_reason_does() -> None:
    old = _record(at=BEFORE)
    old_id = parse_brief_record(old).brief_id
    re_ride = _record(at=AFTER, read=READ2, supersedes=old_id)                     # 只換騎：正文一字不改
    assert _derive([old, re_ride])["declared_before_start_gate"] is True
    re_judged = _record(at=AFTER, read=READ2, supersedes=old_id,
                        reason="缺起始門：押的層判讀是 neither，換騎到現行讀圖後才能判")
    assert _derive([old, re_judged])["declared_before_start_gate"] is False


def test_only_missing_rows_carry_the_flag() -> None:
    assert _derive([_record(at=BEFORE, state="pass", reason="x")])["declared_before_start_gate"] is None


def _collect(candidates) -> dict:
    loaders = {"classification_gaps": lambda: [], "undisposed": lambda: [], "parked_without_expiry": lambda: [],
               "stale_lead_entities": lambda: 0, "story_gaps": lambda: [], "admission_audit_ledger": lambda: ([], [])}
    rows = tl.collect(today=TODAY, leads_store={"leads": {}}, watches=[], todo_items=[], hypotheses=[], briefs=[],
                      reading_needs_reread=0, layer_note_reread=0, candidates=candidates, thesis_due=[],
                      loaders=loaders)
    return {row.key: row for row in rows}


def _board(*missing) -> dict:
    return {"counts": {}, "groups": {"open": [], "missing": list(missing), "pass": [], "held": []},
            "side_groups": {"precondition_failed": []}, "holdings": {"status": "ok"}, "narrative_rewrite": [],
            "new_edges_check": {"status": "ok"}, "reading_change_check": {"status": "ok", "unchecked": 0}}


def test_the_cell_counts_old_gate_rows_names_them_and_pushes_a_drain() -> None:
    rows = _collect(_board({"ticker": "3081.TWO", "declared_before_start_gate": True, "stall_days": 12},
                           {"ticker": "1802.TW", "declared_before_start_gate": False, "stall_days": 3},
                           {"ticker": "AXTI", "declared_before_start_gate": True, "stall_days": 20}))
    cell = rows["todo.old_gate_missing"]
    assert (cell.count, cell.progress, cell.oldest_days) == (2, 2, 20) and cell.work == "3081.TWO、AXTI"
    assert "進展：缺 X 還是舊門寫的 2" in tl.next_prompt(list(rows.values()))


def test_an_old_board_or_no_board_is_unread_not_zero() -> None:
    for board in (None, _board({"ticker": "3081.TWO"})):
        cell = _collect(board)["todo.old_gate_missing"]
        assert cell.count is None and cell.progress is None and cell.reason


def test_end_to_end_through_the_board() -> None:
    row = _derive([_record(at=BEFORE)])
    board = assemble_board([row], universe=[T], held=NOT_HELD, narrative_rewrite=[])
    board.update(new_edges_check={"status": "ok"}, reading_change_check={"status": "ok", "unchecked": 0})
    assert _collect(board)["todo.old_gate_missing"].count == 1


def test_the_boundary_is_the_writer_commit_not_the_display_midnight() -> None:
    from alpha.candidates import RETIRED_READ_SINCE

    assert START_GATE_SINCE == datetime(2026, 11, 3, 15, 33, 32, tzinfo=timezone.utc)
    assert START_GATE_SINCE > RETIRED_READ_SINCE          # 寧可多重判一份：11-03 白天在舊門下寫的也算
