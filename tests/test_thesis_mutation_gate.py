"""Thesis lifecycle 變更的 pq2 門。

事發（2026-08-06）：daily brief prompt 要求「若結果需要 thesis revise／retire，
完整 packet 回 pq2」，但沒有鑄號機制——`thesis_lifecycle` 型別只由到期檢查產生
（「這條該複查了」），研究結論想主張「這條該退場」時沒有任何路徑，lifecycle.json
也只是一個可以直接手改的 tracked JSON。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine_b import todo
from thesis import pending_lifecycle


@pytest.fixture
def env(tmp_path, monkeypatch):
    lifecycle = tmp_path / "lifecycle.json"
    lifecycle.write_text(
        json.dumps({
            "sivers": {"status": "review_required", "ticker": "SIVE.ST",
                       "next_check": "2026-08-27"},
            "axt_inp": {"status": "active", "ticker": "AXTI"},
            "gone": {"status": "retired", "ticker": "X"},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(pending_lifecycle, "PENDING_DIR", tmp_path / "pending")
    monkeypatch.setattr(pending_lifecycle, "LIFECYCLE_PATH", lifecycle)
    return lifecycle


def _propose(**overrides):
    payload = {
        "thesis_id": "sivers",
        "to_status": "retired",
        "rationale": "Q2 財報證實營收不當認列，成長路徑失效",
        "evidence_refs": ["sive_q2_2026_filing"],
        "author": "test",
    }
    payload.update(overrides)
    return pending_lifecycle.propose(**payload)


def test_illegal_transition_is_rejected_before_minting(env) -> None:
    """active 不能直接 retire——必須先經 review_required（L7 狀態機）。"""

    with pytest.raises(pending_lifecycle.ThesisMutationError, match="不允許的轉移"):
        _propose(thesis_id="axt_inp", to_status="retired")

    assert list(pending_lifecycle.iter_pending()) == []


def test_retired_is_terminal(env) -> None:
    with pytest.raises(pending_lifecycle.ThesisMutationError, match="不允許的轉移"):
        _propose(thesis_id="gone", to_status="active")


def test_mutation_requires_rationale_and_evidence(env) -> None:
    with pytest.raises(pending_lifecycle.ThesisMutationError, match="evidence ref"):
        _propose(evidence_refs=[])
    with pytest.raises(pending_lifecycle.ThesisMutationError, match="理由"):
        _propose(rationale="   ")


def test_bare_go_cannot_mutate_lifecycle(env) -> None:
    _propose()
    pool = todo.empty_pool()
    todo.sync(pool, todo._collect_thesis_mutation_rows())

    with pytest.raises(todo.TodoError, match="不得 bare go"):
        todo.resolve(pool, 1, "go", receipt="thesis:sivers:retired")

    assert json.loads(env.read_text(encoding="utf-8"))["sivers"]["status"] == "review_required"


def test_completion_writes_lifecycle_with_audit_trail(env) -> None:
    record = _propose()
    pool = todo.empty_pool()
    todo.sync(pool, todo._collect_thesis_mutation_rows())

    result = todo.complete_thesis_mutation(pool, 1)

    entry = json.loads(env.read_text(encoding="utf-8"))["sivers"]
    assert entry["status"] == "retired"
    assert result["receipt"].startswith("thesis:sivers:retired;proposal:")
    # 稽核軌跡：為什麼變、憑什麼變、誰核准的。
    mutation = entry["mutations"][-1]
    assert mutation["from"] == "review_required" and mutation["to"] == "retired"
    assert mutation["evidence_refs"] == ["sive_q2_2026_filing"]
    assert mutation["proposal_id"] == record["proposal_id"]
    assert todo.active_items(pool) == []


def test_stale_proposal_is_refused_when_status_changed_meanwhile(env) -> None:
    """提案凍結 from_status；期間狀態被改過就不能照舊套用。"""

    _propose()
    data = json.loads(env.read_text(encoding="utf-8"))
    data["sivers"]["status"] = "revised"
    env.write_text(json.dumps(data), encoding="utf-8")

    pool = todo.empty_pool()
    todo.sync(pool, todo._collect_thesis_mutation_rows())
    with pytest.raises(todo.TodoError, match="狀態已改變"):
        todo.complete_thesis_mutation(pool, 1)


def test_lifecycle_due_and_mutation_are_distinct_pq2_types() -> None:
    """「該複查了」與「主張該退場」不是同一件事，不共用型別。"""

    assert "thesis_lifecycle" in todo.ITEM_TYPES
    assert "thesis_mutation" in todo.ITEM_TYPES
    assert todo.ITEM_TYPES["thesis_lifecycle"] != todo.ITEM_TYPES["thesis_mutation"]
