"""thesis_freshness_check 讀 lifecycle.json 到期（plan U5/R17）。"""
from __future__ import annotations

import json
from pathlib import Path

from crons import thesis_freshness_check as hook


def _write(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "lifecycle.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_review_required_and_overdue_are_flagged(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(hook, "LIFECYCLE", _write(tmp_path, {
        "sivers": {"status": "review_required", "next_check": "2099-01-01"},
        "coherent_cpo": {"status": "active", "next_check": "2000-01-01"},  # 早已到期
        "fresh": {"status": "active", "next_check": "2099-12-31"},          # 未到期
    }))
    due = dict(hook.lifecycle_due())
    assert "sivers" in due and "review_required" in due["sivers"]
    assert "coherent_cpo" in due  # next_check 過了
    assert "fresh" not in due


def test_missing_or_malformed_lifecycle_is_silent(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(hook, "LIFECYCLE", tmp_path / "nope.json")
    assert hook.lifecycle_due() == []
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    monkeypatch.setattr(hook, "LIFECYCLE", bad)
    assert hook.lifecycle_due() == []


def test_session_hook_is_quiet_when_lifecycle_is_already_in_todo_pool(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(hook, "LIFECYCLE", _write(tmp_path, {
        "sivers": {"status": "review_required", "next_check": "2099-01-01"},
    }))
    todo = tmp_path / "todo_pool.json"
    todo.write_text(json.dumps({
        "items": [{
            "n": 10,
            "type": "thesis_lifecycle",
            "ref_id": "sivers",
            "resolved_at": None,
            "deferred_at": "2026-07-26T00:00:00+00:00",
        }]
    }), encoding="utf-8")
    monkeypatch.setattr(hook, "TODO_POOL", todo)
    monkeypatch.setattr(hook, "check", lambda: [])

    assert hook.main() == 0
    assert capsys.readouterr().out == ""


def test_resolved_lifecycle_todo_does_not_suppress_new_due_item(
    tmp_path, monkeypatch
) -> None:
    todo = tmp_path / "todo_pool.json"
    todo.write_text(json.dumps({
        "items": [{
            "type": "thesis_lifecycle",
            "ref_id": "sivers",
            "resolved_at": "2026-07-26T00:00:00+00:00",
        }]
    }), encoding="utf-8")
    monkeypatch.setattr(hook, "TODO_POOL", todo)

    assert hook.active_lifecycle_todo_refs() == set()


def test_new_due_item_uses_one_agent_visible_channel(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(hook, "LIFECYCLE", _write(tmp_path, {
        "new_thesis": {"status": "review_required", "next_check": "2099-01-01"},
    }))
    todo = tmp_path / "todo_pool.json"
    todo.write_text(json.dumps({"items": []}), encoding="utf-8")
    monkeypatch.setattr(hook, "TODO_POOL", todo)
    monkeypatch.setattr(hook, "check", lambda: [])

    assert hook.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert "systemMessage" not in payload
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "new_thesis" in payload["hookSpecificOutput"]["additionalContext"]
