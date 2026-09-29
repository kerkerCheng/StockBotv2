"""候選狀態推導（Phase 3 Step 3.6）：持股身分解析、已持有、五組＋附組、前提每天重驗、該重寫、滯留、rollup、整板載入。

全部用注入的輸入（敘事紀錄、讀圖列、watch、三題、邊緣、持股解析結果）——不讀 Sheet、不連圖、不讀真實 ledger。
身分解析用真實 registry 與 execution 別名（`config/company_identity.json`、`identity/execution.py` 都是 tracked 設定）。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from alpha.candidates import WIPEOUT_LINES
from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record
from alpha.providers.candidates import (
    GROUPS, SIDE_GROUPS, assemble_board, derive_row, held_index, rollup, stall_since, three_words,
)
from portfolio.holdings import resolve_holdings
from risk import hard_caps
from risk.hard_caps import beta_instrument_for, is_beta_symbol

TODAY = date(2026, 9, 29)
CO, T = "co:axt", "AXTI"
READ = "sr_" + "a" * 16
EDGE = {"state": "edge", "label": "邊緣", "reasons": ["within_edge"], "market_cap_usd": 4.8e9, "analyst_count": 5}
_DEFAULT = object()


def _slots() -> dict:
    ev = ["graph://x"]
    return {"demand": {"text": "客戶預付產能。", "evidence_refs": ev},
            "position": {"text": "坐在基板層，年增 {in_numbers_latest}（{in_numbers_as_of}）。", "evidence_refs": ev},
            "bottleneck": {"text": "三家供應。", "evidence_refs": ev},
            "priced_in": {"text": "自家三年 {own_history_basis} 第 {own_history_pctile} 百分位。", "evidence_refs": ev},
            "our_bet": {"text": "賭層的量。", "evidence_refs": ev},
            "what_must_be_true": {"text": "擴產沒提前。", "evidence_refs": ev},
            "when": {"text": "{next_checkpoint_date} 財報。", "evidence_refs": ev}}


def _brief(*, state="open", watch_id=None, reason=None, days_ago=0, supersedes=None, disproof=(),
           answers=None, ticker=T, company=CO, retracted=False):
    rec = brief_record(company_id=company, ticker=ticker, slots=_slots(), record_version=RECORD_VERSION_V2,
                       rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}], disproof=list(disproof),
                       answers=answers or {"priced_in": "yes", "in_numbers": "yes"},
                       candidate_state={"state": state, "watch_id": watch_id, "reason": reason},
                       supersedes_id=supersedes, retracted=retracted,
                       created_at=datetime(2026, 9, 29, 3, tzinfo=timezone.utc) - timedelta(days=days_ago))
    return parse_brief_record(rec)


def _v1():
    rec = brief_record(company_id=CO, ticker=T, slots={k: {"text": "x", "evidence_refs": ["e"]} for k in
                       ("demand", "supply", "bottleneck", "market_view", "our_bet", "if_right_if_wrong", "when")},
                       created_at=datetime(2026, 9, 1, tzinfo=timezone.utc))
    return parse_brief_record(rec)


def _tq(*, absent_priced=False, absent_numbers=False, lights=("amber", "green", "amber", None)):
    def row(key, absent):
        return {"key": key, "value": None if absent else 1.0, "absence_kind": "upstream_unavailable" if absent else None}
    return {"priced_in": [row("own_history_pctile", absent_priced), row("cohort_median", True),
                          row("rel_return_30d", True), row("rel_return_90d", True)],
            "in_numbers": [row("in_numbers_series", absent_numbers)],
            "will_it_die": [{"key": k, "value": v, "absence_kind": None if v else "not_yet_recorded"}
                            for k, v in zip(WIPEOUT_LINES, lights)]}


def _rows(status="current", kind="volume", reading_id=READ):
    return {("tech:x", "layer"): {"node": "tech:x", "unit": "layer", "reading_id": reading_id, "status": status,
                                  "kind": kind}}


HELD_NONE = {"status": "ok", "by_company": {}, "unresolved": [], "beta_excluded": 0, "zero_shares": 0}
LINK = {"condition": "讀圖反證：供給側出現第四家（現況 3 家）——中國廠商擴產最可能", "check_frequency": "每季",
        "action_48h": "重讀", "entities": [CO], "expires": "2027-03-01", "source": READ,
        "link_source_ref": f"reading:{READ}#1"}
SELF = {"condition": "若 JX 在 2026-12-31 前宣布新產能投產則供給缺口消失，量的賭注不成立", "check_frequency": "每季",
        "action_48h": "重寫", "entities": [CO], "expires": "2027-03-01", "source": "self", "link_source_ref": None}


def _derive(records, *, rows=None, watches=(), edge=EDGE, tq=_DEFAULT, held=HELD_NONE, lifecycle=None, note=None):
    return derive_row(T, CO, records=records, today=TODAY, reading_rows=rows or _rows(), watches=list(watches),
                      lifecycle={} if lifecycle is None else lifecycle, edge=edge,
                      three_questions=_tq() if tq is _DEFAULT else tq, held=held, three_questions_note=note)


def _active(wid, **kw):
    return {"watch_id": wid, "status": "active", "expires": "2027-01-01", **kw}


# ---------------------------------------------------------------------------
# 持股身分解析與「已持有」
# ---------------------------------------------------------------------------

def test_execution_symbol_resolves_through_the_reverse_alias_without_guessing() -> None:
    res = resolve_holdings([{"ticker": "FRA:2DG", "shares": 100.0, "bucket": "觀察"},
                            {"ticker": "TYO:7803", "shares": 10.0, "bucket": "觀察"},
                            {"ticker": "CASH-TWD", "shares": 0.0, "bucket": "CASH"}])
    by = {r["ticker"]: r for r in res["rows"]}
    assert by["FRA:2DG"]["company_id"] == "co:sivers_semiconductors" and by["FRA:2DG"]["source"] == "execution_alias"
    assert by["TYO:7803"]["company_id"] is None
    assert res["unresolved"] == ["TYO:7803"]                         # 現金列不是「解析不到」
    assert res["cash_rows"] == 1


def test_held_is_alpha_with_shares_and_beta_never_counts() -> None:
    res = resolve_holdings([{"ticker": "FRA:2DG", "shares": 100.0, "bucket": "觀察"},
                            {"ticker": "NVDA", "shares": 5.0, "bucket": "CORE"},
                            {"ticker": "AXTI", "shares": 0.0, "bucket": "觀察"},
                            {"ticker": "QQQ", "shares": 3.0, "bucket": "大盤"},
                            {"ticker": "CASH-USD", "shares": 0.0, "bucket": "現金"},
                            {"ticker": "TYO:7803", "shares": 10.0, "bucket": "觀察"}])
    held = held_index(res, is_beta=is_beta_symbol)
    assert set(held["by_company"]) == {"co:sivers_semiconductors"}   # NVDA 是 beta、AXTI 股數 0
    assert held["beta_excluded"] == 2 and held["zero_shares"] == 1
    # 候選板與心跳讀的是這一份 unresolved：QQQ（beta）與現金列不算，只有 alpha 的 TYO:7803
    assert held["unresolved"] == ["TYO:7803"]


@pytest.mark.parametrize("resolution, failure", [(None, "HttpError"), ({"rows": [], "unresolved": []}, None)])
def test_unreadable_or_empty_sheet_suspends_held_instead_of_saying_not_held(resolution, failure) -> None:
    """讀不到，或回空表（分頁清空時 fetch_portfolio 回 [] 不丟例外）——都是「持股未驗」，不是「持有 0」；
    硬擋對同一份 [] 也回 unmeasurable。"""
    held = held_index(resolution, is_beta=is_beta_symbol, failure=failure)
    assert held["status"] == "upstream_unavailable" and "暫停" in held["reason"]
    row = _derive([_brief(state="priced_wait", watch_id="ew_1")],
                  watches=[_active("ew_1", kind="date", until="2026-11-13", wake_brief=CO)], held=held)
    assert row["holdings_verified"] is False and row["group"] == "priced_wait"
    board = assemble_board([row], universe=[T], held=held, narrative_rewrite=[])
    assert board["counts"]["held"] is None                           # 缺席，不是 0
    if resolution is not None:
        verdict = hard_caps.check_trade_hard_caps([], symbol="FRA:2DG", side="buy", gross_base=100.0)
        assert verdict.status == "unmeasurable"                      # 兩個消費者對同一份 [] 同一個判定


def test_held_keeps_the_declaration_and_a_held_company_without_narrative_still_shows() -> None:
    held = {"status": "ok", "by_company": {CO: {"sheet_ticker": "AXTI", "source": "registry_ticker"}}}
    row = _derive([_brief(state="missing", watch_id="ew_1")], held=held,
                  watches=[_active("ew_1", kind="date", until="2026-11-13", wake_brief=CO)])
    assert row["group"] == "held" and row["derived"] == "held" and row["declared"] == "missing"
    bare = _derive([], held=held)
    assert bare["group"] == "held" and bare["note"] == "已持有、缺敘事"


def test_held_semantics_of_the_pq1_key_are_unchanged(monkeypatch) -> None:
    """`_held` 仍是**全部持股**（含 beta）；Sheet 讀不到時 strict 仍 fail closed。"""
    import fetchers.gsheets as gs
    from engine_b import cli
    from engine_b.cli import PriorityContextError

    monkeypatch.setattr(gs, "fetch_portfolio", lambda **_: [
        {"ticker": "NVDA", "shares": 5.0, "bucket": "CORE", "neo4j_id": None},
        {"ticker": "FRA:2DG", "shares": 1.0, "bucket": "觀察", "neo4j_id": "co:sivers_semiconductors"}])
    tickers, company_ids = cli._held(strict=True)
    assert {"NVDA", "FRA:2DG", "2DG", "SIVE.ST", "SIVE"} <= set(tickers)
    assert {"co:nvidia", "co:sivers_semiconductors"} <= set(company_ids)   # beta 持股仍在 pq1 的持股鍵裡

    def boom(**_):
        raise RuntimeError("sheet down")

    monkeypatch.setattr(gs, "fetch_portfolio", boom)
    with pytest.raises(PriorityContextError):
        cli._held(strict=True)
    assert cli._held(strict=False) == (frozenset(), frozenset())


def test_hard_caps_export_is_the_same_function_and_behaviour() -> None:
    assert hard_caps._instrument_for is beta_instrument_for           # 只匯出、行為不變（#17）
    assert is_beta_symbol("QQQ") and not is_beta_symbol("FRA:2DG")


# ---------------------------------------------------------------------------
# 五組＋附組、前提
# ---------------------------------------------------------------------------

def test_a_clean_open_stays_open() -> None:
    row = _derive([_brief()])
    assert row["group"] == "open" and row["preconditions"] == [] and row["rewrite"] == []
    assert row["three_words"] == {"will_it_die": "黃（灰 1）", "priced_in": "是", "in_numbers": "是"}


@pytest.mark.parametrize("kw, reason", [
    ({"rows": _rows(status="stale")}, "狀態 stale"),
    ({"rows": _rows(reading_id="sr_" + "b" * 16)}, "已不是現行"),
    ({"tq": _tq(absent_priced=True)}, "已定價的稽核行已全部缺席"),
    ({"tq": None, "note": "OperationalError"}, "讀不到三題稽核區"),        # fail closed：讀不到不等於沒變
])
def test_open_preconditions_fail_into_the_side_group(kw, reason) -> None:
    row = _derive([_brief()], **kw)
    assert row["group"] is None and row["side"] == "precondition_failed" and row["declared"] == "open"
    assert any(reason in p for p in row["preconditions"])


def test_a_ticker_in_two_cohorts_is_not_failed_by_the_second_cohorts_absence() -> None:
    """L17：同一個 key 有兩行（兩個主題組）——一行有值就算有值，不得被後一行的缺席蓋掉。"""
    tq = _tq()
    tq["priced_in"] = [{"key": "own_history_pctile", "value": None, "absence_kind": "insufficient_evidence"},
                       {"key": "cohort_median", "value": 3.1, "absence_kind": None},
                       {"key": "cohort_median", "value": None, "absence_kind": "not_yet_recorded"}]
    assert _derive([_brief()], tq=tq)["group"] == "open"


def test_the_narratives_own_touched_disproof_breaks_open_and_is_carried_on_every_row() -> None:
    """plan §5 第 6 點：敘事來源 watch 醒來／觸及／到期未判 → 候選板那一列印「敘事該重寫：<id> <狀態>」——**不論宣告哪一態**。"""
    brief = _brief(disproof=[SELF])
    touched = {"watch_id": "ew_9", "kind": "semantic_condition", "status": "consumed",
               "source_ref": f"brief:{brief.brief_id}#1", "expires": "2027-03-01",
               "judgment": {"touches": "yes", "handled": None}}
    row = _derive([brief], watches=[touched])
    assert row["side"] == "precondition_failed" and any("待處置" in p for p in row["preconditions"])
    assert row["rewrite"] == ["敘事該重寫：ew_9 觸及"] and row["rewrite_watch_ids"] == ["ew_9"]
    for state, extra in (("priced_wait", {"watch_id": "ew_1"}), ("pass", {"reason": "貴"})):
        other = _brief(state=state, disproof=[SELF], **extra)
        fired = {**touched, "status": "fired", "judgment": None, "source_ref": f"brief:{other.brief_id}#1"}
        w = [fired, _active("ew_1", kind="date", until="2026-11-13", wake_brief=CO)]
        got = _derive([other], watches=w)
        assert got["group"] == state and got["rewrite"] == ["敘事該重寫：ew_9 醒來"]


@pytest.mark.parametrize("source, label", [
    (None, "來源不存在"),
    ({"status": "consumed", "closed": {"at": "2026-09-01T00:00:00+00:00"}}, "來源已收掉"),
    ({"status": "consumed", "judgment": {"touches": "yes", "handled": None}}, "來源被判觸及"),
    ({"status": "expired", "expired_at": "2026-09-01T00:00:00+00:00"}, "來源到期未判"),
])
def test_a_broken_link_says_why_it_broke_for_every_state_and_breaks_open(source, label) -> None:
    """L12：「換版」「觸及」「到期」是三件事，下一步不同。"""
    watches = [] if source is None else [{"watch_id": "ew_r", "source_ref": f"reading:{READ}#1", **source}]
    row = _derive([_brief(disproof=[LINK])], watches=watches)
    assert row["side"] == "precondition_failed" and len(row["rewrite"]) == 1 and label in row["rewrite"][0]
    passed = _derive([_brief(state="pass", reason="太貴", disproof=[LINK])], watches=watches)
    assert passed["group"] == "pass" and label in passed["rewrite"][0]


def test_link_breaks_feed_the_narrative_rewrite_queue_segment() -> None:
    """R2-a N1：連結斷了是 narrative_rewrite 的工作——佇列段、audit、心跳、候選推導同一個判定。"""
    from engine_b import queue_segments as qs
    from engine_b.narrative_watches import link_breaks

    brief = _brief(disproof=[LINK])
    breaks = link_breaks([brief], watches=[])
    assert [b["link_source_ref"] for b in breaks] == [f"reading:{READ}#1"] and breaks[0]["reason"] == "missing"
    fired = {"watch_id": "w1", "status": "fired", "source_ref": f"reading:{READ}#1"}
    assert link_breaks([brief], watches=[fired]) == []              # 來源醒著＝連結沒斷（那是來源那一邊的事件）
    seg = next(s for s in qs.observe(narrative_link_breaks=breaks)["segments"] if s["key"] == "narrative_rewrite")
    assert seg["count"] == 1 and "來源不存在" in seg["examples"][0]


def test_not_edge_declared_open_is_not_a_multiple_candidate() -> None:
    row = _derive([_brief()], edge={"state": "not_edge", "reasons": ["cap_over_edge"]})
    assert row["group"] is None and row["side"] == "not_multiple" and row["declared"] == "open"


def test_edge_unmeasurable() -> None:
    row = _derive([_brief()], edge={"state": "unmeasurable", "reasons": ["cap_missing"]})
    assert row["side"] == "edge_unmeasurable"


@pytest.mark.parametrize("watch, text", [
    ({"watch_id": "ew_1", "status": "consumed", "expires": "2027-01-01"}, "已 consumed"),
    ({"watch_id": "ew_1", "status": "active", "expires": "2026-09-01"}, "已過到期日 2026-09-01"),
    (None, "不存在"),
])
def test_a_lapsed_wait_is_flagged_for_rewrite_with_what_happened(watch, text) -> None:
    row = _derive([_brief(state="missing", watch_id="ew_1")], watches=[watch] if watch else [])
    assert row["group"] == "missing" and any(text in r for r in row["rewrite"]), row["rewrite"]


def test_a_woken_wait_is_listed_once_not_twice() -> None:
    w = {"watch_id": "ew_1", "status": "fired", "kind": "date", "until": "2026-09-01", "expires": "2027-01-01",
         "wake_brief": CO}
    row = _derive([_brief(state="missing", watch_id="ew_1")], watches=[w])
    assert row["rewrite"] == ["敘事該重寫：ew_1 醒來"]


def test_v1_is_legacy_and_three_words_are_unanswered() -> None:
    row = _derive([_v1()])
    assert row["side"] == "legacy" and row["three_words"]["priced_in"] == "未答"


def test_no_narrative_is_counted_not_listed_and_zero_groups_still_print() -> None:
    assert _derive([]) is None
    board = assemble_board([None, None, _derive([_brief(state="pass", reason="貴")])], universe=["A", "B", T],
                           held=HELD_NONE, narrative_rewrite=[])
    assert board["counts"]["no_narrative"] == 2 and board["counts"]["pass"] == 1
    assert set(GROUPS) | set(SIDE_GROUPS) <= set(board["counts"]) and board["counts"]["open"] == 0


def test_same_state_rewrites_do_not_reset_the_stall_clock_but_a_retraction_does() -> None:
    first = _brief(state="missing", watch_id="ew_1", days_ago=20)
    second = _brief(state="missing", watch_id="ew_1", days_ago=5, supersedes=first.brief_id)
    assert stall_since([first, second], second) == first.created_at
    other = _brief(state="missing", watch_id="ew_2", days_ago=2, supersedes=second.brief_id)
    assert stall_since([first, second, other], other) == other.created_at   # 換了在等的事＝重新計
    row = _derive([first, second], watches=[_active("ew_1")])
    assert row["stall_days"] == 20
    retract = _brief(state="missing", watch_id="ew_1", days_ago=10, supersedes=first.brief_id, retracted=True)
    again = _brief(state="missing", watch_id="ew_1", days_ago=1, supersedes=retract.brief_id)
    assert stall_since([first, retract, again], again) == again.created_at  # 撤回後那段沒有宣告，不算滯留


def test_groups_are_alphabetical_not_ranked() -> None:
    rows = [dict(_derive([_brief(state="pass", reason="貴")]), ticker=t) for t in ("ZZZ", "AAA", "MMM")]
    board = assemble_board(rows, universe=["AAA", "MMM", "ZZZ"], held=HELD_NONE, narrative_rewrite=[])
    assert [r["ticker"] for r in board["groups"]["pass"]] == ["AAA", "MMM", "ZZZ"]


def test_three_words_worst_light_and_greys() -> None:
    assert three_words(_tq(lights=("red", "green", None, None)), None)["will_it_die"] == "紅（灰 2）"
    assert three_words(_tq(lights=(None, None, None, None)), None)["will_it_die"] == "灰 4"
    assert three_words(None, None)["will_it_die"] == "未讀到"
    assert _derive([_brief(state="pass", reason="貴")], tq=None, note="boom")["three_words"]["will_it_die"] == "未讀到（boom）"


def test_rollup_counts_lamps_greys_by_kind_and_unread_with_reasons() -> None:
    """灰不是綠：一綠三灰算一盞綠、三盞灰（依 kind），不算成「綠 1 檔」；讀不到的檔帶理由（INV-3）。"""
    r = rollup({"A": _tq(lights=("green", None, None, None)),
                "B": _tq(absent_priced=True, lights=("red", "amber", "green", "green")), "C": None},
               {"A": {"state": "edge"}, "B": {"state": "not_edge"}, "C": {}}, not_read_reasons={"C": "OperationalError"})
    assert r["universe"] == 3
    assert r["priced_in_own"] == {"valued": 1, "absent": {"not_read": 1, "upstream_unavailable": 1}, "absent_total": 2}
    assert r["wipeout"]["lamps"] == {"red": 1, "amber": 1, "green": 3, "unlit": 3}
    assert r["wipeout"]["unlit_by_kind"] == {"not_yet_recorded": 3}
    assert r["wipeout"]["red_tickers"] == ["B"] and r["wipeout"]["all_four_non_grey"] == 1
    assert r["not_read"] == {"n": 1, "tickers": ["C"], "reasons": {"C": "OperationalError"}}
    assert r["lines"]["wipeout_cash_runway"] == {"value": 2}          # 逐行沿用 alpha.three_questions.rollup
    assert r["edge"] == {"edge": 1, "not_edge": 1, "unmeasurable": 1}


# ---------------------------------------------------------------------------
# 整板載入（load_board）：宇宙合併、只在 Sheet 的持有、Sheet 讀不到、三題讀不到、ledger 不在
# ---------------------------------------------------------------------------

@pytest.fixture()
def board_env(monkeypatch, tmp_path):
    import alpha.providers.briefs as briefs_mod
    import alpha.providers.candidates as cand
    import alpha.providers.edge as edge_mod
    import alpha.providers.structure_readings as sr
    import engine_b.disproof as disproof
    import query.structure as qstruct
    from alpha.providers.briefs import append_brief_record

    ledger = tmp_path / "briefs"
    ledger.mkdir()
    monkeypatch.setattr(briefs_mod, "BRIEF_DIR", ledger)
    monkeypatch.setattr(disproof, "load_lifecycle", lambda: {})
    monkeypatch.setattr(qstruct, "_load_edges", lambda: [])
    monkeypatch.setattr(sr, "reading_status_rows", lambda *a, **k: ([], []))
    monkeypatch.setattr(edge_mod, "edge_states", lambda tickers: {t: dict(EDGE) for t in tickers})
    state = {"tq_fail": set()}

    def tq(ticker, *, today, history_not_comparable):
        return (None, "OperationalError: locked") if ticker in state["tq_fail"] else (_tq(), None)

    monkeypatch.setattr(cand, "_wipeout_and_three_questions", tq)
    rec = brief_record(company_id=CO, ticker=T, slots=_slots(), record_version=RECORD_VERSION_V2,
                       rides=[], answers={"priced_in": "yes", "in_numbers": "yes"},
                       candidate_state={"state": "pass", "watch_id": None, "reason": "貴"},
                       created_at=datetime(2026, 9, 28, tzinfo=timezone.utc))
    append_brief_record(rec, directory=ledger)
    state["ledger"] = ledger
    return state


def test_load_board_merges_the_ledger_into_the_universe_and_shows_sheet_only_holdings(board_env) -> None:
    from alpha.providers.candidates import load_board

    board = load_board([], today=TODAY, holdings_loader=lambda: [{"ticker": "FRA:2DG", "shares": 5.0, "bucket": "觀察"}])
    assert board["universe"] == [T] and board["counts"]["pass"] == 1       # 宇宙沒給，敘事 ledger 裡有的照上板
    held = board["groups"]["held"]
    assert [r["ticker"] for r in held] == ["SIVE.ST"] and held[0]["note"] == "已持有、缺敘事"
    assert held[0]["three_words"]["will_it_die"] != "未讀到"               # 只在 Sheet 的公司也算三題，不是「沒算」
    assert board["ledger"] == {"present": True, "tickers": 1, "parse_errors": 0, "parse_error_examples": []}


@pytest.mark.parametrize("loader", ["raise", "empty"])
def test_load_board_suspends_held_when_the_sheet_is_unreadable_or_empty(board_env, loader) -> None:
    from alpha.providers.candidates import load_board

    def boom():
        raise RuntimeError("sheet down")

    board = load_board([T], today=TODAY, holdings_loader=boom if loader == "raise" else (lambda: []))
    assert board["holdings"]["status"] == "upstream_unavailable" and board["counts"]["held"] is None
    assert all(r["holdings_verified"] is False for rows in board["groups"].values() for r in rows)


def test_load_board_keeps_the_reason_when_three_questions_cannot_be_read(board_env) -> None:
    from alpha.providers.candidates import load_board

    board_env["tq_fail"].add(T)
    board = load_board([T], today=TODAY, holdings_loader=lambda: [{"ticker": "CASH", "shares": 0.0, "bucket": "CASH"}])
    assert board["rollup"]["not_read"] == {"n": 1, "tickers": [T], "reasons": {T: "OperationalError: locked"}}
    assert board["groups"]["pass"][0]["three_words"]["will_it_die"] == "未讀到（OperationalError: locked）"


def test_load_board_says_the_ledger_is_missing_instead_of_no_narratives(board_env, monkeypatch, tmp_path) -> None:
    import alpha.providers.briefs as briefs_mod
    from alpha.providers.candidates import load_board

    monkeypatch.setattr(briefs_mod, "BRIEF_DIR", tmp_path / "nope")
    board = load_board([T], today=TODAY, holdings_loader=lambda: [{"ticker": "CASH", "shares": 0.0, "bucket": "CASH"}])
    assert board["ledger"]["present"] is False and board["counts"]["no_narrative"] == 1
