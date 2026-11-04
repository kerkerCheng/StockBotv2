"""持股或可開名下的反證工作算進展格（2026-11-04 整體盲點審查複查）。

事發：盲點修法 §1 第 2 條（11-03）讓「下一步貼」只在進展格非 0 或最老 ≥ 7 天才推 `/research-drain`，但醒來待判的反證算在
「未檢」——不是進展格。11-03 起 3081.TWO、4979.TWO、AXTI 被醒來待判的反證卡在起始門外（前提失效），離可開只差一次判定，
提示卻寫「只剩維護」；持股的反證醒了，最慢要等 7 天的「最老一筆」規則才叫人，「出場認反證、48 小時」實際變成 7 天。

修法：候選板在算起始門的同一個地方，把卡著這一列的 watch id 存下來（`blocking_watch_ids`；判定只住
`engine_b.narrative_watches.blocking_watches`，持股列也算）；⑤ 的未檢、叫醒擋下、到期沒人處置、敘事該重寫四格，只把卡著
持股或可開（含前提失效）的那幾條算成進展。其餘列（缺 X、不要）的反證照舊只看年紀——全算進來就回到恆亮（L14-4）。
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from alpha.candidates import assemble_board
from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record
from alpha.providers.candidates import derive_row
from engine_b import event_watch as ew
from engine_b import todo_ledger as tl
from engine_b.narrative_watches import blocking_for_open, blocking_watches

TODAY = date(2026, 11, 4)
CO, T = "co:axt", "AXTI"
READ = "sr_" + "a" * 16
EDGE = {"state": "edge", "label": "邊緣", "reasons": ["within_edge"], "market_cap_usd": 4.8e9, "analyst_count": 5}
NOT_HELD = {"status": "ok", "by_company": {}, "unresolved": [], "beta_excluded": 0, "zero_shares": 0}
HELD = {"status": "ok", "by_company": {CO: {"symbols": [T]}}, "unresolved": [], "beta_excluded": 0, "zero_shares": 0}
DISPROOF = {"condition": "若 JX 在 2026-12-31 前宣布新產能投產則供給缺口消失，量的賭注不成立", "check_frequency": "每季",
            "action_48h": "重寫", "entities": [CO], "expires": "2027-03-01", "source": "self", "link_source_ref": None}


def _slots() -> dict:
    ev = ["graph://x"]
    return {"demand": {"text": "客戶預付產能。", "evidence_refs": ev},
            "position": {"text": "坐在基板層，年增 {in_numbers_latest}（{in_numbers_as_of}）。", "evidence_refs": ev},
            "bottleneck": {"text": "三家供應。", "evidence_refs": ev},
            "priced_in": {"text": "自家三年 {own_history_basis} 第 {own_history_pctile} 百分位。", "evidence_refs": ev},
            "our_bet": {"text": "賭層的量。", "evidence_refs": ev},
            "what_must_be_true": {"text": "擴產沒提前。", "evidence_refs": ev},
            "when": {"text": "{next_checkpoint_date} 財報。", "evidence_refs": ev}}


def _brief(state: str = "open", *, watch_id: str | None = None):
    return parse_brief_record(brief_record(
        company_id=CO, ticker=T, slots=_slots(), record_version=RECORD_VERSION_V2,
        rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}], disproof=[DISPROOF],
        answers={"priced_in": "yes", "in_numbers": "yes"},
        candidate_state={"state": state, "watch_id": watch_id,
                         "reason": {"missing": "缺客戶具名", "pass": "非倍率持股"}.get(state)},
        created_at=datetime(2026, 11, 2, 3, tzinfo=timezone.utc)))


def _tq() -> dict:
    keys = ("wipeout_cash_runway", "wipeout_debt", "wipeout_dilution", "wipeout_going_concern")
    return {"priced_in": [{"key": "own_history_pctile", "value": 88.0, "absence_kind": None}],
            "in_numbers": [{"key": "in_numbers_series", "value": 1.0, "absence_kind": None}],
            "will_it_die": [{"key": k, "value": v, "absence_kind": None if v else "not_yet_recorded"}
                            for k, v in zip(keys, ("amber", "green", "amber", None))]}


def _reading_watch(wid: str = "ew_9001", *, status: str = "fired", **extra) -> dict:
    """持股或候選押的那一層讀圖的反證（來源 `reading:<id>#n`）——醒來待判時歸「未檢」。"""
    return {"watch_id": wid, "kind": ew.SEMANTIC_KIND, "status": status, "source_ref": f"reading:{READ}#1",
            "disproof_ref": f"reading:{READ}#1", "condition": "第二供應商量產", "fired_at": "2026-11-03T01:00:00+00:00",
            **extra}


def _derive(records, *, held=NOT_HELD, watches=()):
    rows = {("tech:x", "layer"): {"node": "tech:x", "unit": "layer", "reading_id": READ, "status": "current",
                                  "kind": "volume"}}
    return derive_row(T, CO, records=records, today=TODAY, reading_rows=rows, watches=list(watches), lifecycle={},
                      edge=EDGE, three_questions=_tq(), held=held)


# ---------------------------------------------------------------------------
# 判定只有一份：起始門的理由與列上的 id 出自同一個函式
# ---------------------------------------------------------------------------

def test_blocking_watches_is_the_single_judgment_behind_the_start_gate_reasons() -> None:
    brief = _brief()
    watches = [_reading_watch(), _reading_watch("ew_9002", status="active")]
    kw = dict(watches=watches, lifecycle={}, brief_ids=[brief.brief_id], current_brief=brief)
    pairs = blocking_watches(CO, T, **kw)
    assert [wid for wid, _ in pairs] == ["ew_9001"]                      # 還在等的不擋
    assert blocking_for_open(CO, T, **kw) == [reason for _, reason in pairs]
    # lifecycle 讀不到：fail closed 那一條沒有 watch id——擋得住起始門，但不會被當成某一條 watch 的工作
    blind = blocking_watches(CO, T, **{**kw, "lifecycle": None})
    assert blind[0][0] is None and "fail closed" in blind[0][1]


def test_the_board_row_carries_what_blocks_it_only_for_held_and_open_rows() -> None:
    blocked = _derive([_brief()], watches=[_reading_watch()])
    assert blocked["side"] == "precondition_failed" and blocked["blocking_watch_ids"] == ["ew_9001"]
    clean = _derive([_brief()])
    assert clean["group"] == "open" and clean["blocking_watch_ids"] == []
    held = _derive([_brief(state="pass")], held=HELD, watches=[_reading_watch()])
    assert held["group"] == "held" and held["blocking_watch_ids"] == ["ew_9001"]    # 持股不走起始門，反證照樣算
    no_narrative = derive_row(T, CO, records=[], today=TODAY, reading_rows={}, watches=[_reading_watch()],
                              lifecycle={}, edge=EDGE, three_questions=_tq(), held=HELD)
    assert no_narrative["group"] == "held" and no_narrative["blocking_watch_ids"] == []   # 沒押讀圖：歸屬不到
    waiting = _derive([_brief(state="missing", watch_id="ew_1")], watches=[_reading_watch()])
    assert waiting["group"] == "missing" and waiting["blocking_watch_ids"] is None        # 缺 X 不算（不是 0）


# ---------------------------------------------------------------------------
# ⑤：只把卡著持股或可開的那幾條算成進展
# ---------------------------------------------------------------------------

def _board(*, held=(), open_=(), failed=(), holdings="ok") -> dict:
    return {"counts": {}, "groups": {"held": list(held), "open": list(open_), "missing": [], "pass": []},
            "side_groups": {"precondition_failed": list(failed)}, "holdings": {"status": holdings},
            "narrative_rewrite": [], "new_edges_check": {"status": "ok"},
            "reading_change_check": {"status": "ok", "unchecked": 0}}


def _collect(*, watches, candidates) -> dict:
    loaders = {"classification_gaps": lambda: [], "undisposed": lambda: [], "parked_without_expiry": lambda: [],
               "stale_lead_entities": lambda: 0, "story_gaps": lambda: [],
               "admission_audit_ledger": lambda: ([], [])}
    rows = tl.collect(today=TODAY, leads_store={"leads": {}}, watches=watches, todo_items=[], hypotheses=[],
                      briefs=[], reading_needs_reread=0, layer_note_reread=0, candidates=candidates, thesis_due=[],
                      loaders=loaders)
    return {row.key: row for row in rows}


def _row(ticker: str, ids, rewrite=()) -> dict:
    return {"ticker": ticker, "company_id": f"co:{ticker.lower()}", "blocking_watch_ids": list(ids),
            "rewrite_watch_ids": list(rewrite), "addon_unchecked": []}


def test_a_woken_disproof_on_a_held_or_blocked_row_is_progress_and_one_elsewhere_is_not() -> None:
    held_watch, failed_watch, missing_watch = (_reading_watch("ew_1"), _reading_watch("ew_2"),
                                               _reading_watch("ew_3"))
    board = _board(held=[_row("SIVE", ["ew_1"])], failed=[_row("AXTI", ["ew_2"])])
    rows = _collect(watches=[held_watch, failed_watch, missing_watch], candidates=board)
    semantic = rows["todo.semantic"]
    assert semantic.count == 3 and semantic.progress == 2          # 缺 X 那一檔（ew_3）的反證照舊只看年紀
    ledger = list(rows.values())
    assert tl.next_prompt(ledger).startswith("`/research-drain`（進展：持股或可開名下的反證醒來待判 2）")
    # 同一批 watch，沒有任何一條卡著持股或可開：只剩維護（最老不到 7 天）
    quiet = _collect(watches=[missing_watch], candidates=_board(held=[_row("SIVE", [])]))
    assert quiet["todo.semantic"].progress == 0 and tl.next_prompt(list(quiet.values())).startswith("只剩維護")


def test_expired_and_held_back_watches_follow_the_same_rule() -> None:
    expired = _reading_watch("ew_4", status="expired")
    stray = _reading_watch("ew_5", status="expired")
    settled = _reading_watch("ew_6", status="expired", expiry_resolution={"kind": "reread", "at": "2026-11-03"})
    rows = _collect(watches=[expired, stray, settled],
                    candidates=_board(open_=[_row("AXTI", [])], failed=[_row("4979", ["ew_4", "ew_6"])]))
    # 已處置的到期（有 expiry_resolution）不是工作——就算列上還帶著它的 id 也不算
    assert rows["todo.expired"].count == 2 and rows["todo.expired"].progress == 1


def test_a_held_back_wake_on_a_held_row_is_progress_too() -> None:
    """叫醒擋下（#96：抓得到全文、還沒預篩）也照同一條規則：卡著持股或可開的才算進展。"""
    kind = next(iter(sorted(ew.SCREENED_WAKE_KINDS)))
    held_back = {"watch_id": "ew_10", "kind": kind, "status": "fired", "wake_reading": "tech:x",
                 "source_ref": f"reading:{READ}#1", "woken_by": {"lead_id": "lead_1", "screen": "fetched"},
                 "fired_at": "2026-11-03T01:00:00+00:00"}
    other = dict(held_back, watch_id="ew_11")
    assert ew.wake_screen(held_back) in ew.WAKE_HELD_STATES
    rows = _collect(watches=[held_back, other], candidates=_board(held=[_row("SIVE", ["ew_10"])]))
    assert rows["todo.wake_hold"].count == 2 and rows["todo.wake_hold"].progress == 1


def test_a_narrative_disproof_counts_once_per_row_not_maintenance_lag() -> None:
    board = _board(held=[_row("SIVE", ["ew_6"], rewrite=["ew_6"])],
                   failed=[_row("AXTI", ["ew_7"], rewrite=["ew_8"])])         # AXTI 卡著的是語意反證，不是敘事來源
    rows = _collect(watches=[], candidates=board)
    assert rows["todo.narrative"].progress == 1


def test_unreadable_holdings_or_an_old_board_is_none_not_zero() -> None:
    watch = _reading_watch("ew_1")
    for board in (None, _board(held=[_row("SIVE", ["ew_1"])], holdings="unreadable"),
                  _board(held=[{"ticker": "SIVE", "company_id": "co:sive"}])):       # 舊板：列上沒有那一格
        rows = _collect(watches=[watch], candidates=board)
        assert rows["todo.semantic"].progress is None and rows["todo.expired"].progress is None
        assert tl.next_prompt(list(rows.values())).startswith("`/research-drain`（進展格算不出，照舊推）")


def test_end_to_end_the_board_the_ledger_and_the_prompt_agree() -> None:
    """真的走一次 derive_row → assemble_board → collect：列上的欄位名與 ⑤ 讀的是同一個（改名就紅）。"""
    watch = _reading_watch()
    blocked = _derive([_brief()], watches=[watch])
    board = assemble_board([blocked], universe=[T], held=NOT_HELD, narrative_rewrite=[])
    board.update(new_edges_check={"status": "ok"}, reading_change_check={"status": "ok", "unchecked": 0})
    assert board["side_groups"]["precondition_failed"][0]["blocking_watch_ids"] == ["ew_9001"]
    rows = _collect(watches=[watch], candidates=board)
    assert rows["todo.semantic"].progress == 1
    assert "持股或可開名下的反證醒來待判 1" in tl.next_prompt(list(rows.values()))


def test_the_progress_cells_are_exactly_these() -> None:
    assert set(tl.PROGRESS_LABELS) == {"todo.disproof_touched", "todo.confirm_touched", "todo.addon_unchecked",
                                       "todo.leads", "todo.semantic", "todo.wake_hold", "todo.expired",
                                       "todo.narrative", "todo.old_gate_missing"}
    assert tl.DECISION_ROWS == (("groups", "held"), ("groups", "open"), ("side_groups", "precondition_failed"))
    assert set(tl.PROGRESS_LABELS) <= set(tl.LEDGER_KEYS)


def test_snapshot_keeps_the_new_progress_so_session_start_makes_the_same_call() -> None:
    rows = _collect(watches=[_reading_watch("ew_1")], candidates=_board(held=[_row("SIVE", ["ew_1"])]))
    ledger = list(rows.values())
    snap = {**{r.key: r.count for r in ledger}, **tl.snapshot_progress(ledger)}
    assert snap["todo.progress"] == 1
    assert tl.next_prompt(snap).startswith("`/research-drain`（進展 1 件）")

