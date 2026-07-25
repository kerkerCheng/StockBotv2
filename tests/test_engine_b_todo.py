"""統一待辦池（廣義 pq2）：持久編號、批次 dispatch、稽核 log。"""
from __future__ import annotations

import json

import pytest

from engine_b import todo
from engine_b.batch import parse_batch_reply


def _pool_with(*rows):
    pool = todo.empty_pool()
    todo.sync(pool, rows)
    return pool


def test_numbers_are_assigned_and_persist_across_resync() -> None:
    rows = [
        {"type": "lead_research", "ref_id": "lead_a", "title": "A"},
        {"type": "ra_admission", "ref_id": "ra_b", "title": "B"},
    ]
    pool = _pool_with(*rows)
    first = {i["ref_id"]: i["n"] for i in todo.active_items(pool)}

    # 再同步一次（順序顛倒、且多一筆）——既有項目編號不得改變
    todo.sync(pool, [rows[1], rows[0], {"type": "manual", "ref_id": "m1", "title": "C"}])
    second = {i["ref_id"]: i["n"] for i in todo.active_items(pool)}

    assert second["lead_a"] == first["lead_a"]
    assert second["ra_b"] == first["ra_b"]
    assert second["m1"] not in (first["lead_a"], first["ra_b"])


def test_upsert_is_idempotent_and_updates_title_only() -> None:
    pool = _pool_with({"type": "lead_research", "ref_id": "x", "title": "舊"})
    n_before = todo.active_items(pool)[0]["n"]
    todo.sync(pool, [{"type": "lead_research", "ref_id": "x", "title": "新"}])
    items = todo.active_items(pool)
    assert len(items) == 1
    assert items[0]["n"] == n_before
    assert items[0]["title"] == "新"


def test_resolve_go_removes_from_active_and_logs() -> None:
    pool = _pool_with({"type": "lead_research", "ref_id": "x", "title": "A"})
    n = todo.active_items(pool)[0]["n"]
    todo.resolve(pool, n, "go", reason="值得深挖")
    assert todo.active_items(pool) == []
    entry = pool["log"][-1]
    assert entry["verb"] == "go" and entry["reason"] == "值得深挖" and entry["n"] == n


def test_pending_defers_but_keeps_item_active() -> None:
    pool = _pool_with({"type": "lead_research", "ref_id": "x", "title": "A"})
    n = todo.active_items(pool)[0]["n"]
    todo.resolve(pool, n, "pending")
    items = todo.active_items(pool)
    assert len(items) == 1 and items[0]["deferred_at"]
    assert pool["log"][-1]["verb"] == "pending"


def test_batch_applies_and_reports_failures() -> None:
    pool = _pool_with(
        {"type": "lead_research", "ref_id": "a", "title": "A"},
        {"type": "lead_research", "ref_id": "b", "title": "B"},
        {"type": "ra_admission", "ref_id": "c", "title": "C"},
    )
    parsed = parse_batch_reply("1 3 go 2 drop 99 pending")
    outcome = todo.apply_batch(pool, parsed)
    assert outcome["applied"] == [1, 2, 3]
    assert outcome["failed"] == [99]  # 不存在的編號不中斷其餘
    assert todo.active_items(pool) == []


def test_unknown_number_and_verb_rejected() -> None:
    pool = _pool_with({"type": "lead_research", "ref_id": "a", "title": "A"})
    with pytest.raises(todo.TodoError):
        todo.resolve(pool, 999, "go")
    with pytest.raises(todo.TodoError):
        todo.resolve(pool, 1, "nonsense")


def test_unknown_type_rejected() -> None:
    pool = todo.empty_pool()
    with pytest.raises(todo.TodoError):
        todo.upsert(pool, item_type="not_a_type", ref_id="x", title="X")


def test_resolved_item_can_reenter_pool_with_new_number() -> None:
    pool = _pool_with({"type": "decision_review", "ref_id": "dc_1", "title": "REVIEW"})
    n1 = todo.active_items(pool)[0]["n"]
    todo.resolve(pool, n1, "go")
    # 同一 cohort 之後又有新 evidence-delta → 應重新進池（resolve 不是永久黑名單）
    todo.sync(pool, [{"type": "decision_review", "ref_id": "dc_1", "title": "REVIEW 再現"}])
    items = todo.active_items(pool)
    assert len(items) == 1 and items[0]["n"] != n1


def test_save_load_round_trip(tmp_path) -> None:
    path = tmp_path / "sub" / "todo_pool.json"
    pool = _pool_with({"type": "manual", "ref_id": "m", "title": "手動項"})
    todo.resolve(pool, 1, "pending")
    todo.save(pool, path)
    again = todo.load(path)
    assert todo.active_items(again)[0]["title"] == "手動項"
    assert again["log"][-1]["verb"] == "pending"
    assert again["next_n"] == pool["next_n"]


def test_load_missing_returns_empty_pool(tmp_path) -> None:
    assert todo.load(tmp_path / "nope.json") == todo.empty_pool()


def test_cli_add_and_batch(tmp_path, capsys) -> None:
    path = str(tmp_path / "todo_pool.json")
    assert todo.main(["--pool", path, "add", "查 COHR 客戶集中度", "--hint", "本機查"]) == 0
    capsys.readouterr()
    assert todo.main(["--pool", path, "batch", "1 go"]) == 0
    out = json.loads(capsys.readouterr().out.strip())
    assert out["applied"] == [1] and out["failed"] == []
    assert todo.active_items(todo.load(path)) == []
