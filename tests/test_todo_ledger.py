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


# ---------------------------------------------------------------------------
# 一、涵蓋登記表：每一種狀態都有去處
# ---------------------------------------------------------------------------

def _vocabularies() -> dict[str, set[str]]:
    from alpha.candidates import GROUPS, SIDE_GROUPS
    from alpha.providers.stories import STORY_GAP_KINDS
    from alpha.structure_reading.staleness import READING_STATUSES
    from crons.heartbeat import THESIS_STATUSES
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
    }


@pytest.mark.parametrize("prefix", ["lead", "segment", "watch", "expiry", "dispatch", "hypothesis", "thesis",
                                    "candidate", "reading", "story"])
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
                  candidates={"counts": {}, "new_edges_check": {"status": "ok"}}, thesis_due=[])
    loaders = {"classification_gaps": lambda: [], "undisposed": lambda: [], "parked_without_expiry": lambda: [],
               "stale_lead_entities": lambda: 0, "story_gaps": lambda: []}
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


def test_a_waiting_narrative_may_have_several_wake_watches() -> None:
    """AXTI：候選狀態指 ew_0148，財報後另登一筆 ew_1433——兩筆都在等，不是孤兒。"""
    watches = [{"watch_id": "ew_0148", "status": "active", "wake_brief": "co:axt"},
               {"watch_id": "ew_1433", "status": "active", "wake_brief": "co:axt"}]
    assert tl.orphan_wake_briefs(watches, [_brief("co:axt", state="priced_wait")]) == []
    assert tl.orphan_wake_briefs(watches, []) == ["ew_0148", "ew_1433"]          # 沒有現行敘事（撤回）


def _board(*items, check: str = "ok"):
    return {"counts": {}, "narrative_rewrite": list(items), "new_edges_check": {"status": check}}


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


def test_kinds_the_ledger_does_not_own_are_not_counted_twice() -> None:
    """連結斷與 watch 待重寫 ⑤ 自己由 watch registry 算；候選板清單裡的同一件事不再加一次。"""
    board = _board({"kind": "link", "ticker": "A", "company_id": "co:a"},
                   {"kind": "watch", "ticker": "A", "company_id": "co:a", "watch_id": "ew_1"})
    assert _collect(candidates=board)["todo.narrative"].count == 0


@pytest.mark.parametrize("candidates, note", [
    (None, "候選板未讀到——騎舊讀圖、新邊沒讀、已回落、前提失效沒算進來"),
    ({"counts": {}, "narrative_rewrite": [], "new_edges_check": {"status": "unavailable", "reason": "SystemExit"}},
     "新邊沒讀這次沒算（候選板沒讀到圖）"),
    ({"counts": {}, "narrative_rewrite": []}, "新邊沒讀這次沒算（候選板沒讀到圖）"),   # 改版前的舊 artifact
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


def test_edge_without_narrative_ignores_non_edge_companies() -> None:
    board = {"counts": {}, "no_narrative": [{"ticker": "AAPL", "edge": {"state": "not_edge"}},
                                             {"ticker": "TINY", "edge": {"state": "edge"}}]}
    rows = _collect(candidates=board)
    assert rows["todo.edge_no_narrative"].count == 1 and rows["todo.edge_no_narrative"].work == "TINY"


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
