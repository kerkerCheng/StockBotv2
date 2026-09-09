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
    # 使用者定案的六段（fired 重排／reassess／已核准工單／triaged_go／forward view／覆蓋缺口）
    # 都在，外加前面的 pending 分流與後面的主動輪詢。
    for required in (
        "fired_lead_requeue", "reassess_stale", "approved_work_orders",
        "triaged_go_leads", "forward_view_backlog", "coverage_gaps",
    ):
        assert required in qs.SEGMENT_BY_KEY


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


def test_todo_item_is_work_only_when_dispatched_or_reassess_only() -> None:
    assert qs.classify_todo({"n": 1, "dispatch_status": "queued"}) == "approved_work_orders"
    assert qs.classify_todo({"n": 1, "dispatch_status": "researching"}) == "approved_work_orders"
    assert qs.classify_todo({"n": 1, "dispatch_status": "awaiting_approval"}) is None
    assert qs.classify_todo({"n": 1}) is None
    assert qs.classify_todo({"n": 1}, reassess_only=True) == "reassess_stale"
    assert qs.classify_todo({"n": 1, "resolved_at": "2026-09-09"}, reassess_only=True) is None
    assert qs.classify_todo({"n": 1, "dispatch_status": "teleported"}) == "unmapped:todo:teleported"


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
        reassess_only_numbers=[6],
        forward_view_backlog=None,
        coverage_gaps=20,
    )
    by_key = {s["key"]: s["count"] for s in obs["segments"]}
    assert by_key["pending_triage"] == 1
    assert by_key["triaged_go_leads"] == 1
    assert by_key["fired_lead_requeue"] == 1
    assert by_key["fired_pq2_wake"] == 1
    assert by_key["pollable_watches"] == 1
    assert by_key["approved_work_orders"] == 1
    assert by_key["reassess_stale"] == 1
    assert by_key["forward_view_backlog"] is None      # 沒讀到 ≠ 0
    assert by_key["coverage_gaps"] == 20
    assert obs["unmapped"] == []
    assert obs["mechanical_total"] == 3               # fired lead＋fired pq2＋reassess
    rendered = qs.render(obs)
    assert "未讀到" in rendered and "coverage" in rendered


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
