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


# ---------------------------------------------------------------------------
# Phase 7 Step 7.0b：逾期只看 lifecycle（is_due 一個 owner），不看 memo 生成日
# 事發 2026-10-04：SessionStart 天天報「cpo 91／90 天、sivers 36／30 天」——sivers 09-29 已複查（無 mutation，memo 沒重寫），
# cpo_v1 是被 coherent_cpo_v2 取代、沒有 lifecycle entry 的舊 memo。

from datetime import date  # noqa: E402

SIVERS_REVIEWED = {"status": "active", "memo": "thesis/sivers_v4_lane_memo.md", "last_checked": "2026-09-29",
                   "next_check": "2026-10-29", "check_interval_days": 30}


def _thesis_dir(tmp_path: Path) -> Path:
    d = tmp_path / "thesis"
    d.mkdir()
    (d / "sivers_v4_lane_memo.md").write_text("# Sivers\n**生成日期：** 2026-08-29\n", encoding="utf-8")
    (d / "cpo_v1_lane_memo.md").write_text("# CPO\n**生成日期：** 2026-07-05\n", encoding="utf-8")
    return d


def _setup(tmp_path: Path, monkeypatch, lifecycle: dict) -> None:
    monkeypatch.setattr(hook, "THESIS_DIR", _thesis_dir(tmp_path))
    monkeypatch.setattr(hook, "LIFECYCLE", _write(tmp_path, lifecycle))
    todo = tmp_path / "todo_pool.json"
    todo.write_text(json.dumps({"items": []}), encoding="utf-8")
    monkeypatch.setattr(hook, "TODO_POOL", todo)


def test_a_reviewed_thesis_is_not_overdue_until_its_next_check(tmp_path, monkeypatch) -> None:
    _setup(tmp_path, monkeypatch, {"sivers": SIVERS_REVIEWED})
    assert hook.check(date(2026, 10, 4)) == []
    assert "sivers" not in dict(hook.lifecycle_due(date(2026, 10, 4)))
    assert hook.check(date(2026, 10, 30)) == [("sivers", 31)]       # 從 09-29 複查起算，不是 memo 的 08-29
    assert "sivers" in dict(hook.lifecycle_due(date(2026, 10, 30)))


def test_a_memo_without_lifecycle_is_listed_not_overdue(tmp_path, monkeypatch) -> None:
    _setup(tmp_path, monkeypatch, {"sivers": SIVERS_REVIEWED})
    assert "cpo" not in {tid for tid, _ in hook.check(date(2026, 10, 4))}
    assert "cpo_v1" not in str(hook.check(date(2027, 6, 1)))         # 多久都不算逾期——它沒有核查週期
    assert hook.legacy_memos() == ["cpo_v1_lane_memo.md"]


def test_a_thesis_with_no_schedule_left_is_still_reported(tmp_path, monkeypatch) -> None:
    """變異：拿掉 last_checked 與 next_check（沒有出口）——真的該複查的要被報，不能因為改看 lifecycle 就安靜。"""
    bare = {k: v for k, v in SIVERS_REVIEWED.items() if k not in ("last_checked", "next_check")}
    _setup(tmp_path, monkeypatch, {"sivers": bare})
    assert hook.check(date(2026, 10, 4)) == [("sivers", 36)]         # 沒有複查紀錄 → 從 memo 08-29 起算
    assert "sivers" in dict(hook.lifecycle_due(date(2026, 10, 4)))


def test_session_hook_is_silent_on_the_day_the_false_alarms_fired(tmp_path, monkeypatch, capsys) -> None:
    _setup(tmp_path, monkeypatch, {"sivers": SIVERS_REVIEWED})
    monkeypatch.setattr(hook, "date", type("FakeDate", (date,), {"today": classmethod(lambda cls: date(2026, 10, 4))}))
    assert hook.main() == 0
    assert capsys.readouterr().out == ""


def test_session_hook_names_legacy_memos_when_it_speaks(tmp_path, monkeypatch, capsys) -> None:
    _setup(tmp_path, monkeypatch, {"sivers": SIVERS_REVIEWED})
    monkeypatch.setattr(hook, "date", type("FakeDate", (date,), {"today": classmethod(lambda cls: date(2026, 10, 30))}))
    assert hook.main() == 0
    text = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert "sivers" in text and "沒有 lifecycle 的舊 memo 1 份" in text and "cpo_v1_lane_memo.md" in text
    assert "📋" not in text                                            # memo 日期那一套已拿掉


def test_session_hook_says_so_when_lifecycle_is_unreadable(tmp_path, monkeypatch, capsys) -> None:
    """讀不到 ≠ 沒有到期：memo 日期那一套拿掉後，讀不到時不能安靜（INV-3）。"""
    monkeypatch.setattr(hook, "THESIS_DIR", _thesis_dir(tmp_path))
    monkeypatch.setattr(hook, "LIFECYCLE", tmp_path / "nope.json")
    todo = tmp_path / "todo_pool.json"
    todo.write_text(json.dumps({"items": []}), encoding="utf-8")
    monkeypatch.setattr(hook, "TODO_POOL", todo)
    assert hook.main() == 0
    assert "lifecycle.json 讀不到" in json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]


def test_memo_date_reads_the_bold_markdown_form(tmp_path) -> None:
    memo = tmp_path / "x_v1_lane_memo.md"
    memo.write_text("**生成日期：** 2026-08-04（v4）\n", encoding="utf-8")
    assert hook._file_date(memo) == date(2026, 8, 4)
