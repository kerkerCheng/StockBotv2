"""佇列段序（engine_b/queue_segments.py）：封閉字彙、逐筆分類、反推觀測。

守的不是「分類對」，是**分不到段的狀態不得靜默**——那正是 2026-09-08 fired 39 筆、
forward view 27 檔沒人取的形狀。
"""
from __future__ import annotations

import pytest

from engine_b import queue_segments as qs


def test_registry_is_closed_and_every_segment_names_a_consumer() -> None:
    keys = [s.key for s in qs.SEGMENTS]
    assert len(keys) == len(set(keys))
    for seg in qs.SEGMENTS:
        assert seg.consumer.strip(), seg.key
        assert seg.cost in {"mechanical", "research"}, seg.key
    # 使用者定案的段（fired 重排／已核准工單／triaged_go／forward view／走圖）都在，
    # 外加前面的 pending 分流與後面的主動輪詢。
    for required in (
        "fired_lead_requeue", "approved_work_orders",
        "triaged_go_leads", "forward_view_backlog", "graph_holes", "fired_reading_reread",
    ):
        assert required in qs.SEGMENT_BY_KEY
    # 2026-09-26（Phase 2 Step 2.6）：三段併進 `graph_holes`（走圖第 4／7／8／9 型）。斷言翻面，不是刪掉——
    # 有人把它們加回來、又讓同一個洞在兩段各算一次，會變紅。
    for retired in ("coverage_gaps", "duplicate_node_candidates", "stale_structure_readings"):
        assert retired not in qs.SEGMENT_BY_KEY
    # 2026-09-22（Phase 0 Step 0a.1）：`reassess_stale` 隨 decision_lab 研究側退役。
    # 斷言翻面，不是刪掉——這樣「有人把它加回來」會變紅（ROADMAP Phase 0 驗收①）。
    assert "reassess_stale" not in qs.SEGMENT_BY_KEY


def test_a_segment_without_consumer_is_rejected_at_registry_level() -> None:
    bad = (qs.Segment("x", 9, "沒人取", "research", "   "),)
    with pytest.raises(qs.QueueSegmentError):
        # validate_registry 讀模組常數；用替身模組屬性驗同一條規則
        original = qs.SEGMENTS
        try:
            qs.SEGMENTS = bad  # type: ignore[misc]
            qs.validate_registry()
        finally:
            qs.SEGMENTS = original  # type: ignore[misc]


@pytest.mark.parametrize("status,expected", [
    ("pending", "pending_triage"),
    ("triaged_go", "triaged_go_leads"),
    ("researching", "triaged_go_leads"),
    ("action_prepared", None),
    ("parked", None),
    ("applied", None),
    ("triaged_no_go", None),
])
def test_every_known_lead_status_is_classified(status, expected) -> None:
    assert qs.classify_lead({"status": status}) == expected


def test_unknown_lead_status_surfaces_as_unmapped_not_none() -> None:
    assert qs.classify_lead({"status": "half_baked"}) == "unmapped:lead:half_baked"
    assert qs.classify_lead({}) == "unmapped:lead:<empty>"


def test_fired_watch_is_split_by_wake_target() -> None:
    assert qs.classify_watch({"status": "fired", "wake_pq2": 12}) == "fired_pq2_wake"
    assert qs.classify_watch({"status": "fired", "wake_lead": "lead_x"}) == "fired_lead_requeue"
    assert qs.classify_watch({"status": "fired", "hypothesis_ref": "h1"}) == "fired_hypothesis_check"
    assert qs.classify_watch({"status": "fired"}) == "fired_hypothesis_check"


def test_active_watch_is_work_only_when_pollable() -> None:
    assert qs.classify_watch({"status": "active"}) is None
    assert qs.classify_watch({"status": "active", "poll": {"eligible": True}}) == "pollable_watches"
    assert qs.classify_watch({"status": "consumed"}) is None
    assert qs.classify_watch({"status": "expired"}) is None
    assert qs.classify_watch({"status": "zombie"}) == "unmapped:watch:zombie"


def test_todo_item_is_work_only_when_dispatched() -> None:
    assert qs.classify_todo({"n": 1, "dispatch_status": "queued"}) == "approved_work_orders"
    assert qs.classify_todo({"n": 1, "dispatch_status": "researching"}) == "approved_work_orders"
    assert qs.classify_todo({"n": 1, "dispatch_status": "awaiting_approval"}) is None
    assert qs.classify_todo({"n": 1}) is None
    assert qs.classify_todo({"n": 1, "resolved_at": "2026-09-09"}) is None
    assert qs.classify_todo({"n": 1, "dispatch_status": "teleported"}) == "unmapped:todo:teleported"
    # 2026-09-22（Step 0a.1）：`reassess_only` 參數隨 reassess 段退役，呼叫端傳它要炸開，
    # 不得靜默被吃掉（否則舊呼叫端會以為自己還在餵那一段）。
    with pytest.raises(TypeError):
        qs.classify_todo({"n": 1}, reassess_only=True)  # type: ignore[call-arg]


def test_observe_counts_per_segment_and_keeps_none_distinct_from_zero() -> None:
    obs = qs.observe(
        leads={
            "a": {"lead_id": "a", "status": "pending"},
            "b": {"lead_id": "b", "status": "triaged_go"},
            "c": {"lead_id": "c", "status": "parked"},
        },
        watches=[
            {"watch_id": "w1", "status": "fired", "wake_lead": "c"},
            {"watch_id": "w2", "status": "fired", "wake_pq2": 5},
            {"watch_id": "w3", "status": "active", "poll": {"eligible": True}},
        ],
        todo_items=[
            {"n": 5, "dispatch_status": "queued"},
            {"n": 6},
            {"n": 7},
        ],
        forward_view_backlog=None,
        graph_holes=20,
    )
    by_key = {s["key"]: s["count"] for s in obs["segments"]}
    assert by_key["pending_triage"] == 1
    assert by_key["triaged_go_leads"] == 1
    assert by_key["fired_lead_requeue"] == 1
    assert by_key["fired_pq2_wake"] == 1
    assert by_key["pollable_watches"] == 1
    assert by_key["approved_work_orders"] == 1
    assert "reassess_stale" not in by_key
    assert by_key["forward_view_backlog"] is None      # 沒讀到 ≠ 0
    assert by_key["graph_holes"] == 20
    assert obs["unmapped"] == []
    assert obs["mechanical_total"] == 2               # fired lead＋fired pq2
    rendered = qs.render(obs)
    assert "未讀到" in rendered and "走圖" in rendered


def test_observe_reports_unmapped_states_instead_of_dropping_them() -> None:
    obs = qs.observe(
        leads={"z": {"lead_id": "z", "status": "mystery"}},
        watches=[{"watch_id": "w9", "status": "limbo"}],
        todo_items=[{"n": 3, "dispatch_status": "elsewhere"}],
    )
    assert len(obs["unmapped"]) == 3
    assert any("lead:mystery" in row for row in obs["unmapped"])
    assert any("watch:limbo" in row for row in obs["unmapped"])
    assert any("todo:elsewhere" in row for row in obs["unmapped"])
    assert "分不到段" in qs.render(obs)


# ---- Phase 3 Step 3.1a：`graph_holes` 的計數是「有命中的型別數」，不是異單位的命中筆數之和 ----

def _walk_questions(hits: list[int], absent: tuple[int, ...] = ()) -> list[dict]:
    return [{"key": f"t{i}", "short": f"型{i}", "hit_n": (None if i in absent else n), "scope_n": 10,
             "absence": ({"kind": "upstream_unavailable"} if i in absent else None)}
            for i, n in enumerate(hits)]


def test_graph_holes_count_is_the_number_of_types_with_hits() -> None:
    # 2026-09-29 基準的九型命中（4,2,2,0,4,6,9,10,23）：舊計數＝60（節點＋公司＋lead＋節點對相加），新計數＝8。
    questions = _walk_questions([4, 2, 2, 0, 4, 6, 9, 10, 23])
    count = qs.graph_holes_count(questions)
    assert count == 8
    assert count <= 9
    assert count == sum(1 for q in questions if q["hit_n"] > 0)


def test_graph_holes_count_skips_absent_types_and_is_none_when_nothing_was_read() -> None:
    assert qs.graph_holes_count(_walk_questions([3, 0, 5], absent=(2,))) == 1
    # 全部沒讀到 ≠ 沒有洞（INV-3）
    assert qs.graph_holes_count(_walk_questions([3, 5], absent=(0, 1))) is None
    assert qs.graph_holes_count([]) is None


def test_research_total_does_not_add_the_graph_holes_type_count() -> None:
    obs = qs.observe(forward_view_backlog=2, graph_holes=8)
    assert obs["research_total"] == 2


def test_audit_and_heartbeat_both_count_graph_holes_with_the_shared_function(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """稽核（跑走圖）與心跳（讀 artifact）各自算一份，就會像 2026-09-26 那樣只在一邊改對。"""
    import query.graph_walk as graph_walk
    from audit import checks
    from crons import heartbeat as hb

    questions = _walk_questions([4, 0, 1])
    seen: list[list] = []

    def sentinel(qs_arg):
        seen.append(list(qs_arg))
        return 42

    monkeypatch.setattr(qs, "graph_holes_count", sentinel)
    monkeypatch.setattr(graph_walk, "collect", lambda **_kw: {"questions": questions})
    assert checks._graph_holes()[0] == 42

    captured: dict = {}

    def fake_observe(**kwargs):
        captured.update(kwargs)
        return {"segments": [], "unmapped": [], "mechanical_total": 0, "research_total": 0, "not_work": {}}

    monkeypatch.setattr(qs, "observe", fake_observe)
    monkeypatch.setattr(hb, "_load_state",
                        lambda _d, kind: ({"questions": questions}, None) if kind == "graph_walk" else ({}, None))
    hb.build_queue()
    assert captured["graph_holes"] == 42
    assert len(seen) == 2 and all(s == questions for s in seen)
