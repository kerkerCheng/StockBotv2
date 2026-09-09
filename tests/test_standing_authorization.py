"""常規授權類別（config/standing_authorization.json＋engine_b/standing_authorization.py＋todo.standing_go）。

守三件事：①封閉性——每種 pq2 類型都必須被明確分到 authorized 或 never；②四個 authority gate 的類型
永遠在 never；③standing_go 只對「使用者本來會下 go」的項目動手：pending 的、等世界的、付費的都不碰。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine_b import standing_authorization as sa
from engine_b import todo


def test_shipped_config_is_closed_over_item_types_and_never_lists_the_gates() -> None:
    auth = sa.load()
    assert set(auth.authorized) | set(auth.never) == set(todo.ITEM_TYPES)
    assert not (set(auth.authorized) & set(auth.never))
    for gate_type in ("ra_admission", "engine_c_observation", "thesis_mutation"):
        assert gate_type in auth.never and not auth.is_authorized(gate_type)
    assert auth.is_authorized("decision_review") and auth.is_authorized("source_trace_review")
    assert "付費" in auth.skip_hint_tokens("source_trace_review")


def test_loader_rejects_unclassified_or_overlapping_types(tmp_path: Path) -> None:
    base = json.loads(sa.DEFAULT_PATH.read_text(encoding="utf-8"))
    missing = dict(base)
    missing["never"] = {k: v for k, v in base["never"].items() if k != "manual"}
    p = tmp_path / "a.json"
    p.write_text(json.dumps(missing), encoding="utf-8")
    with pytest.raises(sa.StandingAuthorizationError, match="未分類"):
        sa.load(p)
    overlap = dict(base)
    overlap["never"] = {**base["never"], "decision_review": "x"}
    p.write_text(json.dumps(overlap), encoding="utf-8")
    with pytest.raises(sa.StandingAuthorizationError, match="同時"):
        sa.load(p)
    with pytest.raises(sa.StandingAuthorizationError, match="不存在"):
        sa.load(tmp_path / "nope.json")


def _pool():
    pool = todo.empty_pool()
    todo.sync(pool, [
        {"type": "decision_review", "ref_id": "dc_go", "title": "A：補獨立來源"},
        {"type": "decision_review", "ref_id": "dc_deferred", "title": "B"},
        {"type": "decision_review", "ref_id": "dc_waiting", "title": "C"},
        {"type": "decision_review", "ref_id": "dc_inflight", "title": "D"},
        {"type": "source_trace_review", "ref_id": "lead_free", "title": "E 追原文", "hint": "go 只排入 bounded pq1"},
        {"type": "source_trace_review", "ref_id": "lead_paid", "title": "F Rosenblatt 券商報告",
         "hint": "若需付費，另核准 exact 金額／方案"},
        {"type": "ra_admission", "ref_id": "ra_x", "title": "G 入圖"},
        {"type": "manual", "ref_id": "m1", "title": "H"},
    ])
    by = {it["ref_id"]: it for it in todo.active_items(pool)}
    todo.resolve(pool, by["dc_deferred"]["n"], "pending")
    todo.resolve(pool, by["dc_waiting"]["n"], "pending", trigger="等 Q3 財報")
    by["dc_inflight"]["dispatch_status"] = "queued"
    return pool, by


def test_candidates_exclude_pending_waiting_inflight_paid_and_never_types() -> None:
    pool, by = _pool()
    candidates, skipped = todo.standing_go_candidates(pool, authorization=sa.load())
    assert [it["ref_id"] for it in candidates] == ["dc_go", "lead_free"]
    reasons = {row["n"]: row["reason"] for row in skipped}
    assert "pending" in reasons[by["dc_deferred"]["n"]]
    assert "等世界" in reasons[by["dc_waiting"]["n"]]
    assert "付費" in reasons[by["lead_paid"]["n"]]
    assert by["dc_inflight"]["n"] not in reasons            # in-flight 直接略過，不是「跳過」
    assert by["ra_x"]["n"] not in reasons and by["m1"]["n"] not in reasons


def test_standing_go_runs_the_same_go_the_user_would_and_logs_it(monkeypatch) -> None:
    pool, by = _pool()
    calls: list[tuple] = []

    def fake_advance(p, n, *, store, at=None):
        calls.append(("decision", n))
        todo.get(p, n)["dispatch_ref"] = f"assessment_gap:{todo.get(p, n)['ref_id']}"
        return {"outcome": "queued_assessment_gap"}

    def fake_dispatch(p, n, *, leads_path, at=None):
        calls.append(("trace", n))
        todo.get(p, n)["dispatch_ref"] = "lead:lead_free"
        return {"item": todo.get(p, n)}

    monkeypatch.setattr(todo, "advance_decision_review", fake_advance)
    monkeypatch.setattr(todo, "dispatch_source_trace_review", fake_dispatch)

    dry = todo.standing_go(pool, object(), dry_run=True)
    assert dry["dry_run"] and calls == []

    out = todo.standing_go(pool, object(), at="2026-09-09T00:00:00+00:00")
    assert [(c[0]) for c in calls] == ["decision", "trace"]
    assert [row["outcome"] for row in out["done"]] == ["queued_assessment_gap", "dispatched"]
    logs = [e for e in pool["log"] if e["verb"] == "standing_go"]
    assert {e["n"] for e in logs} == {by["dc_go"]["n"], by["lead_free"]["n"]}
    assert all("standing_authorization.json" in e["reason"] for e in logs)
    assert all(e["receipt"] for e in logs)
    # 沒動到 never 類型與使用者明示 pending 的項目
    assert todo.get(pool, by["ra_x"]["n"]).get("dispatch_status") is None
    assert todo.get(pool, by["dc_deferred"]["n"]).get("deferred_at")


def test_standing_go_reports_single_failures_without_stopping(monkeypatch) -> None:
    pool, by = _pool()

    def boom(p, n, *, store, at=None):
        raise RuntimeError("store 壞了")

    monkeypatch.setattr(todo, "advance_decision_review", boom)
    monkeypatch.setattr(todo, "dispatch_source_trace_review",
                        lambda p, n, *, leads_path, at=None: {"item": todo.get(p, n)})
    out = todo.standing_go(pool, object())
    assert [row["n"] for row in out["failed"]] == [by["dc_go"]["n"]]
    assert [row["n"] for row in out["done"]] == [by["lead_free"]["n"]]
