"""只差已定價（2026-11-01 使用者「我覺得你講的都算方向正確…可以直接改?」；failure log #123；ROADMAP 旁支「候選板標出只差已定價」）。

10-21 Q3W 處置紀錄：3081.TWO、4979.TWO、AXTI 三檔等回落「假設改宣告可開，四個機械前提都成立——可開與否只剩已定價嗎的判斷」，
但等回落不進使用者的決策時刻（A1 第 1 點），A1 第 4 點又說已定價是脈絡不是否決——這個價格判斷沒有地方印給使用者看。

守的事：
①等回落列假設把已定價當脈絡、改宣告可開，用**同一個** `open_preconditions` 驗前提，結果放在 `open_gaps`——不重用
  `preconditions`（那一格的意思是「宣告可開、前提失效」，兩種意思擠一格下游就分不出來，L12）；
②沒押讀圖、邊緣不是「邊緣」各算一項缺口（寫入端與分組本來就擋的，`open_preconditions` 不查）；
③只呈現：分組、derived、side、rewrite[] 都不變，可開仍是 0（可開為零就零）；
④不是等回落的列、已持有的列一律 None（沒算，不是 []）；
⑤心跳狀態塊、短版等回落行印出；沒算的印「未算」，不壓成 0；短版不出現「該／燈／買／賣」；
⑥首頁卡片的布林由產生端給（APP 不算），None 不是 False。
"""
from __future__ import annotations

import pytest

from alpha.candidates import OPEN_GAP_NO_RIDES, OPEN_GAP_NOT_EDGE, assemble_board, priced_only_counts
from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record
from alpha.providers.candidates import derive_row
from engine_b import event_watch as ew
from test_priced_since import CO, EDGE, HELD_NONE, READ, T, TODAY, _artifact, _at, _chain, _rec, _slots

TQ = {"priced_in": [{"key": "own_history_pctile", "value": 88.0, "absence_kind": None, "basis": "P/S",
                     "as_of": "2026-10-20"}],
      "in_numbers": [{"key": "in_numbers_series", "value": [1], "absence_kind": None}], "will_it_die": []}
WAIT_WATCH = {"watch_id": "ew_wait", "kind": "date", "status": "active", "wake_brief": CO,
              "until": "2026-11-14", "expires": "2027-01-31"}


def _row(records, *, kind="volume", status="current", edge=EDGE, extra_watches=(), held=HELD_NONE):
    return derive_row(T, CO, records=records, today=TODAY, reading_rows={("tech:x", "layer"): {
        "node": "tech:x", "unit": "layer", "reading_id": READ, "status": status, "kind": kind}},
        watches=[WAIT_WATCH, *extra_watches], lifecycle={}, edge=edge, three_questions=TQ, held=held)


def _no_rides_wait() -> list:
    rec = brief_record(company_id=CO, ticker=T, slots=_slots(), record_version=RECORD_VERSION_V2, rides=[],
                       answers={"priced_in": "yes", "in_numbers": "yes"},
                       candidate_state={"state": "priced_wait", "watch_id": "ew_wait", "reason": "寫入時第 88 百分位"},
                       created_at=_at(10, 15))
    return [parse_brief_record(rec)]


# ---- ①③ 前提都成立：標「只差已定價」，其餘一格不動 ----

def test_a_wait_row_whose_open_preconditions_all_hold_is_priced_only_and_nothing_else_moves() -> None:
    row = _row(_chain())
    assert row["open_gaps"] == []
    assert (row["group"], row["derived"], row["side"], row["declared"]) == ("priced_wait",) * 2 + (None, "priced_wait")
    assert row["preconditions"] == []                      # 那一格只給宣告可開的列（L12）
    assert not any("已定價" in r for r in row["rewrite"])   # 不叫醒、不進「敘事該重寫」
    board = assemble_board([row], universe=[T], held=HELD_NONE, narrative_rewrite=[])
    assert board["counts"]["priced_wait_priced_only"] == 1 and board["counts"]["priced_wait_priced_only_unknown"] == 0
    assert board["counts"]["open"] == 0 and board["counts"]["priced_wait"] == 1     # 可開為零就零：標記不改分組


# ---- ② 每一種缺口各自寫出來（同一個 open_preconditions ＋ 它不查的兩項） ----

@pytest.mark.parametrize("kw, expected", [
    ({"kind": "undecided"}, "判讀是 undecided（可開要護城河或量）"),
    ({"status": "superseded"}, "狀態 superseded"),
    ({"extra_watches": [{"watch_id": "ew_rd", "kind": ew.SEMANTIC_KIND, "status": "fired", "expires": "2027-01-01",
                         "source_ref": f"reading:{READ}#c1", "disproof_ref": f"reading:{READ}#c1"}]},
     "待處置的反證 watch：ew_rd"),
    ({"edge": {"state": "unmeasurable", "reasons": ["coverage_unavailable"], "market_cap_usd": 4.8e9,
               "analyst_count": None}}, "邊緣無法量：缺分析師家數"),
    ({"edge": {"state": "not_edge", "reasons": ["coverage_over_edge"], "market_cap_usd": 4.8e9, "analyst_count": 13,
               "prior": {"state": "edge", "inputs_as_of": "2026-10-20"}}}, OPEN_GAP_NOT_EDGE),
])
def test_each_gap_is_written_out_and_the_row_stays_in_its_group(kw, expected) -> None:
    row = _row(_chain(), **kw)
    assert any(expected in gap for gap in row["open_gaps"]), row["open_gaps"]
    assert row["group"] == "priced_wait" and row["derived"] == "priced_wait"
    # 缺口不得寫進 preconditions：個股頁把那一格印成「前提失效」＝宣告可開、前提失效，等回落沒有宣告可開（L12）
    assert row["preconditions"] == []


def test_a_wait_without_any_ride_is_not_priced_only() -> None:
    """寫入端拒收沒押讀圖的可開；`open_preconditions` 的讀圖迴圈對空 rides 什麼都不查——不補這一項就會假裝前提全過。"""
    row = _row(_no_rides_wait())
    assert row["open_gaps"] == [OPEN_GAP_NO_RIDES]


# ---- ④ 不是等回落、已持有：None＝沒算 ----

@pytest.mark.parametrize("state", ["missing", "pass", "open"])
def test_rows_that_are_not_waiting_on_price_carry_none(state) -> None:
    row = _row([parse_brief_record(_rec(at=_at(10, 15), state=state, reason="理由"))])
    assert row["open_gaps"] is None


def test_a_held_wait_row_carries_none() -> None:
    held = {"status": "ok", "by_company": {CO: {"symbol": "AXTI", "shares": 10}}, "unresolved": [], "beta_excluded": 0,
            "zero_shares": 0}
    row = _row(_chain(), held=held)
    assert row["group"] == "held" and row["open_gaps"] is None


def test_counts_tell_not_computed_from_zero() -> None:
    assert priced_only_counts([{"open_gaps": []}, {"open_gaps": ["x"]}, {}]) == {"priced_only": 1,
                                                                              "priced_only_unknown": 1}
    assert priced_only_counts([]) == {"priced_only": 0, "priced_only_unknown": 0}


# ---- ⑤ 心跳 ----

def test_the_status_block_prints_priced_only_and_never_turns_not_computed_into_zero() -> None:
    from crons import heartbeat as hb

    base = {"open": 0, "missing": 0, "priced_wait": 2, "pass": 0, "held": 0, "oldest": {"priced_wait": 3},
            "pulled_back": 0}
    assert "等回落 2（最老 3 天｜已回落 0｜只差已定價 1）" in hb.candidate_states_text(
        {**base, "priced_only": 1, "priced_only_unknown": 0})
    assert "等回落 2（最老 3 天｜已回落 0｜只差已定價 未算）" in hb.candidate_states_text(base)   # 舊計數沒有這一格
    assert "只差已定價 未算" in hb.candidate_states_text({**base, "priced_only": 0, "priced_only_unknown": 2})
    assert "只差已定價 1（1 未算）" in hb.candidate_states_text({**base, "priced_only": 1, "priced_only_unknown": 1})
    assert "只差已定價" not in hb.candidate_states_text({**base, "priced_wait": 0})                   # 0 檔不多印


def test_the_short_wait_block_marks_the_row_and_explains_without_action_words(tmp_path, monkeypatch) -> None:
    from crons import heartbeat as hb

    monkeypatch.setattr(hb, "_load_state", lambda state_dir, kind: (__import__("json").loads(
        (state_dir / "candidates.json").read_text(encoding="utf-8")), None))
    monkeypatch.setattr(ew, "load_watches", lambda: {"watches": []})
    gapped = _row(_chain(), kind="undecided")
    short = hb.priced_wait_short_lines(_artifact(tmp_path / "a", [gapped]), today=TODAY)
    assert "只差已定價" not in "\n".join(short)                                    # 還缺別的就不標
    short = hb.priced_wait_short_lines(_artifact(tmp_path / "b", [_row(_chain())]), today=TODAY)
    assert "｜**只差已定價**｜" in short[1]
    assert "只差已定價＝可開的四個機械前提都成立" in short[-1]
    for word in ("該", "燈", "買", "賣"):
        assert word not in "\n".join(short)


# ---- ⑥ 首頁卡片：產生端給布林 ----

@pytest.mark.parametrize("value, expected", [([], True), (["押的讀圖 sr_x 判讀是 undecided"], False), (None, None)])
def test_the_card_gets_a_boolean_from_the_producer_and_none_is_not_false(value, expected) -> None:
    from webapp.materialize import _card_overview

    row = {"declared": "priced_wait", "derived": "priced_wait", **({"open_gaps": value} if value is not None else {})}
    view = {"candidate": {"lines": [{"key": "candidate:state", "datum": {"value": row}}]}}
    assert _card_overview(view, None)["priced_only"] is expected


def test_old_rows_without_the_key_still_render(tmp_path, monkeypatch) -> None:
    """舊 artifact（candidates/3 之前）的列沒有 open_gaps：短版照印、不標、不報錯。"""
    from crons import heartbeat as hb

    monkeypatch.setattr(hb, "_load_state", lambda state_dir, kind: (__import__("json").loads(
        (state_dir / "candidates.json").read_text(encoding="utf-8")), None))
    monkeypatch.setattr(ew, "load_watches", lambda: {"watches": []})
    old = {k: v for k, v in _row(_chain()).items() if k != "open_gaps"}
    short = hb.priced_wait_short_lines(_artifact(tmp_path, [old]), today=TODAY)
    assert short[0] == "**等回落 1 檔**" and "只差已定價" not in "\n".join(short)
