"""個股頁（Phase 3 Step 3.7）：首屏候選狀態＋三個字、三題稽核區、readiness（讀圖升核心）、argument 鏈段的需求端、
downside 每條反證連 watch、`bet` 純文字。

守的是：
1. **個股頁不另推一份**——候選狀態與候選板同一個 `derive_row`；downside 的歸屬與落格與心跳段 2 同一套（L16）。
2. **缺席分型由產生端宣告**——沒給輸入（upstream_unavailable）、as-of（point_in_time_unavailable）、不上板
   （not_yet_recorded）三者不得同形（L12）。
3. 讀圖升核心兩個方向：圖變了 → 讀圖 stale → readiness `ready_with_flags`；只有 refresh 燈 `review_required`
   （退役估值鏈殘留）時讀圖面板狀態不變。
4. 稽核區每一格是 read model 的同一個 Datum；個股頁不帶任何部位欄位名。
全部用注入的輸入——不讀 Sheet、不連圖、不讀真實 ledger。
"""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from alpha.contracts import FORBIDDEN_POSITION_TOKENS
from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record
from briefing.analyst_view import build_analyst_view
from briefing.analyst_view.compose import _readiness
from briefing.analyst_view.contracts import BLOCKED, READY_WITH_FLAGS
from engine_b import event_watch as ew
from engine_b.disproof import DOWNSIDE_STATES, downside_rows, watch_category
from tests.test_analyst_view import _bare_view, _full_view

TODAY = date(2026, 9, 30)
CO, T = "co:axt", "AXTI"
READ = "sr_" + "a" * 16
MEMO = "thesis/axti_memo.md"
SELF_COND = "若 JX 在 2026-12-31 前宣布新產能投產則供給缺口消失，量的賭注不成立"
READ_COND = "讀圖反證：供給側出現第四家（現況 3 家）——中國廠商擴產最可能"
MEMO_ITEMS = ("客戶在 10-K 揭露 InP 基板改由第二家供應商供貨超過三成",
              "AXT 的中國出口許可連續兩季被拒，出貨量年減超過四成")


def _slots() -> dict:
    ev = ["graph://x"]
    return {"demand": {"text": "客戶預付產能。", "evidence_refs": ev},
            "position": {"text": "坐在基板層，年增 {in_numbers_latest}（{in_numbers_as_of}）。", "evidence_refs": ev},
            "bottleneck": {"text": "三家供應。", "evidence_refs": ev},
            "priced_in": {"text": "自家三年 {own_history_basis} 第 {own_history_pctile} 百分位。", "evidence_refs": ev},
            "our_bet": {"text": "賭層的量。", "evidence_refs": ev},
            "what_must_be_true": {"text": "擴產沒提前。", "evidence_refs": ev},
            "when": {"text": "下次財報。", "evidence_refs": ev}}


def _brief(*, disproof=(), rides=True):
    rec = brief_record(company_id=CO, ticker=T, slots=_slots(), record_version=RECORD_VERSION_V2,
                       rides=[{"node": "mat:inp_substrate", "unit": "layer", "reading_id": READ}] if rides else [],
                       disproof=list(disproof), answers={"priced_in": "no", "in_numbers": "yes"},
                       candidate_state={"state": "priced_wait", "watch_id": "ew_wait", "reason": "等回落"},
                       created_at=datetime(2026, 9, 29, 3, tzinfo=timezone.utc))
    return parse_brief_record(rec)


SELF = {"condition": SELF_COND, "check_frequency": "每季", "action_48h": "重寫", "entities": [CO],
        "expires": "2027-03-01", "source": "self", "link_source_ref": None}
LINK = {"condition": "（敘事的措辭）供給側出現第四家就重寫", "check_frequency": "每季", "action_48h": "重讀",
        "entities": [CO], "expires": "2027-03-01", "source": READ, "link_source_ref": f"reading:{READ}#1"}


def _sem(wid, source_ref, condition, status="active", **kw):
    return {"watch_id": wid, "kind": ew.SEMANTIC_KIND, "status": status, "source_ref": source_ref,
            "condition": condition, "expires": "2027-01-01", "entities": [CO], **kw}


def _memo_root(tmp_path: Path) -> Path:
    (tmp_path / "thesis").mkdir()
    (tmp_path / MEMO).write_text("# AXTI\n\n## 推翻條件\n\n" + "".join(f"- {t}\n" for t in MEMO_ITEMS) + "\n## 其他\n",
                                 encoding="utf-8")
    return tmp_path


LIFECYCLE = {"axti": {"ticker": T, "memo": MEMO, "status": "active"}}
READING_ROWS = {("mat:inp_substrate", "layer"): {
    "node": "mat:inp_substrate", "unit": "layer", "reading_id": READ, "status": "current", "kind": "volume",
    "disproof": [{"condition": READ_COND, "check_frequency": "每季", "action_48h": "重讀"}]}}


# ---------------------------------------------------------------------------
# 1. downside：每條反證 → watch（歸屬與落格與心跳段 2 同一套）
# ---------------------------------------------------------------------------

def test_downside_links_every_disproof_to_its_watch_and_prints_unwatched(tmp_path) -> None:
    brief = _brief(disproof=[SELF, LINK])
    watches = [
        _sem("ew_memo", f"thesis:{MEMO}#2", MEMO_ITEMS[0]),                  # 位置變了（#2 對到第 1 條）——以文字認
        _sem("ew_self", f"brief:{brief.brief_id}#1", SELF_COND, status="fired"),
        _sem("ew_read", f"reading:{READ}#1", READ_COND),
        _sem("ew_other", "thesis:thesis/other.md#1", "別家的條件（不歸屬本檔）" * 3),
    ]
    out = downside_rows(CO, T, records=[brief], current_brief=brief, watches=watches, lifecycle=LIFECYCLE,
                        reading_rows=READING_ROWS, root=_memo_root(tmp_path),
                        judgment_conditions=[{"condition": "舊判讀的推翻條件", "check_frequency": "每季",
                                              "action": "重看"}])
    rows = {(r["source"], r["condition"]): r for r in out["rows"]}
    assert rows[("thesis", MEMO_ITEMS[0])]["watch_id"] == "ew_memo" and rows[("thesis", MEMO_ITEMS[0])]["state"] == "active"
    assert rows[("thesis", MEMO_ITEMS[1])]["watch_id"] is None and rows[("thesis", MEMO_ITEMS[1])]["state_label"] == "未盯"
    assert rows[("brief", SELF_COND)]["watch_id"] == "ew_self" and rows[("brief", SELF_COND)]["state_label"] == "醒來待判"
    link = rows[("link", LINK["condition"])]
    assert link["watch_id"] == "ew_read" and link["source_ref"] == f"reading:{READ}#1", "連結以完整來源鍵對，不以措辭"
    # 騎的讀圖那一條也是 ew_read：同一筆 watch 只印一列，後到的來源併進 also（不多算一次在盯）
    assert ("reading", READ_COND) not in rows
    assert link["also"] == [{"source": "reading", "source_label": "騎的讀圖的反證", "source_ref": f"reading:{READ}",
                             "condition": READ_COND}]
    judged = rows[("judgment", "舊判讀的推翻條件")]
    assert judged["watch_id"] is None and judged["state"] == "unwatched" and "不涵蓋" in judged["source_label"]
    assert all(r["watch_id"] != "ew_other" for r in out["rows"]), "歸屬以來源判：別家 memo 的 watch 不算本檔"
    assert out["counts"]["unwatched"] == 2 and out["counts"]["fired"] == 1 and out["counts"]["active"] == 2
    assert len([r for r in out["rows"] if r["watch_id"]]) == len({r["watch_id"] for r in out["rows"] if r["watch_id"]})
    assert set(out["counts"]) == set(DOWNSIDE_STATES) and out["notes"] == []


def test_downside_state_uses_the_same_priority_as_the_heartbeat_counter(tmp_path) -> None:
    """同一個條件有多筆 watch：觸及待處置 ＞ 到期待複查 ＞ 在盯（`watch_category`＋`_PRIORITY`，與反證計數同一套）。"""
    touched = _sem("ew_t", f"thesis:{MEMO}#1", MEMO_ITEMS[0], status="consumed", judgment={"touches": "yes"})
    expired = _sem("ew_e", f"thesis:{MEMO}#1", MEMO_ITEMS[0], status="expired")
    assert watch_category(touched) == "touched" and watch_category(expired) == "expired"
    out = downside_rows(CO, T, records=[], current_brief=None, watches=[expired, touched], lifecycle=LIFECYCLE,
                        reading_rows={}, root=_memo_root(tmp_path))
    first = next(r for r in out["rows"] if r["condition"] == MEMO_ITEMS[0])
    assert first["watch_id"] == "ew_t" and first["state_label"] == "觸及待處置"


def test_downside_shows_attributed_watches_whose_condition_left_the_source(tmp_path) -> None:
    """memo 改寫後還沒對帳的舊條件：watch 還在處理中、條件已不在現行 memo——也要現形（不是消失）。"""
    stale = _sem("ew_old", f"thesis:{MEMO}#3", "這條已從 memo 刪掉但 watch 還在盯的舊條件，要現形")
    out = downside_rows(CO, T, records=[], current_brief=None, watches=[stale], lifecycle=LIFECYCLE,
                        reading_rows={}, root=_memo_root(tmp_path))
    only = [r for r in out["rows"] if r["source"] == "watch_only"]
    assert [r["watch_id"] for r in only] == ["ew_old"] and only[0]["state"] == "active"


def test_downside_says_what_it_could_not_read_instead_of_printing_fewer_rows(tmp_path) -> None:
    brief = _brief(disproof=[SELF])
    unreadable = downside_rows(CO, T, records=[brief], current_brief=brief, watches=[], lifecycle=None,
                               reading_rows={}, root=tmp_path)
    assert any("lifecycle 讀不到" in n for n in unreadable["notes"]), "thesis 那一半沒列要說出來（不是沒有）"
    assert any("這次沒有那一格的讀圖列" in n and "先修讀取" in n for n in unreadable["notes"]), \
        "騎的讀圖這次沒有列（讀不到）≠ 已換版——下一步不同（L12，與 derive_row 對稱）"
    # rows 空、來源讀不到：面板要依產生端宣告 upstream_unavailable，不是「還沒有反證」
    assert unreadable["empty"]["kind"] == "upstream_unavailable" and unreadable["unread"]
    moved = downside_rows(CO, T, records=[brief], current_brief=brief, watches=[], lifecycle={},
                          reading_rows={("mat:inp_substrate", "layer"): {**READING_ROWS[("mat:inp_substrate", "layer")],
                                                                         "reading_id": "sr_" + "b" * 16}},
                          root=tmp_path)
    assert any("已換版" in n and "重寫敘事" in n for n in moved["notes"]) and moved["unread"] == []
    missing_memo = downside_rows(CO, T, records=[], current_brief=None, watches=[], lifecycle=LIFECYCLE,
                                 reading_rows={}, root=tmp_path)
    assert any("讀不到" in n and MEMO in n for n in missing_memo["notes"])
    nobody = downside_rows(None, T, records=[], current_brief=None, watches=[_sem("ew_x", f"thesis:{MEMO}#1", "x" * 30)],
                           lifecycle={}, reading_rows={}, root=tmp_path)
    assert nobody["rows"] == [], "沒有 co: id 就沒有歸屬（INV-1）——不拿 ticker 猜"


# ---------------------------------------------------------------------------
# 2. 個股頁與候選板同一個推導
# ---------------------------------------------------------------------------

def _context(**over):
    ctx = {"today": TODAY, "watches": [], "lifecycle": {}, "reading_rows": READING_ROWS,
           "held": {"status": "ok", "reason": None, "by_company": {}, "unresolved": [], "beta_excluded": 0,
                    "zero_shares": 0},
           "edges": {T: {"state": "edge", "label": "邊緣", "reasons": [], "market_cap_usd": 1e9, "analyst_count": 3}}}
    ctx.update(over)
    return ctx


def _tq():
    return {"will_it_die": [{"key": "wipeout_cash_runway", "value": "amber", "absence_kind": None},
                            {"key": "wipeout_going_concern", "value": None, "absence_kind": "not_yet_recorded"}],
            "priced_in": [{"key": "own_history_pctile", "value": 88.5, "absence_kind": None}],
            "in_numbers": [{"key": "in_numbers_series", "value": [1], "absence_kind": None}]}


def test_page_input_is_the_board_derivation_and_carries_no_position_field_names(monkeypatch) -> None:
    import alpha.providers.briefs as briefs_mod
    from alpha.providers import candidates as cand

    brief = _brief()
    monkeypatch.setattr(briefs_mod, "read_brief_records", lambda ticker: ([brief], []))
    held = {"status": "ok", "reason": None, "by_company": {CO: {"sheet_ticker": T, "source": "registry"}},
            "unresolved": [], "beta_excluded": 0, "zero_shares": 0}
    ctx = _context(held=held)
    page = cand.page_input(ctx, T, CO, three_questions=_tq())
    board = cand.derive_row(T, CO, records=[brief], today=TODAY, reading_rows=ctx["reading_rows"],
                            watches=[], lifecycle={}, edge=ctx["edges"][T], three_questions=_tq(), held=held)
    assert page["row"]["derived"] == board["derived"] == "held" and page["row"]["derived_label"] == "已持有"
    assert {k: v for k, v in page["row"].items() if k not in ("sheet_verified", "derived_label")} == \
        {k: v for k, v in board.items() if k not in ("held_source", "holdings_verified")}
    assert page["three_words"] == board["three_words"] == {"will_it_die": "黃（灰 1）", "priced_in": "否",
                                                          "in_numbers": "是"}

    def keys(node):
        if isinstance(node, dict):
            for key, value in node.items():
                yield key
                yield from keys(value)
        elif isinstance(node, list):
            for item in node:
                yield from keys(item)

    banned = set(FORBIDDEN_POSITION_TOKENS) | {"held", "holdings"}
    assert not [k for k in keys(page) if set(str(k).lower().split("_")) & banned]


def test_page_input_prints_three_words_even_when_the_company_is_not_on_the_board(monkeypatch) -> None:
    import alpha.providers.briefs as briefs_mod
    from alpha.providers import candidates as cand

    monkeypatch.setattr(briefs_mod, "read_brief_records", lambda ticker: ([], []))
    page = cand.page_input(_context(), T, CO, three_questions=_tq())
    assert page["row"] is None
    assert page["three_words"] == {"will_it_die": "黃（灰 1）", "priced_in": "未答", "in_numbers": "未答"}
    unread = cand.page_input(_context(), T, CO, three_questions=None, three_questions_note="三題取數失敗：locked")
    assert unread["three_words"]["will_it_die"] == "未讀到（三題取數失敗：locked）"


def test_materialize_refuses_candidate_state_in_as_of_view_and_says_unavailable_when_loading_fails(monkeypatch) -> None:
    from alpha.providers import candidates as cand
    from webapp.materialize import candidate_context, candidate_input_for

    assert candidate_context(["AXTI"], as_of=date(2026, 8, 1))["absence"]["kind"] == "point_in_time_unavailable"

    def boom(*a, **k):
        raise RuntimeError("neo4j down")

    monkeypatch.setattr(cand, "candidate_context", boom)
    down = candidate_context(["AXTI"])
    assert down["absence"]["kind"] == "upstream_unavailable" and "不是「不上板」" in down["absence"]["reason"]
    assert candidate_input_for(down, _bare_view()) == {"absence": down["absence"]}


def test_candidate_input_hands_the_view_three_questions_to_the_same_derivation(monkeypatch) -> None:
    from alpha.providers import candidates as cand
    from webapp.materialize import candidate_input_for

    seen = {}

    def spy(ctx, ticker, company_id, *, three_questions, three_questions_note, judgment_conditions):
        seen.update(tq=three_questions, note=three_questions_note, judgments=judgment_conditions)
        return {"row": None}

    monkeypatch.setattr(cand, "page_input", spy)
    view = _full_view(three_questions=_tq())
    candidate_input_for(_context(), view)
    assert seen["tq"] == {q: list(getattr(view.three_questions, q)) for q in ("will_it_die", "priced_in", "in_numbers")}
    assert seen["note"] is None
    assert [j["condition"] for j in seen["judgments"]] == [c.condition for c in view.falsification.conditions]
    candidate_input_for(_context(), _full_view())                         # 三題取不到：交 None＋理由，不交空 dict
    assert seen["tq"] is None and seen["note"]


# ---------------------------------------------------------------------------
# 3. 三個新面板（compose）
# ---------------------------------------------------------------------------

def test_candidate_panel_copies_the_row_and_three_words_and_never_affects_readiness() -> None:
    row = {"ticker": T, "derived": "priced_wait", "derived_label": "已定價等回落", "declared": "priced_wait",
           "rewrite": [], "preconditions": [], "stall_days": 1, "note": None}
    words = {"will_it_die": "黃（灰 1）", "priced_in": "否", "in_numbers": "是"}
    analyst = build_analyst_view(_bare_view(), candidate={"row": row, "three_words": words, "today": "2026-09-30",
                                                          "sheet": {"status": "ok"}, "downside": {"rows": []}})
    panel = analyst.candidate
    by_key = {line.key: line.datum for line in panel.lines}
    assert panel.status == "available" and by_key["candidate:state"].value["derived_label"] == "已定價等回落"
    assert [by_key[f"candidate:{k}"].value for k in ("will_it_die", "priced_in", "in_numbers")] == ["黃（灰 1）", "否", "是"]
    assert "candidate" not in {b.panel for b in analyst.readiness.blocker_details}
    off = build_analyst_view(_bare_view(), candidate={"row": None, "three_words": {**words, "priced_in": "未答"},
                                                      "downside": {"rows": []}}).candidate
    assert off.status == "missing" and off.absence_kind == "not_yet_recorded"
    assert {line.key: line.datum.value for line in off.lines}["candidate:priced_in"] == "未答", "不上板也印三個字"


def test_candidate_and_downside_panels_keep_the_producer_declared_absence() -> None:
    for given, kind in ((None, "upstream_unavailable"),
                        ({"absence": {"kind": "point_in_time_unavailable", "reason": "as-of"}}, "point_in_time_unavailable")):
        analyst = build_analyst_view(_bare_view(), candidate=given)
        assert analyst.candidate.absence_kind == kind and analyst.downside.absence_kind == kind
        assert analyst.candidate.lines == () and analyst.downside.lines == ()


def test_downside_panel_prints_each_row_and_an_empty_list_is_not_yet_recorded() -> None:
    rows = [{"source": "brief", "source_label": "敘事自己登記的反證", "condition": SELF_COND, "watch_id": "ew_1",
             "state": "active", "state_label": "在盯"},
            {"source": "judgment", "source_label": "舊判讀", "condition": "x", "watch_id": None, "state": "unwatched",
             "state_label": "未盯"}]
    panel = build_analyst_view(_bare_view(), candidate={"row": None, "three_words": {},
                                                        "downside": {"rows": rows, "notes": ["n1"],
                                                                     "counts": {"unwatched": 1}}}).downside
    assert [line.datum.value["watch_id"] for line in panel.lines] == ["ew_1", None]
    assert all(line.role == "downside" for line in panel.lines) and panel.notes[0] == "n1"
    empty = build_analyst_view(_bare_view(), candidate={"row": None, "downside": {"rows": []}}).downside
    assert empty.status == "missing" and empty.absence_kind == "not_yet_recorded"


def _raw_tq():
    return {"filer_class": "domestic_quarterly",
            "will_it_die": [{"key": "wipeout_debt", "label": "會死嗎：負債", "value": "green", "source": "yfinance.info",
                             "as_of": None, "basis": None, "rule": "現金 ≥ 總債 → 綠", "absence_kind": None,
                             "reason": None, "detail": {"total_debt": 1.0}}],
            "priced_in": [{"key": "own_history_pctile", "label": "已定價①", "value": 88.5, "source": "engine_c",
                           "as_of": "2026-09-28", "basis": "P/S", "rule": "百分位", "absence_kind": None,
                           "reason": None, "detail": {}},
                          {"key": "cohort_median", "label": "已定價②", "value": None, "source": None, "as_of": None,
                           "basis": None, "rule": "中位數", "absence_kind": "not_yet_recorded",
                           "reason": "主題等權組未定義", "detail": {}},
                          {"key": "rel_return_30d", "label": "已定價③", "value": None, "source": None, "as_of": None,
                           "basis": "P/S", "rule": "相對", "absence_kind": "insufficient_evidence",
                           "reason": "成員不足", "detail": {}}],
            "in_numbers": []}


def test_three_questions_panel_is_the_read_model_rows_with_source_as_of_basis_and_rule() -> None:
    view = _full_view(three_questions=_raw_tq())
    panel = build_analyst_view(view).three_questions
    assert [line.datum for line in panel.lines] == list(view.three_questions.lines)
    assert all(a.datum is b for a, b in zip(panel.lines, view.three_questions.lines)), "同一個物件，不是本層造的"
    by_key = {line.datum.dependencies["row_key"]: line.datum for line in panel.lines}
    pct = by_key["own_history_pctile"]
    assert pct.value == 88.5 and pct.as_of == date(2026, 9, 28) and pct.dependencies["basis"] == "P/S"
    assert pct.dependencies["source"] == "engine_c" and pct.method == "百分位"
    assert by_key["cohort_median"].absence_kind == "not_yet_recorded" and by_key["cohort_median"].value is None
    assert by_key["rel_return_30d"].status == "insufficient_evidence" and by_key["rel_return_30d"].reason == "成員不足"
    assert panel.optional is True and panel.context["filer_class"] == "domestic_quarterly"
    unread = build_analyst_view(_full_view()).three_questions
    assert unread.status == "missing" and unread.absence_kind == "upstream_unavailable" and unread.lines == ()


def test_bet_panel_is_three_pieces_of_text_and_no_price() -> None:
    brief = _brief()
    from tests.test_alpha_investment_view import _view

    # 敘事寫於 2026-09-29：視角的「今天」要在它之後（`_full_view` 固定 2026-09-07，那時這份敘事還不存在）。
    view = _view(today=TODAY, brief_records=[brief], narrative_context={"node_names": {"mat:inp_substrate": "InP 基板"}})
    panel = build_analyst_view(view).bet
    by_key = {line.key: line.datum for line in panel.lines}
    assert list(by_key) == ["our_bet", "rides", "what_must_be_true"]
    assert by_key["rides"] is view.investor_brief.rides
    assert by_key["rides"].value == [{"node": "mat:inp_substrate", "node_name": "InP 基板", "unit": "layer",
                                      "unit_label": "層", "reading_id": READ}]
    assert by_key["what_must_be_true"].value == "擴產沒提前。" and by_key["our_bet"].value == "賭層的量。"
    text = json.dumps(build_analyst_view(view).to_dict()["bet"], ensure_ascii=False)
    assert "price" not in text and "目標價" not in text.replace("沒有價格", "")
    no_brief = build_analyst_view(_full_view()).bet
    rides = {line.key: line.datum for line in no_brief.lines}["rides"]
    assert rides.absence_kind == "not_yet_recorded" and rides.value is None


# ---------------------------------------------------------------------------
# 4. readiness：讀圖升核心，兩個方向
# ---------------------------------------------------------------------------

def _reading(status):
    return {"node": "mat:inp_substrate", "unit": "layer", "unit_label": "層", "kind": "volume",
            "kind_label": "B：量的賭注", "status": status, "status_label": status, "reason": None,
            "reading_id": READ, "read_on": "2026-09-25", "expires": "2026-12-24", "reading": "r", "needs_reread": False}


def test_a_stale_reading_turns_readiness_into_flags_and_nothing_else_does() -> None:
    analyst = build_analyst_view(_full_view(), readings={"seats": ["mat:inp_substrate"], "readings": [_reading("stale")]})
    assert analyst.readings.status == "review_required" and analyst.readings.optional is False
    panels = {p.key: p for p in analyst.panels}
    others = {k: (replace(p, status="available") if k != "readings" else p) for k, p in panels.items()}
    readiness = _readiness(others)
    assert readiness.state == READY_WITH_FLAGS and [f.panel for f in readiness.flag_details] == ["readings"]
    current = build_analyst_view(_full_view(), readings={"seats": [], "readings": [_reading("current")]})
    ready = _readiness({k: (replace(p, status="available") if k != "readings" else p)
                        for k, p in {p.key: p for p in current.panels}.items()})
    assert ready.state == "ready"


def test_refresh_review_required_alone_does_not_touch_the_readings_panel() -> None:
    """`refresh=review_required` 今天全是退役估值鏈殘留——讀圖面板的狀態只由讀圖對圖決定（plan §8 第 3 點）。"""
    view = _full_view()
    view = replace(view, refresh_status=replace(view.refresh_status, overall="review_required"))
    analyst = build_analyst_view(view, readings={"seats": [], "readings": [_reading("current")]})
    assert analyst.refresh.overall == "review_required"
    assert analyst.readings.status == "available"
    assert "readings" not in {f.panel for f in analyst.readiness.flag_details}


def test_graph_change_on_the_read_node_makes_the_reading_stale_end_to_end(tmp_path, monkeypatch) -> None:
    """讀圖節點上的邊變動 → 讀圖對圖 stale → 讀圖面板 review_required → readiness 帶 flag（接回 Phase 0 #16）。"""
    import query.structure as qs
    from alpha.providers import structure_readings as sr
    from alpha.providers.structure_readings import seat_readings_context, seat_readings_for
    from tests.test_structure_reading_v3 import SIVERS, SOCKET, TODAY as READ_DAY, _canonical, _quotes, _row, _v3

    monkeypatch.setattr(sr, "STRUCTURE_READING_DIR", tmp_path / "ledger")
    base = [_row(SIVERS, "supplies_to", SOCKET), _row("prod:teraphy_chiplet", "depends_on", SOCKET)]
    # 快照＝寫讀圖當下的圖（同一批邊），所以一開始是現行；之後供給側多一家＝圖變了。
    sr.append_reading_record(_v3(SOCKET, structure=qs.build_structure(SOCKET, _canonical(base)).as_dict()),
                             quotes=_quotes(SOCKET))
    monkeypatch.setattr(qs, "_load_edges", lambda: _canonical(base))
    before = seat_readings_for(seat_readings_context(today=READ_DAY), SIVERS)
    assert before["readings"][0]["status"] == "current"
    assert build_analyst_view(_full_view(), readings=before).readings.status == "available"
    monkeypatch.setattr(qs, "_load_edges", lambda: _canonical(base + [_row("co:new_maker", "supplies_to", SOCKET)]))
    after = seat_readings_for(seat_readings_context(today=READ_DAY), SIVERS)
    assert after["readings"][0]["status"] == "stale"
    analyst = build_analyst_view(_full_view(), readings=after)
    assert analyst.readings.status == "review_required"
    assert "readings" in {f.panel for f in analyst.readiness.flag_details}


def test_no_reading_is_a_not_yet_recorded_blocker_never_settled() -> None:
    analyst = build_analyst_view(_full_view(), readings={"seats": ["mat:x"], "readings": []})
    blocker = next(b for b in analyst.readiness.blocker_details if b.panel == "readings")
    assert blocker.absence_kind == "not_yet_recorded" and blocker.settled is False
    assert analyst.readiness.state == BLOCKED


# ---------------------------------------------------------------------------
# 5. argument 鏈段的需求端：騎的讀圖，不是 sub≥4 需求錨
# ---------------------------------------------------------------------------

def _ctx_with(rows, seats=("mat:inp_substrate",)):
    return {"seats": {CO: list(seats)}, "by_node": {"mat:inp_substrate": rows}}


def test_chain_readings_follow_the_rides_and_fall_back_to_the_seats() -> None:
    from briefing.alpha_view.sources import _chain_readings

    row = {**_reading("current"), "demand_customers": ["co:coherent"]}
    rides = _chain_readings(_ctx_with([row]), CO, _brief())
    assert rides["basis"] == "rides" and rides["rows"] == [row] and rides["gone"] == []
    moved = _chain_readings(_ctx_with([{**row, "reading_id": "sr_" + "b" * 16}]), CO, _brief())
    assert moved["rows"] == [] and moved["gone"][0]["current"] == "sr_" + "b" * 16
    seats = _chain_readings(_ctx_with([row]), CO, None)
    assert seats["basis"] == "seats" and seats["rows"] == [row]
    assert _chain_readings(None, CO, None)["absence"]["kind"] == "upstream_unavailable"
    assert _chain_readings(_ctx_with([row]), None, None)["absence"]["kind"] == "upstream_unavailable"


def test_argument_chain_reads_the_demand_side_and_carries_where_it_came_from() -> None:
    demand = {"basis": "rides", "gone": [], "seats": ["mat:inp_substrate"],
              "rows": [{**_reading("current"), "demand_customers": ["co:coherent"]}]}
    view = _full_view(chain_readings=demand,
                      narrative_context={"node_names": {"co:coherent": "Coherent", "mat:inp_substrate": "InP 基板"}})
    chain = next(p for p in view.argument.paragraphs if p.key == "argument:chain")
    assert chain.value.startswith("騎的層「InP 基板」讀成「B：量的賭注」（現行）；需求端是「Coherent」。")
    assert chain.dependencies["demand"]["readings"][0]["reading_id"] == READ
    assert chain.dependencies["demand"]["basis"] == "rides"
    unread = next(p for p in _full_view().argument.paragraphs if p.key == "argument:chain")
    assert "這次沒讀到讀圖" in unread.value and unread.dependencies["demand"]["absence"]["kind"] == "upstream_unavailable"


def test_the_chain_no_longer_reads_the_bottleneck_demand_anchor() -> None:
    """`get_bottlenecks` 不退役（Q1 與 PointInTime 探針仍用它）；只是鏈段不再經 `demand_anchor` 取錨（plan §8 第 4 點）。"""
    source = (Path(__file__).resolve().parents[1] / "briefing" / "alpha_view" / "builder.py").read_text(encoding="utf-8")
    body = source.split("def _argument_section", 1)[1].split("\ndef ", 1)[0]
    assert "scarcity_inputs" not in body.split("# ⚠ 2026-09-30", 1)[1].split("_para(\"chain\"", 1)[0].replace(
        "`structural.scarcity_inputs`", "")
    sources = (Path(__file__).resolve().parents[1] / "briefing" / "alpha_view" / "sources.py").read_text(encoding="utf-8")
    assert "structural.demand_anchor" not in sources


def test_the_stock_page_three_questions_get_the_declared_history_not_comparable(monkeypatch, tmp_path) -> None:
    """L17 對稱面：候選板與寫入端都把敘事宣告的 history_not_comparable 交給三題，個股頁也要。"""
    import alpha.providers.three_questions as tqp
    from alpha.testing import FakeGraphResearchProvider
    from briefing.alpha_view import sources
    from tests.test_alpha_investment_view import COMPANY, _FakeFundamentals

    rec = brief_record(company_id=COMPANY, ticker="COHR", slots=_slots(), record_version=RECORD_VERSION_V2, rides=[],
                       answers={"priced_in": "unmeasurable", "in_numbers": "yes"},
                       candidate_state={"state": "pass", "watch_id": None, "reason": "非邊緣"},
                       history_not_comparable={"since": "2026-01-01", "reason": "剛轉型", "source": "self"},
                       created_at=datetime(2026, 9, 28, tzinfo=timezone.utc))
    monkeypatch.setattr(sources.brief_ledger, "read_brief_records", lambda ticker: ([parse_brief_record(rec)], []))
    monkeypatch.setattr(sources, "DECISION_DB", tmp_path / "nope.db")
    monkeypatch.setattr(sources, "LIFECYCLE_PATH", tmp_path / "nope.json")
    monkeypatch.setattr(sources, "JUDGMENT_DIR", tmp_path / "judgments")
    monkeypatch.setattr(sources, "LEGACY_JUDGMENT_DIR", tmp_path / "legacy")
    import engine_c.checklist as checklist_mod

    monkeypatch.setattr(checklist_mod, "get_checklist", lambda ticker: {"engine_c_available": False, "note": "t"})
    monkeypatch.setattr(checklist_mod, "get_wipeout_inputs", lambda ticker: {"status": "unavailable", "reason": "t"})
    seen = {}

    def spy(ticker, *, today, wipeout, wipeout_reason=None, history_not_comparable=None, conn=None):
        seen["hnc"] = history_not_comparable
        raise RuntimeError("stop here")

    monkeypatch.setattr(tqp, "three_questions_for", spy)
    sources.fetch_alpha_investment_view("COHR", today=date(2026, 9, 30), detect_refresh=False,
                                        graph_provider=FakeGraphResearchProvider(company_id=COMPANY),
                                        fundamentals_provider=_FakeFundamentals())
    assert seen["hnc"] == {"since": "2026-01-01", "reason": "剛轉型", "source": "self"}



# ---------------------------------------------------------------------------
# 6. R1 覆核補的（2026-09-30）：as-of、接線、產生端的缺席分型、呈現
# ---------------------------------------------------------------------------

from tests.test_candidates import board_env  # noqa: E402,F401 — 共用夾具（只在本檔的 alias 測試用）


def test_as_of_view_refuses_the_reading_context_instead_of_using_todays_graph() -> None:
    """INV-6：坐在哪一層、那一層變了沒都只有現在的圖——as-of 視角明確拒絕，鏈段與（核心）讀圖面板都照抄。"""
    from alpha.providers.structure_readings import seat_readings_context, seat_readings_for
    from briefing.alpha_view.sources import _chain_readings

    ctx = seat_readings_context(as_of=date(2026, 9, 26))
    assert ctx["absence"]["kind"] == "point_in_time_unavailable"
    chain = _chain_readings(ctx, CO, _brief())
    assert chain["absence"]["kind"] == "point_in_time_unavailable"
    panel = build_analyst_view(_full_view(), readings=seat_readings_for(ctx, CO)).readings
    assert panel.status == "missing" and panel.absence_kind == "point_in_time_unavailable"


def test_as_of_three_questions_say_point_in_time_not_upstream() -> None:
    panel = build_analyst_view(_full_view(three_questions_absence_kind="point_in_time_unavailable")).three_questions
    assert panel.absence_kind == "point_in_time_unavailable"


def test_no_seat_on_the_graph_is_not_the_same_as_not_read_yet() -> None:
    """L12：「圖上沒有它坐的層」（先補圖）≠「坐了但還沒讀」（去寫讀圖）——產生端宣告，面板照抄。"""
    from alpha.providers.structure_readings import seat_readings_for

    ctx = {"seats": {CO: ["mat:inp_substrate"]}, "by_node": {}}
    unread = build_analyst_view(_full_view(), readings=seat_readings_for(ctx, CO)).readings
    assert unread.absence_kind == "not_yet_recorded" and "mat:inp_substrate" in unread.reason
    seatless = build_analyst_view(_full_view(), readings=seat_readings_for(ctx, "co:nobody")).readings
    assert seatless.absence_kind == "upstream_unavailable" and "圖上沒有它供貨或開發的層" in seatless.reason


def test_sheet_unreadable_means_held_is_suspended_not_not_held(monkeypatch) -> None:
    import alpha.providers.briefs as briefs_mod
    from alpha.providers import candidates as cand

    monkeypatch.setattr(briefs_mod, "read_brief_records", lambda ticker: ([], []))
    down = _context(held={"status": "upstream_unavailable", "reason": "Sheet 讀不到", "by_company": {}})
    page = cand.page_input(down, T, CO, three_questions=_tq())
    assert page["row"] is None and page["row_absence"]["kind"] == "upstream_unavailable"
    panel = build_analyst_view(_bare_view(), candidate=page).candidate
    assert panel.absence_kind == "upstream_unavailable" and "也沒有持有" not in (panel.reason or "")
    assert {line.key: line.datum.value for line in panel.lines}["candidate:priced_in"] == "未答", "三個字照印"
    ok = cand.page_input(_context(), T, CO, three_questions=_tq())
    assert ok["row_absence"]["kind"] == "not_yet_recorded"


def test_legacy_narrative_gets_the_board_label_not_a_dash(monkeypatch) -> None:
    import alpha.providers.briefs as briefs_mod
    from alpha.providers import candidates as cand
    from tests.test_candidates import _v1

    monkeypatch.setattr(briefs_mod, "read_brief_records", lambda ticker: ([_v1()], []))
    page = cand.page_input(_context(), T, CO, three_questions=_tq())
    assert page["row"]["side"] == "legacy" and page["row"]["derived_label"] == "舊版（缺候選狀態）"


def test_page_input_hands_every_disproof_source_to_downside(tmp_path, monkeypatch) -> None:
    """page_input → downside_rows 整段：舊判讀的 action 鍵、敘事自己的反證 watch、thesis 列的 L7 兩欄都要到（R1 變異存活處）。"""
    import alpha.providers.briefs as briefs_mod
    import engine_b.disproof as disproof
    from alpha.providers import candidates as cand

    brief = _brief(disproof=[SELF])
    monkeypatch.setattr(briefs_mod, "read_brief_records", lambda ticker: ([brief], []))
    monkeypatch.setattr(disproof, "ROOT", _memo_root(tmp_path))
    watches = [_sem("ew_self", f"brief:{brief.brief_id}#1", SELF_COND),
               _sem("ew_memo", f"thesis:{MEMO}#1", MEMO_ITEMS[0], check_frequency="每季", action_48h="重讀 memo")]
    page = cand.page_input(_context(watches=watches, lifecycle=LIFECYCLE), T, CO, three_questions=_tq(),
                           judgment_conditions=[{"condition": "舊判讀條件", "check_frequency": "每季", "action": "重看"}])
    rows = {r["source"]: r for r in page["downside"]["rows"]}
    assert rows["judgment"]["action_48h"] == "重看" and rows["judgment"]["state"] == "unwatched"
    assert rows["brief"]["watch_id"] == "ew_self"
    thesis = next(r for r in page["downside"]["rows"] if r["watch_id"] == "ew_memo")
    assert thesis["source"] == "thesis", "要走 memo 條目那條路（不是 watch_only）——否則 L7 兩欄本來就從 watch 來"
    assert thesis["check_frequency"] == "每季" and thesis["action_48h"] == "重讀 memo", "L7 兩欄照抄 watch"


def test_downside_priority_does_not_depend_on_registry_order(tmp_path) -> None:
    root = _memo_root(tmp_path)
    touched = _sem("ew_t", f"thesis:{MEMO}#1", MEMO_ITEMS[0], status="consumed", judgment={"touches": "yes"})
    active = _sem("ew_a", f"thesis:{MEMO}#1", MEMO_ITEMS[0])
    for order in ([touched, active], [active, touched]):
        out = downside_rows(CO, T, records=[], current_brief=None, watches=order, lifecycle=LIFECYCLE,
                            reading_rows={}, root=root)
        assert next(r for r in out["rows"] if r["condition"] == MEMO_ITEMS[0])["watch_id"] == "ew_t"
    brief = _brief(disproof=[LINK])
    link_touched = _sem("ew_lt", f"reading:{READ}#1", READ_COND, status="consumed", judgment={"touches": "yes"})
    link_active = _sem("ew_la", f"reading:{READ}#1", READ_COND)
    for order in ([link_touched, link_active], [link_active, link_touched]):
        out = downside_rows(CO, T, records=[brief], current_brief=brief, watches=order, lifecycle={},
                            reading_rows={}, root=root)
        assert next(r for r in out["rows"] if r["source"] == "link")["watch_id"] == "ew_lt", "exact 路徑也照優先序"


def test_unparsable_memo_is_declared_not_silently_dropped(tmp_path) -> None:
    (tmp_path / "thesis").mkdir()
    (tmp_path / MEMO).write_text("# AXTI\n\n沒有推翻那一節\n", encoding="utf-8")
    out = downside_rows(CO, T, records=[], current_brief=None, watches=[], lifecycle=LIFECYCLE, reading_rows={},
                        root=tmp_path)
    assert out["rows"] == [] and any("解析不到" in n for n in out["notes"])
    assert out["empty"]["kind"] == "upstream_unavailable"
    panel = build_analyst_view(_bare_view(), candidate={"row": None, "downside": out}).downside
    assert panel.absence_kind == "upstream_unavailable" and "解析不到" in panel.reason


def test_chain_readings_match_the_ride_unit_when_a_node_has_both() -> None:
    from briefing.alpha_view.sources import _chain_readings

    layer = {**_reading("current"), "reading_id": "sr_" + "c" * 16, "unit": "layer"}
    socket = {**_reading("current"), "reading_id": READ, "unit": "socket", "unit_label": "插槽"}
    rec = brief_record(company_id=CO, ticker=T, slots=_slots(), record_version=RECORD_VERSION_V2,
                       rides=[{"node": "mat:inp_substrate", "unit": "socket", "reading_id": READ}],
                       answers={"priced_in": "no", "in_numbers": "yes"},
                       candidate_state={"state": "pass", "watch_id": None, "reason": "x"},
                       created_at=datetime(2026, 9, 29, 3, tzinfo=timezone.utc))
    out = _chain_readings(_ctx_with([layer, socket]), CO, parse_brief_record(rec))
    assert out["rows"] == [socket] and out["gone"] == []


def test_demand_customers_come_from_the_real_reading_path(tmp_path, monkeypatch) -> None:
    import query.structure as qs
    from alpha.providers import structure_readings as sr
    from alpha.providers.structure_readings import seat_readings_context, seat_readings_for
    from tests.test_structure_reading_v3 import SIVERS, SOCKET, TODAY as READ_DAY, _canonical, _quotes, _row, _v3

    monkeypatch.setattr(sr, "STRUCTURE_READING_DIR", tmp_path / "ledger")
    edges = _canonical([_row(SIVERS, "supplies_to", SOCKET), _row("prod:teraphy_chiplet", "depends_on", SOCKET),
                        _row("co:ayar_labs", "depends_on", SOCKET)])
    sr.append_reading_record(_v3(SOCKET, structure=qs.build_structure(SOCKET, edges).as_dict()), quotes=_quotes(SOCKET))
    monkeypatch.setattr(qs, "_load_edges", lambda: edges)
    rows = seat_readings_for(seat_readings_context(today=READ_DAY), SIVERS)["readings"]
    assert rows[0]["demand_customers"] == ["co:ayar_labs"]


def test_materialize_many_loads_each_context_once_and_wires_them_into_every_page(tmp_path, monkeypatch) -> None:
    """plan §8 第 4 點「不得每檔各自重載一次圖」＋偏差 28 的注入——掉任何一條，鏈段仍有字（與掉線同形，L13），所以要測接線。"""
    from webapp import materialize as mat
    from webapp.store import ArtifactStore

    calls = {"readings": 0, "candidates": 0, "fetch": []}
    readings_ctx = {"seats": {}, "by_node": {}}

    def fake_readings(**kwargs):
        calls["readings"] += 1
        return readings_ctx

    def fake_candidates(tickers, **kwargs):
        calls["candidates"] += 1
        return {"absence": {"kind": "upstream_unavailable", "reason": "測試"}}

    def fake_fetch(ticker, **kwargs):
        calls["fetch"].append(kwargs.get("seat_readings"))
        return _full_view()

    import briefing.alpha_view.sources as sources

    monkeypatch.setattr(mat, "readings_context", fake_readings)
    monkeypatch.setattr(mat, "candidate_context", fake_candidates)
    monkeypatch.setattr(sources, "fetch_alpha_investment_view", fake_fetch)
    monkeypatch.setattr(mat, "_close_series", lambda ticker, **k: [])
    seen = []
    real_input = mat.candidate_input_for
    monkeypatch.setattr(mat, "candidate_input_for", lambda ctx, view: (seen.append(ctx), real_input(ctx, view))[1])
    results = mat.materialize_many(["COHR", "AXTI"], store=ArtifactStore(tmp_path))
    assert all(path is not None for _t, path, _r in results), results
    assert calls["readings"] == 1 and calls["candidates"] == 1
    assert calls["fetch"] == [readings_ctx, readings_ctx], "每檔 fetch 都收到同一份讀圖 context"
    assert len(seen) == 2 and seen[0] is seen[1]
    shared = {"absence": {"kind": "point_in_time_unavailable", "reason": "共用"}}
    calls["candidates"] = 0
    mat.materialize_many(["COHR"], store=ArtifactStore(tmp_path), candidates=shared)
    assert calls["candidates"] == 0 and seen[-1] is shared, "給了共用的就不再載一次"


def test_markdown_renders_every_new_panel_and_no_python_repr(monkeypatch) -> None:
    from briefing.analyst_view import render_analyst_view_markdown
    from tests.test_alpha_investment_view import _view

    view = _view(today=TODAY, brief_records=[_brief()], three_questions=_raw_tq(),
                 narrative_context={"node_names": {"mat:inp_substrate": "InP 基板"}})
    text = render_analyst_view_markdown(build_analyst_view(
        view, readings={"seats": ["mat:inp_substrate"], "readings": [_reading("stale")]},
        candidate={"row": {"derived": "priced_wait", "derived_label": "已定價等回落", "declared": "priced_wait",
                           "rewrite": [], "preconditions": [], "stall_days": 1},
                   "three_words": {"will_it_die": "黃（灰 1）", "priced_in": "否", "in_numbers": "是"},
                   "downside": {"rows": [{"source": "brief", "source_label": "敘事自己登記的反證", "condition": SELF_COND,
                                          "watch_id": "ew_1", "state": "active", "state_label": "在盯"}],
                                "counts": {"active": 1}}}))
    for heading in ("## 這檔現在在哪一格", "## 讀圖：它坐的那一層結構變了沒（核心）", "## 錯了怎麼知道",
                    "## 財務三題的數字", "## 賭注：我們賭什麼、騎在哪、什麼必須為真"):
        assert heading in text, heading
    assert "已定價等回落" in text and "B：量的賭注" in text and "ew\\_1" in text
    assert "「InP 基板」（層）" in text and "{'node'" not in text and "\nNone" not in text
    assert "核心四段" not in text


def test_frontend_series_points_cover_all_three_shapes_and_the_lamp_label_fallback() -> None:
    source = (Path(__file__).resolve().parents[1] / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    point = source.split("const TQ_POINT_KEYS", 1)[1].split("function threeQuestionsCard", 1)[0]
    for key in ("period_end", "data_month", "revenue_twd_thousand", "available_on", "revenue_mix", "derived"):
        assert key in point, f"三題序列少認了 {key}（alpha/three_questions.py 會產這個鍵）"
    assert "keyValueList(rest)" in point, "認不得的鍵要照印，不得濾掉（INV-3）"
    wipe = source.split("function wipeoutBlock", 1)[1].split("\nfunction ", 1)[0]
    assert "plainLine(line.key, line.display_label)" in wipe, "燈名的 fallback 要傳進 plainLine（否則印內部 key）"


def test_candidate_context_normalises_aliases_to_the_research_ticker(board_env) -> None:
    from alpha.providers import candidates as cand

    ctx = cand.candidate_context(["SIVEF"], today=date(2026, 9, 29), holdings_loader=lambda: [], board=False)
    assert ctx["universe"] == ["SIVE.ST"] and "SIVE.ST" in ctx["edges"]



# ---------------------------------------------------------------------------
# 7. 覆核第二輪補的（2026-09-30）
# ---------------------------------------------------------------------------

def test_a_fully_retracted_ride_cell_says_rewrite_not_fix_the_reader(tmp_path) -> None:
    brief = _brief(disproof=[])
    out = downside_rows(CO, T, records=[brief], current_brief=brief, watches=[], lifecycle={}, reading_rows={},
                        root=tmp_path, retracted_cells=[("mat:inp_substrate", "layer")])
    assert out["unread"] == [] and any("已全部撤回" in n and "重寫敘事" in n for n in out["notes"])
    assert out["empty"]["kind"] == "not_yet_recorded" and "重寫敘事" in out["empty"]["reason"]
    whole_node = downside_rows(CO, T, records=[brief], current_brief=brief, watches=[], lifecycle={}, reading_rows={},
                               root=tmp_path, retracted_cells=[("mat:inp_substrate", None)])
    assert any("已全部撤回" in n for n in whole_node["notes"]), "整個節點撤回（unit=None）也算"


def test_empty_downside_reason_is_built_from_facts_not_a_fixed_sentence(tmp_path) -> None:
    brief = _brief(disproof=[])
    moved = {("mat:inp_substrate", "layer"): {**READING_ROWS[("mat:inp_substrate", "layer")], "reading_id": "sr_" + "d" * 16}}
    out = downside_rows(CO, T, records=[brief], current_brief=brief, watches=[], lifecycle={}, reading_rows=moved,
                        root=tmp_path)
    assert "v2 敘事沒有寫自己的反證" in out["empty"]["reason"] and "沒有 v2 敘事" not in out["empty"]["reason"]
    assert "已換版" in out["empty"]["reason"]
    none = downside_rows(CO, T, records=[], current_brief=None, watches=[], lifecycle={}, reading_rows={}, root=tmp_path)
    assert "沒有 v2 敘事" in none["empty"]["reason"]


def test_fired_beats_active_for_the_same_condition_whatever_the_order(tmp_path) -> None:
    root = _memo_root(tmp_path)
    fired = _sem("ew_f", f"thesis:{MEMO}#1", MEMO_ITEMS[0], status="fired")
    active = _sem("ew_a", f"thesis:{MEMO}#1", MEMO_ITEMS[0])
    for order in ([fired, active], [active, fired]):
        out = downside_rows(CO, T, records=[], current_brief=None, watches=order, lifecycle=LIFECYCLE,
                            reading_rows={}, root=root)
        assert next(r for r in out["rows"] if r["condition"] == MEMO_ITEMS[0])["watch_id"] == "ew_f"


def test_shared_context_board_excludes_a_ticker_that_failed_to_materialize(board_env) -> None:
    from alpha.providers import candidates as cand

    ctx = cand.candidate_context(["AXTI", "FAILED1"], today=date(2026, 9, 29), holdings_loader=lambda: [], board=True)
    assert "FAILED1" in ctx["universe"]
    board = cand.load_board([], context=ctx)                           # materialize 之後的目錄不含 FAILED1
    assert "FAILED1" not in board["universe"] and "AXTI" in board["universe"], "敘事 ledger 裡的照舊上板"


def test_candidate_input_carries_the_judgment_action_under_the_key_downside_reads(monkeypatch) -> None:
    from alpha.providers import candidates as cand
    from webapp.materialize import candidate_input_for

    seen = {}
    monkeypatch.setattr(cand, "page_input", lambda ctx, t, c, **kw: (seen.update(kw), {"row": None})[1])
    view = _full_view()
    candidate_input_for(_context(), view)
    first = view.falsification.conditions[0]
    assert seen["judgment_conditions"][0] == {"condition": first.condition, "check_frequency": first.check_frequency,
                                              "action": first.action_within_48h}


def test_cmd_materialize_shares_one_board_context_between_pages_and_board(tmp_path, monkeypatch) -> None:
    from webapp import __main__ as cli
    from webapp import materialize as mat

    calls = {"ctx": [], "many": None, "board": None}
    marker = {"today": "x"}

    def fake_ctx(tickers, **kwargs):
        calls["ctx"].append((list(tickers), kwargs))
        return marker

    def fake_many(tickers, **kwargs):
        calls["many"] = kwargs.get("candidates")
        return [(t, None, "測試不寫") for t in tickers]

    def fake_board(**kwargs):
        calls["board"] = kwargs.get("context")
        raise RuntimeError("測試到此為止")

    monkeypatch.setattr(mat, "candidate_context", fake_ctx)
    monkeypatch.setattr(mat, "materialize_many", fake_many)
    monkeypatch.setattr(mat, "materialize_candidates", fake_board)
    monkeypatch.setattr(mat, "write_vocabularies", lambda store=None: tmp_path / ".meta.json")
    args = cli.build_parser().parse_args(["materialize", "AXTI", "--candidates", "--dir", str(tmp_path / "av"),
                                          "--state-dir", str(tmp_path / "state")])
    cli.cmd_materialize(args)
    assert len(calls["ctx"]) == 1 and calls["ctx"][0][1].get("board") is True
    assert calls["many"] is marker and calls["board"] is marker, "同一份 context 交給個股頁與候選板"


def test_markdown_audit_rows_never_print_python_repr_for_nested_values() -> None:
    from briefing.analyst_view import render_analyst_view_markdown

    raw = _raw_tq()
    raw["in_numbers"] = [{"key": "in_numbers_structure", "label": "結構脈絡", "value": {"Systems": 0.5, "_amounts_usd": {"Systems": 1}},
                          "source": "segment_revenue_share", "as_of": "2025-12-31", "basis": None, "rule": "r",
                          "absence_kind": None, "reason": None, "detail": {}}]
    text = render_analyst_view_markdown(build_analyst_view(_full_view(three_questions=raw)))
    assert "_amounts_usd Systems 1" in text.replace("\\", "") and "{'" not in text


def test_frontend_guards_for_the_second_review_round() -> None:
    source = (Path(__file__).resolve().parents[1] / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    point = source.split("const TQ_POINT_KEYS", 1)[1].split("function tqPoint", 1)[0]
    assert "x >= 0 && x <= 1" in point, "占比只對 0–1 的數字 ×100（金額不得印成百分比）"
    card = source.split("function downsideCard", 1)[1].split("\nfunction ", 1)[0]
    assert "c.description" in card and "c.expected_at" in card and "c.label, c.due, c.state" not in card
    assert "point_in_time_unavailable" in card
    readiness = source.split("function renderReadiness", 1)[1].split("\nfunction ", 1)[0]
    assert "plainPanel(key" in readiness and "沒有 entry 判準" not in readiness
    tq = source.split("function threeQuestionsCard", 1)[1].split("\nfunction ", 1)[0]
    assert "keyValueList(deps.detail)" in tq, "敘事引用的倍數與中位數要在稽核區核對得到"



def test_retracted_cell_through_page_input_reaches_downside(monkeypatch) -> None:
    """candidate_context 帶出的撤回格子要經 page_input 交到 downside（不然撤回又被說成讀不到）。"""
    import alpha.providers.briefs as briefs_mod
    from alpha.providers import candidates as cand

    brief = _brief(disproof=[])
    monkeypatch.setattr(briefs_mod, "read_brief_records", lambda ticker: ([brief], []))
    page = cand.page_input(_context(reading_rows={}, retracted_cells=[("mat:inp_substrate", "layer")]), T, CO,
                           three_questions=_tq())
    assert any("已全部撤回" in n for n in page["downside"]["notes"]) and page["downside"]["unread"] == []
