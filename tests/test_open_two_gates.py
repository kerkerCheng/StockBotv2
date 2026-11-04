"""可開分起始與加碼兩道門（盲點修法 plan 2026-11-02-001 第 18＋16 條，2026-11-03；AGENTS「讀到邊是加碼的門、不是起始的門」、
「候選狀態是封閉字彙：可開／缺 X／不要／已持有」；決定紀錄 §10.1 條 2 作答 (a)）。

守的事：
①封閉字彙少一格：新寫的「已定價等回落」寫入端拒收；舊紀錄照讀（append-only、brief_id 不變）、一律**讀成可開**，走同一道起始門；
②起始門：會死嗎不是紅（四盞燈都讀不到＝fail closed）、押的那一層讀過且判讀不是 neither（undecided 可以）、反證已寫下且有到期、
  已定價寫成一句脈絡（v2 契約本來就要）——寫入端與候選板每天重驗同一套；
③深挖清單存進敘事（`depth_check`）：引用／不適用／加碼條件：c<n>／缺；沒寫不進 payload（舊紀錄 id 不變）；c<n> 要指得到這一版的
  confirm[]；一手節錄要指得回；
④⑤「加碼條件還沒查」：只數可開與已持有、還有沒查的項目的檔（已持有沒有 v2 敘事＝十項都還沒查）；進展格；
⑤短版 ③「可開待你選」：只列**這一版敘事**還沒選過的（看了沒買記過就不再列，敘事換版再問）；摘要行「球在你」旁邊印它；
  完整心跳段 3 也印一行（0 也印、讀不到照說）。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from alpha.candidates import GROUPS, GROUP_LABELS, addon_unchecked_rows, assemble_board, stall_version
from alpha.errors import ContractViolation
from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record
from alpha.narrative.contracts import CANDIDATE_STATES_DECLARABLE, CandidateState, new_brief_id
from alpha.narrative.depth_check import DEPTH_CHECK_KEYS, addon_index, depth_check_lines, unchecked_items
from alpha.providers.briefs import WriteContext, write_brief
from alpha.providers.candidates import derive_row
from engine_b import event_watch as ew

TODAY = date(2026, 11, 3)
CO, T = "co:axt", "AXTI"
READ = "sr_" + "a" * 16
EDGE = {"state": "edge", "label": "邊緣", "reasons": ["within_edge"], "market_cap_usd": 4.8e9, "analyst_count": 5}
HELD_NONE = {"status": "ok", "by_company": {}, "unresolved": [], "beta_excluded": 0, "zero_shares": 0}
DISPROOF = {"condition": "若 JX 在 2026-12-31 前宣布新產能投產則供給缺口消失，量的賭注不成立", "check_frequency": "每季",
            "action_48h": "重寫", "entities": [CO], "expires": "2027-03-01", "source": "self", "link_source_ref": None}
CONFIRM = {"condition": "客戶自己的一手文件具名 AXT 供貨 InP 基板並走到量產", "check_frequency": "每季",
           "action_48h": "重寫敘事：寫明確認了什麼", "entities": [CO], "expires": "2027-06-30", "source": "self"}
ALL_CHECKED = {key: "sr_" + "c" * 16 for key in DEPTH_CHECK_KEYS}


def _slots() -> dict:
    ev = ["graph://x"]
    return {"demand": {"text": "客戶預付產能。", "evidence_refs": ev},
            "position": {"text": "坐在基板層，年增 {in_numbers_latest}（{in_numbers_as_of}）。", "evidence_refs": ev},
            "bottleneck": {"text": "三家供應。", "evidence_refs": ev},
            "priced_in": {"text": "自家三年 {own_history_basis} 第 {own_history_pctile} 百分位。", "evidence_refs": ev},
            "our_bet": {"text": "賭層的量。", "evidence_refs": ev},
            "what_must_be_true": {"text": "擴產沒提前。", "evidence_refs": ev},
            "when": {"text": "{next_checkpoint_date} 財報。", "evidence_refs": ev}}


def _record(*, state="open", watch_id=None, reason=None, at=None, disproof=(DISPROOF,), confirm=(), depth_check=None,
            supersedes=None, reopen=None, rides=None) -> dict:
    return brief_record(company_id=CO, ticker=T, slots=_slots(), record_version=RECORD_VERSION_V2,
                        rides=([{"node": "tech:x", "unit": "layer", "reading_id": READ}] if rides is None
                               else list(rides)), disproof=list(disproof),
                        answers={"priced_in": "yes", "in_numbers": "yes"},
                        candidate_state={"state": state, "watch_id": watch_id, "reason": reason,
                                         **({"reopen": reopen} if reopen else {})},
                        confirm=list(confirm), depth_check=depth_check, supersedes_id=supersedes,
                        created_at=at or datetime(2026, 11, 2, 3, tzinfo=timezone.utc))


def _brief(**kw):
    return parse_brief_record(_record(**kw))


def _tq(lights=("amber", "green", "amber", None), *, unavailable=False) -> dict:
    keys = ("wipeout_cash_runway", "wipeout_debt", "wipeout_dilution", "wipeout_going_concern")
    die = [{"key": k, "value": None if unavailable else v,
            "absence_kind": "upstream_unavailable" if unavailable else (None if v else "not_yet_recorded")}
           for k, v in zip(keys, lights)]
    return {"priced_in": [{"key": "own_history_pctile", "value": 88.0, "absence_kind": None},
                          {"key": "cohort_median", "value": None, "absence_kind": "upstream_unavailable"}],
            "in_numbers": [{"key": "in_numbers_series", "value": 1.0, "absence_kind": None}],
            "will_it_die": die}


def _rows(kind="volume") -> dict:
    return {("tech:x", "layer"): {"node": "tech:x", "unit": "layer", "reading_id": READ, "status": "current",
                                  "kind": kind}}


def _derive(records, *, kind="volume", tq=None, held=HELD_NONE, watches=()):
    return derive_row(T, CO, records=records, today=TODAY, reading_rows=_rows(kind), watches=list(watches),
                      lifecycle={}, edge=EDGE, three_questions=_tq() if tq is None else tq, held=held)


# ---------------------------------------------------------------------------
# ① 封閉字彙少一格：舊的等回落照讀、讀成可開；新寫的拒收
# ---------------------------------------------------------------------------

def test_the_declarable_states_lose_priced_wait_and_the_board_groups_follow() -> None:
    assert CANDIDATE_STATES_DECLARABLE == ("open", "missing", "pass")
    assert GROUPS == ("open", "missing", "pass", "held") and "priced_wait" not in GROUP_LABELS


def test_an_old_priced_wait_record_parses_with_its_id_and_reads_as_open() -> None:
    """append-only：舊紀錄不回寫——id 照原樣算得回來、重開條件照讀；讀法（effective）是可開。"""
    raw = _record(state="priced_wait", watch_id="ew_wait", reason="寫入時第 88 百分位",
                  reopen={"text": "回到 70 以下就重開", "price_at_or_below": 70.0})
    old = parse_brief_record(raw)
    assert old.brief_id == raw["brief_id"] == new_brief_id(raw)
    assert old.candidate_state.state == "priced_wait" and old.candidate_state.effective == "open"
    assert old.candidate_state.reopen.price_at_or_below == 70.0
    assert CandidateState(state="missing", watch_id="ew_x").effective == "missing"
    with pytest.raises(ContractViolation):
        CandidateState(state="priced_wait")                             # 舊紀錄都帶 watch：形狀照舊驗


def test_an_old_priced_wait_rides_the_same_start_gate_as_open(tmp_path: Path) -> None:
    old = _brief(state="priced_wait", watch_id="ew_wait", reason="已定價")
    row = _derive([old])
    assert (row["group"], row["declared"], row["declared_retired"]) == ("open", "open", "priced_wait")
    assert row["declared_label"] == "可開" and row["preconditions"] == []
    assert row["declared_retired_label"].startswith("已定價等回落")        # 當時寫的字（11-04 R2：畫面印它）
    assert _derive([_brief()])["declared_retired_label"] is None
    failed = _derive([old], kind="neither")
    assert failed["side"] == "precondition_failed" and failed["group"] is None
    for gone in ("pulled_back", "open_gaps", "reopen", "reopen_missing", "wake_by"):
        assert gone not in row                                          # 價格叫醒、重開、只差已定價都退役


def test_an_old_priced_wait_without_a_ridden_reading_fails_closed() -> None:
    """舊等回落可能沒押讀圖（當時的契約只要求可開押）：讀成可開也驗不了押的那一層——不放行（R2 變異 M1 存活，補這一條）。"""
    old = _brief(state="priced_wait", watch_id="ew_wait", reason="已定價", rides=())
    row = _derive([old])
    assert row["side"] == "precondition_failed" and row["group"] is None
    assert any("沒有押任何讀圖" in p for p in row["preconditions"])


def test_writing_priced_wait_is_refused_with_where_it_went(tmp_path: Path) -> None:
    ctx, wid = _ctx()
    with pytest.raises(ContractViolation, match="已併回可開"):
        write_brief(_fresh(state="priced_wait", watch_id=wid, reason="已定價",
                           reopen={"text": "回到 70 以下", "price_at_or_below": 70.0}),
                    ctx=ctx, directory=tmp_path / "b", watches_path=tmp_path / "w.json")


def test_an_old_wait_followed_by_open_keeps_counting_the_stall() -> None:
    """同一段（讀成可開）：版本鏈照連——但天數不把 11-03 前的等回落算成可開（11-04 R2：那時給人看的是等回落；INV-6）。
    變異：stall_since 不看退役字 → 第二、三條紅。"""
    from alpha.candidates import RETIRED_READ_SINCE, stall_since

    a = _record(state="priced_wait", watch_id="ew_1", reason="已定價", at=datetime(2026, 10, 1, 3, tzinfo=timezone.utc))
    b = _record(at=datetime(2026, 11, 2, 3, tzinfo=timezone.utc), supersedes=a["brief_id"])
    records = [parse_brief_record(r) for r in (a, b)]
    assert stall_version(records, records[-1]).brief_id == a["brief_id"]
    assert stall_since(records, records[-1]) == records[-1].created_at       # 11-02 照原字就是可開：從那天算
    only_old = [parse_brief_record(a)]
    assert stall_since(only_old, only_old[0]) == RETIRED_READ_SINCE           # 只有等回落：從讀成可開那一刻算
    row = _derive(only_old)
    assert row["group"] == "open" and row["stall_days"] == 0                  # TODAY＝11-03（上線當天）＝第 0 天
    late = parse_brief_record(_record(state="priced_wait", watch_id="ew_1", reason="已定價",
                                      at=datetime(2026, 11, 3, 1, tzinfo=timezone.utc)))
    assert stall_since([late], late) == late.created_at                       # 上線後才寫的不受影響


# ---------------------------------------------------------------------------
# ② 起始門
# ---------------------------------------------------------------------------

def test_an_undecided_layer_passes_the_start_gate_and_neither_does_not() -> None:
    assert _derive([_brief()], kind="undecided")["group"] == "open"
    row = _derive([_brief()], kind="neither")
    assert row["side"] == "precondition_failed"
    assert any("neither" in p for p in row["preconditions"])


def test_a_red_lamp_fails_the_start_gate_grey_does_not_and_all_unreadable_fails_closed() -> None:
    row = _derive([_brief()], tq=_tq(("red", "green", "green", "green")))
    assert row["side"] == "precondition_failed" and any("會死嗎是紅" in p for p in row["preconditions"])
    assert _derive([_brief()], tq=_tq((None, None, "amber", None)))["group"] == "open"   # 灰燈不是紅
    closed = _derive([_brief()], tq=_tq(unavailable=True))
    assert closed["side"] == "precondition_failed" and any("fail closed" in p for p in closed["preconditions"])


def test_no_written_disproof_fails_the_start_gate() -> None:
    row = _derive([_brief(disproof=())])
    assert row["side"] == "precondition_failed" and any("沒寫反證" in p for p in row["preconditions"])


def test_the_writer_holds_the_same_start_gate(tmp_path: Path) -> None:
    ctx, _wid = _ctx(kind="undecided")
    out = write_brief(_fresh(), ctx=ctx, directory=tmp_path / "b", watches_path=tmp_path / "w.json")
    assert out["brief_id"]
    ctx, _wid = _ctx(kind="neither")
    with pytest.raises(ContractViolation, match="neither"):
        write_brief(_fresh(), ctx=ctx, directory=tmp_path / "b2", watches_path=tmp_path / "w2.json")
    ctx, _wid = _ctx()
    with pytest.raises(ContractViolation, match="反證已寫下"):
        write_brief(_fresh(disproof=()), ctx=ctx, directory=tmp_path / "b3", watches_path=tmp_path / "w3.json")


# ---------------------------------------------------------------------------
# ③ 深挖清單存進敘事
# ---------------------------------------------------------------------------

def test_depth_check_is_saved_only_when_written_and_old_ids_do_not_move() -> None:
    plain = _record()
    assert "depth_check" not in plain and parse_brief_record(plain).depth_check == ()
    checked = _record(confirm=(CONFIRM,), depth_check={**ALL_CHECKED, "why_chosen": "加碼條件：c1",
                                                       "latest_call": "不適用：沒有法說，只有股東會"})
    assert checked["brief_id"] != plain["brief_id"] and checked["brief_id"] == new_brief_id(checked)
    parsed = parse_brief_record(checked)
    assert parsed.depth_check_map["why_chosen"] == "加碼條件：c1" and unchecked_items(parsed.depth_check_map) == []


@pytest.mark.parametrize("depth_check, confirm, match", [
    ({"vibes": "sr_x"}, (), "不認得的鍵"),
    ({"why_chosen": "加碼條件：c2"}, (CONFIRM,), "只有 1 條"),
    ({"why_chosen": "加碼條件：客戶 10-K"}, (CONFIRM,), "c<n>"),
    ({"why_chosen": "  "}, (), "非空字串"),
    ({"latest_call": "不適用："}, (), "理由"),
    ({"latest_call": "待查"}, (), "四種之一"),                      # 11-04 R2：不認得的字不算查過、拒收
    ({"dilution": "看過了，沒問題"}, (), "四種之一"),
])
def test_a_malformed_depth_check_is_refused_by_the_contract(depth_check, confirm, match) -> None:
    with pytest.raises(ContractViolation, match=match):
        _record(confirm=confirm, depth_check=depth_check)


def test_only_the_four_forms_count_as_checked() -> None:
    """11-04 R2（L18）：引用要指得回來源（`CITATION_PREFIXES`）——「待查」「看過了」不算查過，⑤ 照數。
    變異：is_checked 退回「不以缺開頭就算」→ 紅。"""
    from alpha.narrative.depth_check import CITATION_PREFIXES, is_checked, value_form

    for good in ("library/raw/a.md", "library/private/b.md", "sr_" + "a" * 16, "graph:doc_1", "engine_c:AXTI#gm",
                 "alpha://three_questions/v1/AXTI#in_numbers_series", "thesis/axti.md#1", "https://x.com/a"):
        assert value_form(good) == "cite" and is_checked(good), good
    assert {value_form("不適用：沒有法說"), value_form("加碼條件：c1"), value_form("缺：還沒讀")} == {
        "not_applicable", "addon", "unchecked"}
    for bad in ("待查", "看過了", "加碼條件：客戶 10-K", "不適用：", "", None, 3):
        assert not is_checked(bad), bad
    assert len(CITATION_PREFIXES) == len(set(CITATION_PREFIXES))
    left = unchecked_items({**ALL_CHECKED, "dilution": "待查"})
    assert left == ["稀釋"]


def test_a_rewrite_that_drops_checked_items_is_reminded_not_refused() -> None:
    """11-04 R2：為別的原因重寫沒抄清單，⑤ 會把那一檔數回去——寫入時點名掉了哪幾項；沒掉、或上一版本來沒查的不印。"""
    from alpha.narrative.depth_check import dropped_checks_line

    before = {**ALL_CHECKED, "why_chosen": "缺：客戶沒具名"}
    line = dropped_checks_line(before, {"latest_report": ALL_CHECKED["latest_report"]})
    assert line.startswith("  ⚠ 上一版查過的 8 項這一版沒寫") and "讀到邊：客戶為什麼選它的變體" not in line
    assert dropped_checks_line(before, before) is None and dropped_checks_line(None, None) is None
    assert dropped_checks_line({"dilution": "缺"}, None) is None


def test_a_private_excerpt_in_the_depth_check_must_exist_too(tmp_path: Path) -> None:
    """⑬ 對稱面（11-04 R2）：私人節錄與一手節錄同一條——檔要在。"""
    ctx, _wid = _ctx()
    with pytest.raises(ContractViolation, match="library/private"):
        write_brief(_fresh(depth_check={"latest_report": "library/private/沒有這個檔.md"}), ctx=ctx,
                    directory=tmp_path / "b", watches_path=tmp_path / "w.json")


def test_unchecked_items_and_the_lines_say_what_is_left() -> None:
    assert addon_index("加碼條件：c2（客戶 10-K 具名）") == 2 and addon_index("sr_x") is None
    left = unchecked_items({**ALL_CHECKED, "why_chosen": "缺：客戶沒具名", "replaced_by": None})
    assert left == ["讀到邊：客戶為什麼選它的變體", "讀到邊：什麼會讓它被換掉"]
    assert "加碼條件還沒查 2 項" in depth_check_lines({**ALL_CHECKED, "why_chosen": "缺", "replaced_by": "缺"})[0]
    assert "沒有深挖清單" in depth_check_lines(None)[0]
    assert depth_check_lines(ALL_CHECKED)[0].startswith("  ✓ 深挖清單 10 項都查過")


def test_a_raw_excerpt_in_the_depth_check_must_exist(tmp_path: Path) -> None:
    ctx, _wid = _ctx()
    with pytest.raises(ContractViolation, match="library/raw"):
        write_brief(_fresh(depth_check={"latest_report": "library/raw/沒有這個檔.md"}), ctx=ctx,
                    directory=tmp_path / "b", watches_path=tmp_path / "w.json")


def test_a_citation_may_carry_a_note_and_every_cited_path_and_reading_is_checked(tmp_path: Path) -> None:
    """2026-11-04 drain：⑬ 原本整串當一個路徑——「library/raw/x.txt（第三季新聞稿）」檔明明在也拒收，接在後面的第二個
    引用反而不驗。改成值裡每一個路徑與讀圖 id 都驗（檔名可含全形逗號）。變異：退回整串比對 → 第一條紅；只驗開頭 → 第二、四條紅。"""
    from types import SimpleNamespace

    from alpha.providers.briefs import depth_check_ref_problems

    (tmp_path / "library" / "raw").mkdir(parents=True)
    (tmp_path / "library" / "private" / "inbox").mkdir(parents=True)
    (tmp_path / "library" / "raw" / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "library" / "private" / "inbox" / "報告_甲，乙_中文.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "library" / "outside.txt").write_text("x", encoding="utf-8")
    reading = "sr_" + "a" * 16

    def problems(value: str) -> list[str]:
        return depth_check_ref_problems(SimpleNamespace(depth_check=(("latest_report", value),)),
                                        readings_by_id={reading: object()}, root=tmp_path)

    assert problems("library/raw/a.txt（第三季新聞稿與三表）") == []
    assert len(problems("library/raw/a.txt（新聞稿）＋ library/raw/沒有.txt（10-Q）")) == 1
    assert problems("library/private/inbox/報告_甲，乙_中文.pdf（p.3）") == []
    assert problems(f"{reading}（第三方列舉）") == [] and len(problems(f"library/raw/a.txt ＋ sr_{'b' * 16}")) == 1
    assert len(problems("library/raw/../outside.txt")) == 1 and len(problems("sr_bogus（註）")) == 1


# ---------------------------------------------------------------------------
# ④ ⑤「加碼條件還沒查」
# ---------------------------------------------------------------------------

def test_the_addon_cell_counts_open_and_held_rows_with_items_left() -> None:
    complete = _derive([_brief(confirm=(CONFIRM,), depth_check={**ALL_CHECKED, "why_chosen": "加碼條件：c1"})])
    partial = _derive([_brief()])
    assert complete["addon_unchecked"] == [] and len(partial["addon_unchecked"]) == len(DEPTH_CHECK_KEYS)
    held = {"status": "ok", "by_company": {CO: {"symbols": ["AXTI"]}}, "unresolved": [], "beta_excluded": 0,
            "zero_shares": 0}
    no_narrative = derive_row(T, CO, records=[], today=TODAY, reading_rows=_rows(), watches=[], lifecycle={},
                              edge=EDGE, three_questions=_tq(), held=held)
    assert no_narrative["group"] == "held" and len(no_narrative["addon_unchecked"]) == len(DEPTH_CHECK_KEYS)
    missing = _derive([_brief(state="missing", watch_id="ew_1", disproof=())])
    groups = {"open": [complete, partial], "held": [no_narrative], "missing": [missing]}
    assert addon_unchecked_rows(groups) == [partial, no_narrative]          # 缺 X 不數；都查過的不數
    # 已持有、敘事判「不要」的非倍率持股（例：COHR）：加碼與反證住 thesis（research-drain ⓓ），不數加碼條件
    held_pass = _derive([_brief(state="pass", reason="非倍率持股，加碼與反證住 thesis")], held=held)
    assert held_pass["group"] == "held" and held_pass["addon_unchecked"] == []
    # 板上的計數：持股讀到才數；讀不到時已持有那一半數不到——整格 None，不是少算（R2 變異 M5 存活，補這一段）
    board = assemble_board([complete, partial, missing], universe=[T], held=HELD_NONE, narrative_rewrite=[])
    assert board["counts"]["addon_unchecked"] == 1
    blind = assemble_board([complete, partial, missing], universe=[T], narrative_rewrite=[],
                           held={"status": "unavailable", "reason": "Sheet 讀不到"})
    assert blind["counts"]["addon_unchecked"] is None


def _ctx(kind="volume"):
    tq = {"priced_in": [{"key": "own_history_pctile", "value": 88.0, "absence_kind": None, "basis": "P/S",
                         "as_of": "2026-10-20", "detail": {"multiple_today": 4.2}},
                        {"key": "cohort_median", "value": None, "absence_kind": "not_yet_recorded"}],
          "in_numbers": [{"key": "in_numbers_series", "value": [{"yoy": 1.0}], "absence_kind": None}]}
    today = date.today()
    watches = {"schema_version": 1, "watches": []}
    ctx = WriteContext(today=today, reading_rows=[{"node": "tech:x", "unit": "layer", "reading_id": READ,
                                                   "status": "current", "kind": kind}],
                       readings_by_id={READ: SimpleNamespace(angles={"supply_side": [(CO, "supplies_to", "tech:x")],
                                                                     "demand_side": []})},
                       three_questions=tq, watches=watches, lifecycle={})
    wake = ew.add_watch(ctx.watches, kind="date", wake_brief=CO, expires=(today + timedelta(days=200)).isoformat(),
                        until=(today + timedelta(days=30)).isoformat())
    return ctx, wake["watch_id"]


def _fresh(**kw) -> dict:
    expires = (date.today() + timedelta(days=200)).isoformat()
    disproof = kw.pop("disproof", ({**DISPROOF, "expires": expires},))
    return _record(at=datetime.now(timezone.utc), disproof=disproof, **kw)


# ---------------------------------------------------------------------------
# ⑤ 短版 ③「可開待你選」與摘要行
# ---------------------------------------------------------------------------

NOW = datetime(2026, 11, 3, 1, 0, tzinfo=timezone.utc)
OPEN_ROWS = [{"ticker": "AAA", "company_id": "co:aaa", "brief_id": "ib_a2", "stall_days": 3,
              "priced_since": {"answer": "yes", "then": {"value": 88.4}, "now": {"value": 81.6}, "return_since": -0.174}},
             {"ticker": "BBB", "company_id": "co:bbb", "brief_id": "ib_b1", "stall_days": 0, "priced_since": None}]
LOOKED_RECEIPT = {"version": "research-receipt/v1", "side": "看了沒買", "narrative": "present",
                  "company_id": "co:aaa", "research_ticker": "AAA", "declared": {"brief_id": "ib_a1"}}


def _looked(tmp_path: Path, brief_id: str, *, choice: str = "不要", until: date | None = None) -> Path:
    """記一次看了沒買：收據裡候選板那一列就是這一版（寫入端要板上那一版，2026-11-04 R2）。"""
    from portfolio import looked_log as ll

    path = tmp_path / "looked.jsonl"
    board = {"candidate_as_of": TODAY.isoformat(),
             "candidate": {"ticker": "AAA", "company_id": "co:aaa", "brief_id": brief_id, "group": "open"}}
    ll.append(ll.build_entry(symbol="AAA", choice=choice, why="翻倍條件太遠", today=TODAY, until=until,
                             recorded_at="2026-11-03T02:00:00+00:00",
                             receipt={**LOOKED_RECEIPT, "declared": {"brief_id": brief_id}, "derived": board}), path)
    return path


def test_open_rows_this_version_already_chosen_are_not_asked_again(monkeypatch, tmp_path: Path) -> None:
    from crons import heartbeat as hb

    monkeypatch.setattr(hb, "_load_state", lambda state_dir, kind: ({"groups": {"open": OPEN_ROWS}}, None))
    rows, problem = hb.open_choice_rows(tmp_path, looked_path=tmp_path / "none.jsonl")
    assert [r["ticker"] for r in rows] == ["AAA", "BBB"] and problem is None
    rows, _ = hb.open_choice_rows(tmp_path, looked_path=_looked(tmp_path, "ib_a2"))     # 這一版選過 → 不再列
    assert [r["ticker"] for r in rows] == ["BBB"]
    (tmp_path / "looked.jsonl").unlink()
    rows, _ = hb.open_choice_rows(tmp_path, looked_path=_looked(tmp_path, "ib_a1"))     # 選的是舊版 → 換版再問
    assert [r["ticker"] for r in rows] == ["AAA", "BBB"]
    monkeypatch.undo()
    rows, problem = hb.open_choice_rows(tmp_path / "none")
    assert rows is None and problem                                                     # 讀不到＝None＋理由，不是 []


def test_only_the_open_group_is_asked_not_a_failed_precondition(monkeypatch, tmp_path: Path) -> None:
    """可開待你選只讀「可開」組——前提失效那一組（附組）不混進來（R2 變異 M6 存活，補這一條）。"""
    from crons import heartbeat as hb

    board = {"groups": {"open": OPEN_ROWS[:1], "missing": [OPEN_ROWS[1]]},
             "side_groups": {"precondition_failed": [{"ticker": "CCC", "company_id": "co:ccc", "brief_id": "ib_c1"}]}}
    monkeypatch.setattr(hb, "_load_state", lambda state_dir, kind: (board, None))
    rows, _ = hb.open_choice_rows(tmp_path, looked_path=tmp_path / "none.jsonl")
    assert [r["ticker"] for r in rows] == ["AAA"]


def test_a_wait_comes_back_on_its_day_and_is_counted_while_it_waits(monkeypatch, tmp_path: Path) -> None:
    """2026-11-04 R2（INV-2）：等到條件到期那天起列回來、附上次等的是什麼；在等的那幾天由「等到條件 M 檔在等」每天現形。"""
    from crons import heartbeat as hb
    from crons.daily_brief import open_choice_block, open_choice_lines, open_waiting_line

    monkeypatch.setattr(hb, "_load_state", lambda state_dir, kind: ({"groups": {"open": OPEN_ROWS}}, None))
    looked = _looked(tmp_path, "ib_a2", choice="等到條件", until=date(2026, 11, 20))
    rows, _ = hb.open_choice_rows(tmp_path, looked_path=looked, today=date(2026, 11, 19))
    assert [r["ticker"] for r in rows] == ["BBB"]
    waiting, _ = hb.open_choice_waiting(tmp_path, looked_path=looked, today=date(2026, 11, 19))
    assert [(r["ticker"], e.until.isoformat()) for r, e in waiting] == [("AAA", "2026-11-20")]
    assert hb.open_choice_queue_line(rows, None, waiting).endswith("｜等到條件 1 檔在等（最近 2026-11-20 重問）：AAA")
    line = open_waiting_line(waiting)
    assert line == "- 等到條件 1 檔在等（最近 2026-11-20 重問）：AAA（2026-11-20：翻倍條件太遠）"
    assert open_choice_block([], None, line) == [line]                         # 沒有待選、還有在等 → 那一句照印
    rows, _ = hb.open_choice_rows(tmp_path, looked_path=looked, today=date(2026, 11, 20))
    assert [r["ticker"] for r in rows] == ["AAA", "BBB"]
    assert rows[0]["wait_expired"] == {"until": "2026-11-20", "why": "翻倍條件太遠"}
    assert open_choice_lines(rows[:1])[0].endswith("｜上次說等到條件（翻倍條件太遠），2026-11-20 到期重問")
    assert hb.open_choice_waiting(tmp_path, looked_path=looked, today=date(2026, 11, 20))[0] == []


def test_the_heartbeat_and_the_brief_judge_the_wait_on_their_own_today(monkeypatch, tmp_path: Path) -> None:
    """11-04 R2 覆核：心跳段 3 與短版 ③ 都收 `now`——等到條件到不到期看那一輪的今天，不看真實時鐘。假的 now 一天在到期前、
    一天在到期當天：前者不列、後者列回來（不管真實時鐘是哪天）。變異：today_local 不吃 now、或回固定日子 → 紅。"""
    import json

    from crons import daily_brief
    from crons import heartbeat as hb
    from engine_b import todo

    monkeypatch.setattr(hb, "_load_state", lambda state_dir, kind: ({"groups": {"open": OPEN_ROWS}}, None))
    monkeypatch.setattr("portfolio.looked_log.LOOKED_LOG", _looked(tmp_path, "ib_a2", choice="等到條件",
                                                                   until=date(2026, 11, 20)))
    eve, due = (datetime(2026, 11, d, 1, 0, tzinfo=timezone.utc) for d in (19, 20))
    queue = {when: hb.build_queue(state_dir=tmp_path, now=when).lines for when in (eve, due)}
    assert any(x.startswith("**可開待你選 1**") and "等到條件 1 檔在等" in x for x in queue[eve])
    assert any(x.startswith("**可開待你選 2**") and x.endswith("：AAA、BBB") for x in queue[due])
    # 短版 ③：交下去的今天就是這一則的 today（由 now 換算）
    seen: list = []
    monkeypatch.setattr(hb, "open_choice_rows", lambda state_dir, **kw: seen.append(kw.get("today")) or ([], None))
    monkeypatch.setattr(hb, "open_choice_waiting", lambda state_dir, **kw: seen.append(kw.get("today")) or ([], None))
    monkeypatch.setattr(todo, "load", lambda *a, **k: todo.empty_pool())
    monkeypatch.setattr(hb, "quota_entries", lambda rows, now: [])
    leads = tmp_path / "pending_leads.json"
    leads.write_text(json.dumps({"leads": {}, "harvest_log": []}), encoding="utf-8")
    daily_brief.compose_brief(now=due, summary="Daily", snapshot={}, run_record_path=tmp_path / "missing.json",
                              leads_path=leads, heartbeat_dir=tmp_path, state_dir=tmp_path)
    assert seen and set(seen) == {date(2026, 11, 20)}


def test_the_narrative_writer_reminds_when_a_rewrite_drops_checked_items(monkeypatch, tmp_path: Path, capsys) -> None:
    """11-04 R2 覆核：`alpha brief --add` 取代上一版時，從 ledger 找到被取代的那一版、點名沒抄的項目——走整段 CLI，
    寫入與脈絡換成假的（不寫任何檔）。變異：找上一版用錯鍵 → 提醒永遠不印 → 紅。"""
    import json

    import alpha.providers.briefs as briefs
    from alpha import cli
    from alpha.providers import closure as provider

    previous = _brief(confirm=(CONFIRM,), depth_check={**ALL_CHECKED, "why_chosen": "加碼條件：c1"})
    monkeypatch.setattr(provider, "first_narrative_awaiting_cohort", lambda _t: None)
    monkeypatch.setattr(briefs, "WriteContext", SimpleNamespace(load=lambda ticker: None))
    monkeypatch.setattr(briefs, "write_brief", lambda record, ctx: {"path": "（假）", "registered": [], "linked": [],
                                                                    "consumed": [], "acknowledged": []})
    monkeypatch.setattr(briefs, "read_brief_records", lambda ticker: ([previous], []))
    monkeypatch.setattr("alpha.providers.candidates.held_on_board", lambda ticker: None)
    raw = _fresh(depth_check={"latest_report": ALL_CHECKED["latest_report"]}, supersedes=previous.brief_id)
    spec = {key: raw[key] for key in ("slots", "rides", "disproof", "answers", "candidate_state", "depth_check")}
    spec["supersedes_id"] = previous.brief_id
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    assert cli.main(["brief", T, "--add", str(path)]) == 0
    out = capsys.readouterr().out
    assert "上一版查過的 9 項這一版沒寫" in out and "讀到邊：客戶為什麼選它的變體" in out
    spec["supersedes_id"] = None                                           # 不是取代：不印
    path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    assert cli.main(["brief", T, "--add", str(path)]) == 0
    assert "上一版查過的" not in capsys.readouterr().out


def test_an_unreadable_looked_log_is_said_not_raised(monkeypatch, tmp_path: Path) -> None:
    """2026-11-04 R2：帳整本讀不到（編碼壞了）→ (None, 理由)；完整心跳段 3 照樣組得出來（pq2 清單不被帶走）。"""
    from crons import heartbeat as hb

    monkeypatch.setattr(hb, "_load_state", lambda state_dir, kind: ({"groups": {"open": OPEN_ROWS}}, None))
    bad = tmp_path / "looked.jsonl"
    bad.write_bytes("看了沒買".encode("big5"))
    rows, problem = hb.open_choice_rows(tmp_path, looked_path=bad)
    assert rows is None and "看了沒買的帳讀不到（UnicodeDecodeError）" in problem
    monkeypatch.setattr("portfolio.looked_log.LOOKED_LOG", bad)
    lines = hb.build_queue(state_dir=tmp_path, now=NOW).lines
    assert any(x.startswith("可開待你選：讀不到（看了沒買的帳讀不到") for x in lines) and len(lines) > 1


def test_the_decision_block_lists_each_open_row_with_its_priced_context_and_stays_out_of_the_batch() -> None:
    from crons.daily_brief import decisions_block, open_choice_lines
    from engine_b import todo

    lines = open_choice_lines(OPEN_ROWS, label=lambda r: f"名 {r['ticker']}")
    assert lines[0] == "- 名 AAA：可開 3 天｜已定價答是｜自家三年百分位 88→82｜判斷日以來 −17.4%"
    assert lines[1] == "- 名 BBB：可開 0 天｜已定價答量不到（今天也量不到）"
    item = {"n": 900, "type": "manual", "title": "題目", "recommendation": {"verb": "go", "reason": "r"}}
    block, batch = decisions_block(actionable=[item], problem=None, todo_mod=todo, open_choice=lines)
    assert block[0] == "### ③ 待你決定（1＋可開待你選 2）"
    assert block[1].startswith("**可開 2 檔待你選**") and block[2:4] == lines
    assert any("看了沒買" in x for x in block) and batch == "900 go"                    # 批次指令只有編號
    for word in ("該買", "燈", "目標價", "名次"):
        assert not any(word in x for x in block)
    alone, batch = decisions_block(actionable=[], problem=None, todo_mod=todo, open_choice=[])
    assert alone == ["### ③ 待你決定（0）", "- 沒有"] and batch is None
    unread, _ = decisions_block(actionable=[], problem=None, todo_mod=todo, open_choice=None,
                                open_problem="候選板沒有 artifact")
    assert "**可開待你選：讀不到（候選板沒有 artifact）**" in unread and "- 沒有" not in unread


def test_the_summary_line_and_the_full_heartbeat_count_it(monkeypatch, tmp_path: Path) -> None:
    from crons import heartbeat as hb

    kw = dict(now=NOW, run_record_path=tmp_path / "nope.json", leads_path=tmp_path / "nope.json", theme_nudge=False,
              theme_line="")
    assert hb.summary_line(snapshot={"pq2.actionable": 2, "candidate.open_undecided": 1}, **kw).startswith(
        "Daily 2026-11-03｜球在你 2｜可開待你選 1")
    assert "可開待你選" not in hb.summary_line(snapshot={"pq2.actionable": 2, "candidate.open_undecided": 0}, **kw)
    assert hb.open_choice_queue_line([], None).startswith("**可開待你選 0**")
    assert hb.open_choice_queue_line(None, "候選板讀不到") == "可開待你選：讀不到（候選板讀不到）"
    monkeypatch.setattr(hb, "_load_state", lambda state_dir, kind: ({"groups": {"open": OPEN_ROWS}}, None))
    monkeypatch.setattr("portfolio.looked_log.LOOKED_LOG", tmp_path / "none.jsonl")
    lines = hb.build_queue(state_dir=tmp_path, now=NOW).lines
    assert any(x.startswith("**可開待你選 2**") and x.endswith("：AAA、BBB") for x in lines)


# ---------------------------------------------------------------------------
# ④ ⑤ 待做清單一格
# ---------------------------------------------------------------------------

def test_the_ledger_cell_counts_addon_rows_and_is_a_progress_cell() -> None:
    from engine_b import todo_ledger as tl

    assert "todo.addon_unchecked" in tl.LEDGER_KEYS and tl.PROGRESS_LABELS["todo.addon_unchecked"] == "加碼條件還沒查"
    board = {"counts": {}, "new_edges_check": {"status": "ok"}, "reading_change_check": {"status": "ok", "unchecked": 0},
             "groups": {"open": [{"ticker": "AAA", "addon_unchecked": ["讀到邊：客戶為什麼選它的變體"],
                                  "record_version": RECORD_VERSION_V2, "brief_id": "ib_a"},
                                 {"ticker": "CCC", "addon_unchecked": [], "record_version": RECORD_VERSION_V2}],
                        "held": [{"ticker": "BBB", "addon_unchecked": ["x"] * 10, "record_version": None,
                                  "brief_id": None}],
                        "missing": [{"ticker": "DDD", "addon_unchecked": ["x"]}]}}
    params = dict(today=TODAY, leads_store={"leads": {}}, watches=[], todo_items=[], hypotheses=[], briefs=[],
                  reading_needs_reread=0, layer_note_reread=0, candidates=board, thesis_due=[],
                  loaders={"classification_gaps": lambda: [], "undisposed": lambda: [],
                           "parked_without_expiry": lambda: [], "stale_lead_entities": lambda: 0,
                           "story_gaps": lambda: [], "admission_audit_ledger": lambda: ([], [])})
    row = {r.key: r for r in tl.collect(**params)}["todo.addon_unchecked"]
    assert (row.count, row.progress) == (2, 2) and row.work == "AAA（1 項）、BBB（沒有 v2 敘事）"
    unread = {r.key: r for r in tl.collect(**{**params, "candidates": None})}["todo.addon_unchecked"]
    assert unread.count is None
    # 持股讀不到（已持有那一半數不到）、舊板（列上沒有這一格）也是沒算，不是 0（INV-3）
    no_sheet = {r.key: r for r in tl.collect(**{**params, "candidates": {**board, "holdings": {"status": "unavailable"}}})}
    assert no_sheet["todo.addon_unchecked"].count is None and "持股沒讀到" in no_sheet["todo.addon_unchecked"].reason
    old = {**board, "groups": {"open": [{"ticker": "AAA", "record_version": RECORD_VERSION_V2}]}}
    stale = {r.key: r for r in tl.collect(**{**params, "candidates": old})}["todo.addon_unchecked"]
    assert stale.count is None and "舊版" in stale.reason and stale.progress is None
