"""待做清單（短版 ⑤）與涵蓋登記表（2026-10-22 使用者：「要確保以後的東西都不會被計數漏掉」）。

這支測試的重點是第一段：**系統裡每一種狀態都要登記去處**（⑤ 的哪一格、③、有到期的等事件、機械段、終局、題庫、
Phase plan）。狀態清單一律從各自的 SSOT 列舉——以後誰新增一種 lead／watch／pq2／假說／thesis／候選／讀圖狀態、
或一個佇列段、一種到期類型，沒有登記就在這裡紅（L14：會自己出現的計數器才算防呆）。
"""
from __future__ import annotations

import ast
import inspect
from datetime import date
from types import SimpleNamespace

import pytest

from engine_b import todo_ledger as tl

TODAY = date(2026, 10, 22)
#: 候選板「何時格的裁決點」兩半都核了（2026-11-10）——沒帶這一格的板，⑤ 會多一句「只核了日期」
CHECKPOINT_OK = {"status": "ok", "filings": "ok", "calendar": "ok", "reason": None}


# ---------------------------------------------------------------------------
# 一、涵蓋登記表：每一種狀態都有去處
# ---------------------------------------------------------------------------

def _vocabularies() -> dict[str, set[str]]:
    from alpha.candidates import GROUPS, SIDE_GROUPS
    from alpha.providers.fact_anchors import ANCHOR_SCOPE
    from alpha.providers.fact_checks import FACT_CHECK_GAP_KINDS
    from alpha.providers.stories import STORY_GAP_KINDS
    from alpha.structure_reading.staleness import READING_STATUSES
    from crons.heartbeat import THESIS_STATUSES
    from engine_b import admission_audit
    from engine_b import event_watch as ew
    from engine_b import hypotheses, leads
    from engine_b import queue_segments as qs

    return {
        "lead": set(leads.ALL_STATUSES),
        "segment": {s.key for s in qs.SEGMENTS},
        "watch": set(qs.WATCH_STATUSES),
        "expiry": set(ew.EXPIRY_CLASSES),
        "dispatch": {str(d) if d else "none" for d in qs.DISPATCH_STATUSES},
        "hypothesis": set(hypotheses.HYPOTHESIS_STATUSES),
        "thesis": set(THESIS_STATUSES),
        "candidate": set(GROUPS) | set(SIDE_GROUPS) | {"no_narrative"},
        "reading": set(READING_STATUSES),
        "story": set(STORY_GAP_KINDS),
        "fact_check": set(FACT_CHECK_GAP_KINDS),
        "fact_anchor": set(ANCHOR_SCOPE),
        "admission_audit": set(admission_audit.AUDIT_STATES),
    }


@pytest.mark.parametrize("prefix", ["lead", "segment", "watch", "expiry", "dispatch", "hypothesis", "thesis",
                                    "candidate", "reading", "story", "fact_check", "fact_anchor", "admission_audit"])
def test_every_state_in_every_vocabulary_has_a_registered_destination(prefix: str) -> None:
    missing = sorted(v for v in _vocabularies()[prefix] if f"{prefix}:{v}" not in tl.COVERAGE)
    assert not missing, (f"{prefix} 有狀態沒登記去處：{missing}——新增狀態時先在 engine_b/todo_ledger.py 的 COVERAGE "
                         "寫它落在 ⑤ 哪一格、或為什麼不是研究待做（③／等事件／機械段／終局／題庫／Phase plan）")


def test_every_destination_is_a_ledger_cell_or_a_declared_non_todo() -> None:
    bad = {k: v for k, v in tl.COVERAGE.items() if v not in tl.LEDGER_BY_KEY and v not in tl.DESTINATIONS}
    assert not bad


def test_every_ledger_cell_is_the_destination_of_something() -> None:
    """沒有任何狀態指到的格是死格——它恆為 0，會讓人以為那類事情被看著。"""
    targets = set(tl.COVERAGE.values())
    assert not [r.key for r in tl.LEDGER if r.key not in targets]


def test_expiry_classes_constant_matches_the_function_body() -> None:
    from engine_b import event_watch as ew

    tree = ast.parse(inspect.getsource(ew.expiry_class))
    returned = {n.value.value for n in ast.walk(tree) if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)}
    assert returned == set(ew.EXPIRY_CLASSES)


def test_the_snapshot_carries_every_ledger_cell_and_the_brief_reads_the_ledger() -> None:
    from crons.daily_brief import TODO_COUNTERS
    from crons.heartbeat import SNAPSHOT_KEYS

    assert set(tl.LEDGER_KEYS) <= set(SNAPSHOT_KEYS)
    assert [k for k, _ in TODO_COUNTERS] == list(tl.LEDGER_KEYS)
    # 「等你提供的文件」是使用者的動作：只住 ③b，不算研究待做
    assert "pq2.source_trace_review" not in dict(TODO_COUNTERS)


# ---------------------------------------------------------------------------
# 二、每一格的計數規則
# ---------------------------------------------------------------------------

def _brief(company: str, *, state: str = "missing", brief_id: str = "ib_1", ticker: str = "T", rides=()):
    return SimpleNamespace(company_id=company, ticker=ticker, brief_id=brief_id,
                           candidate_state=SimpleNamespace(state=state, watch_id="ew_x"), rides=tuple(rides),
                           disproof=(), retracted=False)


def _collect(**over):
    params = dict(today=TODAY, leads_store={"leads": {}}, watches=[], todo_items=[], hypotheses=[], briefs=[],
                  reading_needs_reread=0, layer_note_reread=0,
                  candidates={"counts": {}, "new_edges_check": {"status": "ok"},
                              "reading_change_check": {"status": "ok", "unchecked": 0},
                              "checkpoint_check": CHECKPOINT_OK}, thesis_due=[])
    loaders = {"classification_gaps": lambda: [], "undisposed": lambda: [], "parked_without_expiry": lambda: [],
               "stale_lead_entities": lambda: 0, "story_gaps": lambda: [], "pending_admission": lambda: {},
               "pending_cohort": lambda: {}, "fact_check_gaps": lambda: [], "fact_anchor_gaps": lambda: []}
    loaders.update(over.pop("loaders", {}))       # 只換掉測試點名的那幾個；其餘不讀真的 ledger
    params.update(over, loaders=loaders)
    return {row.key: row for row in tl.collect(**params)}


def test_unclassified_leads_are_their_own_cell_and_not_double_counted_in_leads() -> None:
    leads = {"leads": {"a": {"status": "triaged_go"}, "b": {"status": "triaged_go"}, "c": {"status": "researching"}}}
    rows = _collect(leads_store=leads, loaders={"classification_gaps": lambda: [{"lead_id": "b"}],
                                                "undisposed": lambda: [], "parked_without_expiry": lambda: [],
                                                "stale_lead_entities": lambda: 0})
    assert rows["todo.unclassified"].count == 1
    assert rows["todo.leads"].count == 2 and "缺分類" in rows["todo.leads"].note


def test_narrative_source_watches_are_not_counted_as_unchecked() -> None:
    """舊 ⑤ 把敘事來源的醒來同時算進「未檢」與「敘事該重寫」；現在照佇列段分開。"""
    reading = {"watch_id": "ew_1", "status": "fired", "kind": "semantic_condition", "source_ref": "reading:sr_1#1",
               "disproof_ref": "reading:sr_1#1", "woken_by": {"at": "2026-10-20T00:00:00+00:00"}}
    brief = {"watch_id": "ew_2", "status": "fired", "kind": "semantic_condition", "source_ref": "brief:ib_1#1",
             "disproof_ref": "brief:ib_1#1", "woken_by": {"at": "2026-10-21T00:00:00+00:00"}}
    wake = {"watch_id": "ew_3", "status": "fired", "kind": "date", "wake_brief": "co:a"}
    rows = _collect(watches=[reading, brief, wake], briefs=[_brief("co:a")])
    assert rows["todo.semantic"].count == 1 and rows["todo.semantic"].oldest_days == 2
    assert rows["todo.narrative"].count == 1          # 同一家公司（brief: 與 wake_brief）只算一檔
    assert "watch 醒 2 條" in rows["todo.narrative"].work


def test_broken_waits_catch_the_four_kinds_seen_on_2026_10_22() -> None:
    leads = {"leads": {"L1": {"status": "parked", "refs": {"trace_requires_user": "true"}},
                       "L2": {"status": "parked", "refs": {"trace_requires_user": "true", "pq2_ref": "701"}}}}
    watches = [{"watch_id": "ew_9", "status": "active", "wake_brief": "co:pass"},
               {"watch_id": "ew_8", "status": "active", "wake_brief": "co:wait"}]
    hyps = [{"hypothesis_id": "hy_1", "status": "active"}, {"hypothesis_id": "hy_2", "status": "verified"}]
    rows = _collect(leads_store=leads, watches=watches, hypotheses=hyps,
                    briefs=[_brief("co:pass", state="pass"), _brief("co:wait", state="priced_wait", brief_id="ib_2")],
                    loaders={"classification_gaps": lambda: [], "undisposed": lambda: [],
                             "parked_without_expiry": lambda: [{"lead_id": "L9"}], "stale_lead_entities": lambda: 0})
    row = rows["todo.broken_waits"]
    assert row.count == 4                              # 停放沒到期 1＋等使用者沒 pq2 1＋敘事不等的喚醒 1＋假說沒 watch 1
    assert all(w in row.work for w in ("停放沒到期 1", "等使用者卻沒 pq2 1", "敘事不等的喚醒 watch 1", "假說沒 watch 1"))


def test_requires_user_without_pq2_sees_open_todo_items_pointing_back() -> None:
    """對稱面同 `leads.parked_without_expiry`：「向你要文件」的 pq2 項目以 ref_id 指回 lead、lead 不回寫 pq2_ref——
    開著的項目算有 pq2；已結案的不算（2026-10-31 實測 [897]–[899] 三則全被算成接不上）。"""
    leads = {"L1": {"status": "parked", "refs": {"trace_requires_user": "true"}},
             "L2": {"status": "parked", "refs": {"trace_requires_user": "true"}},
             "L3": {"status": "parked", "refs": {"trace_requires_user": "true"}}}
    items = [{"ref_id": "L2", "resolved_at": None}, {"ref_id": "L3", "resolved_at": "2026-10-30T00:00:00+00:00"}]
    assert tl.requires_user_without_pq2(leads, [], items) == ["L1", "L3"]
    rows = _collect(leads_store={"leads": leads}, todo_items=items)
    assert "等使用者卻沒 pq2 2" in rows["todo.broken_waits"].work


def test_a_waiting_narrative_may_have_several_wake_watches() -> None:
    """AXTI：候選狀態指 ew_0148，財報後另登一筆 ew_1433——兩筆都在等，不是孤兒。"""
    watches = [{"watch_id": "ew_0148", "status": "active", "wake_brief": "co:axt"},
               {"watch_id": "ew_1433", "status": "active", "wake_brief": "co:axt"}]
    assert tl.orphan_wake_briefs(watches, [_brief("co:axt", state="priced_wait")]) == []
    assert tl.orphan_wake_briefs(watches, []) == ["ew_0148", "ew_1433"]          # 沒有現行敘事（撤回）


def _board(*items, check: str = "ok", reading_check: dict | None = None):
    return {"counts": {}, "narrative_rewrite": list(items), "new_edges_check": {"status": check},
            "reading_change_check": reading_check or {"status": "ok", "unchecked": 0},
            "checkpoint_check": CHECKPOINT_OK}


def test_a_narrative_riding_a_superseded_reading_needs_a_rewrite() -> None:
    """騎舊讀圖由候選板清單帶進來（kind=rides；候選板是唯一 owner）——⑤ 不自己再讀讀圖算一份。"""
    ride = {"kind": "rides", "ticker": "A", "company_id": "co:a", "brief_id": "ib_1", "node": "tech:x",
            "unit": "layer", "reading_id": "sr_old", "current_reading_id": "sr_new"}
    rows = _collect(candidates=_board(ride, dict(ride, node="tech:y")))
    row = rows["todo.narrative"]
    assert row.count == 1 and "騎舊讀圖 1（A）" in row.work and row.note is None   # 同一檔騎兩份舊讀圖只算一檔


def test_new_edges_the_narrative_never_read_count_once_per_company_and_name_it() -> None:
    """敘事 stale ③：正文寫完後圖上有新邊、敘事沒讀過——點名是哪幾檔（drain 照名字去改）；同一檔同時有 watch 醒
    與新邊沒讀只算一檔。"""
    brief_watch = {"watch_id": "ew_2", "status": "fired", "kind": "semantic_condition", "source_ref": "brief:ib_1#1",
                   "disproof_ref": "brief:ib_1#1", "woken_by": {"at": "2026-10-21T00:00:00+00:00"}}
    edges = {"kind": "new_edges", "ticker": "T", "company_id": "co:a", "brief_id": "ib_1",
             "edges": [{"src": "co:a", "relation": "SUPPLIES", "dst": "co:b", "at": "2026-10-20", "docs": ["d1"]}]}
    other = dict(edges, ticker="B", company_id="co:b", brief_id="ib_2")
    row = _collect(watches=[brief_watch], briefs=[_brief("co:a")], candidates=_board(edges, other))["todo.narrative"]
    assert row.count == 2 and "新邊沒讀 2（B、T）" in row.work and "watch 醒 1 條" in row.work


def test_reading_kind_and_supply_count_changes_are_named_and_counted_once_per_company() -> None:
    """敘事 stale ②④（2026-11-03）：候選板清單 kind=reading_kind／supply_count——⑤ 點名是哪幾檔；同一檔兩種都有只算一檔。"""
    base = {"ticker": "AEVA", "company_id": "co:aeva", "brief_id": "ib_1", "node": "tech:npo", "unit": "layer",
            "body_reading_id": "sr_old", "current_reading_id": "sr_new"}
    row = _collect(candidates=_board(dict(base, kind="reading_kind"), dict(base, kind="supply_count"),
                                     dict(base, kind="supply_count", ticker="COHR", company_id="co:cohr")))["todo.narrative"]
    assert row.count == 2 and row.note is None
    assert "判讀變了 1（AEVA）" in row.work and "家數變了 2（AEVA、COHR）" in row.work


def test_a_passed_checkpoint_is_named_and_counted_once_per_company() -> None:
    """何時格的裁決點已過（2026-11-10，failure log #150）：候選板清單 kind=checkpoint——⑤ 點名是哪幾檔；同一檔另有別的
    原因（騎舊讀圖）只算一檔。"""
    cp = {"kind": "checkpoint", "ticker": "PSIX", "company_id": "co:psix", "brief_id": "ib_1", "checkpoint_kind": "filing",
          "since": "2026-10-28", "form": "10-Q", "filed": "2026-11-05", "lead_id": "lead_x"}
    ride = {"kind": "rides", "ticker": "PSIX", "company_id": "co:psix", "brief_id": "ib_1", "node": "tech:x",
            "unit": "layer", "reading_id": "sr_old", "current_reading_id": "sr_new"}
    row = _collect(candidates=_board(cp, ride, dict(cp, ticker="AAOI", company_id="co:aaoi")))["todo.narrative"]
    assert row.count == 2 and row.note is None
    assert "裁決點過了 2（AAOI、PSIX）" in row.work and "騎舊讀圖 1（PSIX）" in row.work


def test_kinds_the_ledger_does_not_own_are_not_counted_twice() -> None:
    """連結斷與 watch 待重寫 ⑤ 自己由 watch registry 算；候選板清單裡的同一件事不再加一次。"""
    board = _board({"kind": "link", "ticker": "A", "company_id": "co:a"},
                   {"kind": "watch", "ticker": "A", "company_id": "co:a", "watch_id": "ew_1"})
    assert _collect(candidates=board)["todo.narrative"].count == 0


@pytest.mark.parametrize("candidates, note", [
    (None, "候選板未讀到——騎舊讀圖、判讀／家數變了、新邊沒讀、裁決點過了、前提失效沒算進來"),
    ({"counts": {}, "narrative_rewrite": [], "new_edges_check": {"status": "unavailable", "reason": "SystemExit"},
      "reading_change_check": {"status": "ok", "unchecked": 0}, "checkpoint_check": CHECKPOINT_OK},
     "新邊沒讀這次沒算（候選板沒讀到圖）"),
    ({"counts": {}, "narrative_rewrite": []},                                          # 改版前的舊 artifact：三種都沒算
     "新邊沒讀這次沒算（候選板沒讀到圖）；判讀／家數變了這次沒算（候選板沒讀到讀圖紀錄，或是舊板）；"
     "裁決點過了只核了日期——申報、佔位字那一半這次沒核（舊板沒有這一格）"),
    ({"counts": {}, "narrative_rewrite": [], "new_edges_check": {"status": "ok"},
      "reading_change_check": {"status": "ok", "unchecked": 2}, "checkpoint_check": CHECKPOINT_OK},
     "判讀／家數變了有 2 格沒比成（正文寫時騎的讀圖紀錄找不到）"),
    ({"counts": {}, "narrative_rewrite": [], "new_edges_check": {"status": "ok"},             # lead 池讀不到（2026-11-10）
      "reading_change_check": {"status": "ok", "unchecked": 0},
      "checkpoint_check": {"status": "partial", "filings": "unavailable", "calendar": "ok",
                           "reason": "lead 池讀不到（OSError: x）"}},
     "裁決點過了只核了日期——申報那一半這次沒核（lead 池讀不到（OSError: x））"),
])
def test_new_edges_not_checked_is_said_not_printed_as_zero(candidates, note) -> None:
    """圖或候選板讀不到時「新邊沒讀」是沒算，不是 0（INV-3）——而且**印出來**：0 的格也帶著註記。"""
    rows = _collect(candidates=candidates)
    assert rows["todo.narrative"].count == 0 and rows["todo.narrative"].note == note
    zero_line = tl.render_cells(list(rows.values()))[1]
    assert f"敘事該重寫（{note}）" in zero_line


def test_an_unreadable_source_is_none_not_zero() -> None:
    def boom():
        raise OSError("ledger 不在")

    rows = _collect(loaders={"classification_gaps": boom, "undisposed": lambda: [],
                             "parked_without_expiry": lambda: [], "stale_lead_entities": lambda: 0},
                    reading_needs_reread=None)
    assert rows["todo.unclassified"].count is None and "OSError" in rows["todo.unclassified"].reason
    assert rows["todo.reading"].count is None
    text = "\n".join(tl.render_cells(list(rows.values())))
    assert "未讀到（不是 0）" in text and "缺分類" in text.split("未讀到")[1]


def test_thesis_due_counts_only_what_has_not_been_minted() -> None:
    pool = [{"type": "thesis_lifecycle", "title": "thesis axt_inp 該核查", "resolved_at": None}]
    rows = _collect(todo_items=pool, thesis_due=["axt_inp", "sivers"])
    assert rows["todo.thesis_due"].count == 1 and rows["todo.thesis_due"].work == "sivers"


def test_story_gaps_count_per_company_and_split_never_from_a_new_brief_version() -> None:
    """⑤「故事還沒寫」＝`python -m alpha stories --gaps` 同一個判定（L16）：敘事換版的那檔照樣算——故事過期會自己出現。"""
    from alpha.providers.stories import STORY_GAP_KINDS, story_gaps

    briefs = [_brief("co:a", brief_id="ib_new", ticker="A"), _brief("co:b", brief_id="ib_b", ticker="B"),
              _brief("co:c", brief_id="ib_c", ticker="C")]
    gaps = story_gaps(briefs, stories={"ib_c": {"story_id": "st_c"}}, all_story_briefs={"ib_old": "co:a"})
    assert [(g["ticker"], g["kind"]) for g in gaps] == [("A", "stale"), ("B", "never")]
    assert {g["kind"] for g in gaps} == set(STORY_GAP_KINDS)
    row = _collect(loaders={"story_gaps": lambda: gaps})["todo.story"]
    assert row.count == 2 and row.work == "從沒寫 1；敘事換版 1"

    def boom():
        raise OSError("ledger 壞了")

    unread = _collect(loaders={"story_gaps": boom})["todo.story"]
    assert unread.count is None and "OSError" in unread.reason


def test_fact_check_gaps_count_per_version_grouped_by_the_board_and_unreadable_is_not_zero() -> None:
    """⑤「敘事還沒逐句核對」＝`python -m alpha brief-check --gaps` 同一個判定（L16）；工作量照候選板的組分（已持有先核）。"""
    since = "2026-10-20T00:00:00+00:00"
    gaps = [{"ticker": "A", "kind": "brief", "state": "open", "since": since},
            {"ticker": "B", "kind": "story", "state": "pass", "since": since},
            {"ticker": "H", "kind": "brief", "state": "open", "since": since}]
    board = {"counts": {}, "new_edges_check": {"status": "ok"}, "reading_change_check": {"status": "ok", "unchecked": 0},
             "checkpoint_check": CHECKPOINT_OK, "groups": {"held": [{"ticker": "H"}], "open": [{"ticker": "A"}]}}
    row = _collect(candidates=board, loaders={"fact_check_gaps": lambda: gaps})["todo.fact_check"]
    assert row.count == 3 and row.work == "已持有 1、可開 1、不要 1、其中故事換了 1" and row.oldest_days == 2
    # 板沒讀到：照敘事宣告的狀態分，註記照寫（INV-3）
    no_board = _collect(candidates=None, loaders={"fact_check_gaps": lambda: gaps})["todo.fact_check"]
    assert no_board.work == "可開 2、不要 1、其中故事換了 1" and "候選板沒讀到" in no_board.note

    def boom():
        raise OSError("ledger 壞了")

    unread = _collect(loaders={"fact_check_gaps": boom})["todo.fact_check"]
    assert unread.count is None and "OSError" in unread.reason


def test_fact_anchor_gaps_count_held_and_open_and_missing_holdings_is_unread() -> None:
    """⑤「事實句還沒錨點」＝`python -m alpha brief-anchor --gaps` 同一個判定（L16）；已持有要讀候選板的持股——讀不到是未讀到，
    不退回只數宣告可開（那會把已持有那一半當 0；INV-3）。"""
    since = "2026-11-13T00:00:00+00:00"
    gaps = [{"ticker": "H", "scope": "held", "facts": 4, "missing": 3, "since": since},
            {"ticker": "A", "scope": "open", "facts": 9, "missing": 9, "since": since}]
    board = {"counts": {}, "new_edges_check": {"status": "ok"}, "reading_change_check": {"status": "ok", "unchecked": 0},
             "checkpoint_check": CHECKPOINT_OK, "holdings": {"status": "ok"}, "groups": {"held": [{"ticker": "H"}]}}
    row = _collect(candidates=board, loaders={"fact_anchor_gaps": lambda: gaps})["todo.fact_anchor"]
    assert (row.count, row.work) == (2, "已持有 1、可開 1；沒錨點的事實句 12")
    unread = _collect(candidates=dict(board, holdings={"status": "error"}),
                      loaders={"fact_anchor_gaps": lambda: gaps})["todo.fact_anchor"]
    assert unread.count is None and "持股沒讀到" in unread.reason
    assert _collect(candidates=None, loaders={"fact_anchor_gaps": lambda: gaps})["todo.fact_anchor"].count is None
    assert _collect(candidates=board)["todo.fact_anchor"].count == 0


def test_edge_without_narrative_ignores_non_edge_companies() -> None:
    board = {"counts": {}, "no_narrative": [{"ticker": "AAPL", "edge": {"state": "not_edge"}},
                                             {"ticker": "TINY", "edge": {"state": "edge"}}]}
    rows = _collect(candidates=board)
    assert rows["todo.edge_no_narrative"].count == 1 and rows["todo.edge_no_narrative"].work == "TINY"


def test_edge_without_narrative_names_but_does_not_count_a_company_awaiting_admission() -> None:
    # failure log #51 的對稱面（2026-11-04 300757.SZ）：短檢查結論①的入圖包還在 pq2，閉環佇列判「不排」，⑤ 不得照舊叫人寫敘事
    board = {"counts": {}, "no_narrative": [{"ticker": "TINY", "edge": {"state": "edge"}},
                                             {"ticker": "300757.SZ", "edge": {"state": "edge"}}]}
    row = _collect(candidates=board, loaders={"pending_admission": lambda: {"300757.SZ": 905}})["todo.edge_no_narrative"]
    assert (row.count, row.work, row.note) == (1, "TINY", "300757.SZ 等入圖 [905]")

    def boom():
        raise OSError("待辦池壞了")

    unread = _collect(candidates=board, loaders={"pending_admission": boom})["todo.edge_no_narrative"]
    assert unread.count == 2 and "等入圖讀不到（OSError）" in unread.note    # 讀不到不扣、也不讓整格未讀到


def test_edge_without_narrative_names_but_does_not_count_a_company_awaiting_its_theme_cohort() -> None:
    # failure log #161（2026-11-12 [934]）：主題組提案還在 pq2，寫入端拒收第一份敘事、閉環佇列判「等主題組」——⑤ 不得照舊叫人寫
    board = {"counts": {}, "no_narrative": [{"ticker": "TINY", "edge": {"state": "edge"}},
                                             {"ticker": "6278.T", "edge": {"state": "edge"}},
                                             {"ticker": "3167.TW", "edge": {"state": "edge"}}]}
    row = _collect(candidates=board, loaders={"pending_cohort": lambda: {"6278.T": 934, "3167.TW": 934, "AAPL": 934}})[
        "todo.edge_no_narrative"]
    assert (row.count, row.work, row.note) == (1, "TINY", "等主題組 [934]：3167.TW、6278.T")

    both = _collect(candidates=board, loaders={"pending_admission": lambda: {"TINY": 905},
                                               "pending_cohort": lambda: {"6278.T": 934}})["todo.edge_no_narrative"]
    assert (both.count, both.note) == (1, "TINY 等入圖 [905]；等主題組 [934]：6278.T")

    def boom():
        raise OSError("待辦池壞了")

    unread = _collect(candidates=board, loaders={"pending_cohort": boom})["todo.edge_no_narrative"]
    assert unread.count == 3 and "等主題組讀不到（OSError）" in unread.note    # 讀不到不扣、也不讓整格未讀到


def test_edge_without_narrative_reads_the_cohort_proposal_from_the_pool_items() -> None:
    # 預設 loader 讀待辦池同一份（alpha.closure.pending_cohort_members；L16）：已結案的組不算
    board = {"counts": {}, "no_narrative": [{"ticker": "6278.T", "edge": {"state": "edge"}},
                                             {"ticker": "8021.TW", "edge": {"state": "edge"}}]}
    items = [{"n": 934, "frozen_spec": {"kind": "theme_cohort", "spec": {"members": [{"ticker": "6278.T"}]}}},
             {"n": 931, "resolved_at": "2026-11-12", "frozen_spec": {"kind": "theme_cohort",
                                                                     "spec": {"members": [{"ticker": "8021.TW"}]}}}]
    loaders = {"pending_cohort": None}
    row = _collect(candidates=board, todo_items=items, loaders=loaders)["todo.edge_no_narrative"]
    assert (row.count, row.work, row.note) == (1, "8021.TW", "等主題組 [934]：6278.T")


def test_pending_admission_tickers_resolves_the_focus_through_the_research_action(monkeypatch) -> None:
    from alpha.providers import closure as provider

    actions = {"ra_a": {"payload": {"focus_company_id": "co:robotechnik_intelligent"}}}
    monkeypatch.setattr("intake.actions.read_action", lambda ref_id: actions[ref_id])
    monkeypatch.setattr(provider, "_research_ticker", lambda cid, registry=None: {
        "co:robotechnik_intelligent": "300757.SZ"}.get(cid))
    pool = {"items": [{"n": 905, "type": "ra_admission", "ref_id": "ra_a"},
                      {"n": 906, "type": "ra_admission", "ref_id": "ra_missing"},          # 讀不到那一號就不算
                      {"n": 700, "type": "ra_admission", "ref_id": "ra_a", "resolved_at": "2026-11-01"},
                      {"n": 897, "type": "source_trace_review", "ref_id": "ra_a"}]}
    assert provider.pending_admission_tickers(pool) == {"300757.SZ": 905}


# ---------------------------------------------------------------------------
# 三、下一步貼：只由計數導出，而且會滅
# ---------------------------------------------------------------------------

def _counts(**values):
    base = {k: 0 for k in tl.LEDGER_KEYS}
    base.update({f"todo.{k}": v for k, v in values.items()})
    return base


def test_next_prompt_is_silent_when_everything_is_zero() -> None:
    assert tl.next_prompt(_counts()).startswith("今天沒有要貼的")


def test_next_prompt_orders_decisions_then_research_then_phase() -> None:
    text = tl.next_prompt(_counts(semantic=3), decision_batch="837 go", phase_step="7.1b")
    assert text.index("837 go") < text.index("/research-drain") and "未檢 3" in text and "/phase-run" not in text
    assert "/phase-run" in tl.next_prompt(_counts(), phase_step="7.1b")
    assert "掃題材" in tl.next_prompt(_counts(), theme_due=True)
    assert "48 小時內" in tl.next_prompt(_counts(disproof_touched=1))


def test_next_prompt_says_when_a_cell_was_not_read() -> None:
    counts = _counts()
    counts["todo.semantic"] = None
    assert "未讀到" in tl.next_prompt(counts)


def _ledger(**cells):
    """LedgerCount 序列：每格 (count, progress, oldest_days)；沒寫的格全 0。"""
    out = []
    for row in tl.LEDGER:
        count, progress, oldest = cells.get(row.key.removeprefix("todo."), (0, 0, None))
        out.append(tl.LedgerCount(row.key, row.label, count, oldest_days=oldest, progress=progress))
    return out


def test_next_prompt_pushes_drain_only_on_progress_or_age() -> None:
    """盲點修法 §1 第 2 條（整體盲點審查 2026-11-01 §1.3：十天 15 段 drain、候選狀態轉換 0）：格子非 0、但沒有一格歸零會讓
    哪一檔離決定更近、最老不到 7 天 → 只剩維護，不推 drain；題材到期照提。"""
    quiet = tl.next_prompt(_ledger(semantic=(3, 0, 2), leads=(5, 0, 3)), theme_due=True)
    assert quiet.startswith("只剩維護") and "掃題材" in quiet and "未檢 3" in quiet and "待深挖 lead 5" in quiet
    assert tl.next_prompt(_ledger(semantic=(3, 0, 2), addon_unchecked=(1, 1, 0))).startswith(
        "`/research-drain`（進展：加碼條件還沒查 1）")
    # 2026-11-03（第 18＋16 條）：敘事該重寫不再是進展格（它的進展件數「重開達成／已回落」隨等回落退役）
    assert tl.next_prompt(_ledger(semantic=(3, 0, 2), narrative=(1, 1, 0))).startswith("只剩維護")
    assert "進展：使用者 go 的工單 1" in tl.next_prompt(_ledger(leads=(2, 1, 1)))
    assert tl.next_prompt(_ledger(semantic=(3, 0, 8))).startswith("`/research-drain`（最老 8 天）")
    assert tl.next_prompt(_ledger(disproof_touched=(1, 1, None))).startswith(
        "`/research-drain`（反證觸及：48 小時內）（進展：反證觸及 1）")
    # 進展格算不出（候選板讀不到 → 加碼條件還沒查沒算）不是 0：照舊推（INV-3）
    assert tl.next_prompt(_ledger(semantic=(3, 0, 2), addon_unchecked=(None, None, None))).startswith(
        "`/research-drain`（進展格算不出，照舊推）")


def test_the_snapshot_path_makes_the_same_call() -> None:
    """SessionStart 只讀得到快照：`snapshot_progress` 存的兩個值讓 Mapping 路徑做同一個判斷；舊快照沒有這兩個鍵就照舊推。"""
    ledger = _ledger(semantic=(3, 0, 2))
    snap = {**{r.key: r.count for r in ledger}, **tl.snapshot_progress(ledger)}
    assert snap["todo.progress"] == 0 and snap["todo.oldest_days"] == 2
    assert tl.next_prompt(snap).startswith("只剩維護")
    assert tl.next_prompt({r.key: r.count for r in ledger}).startswith("`/research-drain`（進展格算不出")


def test_retired_price_kinds_are_no_longer_counted_and_addon_rows_are_progress() -> None:
    """2026-11-03（第 18＋16 條）：已回落、重開達成、沒寫重開三種隨等回落退役——候選板清單就算還帶著（舊板）也不數；
    進展改由「加碼條件還沒查」那一格給（候選板讀不到＝None，不是 0）。"""
    reopen = {"kind": "reopen_met", "ticker": "AXTI", "company_id": "co:axt", "brief_id": "ib_1"}
    rows = _collect(candidates=_board(reopen, dict(reopen, kind="no_reopen", ticker="X", company_id="co:x"),
                                      dict(reopen, kind="pulled_back", ticker="Y", company_id="co:y")))
    assert rows["todo.narrative"].count == 0
    assert set(tl.PROGRESS_LABELS) == {"todo.disproof_touched", "todo.confirm_touched", "todo.addon_unchecked",
                                       "todo.leads"}
    assert _collect(candidates=None)["todo.addon_unchecked"].progress is None
    assert rows["todo.semantic"].progress == 0 and rows["todo.leads"].progress == 0


# ---------------------------------------------------------------------------
# 四、敘事撤回或不再等：喚醒 watch 一起收（failure log #34 ⑥）
# ---------------------------------------------------------------------------

def _record(state: str | None, *, retracted: bool = False):
    return SimpleNamespace(brief_id="ib_new", supersedes_id="ib_old", retracted=retracted, company_id="co:a",
                           ticker="T", acknowledged_touched=(), disproof=(), confirm=(),
                           candidate_state=None if state is None else SimpleNamespace(state=state, watch_id=None))


@pytest.mark.parametrize("record, closed", [
    (_record(None, retracted=True), True), (_record("pass"), True), (_record("open"), True),
    (_record("missing"), False), (_record("priced_wait"), False)])
def test_wake_watches_close_when_the_narrative_stops_waiting(record, closed) -> None:
    from engine_b.narrative_watches import register_brief_watches

    data = {"watches": [{"watch_id": "ew_1", "status": "active", "wake_brief": "co:a"},
                        {"watch_id": "ew_2", "status": "active", "wake_brief": "co:b"}]}
    register_brief_watches(record, data=data, company_brief_ids=["ib_old", "ib_new"])
    assert (data["watches"][0]["status"] == "consumed") is closed
    assert data["watches"][1]["status"] == "active"
