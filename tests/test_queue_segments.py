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
