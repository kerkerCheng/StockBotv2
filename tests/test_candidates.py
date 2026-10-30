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


def _derive(records, *, rows=None, watches=(), edge=EDGE, tq=_DEFAULT, held=HELD_NONE, lifecycle=None, note=None,
            assertions=None, raw_text=None):
    return derive_row(T, CO, records=records, today=TODAY, reading_rows=rows or _rows(), watches=list(watches),
                      lifecycle={} if lifecycle is None else lifecycle, edge=edge,
                      three_questions=_tq() if tq is _DEFAULT else tq, held=held, three_questions_note=note,
                      company_assertions=assertions, raw_text=raw_text)


def _active(wid, **kw):
    return {"watch_id": wid, "status": "active", "expires": "2027-01-01", **kw}


# ---------------------------------------------------------------------------
# 持股身分解析與「已持有」
# ---------------------------------------------------------------------------

def test_execution_symbol_resolves_through_the_reverse_alias_without_guessing() -> None:
    res = resolve_holdings([{"ticker": "FRA:2DG", "shares": 100.0, "bucket": "觀察"},
                            {"ticker": "7803.T", "shares": 10.0, "bucket": "觀察"},
                            {"ticker": "CASH-TWD", "shares": 0.0, "bucket": "CASH"}])
    by = {r["ticker"]: r for r in res["rows"]}
    assert by["FRA:2DG"]["company_id"] == "co:sivers_semiconductors" and by["FRA:2DG"]["source"] == "execution_alias"
    assert by["7803.T"]["company_id"] is None
    assert res["unresolved"] == ["7803.T"]                         # 現金列不是「解析不到」
    assert res["cash_rows"] == 1


def test_held_is_alpha_with_shares_and_beta_never_counts() -> None:
    res = resolve_holdings([{"ticker": "FRA:2DG", "shares": 100.0, "bucket": "觀察"},
                            {"ticker": "NVDA", "shares": 5.0, "bucket": "CORE"},
                            {"ticker": "AXTI", "shares": 0.0, "bucket": "觀察"},
                            {"ticker": "QQQ", "shares": 3.0, "bucket": "大盤"},
                            {"ticker": "CASH-USD", "shares": 0.0, "bucket": "現金"},
                            {"ticker": "CASH-TWD", "shares": 1000.0, "bucket": "CASH"},   # 股數 > 0 的現金也不算
                            {"ticker": "7803.T", "shares": 10.0, "bucket": "觀察"}])
    held = held_index(res, is_beta=is_beta_symbol)
    assert set(held["by_company"]) == {"co:sivers_semiconductors"}   # NVDA 是 beta、AXTI 股數 0
    assert held["beta_excluded"] == 2 and held["zero_shares"] == 1
    # 候選板與心跳讀的是這一份 unresolved：QQQ（beta）與現金列不算，只有 alpha 的 7803.T
    assert held["unresolved"] == ["7803.T"]


def test_a_user_ignored_holding_is_listed_apart_not_as_unresolved(tmp_path) -> None:
    """Phase 4 Step 4.7b：`config/holdings_coverage.json` 的不研究名單——解析不到的列若在名單上，另列 `ignored[]`
    （附理由與決定日），不算「解析不到」；名單讀不到或壞掉 → 整份不採用、全部照列解析不到（fail safe）。"""
    import json

    from portfolio.holdings import load_ignored

    cfg = tmp_path / "holdings_coverage.json"
    entry = {"sheet_ticker": "7803.T", "reason": "使用者決定不研究", "decided_at": "2026-07-29"}
    cfg.write_text(json.dumps({"schema_version": "holdings-coverage-v1", "ignored": [entry]}), encoding="utf-8")
    names, problem = load_ignored(cfg)
    assert problem is None and set(names) == {"7803.T"}
    res = resolve_holdings([{"ticker": "7803.T", "shares": 10.0, "bucket": "觀察"},
                            {"ticker": "9999.T", "shares": 1.0, "bucket": "觀察"}])
    held = held_index(res, is_beta=is_beta_symbol, ignored=names)
    assert held["unresolved"] == ["9999.T"] and held["ignored"] == [entry]
    board = assemble_board([], universe=[], held=held, narrative_rewrite=[])
    assert board["holdings"]["ignored"] == [entry] and board["holdings"]["unresolved"] == ["9999.T"]
    # 名單壞掉：整份不採用、全部照列解析不到，讀取問題帶出去
    cfg.write_text(json.dumps({"schema_version": "holdings-coverage-v1", "ignored": [{"sheet_ticker": "7803.T"}]}),
                   encoding="utf-8")
    names, problem = load_ignored(cfg)
    assert names == {} and "第 1 筆" in problem
    held = held_index(res, is_beta=is_beta_symbol, ignored=names, ignored_problem=problem)
    assert held["unresolved"] == ["7803.T", "9999.T"] and held["ignored"] == [] and held["ignored_problem"] == problem
    cfg.write_text(json.dumps({"schema_version": "holdings-coverage-v0", "ignored": []}), encoding="utf-8")
    assert load_ignored(cfg) == ({}, "holdings_coverage.json 的 schema_version 不是 holdings-coverage-v1")
    assert load_ignored(tmp_path / "missing.json")[1].startswith("missing.json 讀不到")


def test_the_real_ignore_list_parses() -> None:
    """真實設定讀得進來（筆數會變，不斷言是幾筆——現況數字會腐壞）。"""
    from portfolio.holdings import load_ignored

    names, problem = load_ignored()
    assert problem is None, problem
    assert all(v["reason"] and v["decided_at"] for v in names.values())


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

    # 真實 Sheet 的形狀：不帶任何身分欄（2026-10-01 Phase 4 Step 4.1d 拿掉 enrichment 的 neo4j_id 注入）——
    # Sivers 要靠名冊的 execution_symbol（FRA:2DG → SIVE.ST）解出來，pq1 的持股鍵才不變。
    monkeypatch.setattr(gs, "fetch_portfolio", lambda **_: [
        {"ticker": "NVDA", "shares": 5.0, "bucket": "CORE"},
        {"ticker": "FRA:2DG", "shares": 1.0, "bucket": "觀察"}])
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
    ({"tq": _tq(absent_numbers=True)}, "出現在數字裡的稽核行已缺席"),
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
    assert row["rewrite_words"] == ["條件觸及"]          # 卡片與個股頁那一行的幾個字（2026-10-29）
    for state, extra in (("priced_wait", {"watch_id": "ew_1"}), ("pass", {"reason": "貴"})):
        other = _brief(state=state, disproof=[SELF], **extra)
        fired = {**touched, "status": "fired", "judgment": None, "source_ref": f"brief:{other.brief_id}#1"}
        w = [fired, _active("ew_1", kind="date", until="2026-11-13", wake_brief=CO)]
        got = _derive([other], watches=w)
        assert got["group"] == state and got["rewrite"] == ["敘事該重寫：ew_9 醒來"]
        assert got["rewrite_words"] == ["條件醒了"]


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
    assert row["rewrite_words"] == ["連結斷了"]          # 斷的原因含「觸及」「到期」也先認連結（先中先贏）
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


UNMEASURED = {"state": "unmeasurable", "label": "邊緣無法量", "reasons": ["coverage_unavailable"],
              "market_cap_usd": 1.6e9, "analyst_count": None}


def test_edge_unmeasurable_only_holds_back_a_declared_open() -> None:
    """2026-10-30 使用者「好 改吧」：邊緣無法量缺的是**篩選的輸入**，不是敘事的 X——缺輸入不放行，要擋的只有宣告可開。"""
    row = _derive([_brief()], edge=UNMEASURED)
    assert row["side"] == "edge_unmeasurable" and row["derived"] == "edge_unmeasurable" and row["group"] is None
    assert row["declared"] == "open" and row["edge_note"] == "邊緣無法量：缺分析師家數"


@pytest.mark.parametrize("state, watch_id, reason", [
    ("missing", "ew_1", None), ("priced_wait", "ew_1", None), ("pass", None, "這一層不卡"),
])
def test_edge_unmeasurable_keeps_the_narratives_own_state_and_carries_a_tag(state, watch_id, reason) -> None:
    """原本一律蓋掉宣告：真資料 9 檔裡 5 檔缺 X、4 檔不要被藏進附組，缺 X 與不要的檔數各少算（L12）。"""
    row = _derive([_brief(state=state, watch_id=watch_id, reason=reason)], edge=UNMEASURED,
                  watches=[_active("ew_1")] if watch_id else ())
    assert row["group"] == state and row["derived"] == state and row["side"] is None
    assert row["edge_note"] == "邊緣無法量：缺分析師家數"


def test_edge_note_says_which_input_is_missing_and_is_absent_when_the_edge_is_known() -> None:
    from alpha.candidates import edge_note

    assert _derive([_brief()])["edge_note"] is None                                      # 邊緣：沒有標記
    assert _derive([_brief(state="pass", reason="x")],
                   edge={"state": "not_edge", "reasons": ["cap_over_edge"]})["edge_note"] is None   # 非邊緣另一組
    held = {"status": "ok", "by_company": {CO: {"sheet_ticker": "AXTI", "source": "registry_ticker"}}}
    assert _derive([_brief(state="pass", reason="x")], edge=UNMEASURED, held=held)["edge_note"] is None  # 已持有優先
    assert edge_note({"reasons": ["market_cap_unavailable", "coverage_unavailable"]}) == "邊緣無法量：缺市值、分析師家數"
    assert edge_note(None) == "邊緣無法量：沒有判定"                                       # 沒有判定不猜缺哪一個
    no_edge = _derive([_brief(state="pass", reason="x")], edge=None)
    assert no_edge["group"] == "pass" and no_edge["edge_note"] == "邊緣無法量：沒有判定"


@pytest.mark.parametrize("watch, text, word", [
    ({"watch_id": "ew_1", "status": "consumed", "expires": "2027-01-01"}, "已 consumed", "等待結束了"),
    ({"watch_id": "ew_1", "status": "active", "expires": "2026-09-01"}, "已過到期日 2026-09-01", "到期了"),
    (None, "不存在", "等待不見了"),
])
def test_a_lapsed_wait_is_flagged_for_rewrite_with_what_happened(watch, text, word) -> None:
    row = _derive([_brief(state="missing", watch_id="ew_1")], watches=[watch] if watch else [])
    assert row["group"] == "missing" and any(text in r for r in row["rewrite"]), row["rewrite"]
    assert row["rewrite_words"] == [word]


def test_a_woken_wait_is_listed_once_not_twice() -> None:
    w = {"watch_id": "ew_1", "status": "fired", "kind": "date", "until": "2026-09-01", "expires": "2027-01-01",
         "wake_brief": CO}
    row = _derive([_brief(state="missing", watch_id="ew_1")], watches=[w])
    assert row["rewrite"] == ["敘事該重寫：ew_1 醒來"] and row["rewrite_words"] == ["條件醒了"]


def test_rewrite_words_never_drop_a_reason_and_count_repeats() -> None:
    """2026-10-29 使用者：「該重寫為啥沒寫…可以五字一目瞭然嗎」——每一條原因都歸一個短詞，認不得的歸「其他」（INV-3），
    同一個詞出現幾次就寫幾次（不靜默合併）；原句照舊留在 `rewrite[]`。"""
    from alpha.candidates import rewrite_words

    assert rewrite_words(["敘事該重寫：ew_1 醒來", "敘事該重寫：ew_2 醒來", "一句沒見過的原因"]) == ["條件醒了 × 2", "其他"]
    assert rewrite_words([]) == [] and rewrite_words(None) == []


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


def test_in_numbers_counts_a_ticker_measurable_when_either_series_has_a_value() -> None:
    """2026-10-14 營收序列與占比序列拆成兩行：只有占比序列的公司（ATS.VI 等）照樣算「出現在數字裡」量得到；
    兩行都缺席時記營收那一行的缺席 kind。"""
    mix_only = _tq(absent_numbers=True)
    mix_only["in_numbers"].append({"key": "in_numbers_mix_series", "value": [1], "absence_kind": None})
    r = rollup({"A": _tq(), "B": mix_only, "C": _tq(absent_numbers=True)}, {})
    assert r["in_numbers"] == {"valued": 2, "absent": {"upstream_unavailable": 1}, "absent_total": 1}
    row = _derive([_brief()], tq=mix_only)                            # 可開的前提：占比序列有值就沒失效
    assert not any("出現在數字裡" in p for p in row.get("preconditions") or ())


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
    state = {"tq_fail": set(), "hnc": {}}

    def tq(ticker, *, today, history_not_comparable):
        state["hnc"][ticker] = history_not_comparable
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
    # 宇宙沒給：敘事 ledger 裡有的照上板；只在 Sheet 持有的也進宇宙與彙總（已持有最需要看會死嗎）
    assert board["universe"] == [T, "SIVE.ST"] and board["counts"]["pass"] == 1
    assert board["rollup"]["universe"] == 2 and board["rollup"]["wipeout"]["companies"] == 2
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


def test_load_board_passes_the_declared_history_not_comparable_to_three_questions(board_env) -> None:
    """敘事宣告「歷史不可比」→ 三題讀取端收到它（R2-a N3；3.6 覆核 c23 第 ③ 點）。"""
    from alpha.providers.briefs import append_brief_record
    from alpha.providers.candidates import load_board

    rec = brief_record(company_id="co:coherent", ticker="COHR", slots=_slots(), record_version=RECORD_VERSION_V2,
                       rides=[], answers={"priced_in": "unmeasurable", "in_numbers": "yes"},
                       candidate_state={"state": "pass", "watch_id": None, "reason": "非邊緣"},
                       history_not_comparable={"since": "2026-01-01", "reason": "剛轉型", "source": "self"},
                       created_at=datetime(2026, 9, 28, tzinfo=timezone.utc))
    append_brief_record(rec, directory=board_env["ledger"])
    load_board([], today=TODAY, holdings_loader=lambda: [{"ticker": "CASH", "shares": 0.0, "bucket": "CASH"}])
    assert board_env["hnc"]["COHR"] == {"since": "2026-01-01", "reason": "剛轉型", "source": "self"}
    assert board_env["hnc"][T] is None


def test_load_board_counts_ledger_parse_errors(board_env) -> None:
    from alpha.providers.candidates import load_board

    with (board_env["ledger"] / "AXTI.jsonl").open("a", encoding="utf-8") as fh:
        fh.write("{這不是 json\n")
    board = load_board([T], today=TODAY, holdings_loader=lambda: [{"ticker": "CASH", "shares": 0.0, "bucket": "CASH"}])
    assert board["ledger"]["parse_errors"] == 1 and board["counts"]["pass"] == 1   # 壞行現形，好的照上板


def test_load_board_shows_a_holding_whose_company_has_no_research_ticker(board_env, monkeypatch) -> None:
    import identity.registry as reg_mod
    from alpha.providers.candidates import load_board

    real = reg_mod.get_registry()

    class NoResearch:
        def __getattr__(self, name):
            return getattr(real, name)

        def research_ticker(self, company_id):
            return None if company_id == "co:sivers_semiconductors" else real.research_ticker(company_id)

    monkeypatch.setattr(reg_mod, "get_registry", lambda: NoResearch())
    board = load_board([T], today=TODAY, holdings_loader=lambda: [{"ticker": "FRA:2DG", "shares": 5.0, "bucket": "觀察"}])
    held = board["groups"]["held"]
    assert [r["company_id"] for r in held] == ["co:sivers_semiconductors"]
    assert held[0]["three_words"]["will_it_die"] == "未讀到（registry 沒有這家公司的 research ticker）"


def test_a_retraction_breaks_the_stall_clock_even_when_the_rewrite_supersedes_the_retracted_target() -> None:
    """撤回用時間判：新版直接 supersede 被撤的那一筆（撤回紀錄不在鏈上），中間那段仍沒有宣告。"""
    first = _brief(state="missing", watch_id="ew_1", days_ago=20)
    retract = _brief(state="missing", watch_id="ew_1", days_ago=10, supersedes=first.brief_id, retracted=True)
    again = _brief(state="missing", watch_id="ew_1", days_ago=1, supersedes=first.brief_id)
    assert stall_since([first, retract, again], again) == again.created_at


def test_stall_days_count_in_the_schedule_timezone() -> None:
    """「今天」是排程時區的今天：台北 09-29 01:00（UTC 09-28 17:00）寫的，09-29 當天是 0 天，不是 1 天。"""
    rec = brief_record(company_id=CO, ticker=T, slots=_slots(), record_version=RECORD_VERSION_V2,
                       rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}],
                       answers={"priced_in": "yes", "in_numbers": "yes"},
                       candidate_state={"state": "pass", "watch_id": None, "reason": "貴"},
                       created_at=datetime(2026, 9, 28, 17, tzinfo=timezone.utc))
    assert _derive([parse_brief_record(rec)])["stall_days"] == 0


def test_a_date_wait_whose_day_arrived_but_daily_has_not_fired_is_flagged() -> None:
    w = _active("ew_1", kind="date", until="2026-09-29", wake_brief=CO)
    row = _derive([_brief(state="missing", watch_id="ew_1")], watches=[w])
    assert any("在等的日子 2026-09-29 已到" in r for r in row["rewrite"]), row["rewrite"]
    assert row["rewrite_words"] == ["重看日到了"]


def test_the_board_carries_rewrite_watches_of_companies_without_a_current_v2_row() -> None:
    """現行敘事已撤回／是 v1／沒有敘事時，那筆該重寫的 watch 仍要在板上（整板清單），audit 才不會報錯主詞。"""
    from alpha.providers.candidates import board_rewrite

    fired = {"watch_id": "ew_w", "kind": "date", "status": "fired", "wake_brief": CO, "until": "2026-09-01",
             "expires": "2027-01-01"}
    out = board_rewrite([None], [], watches=[fired], company_ticker={CO: T})
    assert out == [{"kind": "watch", "ticker": T, "company_id": CO, "brief_id": None, "watch_id": "ew_w",
                    "state": "醒來", "note": "那家公司的現行敘事已撤回、是舊版或沒有敘事——板上沒有帶著它的 v2 列"}]
    row = _derive([_brief(state="missing", watch_id="ew_w")], watches=[fired])
    carried = board_rewrite([row], [], watches=[fired])
    assert [(b["watch_id"], b["state"]) for b in carried] == [("ew_w", "醒來")]   # 列帶著就不重複


def test_a_link_break_prefers_the_unresolved_reason_among_several_watches_on_one_key() -> None:
    from engine_b.narrative_watches import link_break_reason

    older = {"status": "consumed", "judgment": {"touches": "yes", "handled": None}}
    newer = {"status": "consumed", "closed": {"at": "2026-09-20T00:00:00+00:00"}}
    assert link_break_reason([older, newer])[0] == "touched"


def test_a_ride_whose_reading_row_is_missing_is_not_called_superseded() -> None:
    row = _derive([_brief(state="pass", reason="貴")], rows={("tech:other", "layer"): {"reading_id": "sr_z"}})
    assert row["rides"][0]["status"] == "not_found"
    row = _derive([_brief(state="pass", reason="貴")], rows=_rows(reading_id="sr_" + "b" * 16))
    assert row["rides"][0]["status"] == "superseded"


def test_load_board_lists_who_has_no_narrative_not_only_how_many(board_env) -> None:
    """2026-09-30 使用者回饋（「候選板是死的頁面」）：不上板的檔原本只有計數，看不到是誰（INV-3 的可見面）。
    清單與計數同一個來源（`derive_row` 回 None 的那幾檔），每檔帶首屏三個字——會死嗎照燈、兩題「未答」。"""
    from alpha.providers.candidates import load_board

    board = load_board([T, "ZZZ", "AAA"], today=TODAY,
                       holdings_loader=lambda: [{"ticker": "CASH", "shares": 0.0, "bucket": "CASH"}])
    listed = [r["ticker"] for r in board["no_narrative"]]
    assert listed == ["AAA", "ZZZ"] and board["counts"]["no_narrative"] == len(listed)
    assert T not in listed                                                  # 有敘事的在組裡，不在這份清單
    words = board["no_narrative"][0]["three_words"]
    assert words["priced_in"] == words["in_numbers"] == "未答" and words["will_it_die"] not in ("未讀到", "未答")


def test_no_narrative_rows_keep_the_three_questions_read_failure_reason(board_env) -> None:
    """讀不到三題的那一檔也要在清單上，而且說得出為什麼讀不到——不是安靜少一檔（INV-3）。"""
    from alpha.providers.candidates import load_board

    board_env["tq_fail"].add("ZZZ")
    board = load_board([T, "ZZZ"], today=TODAY,
                       holdings_loader=lambda: [{"ticker": "CASH", "shares": 0.0, "bucket": "CASH"}])
    assert board["no_narrative"][0]["three_words"]["will_it_die"] == "未讀到（OperationalError: locked）"


def test_rides_carry_chinese_unit_and_kind_labels_from_the_reading_vocabulary() -> None:
    """候選板印 `volume`／`layer` 看不懂（2026-09-30）：標籤跟著列走，取自讀圖 contracts（唯一字彙）。"""
    from alpha.structure_reading.contracts import READING_KINDS

    brief = _brief(state="pass", reason="貴")
    ride = _derive([brief])["rides"][0]
    assert ride["unit_label"] == "層" and ride["kind_label"] == READING_KINDS["volume"].split("——")[0]
    gone = _derive([brief], rows={("tech:other", "layer"): {"reading_id": "sr_z"}})["rides"][0]
    assert gone["status"] == "not_found" and gone["kind_label"] is None and gone["unit_label"] == "層"


# ---------------------------------------------------------------------------
# 敘事落後於讀圖與圖（ROADMAP「敘事 stale 計數器」①③，2026-10-29）：候選板是唯一 owner，心跳 ⑤ 讀它的清單
# ---------------------------------------------------------------------------

NEW_READ = "sr_" + "b" * 16


def _version(*, days_ago, supersedes=None, refs=("graph://x",), our_bet="賭層的量。", ride=READ):
    slots = {k: {**v, "evidence_refs": list(refs)} for k, v in _slots().items()}
    slots["our_bet"]["text"] = our_bet
    rec = brief_record(company_id=CO, ticker=T, slots=slots, record_version=RECORD_VERSION_V2,
                       rides=[{"node": "tech:x", "unit": "layer", "reading_id": ride}],
                       answers={"priced_in": "yes", "in_numbers": "yes"},
                       candidate_state={"state": "pass", "watch_id": None, "reason": "貴"}, supersedes_id=supersedes,
                       created_at=datetime(2026, 9, 29, 3, tzinfo=timezone.utc) - timedelta(days=days_ago))
    return parse_brief_record(rec)


def _assertion(at, *, doc="doc_new", url=None, relation="supplies_to", dst="co:cust"):
    return {"src": CO, "relation": relation, "dst": dst, "updated_at": at, "doc_id": doc, "url": url}


def test_the_body_version_skips_rerides_but_not_a_rewritten_slot() -> None:
    """換騎包裝成的新版不算重寫過正文（③ 的起點是正文最後一次改動，不是最新一版的日期）。"""
    from alpha.candidates import body_version

    v1 = _version(days_ago=5)
    reride = _version(days_ago=1, supersedes=v1.brief_id, ride=NEW_READ)
    assert body_version([v1, reride], reride).brief_id == v1.brief_id
    rewritten = _version(days_ago=0, supersedes=reride.brief_id, ride=NEW_READ, our_bet="賭層的量，第二家客戶也來了。")
    assert body_version([v1, reride, rewritten], rewritten).brief_id == rewritten.brief_id


@pytest.mark.parametrize("url, expected", [
    ("https://www.Example.com/IR/a.pdf#page=3", "example.com/IR/a.pdf"), ("http://example.com/", "example.com"),
    ("https://example.com/x.", "example.com/x"), ("ftp://example.com/x", None), (None, None),
    ("library/raw/x.txt", None),
])
def test_urls_are_compared_without_scheme_www_anchor_or_trailing_slash(url, expected) -> None:
    from alpha.candidates import normalize_url

    assert normalize_url(url) == expected


def test_cited_identities_read_every_ref_form() -> None:
    from alpha.candidates import cited_identities

    brief = _version(days_ago=0, refs=("graph://source/doc_a", f"graph://edge/{CO}/supplies_to/co:cust",
                                       "library/raw/nittobo_2026.txt", "https://www.x.com/p#s"))
    cited = cited_identities(brief)
    assert cited.docs == {"doc_a", "nittobo_2026"} and cited.urls == {"x.com/p"}
    assert cited.edges == {(CO, "supplies_to", "co:cust")} and cited.raw_refs == ("library/raw/nittobo_2026.txt",)


def test_unread_new_edges_count_only_edges_the_narrative_never_read() -> None:
    """以邊為單位：任何一筆來源讀過（doc id、直接引的網址，或逐字在敘事引的 raw 檔裡）、或直接引了那條邊＝讀過；
    同一輪先寫敘事再入圖的不算落後（2026-10-29 量測 4 份）；時間讀不懂的當新的。"""
    from alpha.candidates import Cited, squash, unread_new_edges

    since = datetime(2026, 10, 1, tzinfo=timezone.utc)
    cited = Cited(frozenset({"doc_cited"}), frozenset({"n.com/page"}), frozenset({(CO, "competes_with", "co:rival")}),
                  ("library/raw/excerpt_a.txt",))
    text = squash("…NER ガラスの需要は AI サーバー向けで\n非常に伸びており…")          # 敘事引的那份節錄
    rows = [
        _assertion("2026-10-10T00:00:00+00:00", doc="doc_new", url="https://n.com/1", dst="co:new"),
        _assertion("2026-09-01T00:00:00+00:00", doc="doc_old", dst="co:old"),                    # 舊邊
        _assertion("2026-09-01T00:00:00+00:00", doc="doc_cited", dst="co:same_round"),           # 舊來源引過…
        _assertion("2026-10-02T00:00:00+00:00", doc="doc_more", dst="co:same_round"),            # …同一條邊的新來源不算
        _assertion("2026-10-03T00:00:00+00:00", doc="doc_page", url="https://www.n.com/page/", dst="co:page"),
        _assertion("2026-10-04T00:00:00+00:00", doc="doc_x", relation="competes_with", dst="co:rival"),
        _assertion("not a time", doc="doc_bad", dst="co:bad"),
        _assertion("2026-10-05T00:00:00", doc="doc_naive", dst="co:naive"),                      # 沒時區＝UTC
        _assertion("2026-09-30T23:00:00", doc="doc_naive_old", dst="co:naive_old"),
        # 3110.T 型：圖上另一個名字，逐字就在敘事引的檔裡（空白、換行不算差別）＝讀過
        dict(_assertion("2026-10-06T00:00:00+00:00", doc="graph_name", dst="co:renamed"),
             quotes=["NER ガラスの需要は AI サーバー向けで 非常に伸びており"]),
        # 9856.HK 型：同一份招股書的另一段節錄，逐字不在敘事引的檔裡＝沒讀過（比網址會當成讀過）
        dict(_assertion("2026-10-07T00:00:00+00:00", doc="other_excerpt", dst="co:lpo"),
             quotes=["We offer 1.6T optical transceivers in three primary architectural approaches"]),
        dict(_assertion("2026-10-08T00:00:00+00:00", doc="doc_blank", dst="co:blank"), quotes=["  \n "]),  # 空逐字不算
    ]
    out = unread_new_edges(rows, since=since, cited=cited, cited_text=text)
    assert [(e["dst"], e["at"], e["docs"]) for e in out] == [
        ("co:bad", None, ["doc_bad"]), ("co:naive", "2026-10-05T00:00:00+00:00", ["doc_naive"]),
        ("co:lpo", "2026-10-07T00:00:00+00:00", ["other_excerpt"]),
        ("co:blank", "2026-10-08T00:00:00+00:00", ["doc_blank"]),
        ("co:new", "2026-10-10T00:00:00+00:00", ["doc_new"])]
    # 沒給 raw 全文（讀不到檔）：比不到逐字的那一條照列——往看得見那邊倒
    assert "co:renamed" in [e["dst"] for e in unread_new_edges(rows, since=since, cited=cited)]


def test_raw_text_stays_inside_the_raw_library() -> None:
    from alpha.providers.candidates import raw_text

    assert raw_text("library/raw/../../AGENTS.md") == "" and raw_text("library/raw/沒有這個檔.txt") == ""


def test_a_row_lists_new_edges_since_the_body_was_written_and_says_not_checked_without_the_graph() -> None:
    v1 = _version(days_ago=5)
    reride = _version(days_ago=0, supersedes=v1.brief_id, ride=NEW_READ)     # 換騎：正文沒變，起點仍是 v1
    middle = (datetime(2026, 9, 29, 3, tzinfo=timezone.utc) - timedelta(days=2)).isoformat()
    rows = _rows(reading_id=NEW_READ)
    row = _derive([v1, reride], rows=rows, assertions=[_assertion(middle)])
    assert [e["docs"] for e in row["rewrite_new_edges"]] == [["doc_new"]]
    assert f"圖上有新邊、敘事沒讀過：{CO} -supplies_to-> co:cust（2026-09-27 寫入；文件 doc_new）" in row["rewrite"]
    assert row["rewrite_words"] == ["新邊沒讀"]
    unread = _derive([v1, reride], rows=rows, assertions=None)
    assert unread["rewrite_new_edges"] is None and unread["rewrite_words"] == []          # 沒算，不是 0
    clean = _derive([v1, reride], rows=rows, assertions=[])
    assert clean["rewrite_new_edges"] == [] and clean["rewrite"] == []


def test_a_row_reads_the_cited_raw_files_to_decide_what_was_read() -> None:
    """9856.HK（2026-10-29）：敘事引的是招股書一段節錄；同一份招股書另一段入圖的邊，逐字在節錄裡的（CW-DFB）讀過，
    不在的（LPO）沒讀過。只讀敘事引的那幾份 raw 檔。"""
    from alpha.candidates import squash

    refs = ("library/raw/ligent_excerpt.txt",)
    later = datetime(2026, 9, 29, 5, tzinfo=timezone.utc).isoformat()
    seen = dict(_assertion(later, doc="ligent_full", dst="tech:cw_dfb"), quotes=["75mW and 100mW high-power CW-DFB"])
    unseen = dict(_assertion(later, doc="ligent_full", dst="tech:lpo"), quotes=["three primary architectural approaches"])
    calls: list[str] = []

    def text(ref: str) -> str:
        calls.append(ref)
        return squash("…including 75mW and 100mW high-power\nCW-DFB laser chips…")

    row = _derive([_version(days_ago=0, refs=refs)], assertions=[seen, unseen], raw_text=text)
    assert [e["dst"] for e in row["rewrite_new_edges"]] == ["tech:lpo"] and calls == list(refs)
    # 兩份檔的頭尾接起來不得湊出一段假的逐字
    files = {"library/raw/a.txt": squash("…three primary"), "library/raw/b.txt": squash("architectural approaches…")}
    split = _derive([_version(days_ago=0, refs=tuple(files))], assertions=[unseen], raw_text=files.__getitem__)
    assert [e["dst"] for e in split["rewrite_new_edges"]] == ["tech:lpo"]


def test_riding_a_superseded_reading_is_a_rewrite_reason_that_names_the_current_reading() -> None:
    row = _derive([_brief(state="pass", reason="貴")], rows=_rows(reading_id=NEW_READ))
    assert row["rewrite_rides"] == [{"node": "tech:x", "unit": "layer", "reading_id": READ,
                                     "current_reading_id": NEW_READ}]
    assert row["rewrite"] == [f"騎的讀圖已換版：{READ}（tech:x；現行 {NEW_READ}）"] and row["rewrite_words"] == ["騎舊讀圖"]
    gone = _derive([_brief(state="pass", reason="貴")], rows={("tech:other", "layer"): {"reading_id": "sr_z"}})
    assert gone["rewrite_rides"] == []          # 那一格沒有讀圖列＝讀不到，不是換版


def test_the_board_list_carries_rides_and_new_edges_for_the_ledger_to_read() -> None:
    from alpha.providers.candidates import board_rewrite

    edge = {"src": CO, "relation": "supplies_to", "dst": "co:cust", "at": "2026-09-27T03:00:00+00:00", "docs": ["d"]}
    ride = {"node": "tech:x", "unit": "layer", "reading_id": READ, "current_reading_id": NEW_READ}
    row = {"ticker": T, "company_id": CO, "brief_id": "ib_1", "rewrite_watch_ids": [], "rewrite_rides": [ride],
           "rewrite_new_edges": [edge]}
    out = board_rewrite([row, dict(row, ticker="ZZZ", rewrite_rides=[], rewrite_new_edges=None)], [])
    who = {"ticker": T, "company_id": CO, "brief_id": "ib_1"}
    assert out == [{"kind": "rides", **who, **ride}, {"kind": "new_edges", **who, "edges": [edge]}]


def test_load_board_reads_the_graph_once_and_says_when_it_could_not(board_env, _isolate_company_assertions,
                                                                     monkeypatch) -> None:
    from alpha.providers.candidates import load_board
    from query import company_assertions

    def cash():
        return [{"ticker": "CASH", "shares": 0.0, "bucket": "CASH"}]

    _isolate_company_assertions[CO] = [_assertion("2026-09-28T12:00:00+00:00")]      # ledger 那一版 09-28 00:00 寫的
    board = load_board([T], today=TODAY, holdings_loader=cash)
    assert board["new_edges_check"] == {"status": "ok", "reason": None}
    assert [(b["kind"], b["ticker"]) for b in board["narrative_rewrite"]] == [("new_edges", T)]

    def down():
        raise SystemExit("請設 NEO4J_PASSWORD")          # `_graph_driver` 缺密碼丟的是 SystemExit，不是 Exception

    monkeypatch.setattr(company_assertions, "load_company_assertions", down)
    board = load_board([T], today=TODAY, holdings_loader=cash)
    assert board["new_edges_check"]["status"] == "unavailable" and "SystemExit" in board["new_edges_check"]["reason"]
    assert board["narrative_rewrite"] == []
# ---------------------------------------------------------------------------
# 缺 X 三分法與文件請求（ROADMAP「缺 X 三分法與文件請求上限」；failure log #117；2026-10-30）
# ---------------------------------------------------------------------------

def test_missing_kind_is_declared_only_on_missing_and_open_document_requests_ride_the_row() -> None:
    """`missing_kind` 只有缺 X 能帶、字彙封閉、沒寫就不進 payload（舊紀錄的 brief_id 不變）；待辦池開著的文件請求併到列上，
    計數分「已開口／可拿未開口／未分」；池沒讀到（None）前兩格是 None＝未算，不印 0（INV-3）。"""
    from alpha.candidates import missing_request_counts
    from alpha.errors import ContractViolation
    from alpha.narrative.contracts import CandidateState

    with pytest.raises(ContractViolation, match="missing_kind 只有"):
        CandidateState(state="open", missing_kind="filing")
    with pytest.raises(ContractViolation, match="missing_kind 必須是"):
        CandidateState(state="missing", watch_id="ew_1", missing_kind="broker")
    assert "missing_kind" not in CandidateState(state="missing", watch_id="ew_1").as_dict()
    assert CandidateState(state="missing", watch_id="ew_1", missing_kind="user_document").as_dict()["missing_kind"] == "user_document"

    rec = brief_record(company_id=CO, ticker=T, slots=_slots(), record_version=RECORD_VERSION_V2,
                       rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}],
                       answers={"priced_in": "yes", "in_numbers": "yes"},
                       candidate_state={"state": "missing", "watch_id": "ew_1", "reason": "客戶具名", "missing_kind": "user_document"},
                       created_at=datetime(2026, 9, 29, 3, tzinfo=timezone.utc))
    brief = parse_brief_record(rec)
    assert brief.candidate_state.missing_kind == "user_document"
    watches = [_active("ew_1", kind="date", wake_brief=CO, until="2026-11-14")]
    asked = derive_row(T, CO, records=[brief], today=TODAY, reading_rows=_rows(), watches=watches, lifecycle={}, edge=EDGE,
                       three_questions=_tq(), held=HELD_NONE, open_document_requests=[897])
    unasked = _derive([brief], watches=watches)                  # 沒給池（單檔頁、測試）＝None
    assert asked["group"] == "missing" and asked["missing_kind"] == "user_document" and asked["document_requests"] == [897]
    assert unasked["document_requests"] is None
    assert missing_request_counts([asked]) == {"asked": 1, "fetchable_unasked": 0, "unclassified": 0}
    assert missing_request_counts([dict(asked, document_requests=[])]) == {"asked": 0, "fetchable_unasked": 1, "unclassified": 0}
    assert missing_request_counts([unasked]) == {"asked": None, "fetchable_unasked": None, "unclassified": 0}
    legacy = _derive([_brief(state="missing", watch_id="ew_1")], watches=watches)
    assert legacy["missing_kind"] is None
    assert missing_request_counts([dict(legacy, document_requests=[])]) == {"asked": 0, "fetchable_unasked": 0, "unclassified": 1}
    board = assemble_board([dict(asked), dict(legacy, document_requests=[])], universe=[T], held=HELD_NONE, narrative_rewrite=[])
    assert board["counts"]["missing_asked"] == 1 and board["counts"]["missing_unclassified"] == 1
