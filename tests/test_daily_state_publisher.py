from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.publish_daily_state import STATE_PATHS, publish_daily_state


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    _git(tmp_path, "init", "--bare", str(remote))
    _git(tmp_path, "init", "-b", "master", str(work))
    _git(work, "config", "user.name", "Test")
    _git(work, "config", "user.email", "test@example.com")
    _git(work, "remote", "add", "origin", str(remote))
    for relpath in (*STATE_PATHS, "README.md"):
        path = work / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("initial\n", encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-m", "initial")
    _git(work, "push", "-u", "origin", "master")
    return work, remote


def test_publishes_only_daily_state_and_preserves_unrelated_changes(tmp_path: Path) -> None:
    work, remote = _repo(tmp_path)
    (work / STATE_PATHS[0]).write_text("changed\n", encoding="utf-8")
    (work / "README.md").write_text("user work\n", encoding="utf-8")

    result = publish_daily_state(work)

    assert result == {"status": "pushed", "committed": True, "pushed": True}
    assert _git(work, "show", "--name-only", "--pretty=format:", "HEAD") == STATE_PATHS[0]
    assert "README.md" in _git(work, "status", "--porcelain")
    assert _git(remote, "show", "master:library/leads/pending_leads.json") == "changed"


def test_pathset_contract_is_exactly_four_leads_state_files() -> None:
    """2026-09-02 sandbox impact review ④：明確斷言允許項全集與順序無關的邊界。

    pathset 由二擴四（event watch registry＋假設對照）；擴充只可發生在
    `library/leads/` 的 state 檔，且必須逐一列名——不允許 glob 或整目錄。"""
    assert STATE_PATHS == (
        "library/leads/pending_leads.json",
        "library/leads/todo_pool.json",
        "library/leads/event_watches.json",
        "library/leads/hypotheses.json",
    )


def test_publishes_watch_state_but_not_adjacent_leads_file(tmp_path: Path) -> None:
    """相鄰排除：同目錄的非 state 檔（如 backfill 快照）不得被 publisher 帶走。"""
    work, remote = _repo(tmp_path)
    adjacent = work / "library" / "leads" / "backfill_snapshot.json"
    adjacent.write_text("initial\n", encoding="utf-8")
    _git(work, "add", str(adjacent))
    _git(work, "commit", "-m", "user snapshot")
    _git(work, "push", "origin", "master")

    (work / "library" / "leads" / "event_watches.json").write_text(
        "watch changed\n", encoding="utf-8"
    )
    adjacent.write_text("user work in progress\n", encoding="utf-8")

    result = publish_daily_state(work)

    assert result == {"status": "pushed", "committed": True, "pushed": True}
    committed = _git(work, "show", "--name-only", "--pretty=format:", "HEAD")
    assert committed == "library/leads/event_watches.json"
    assert "backfill_snapshot.json" in _git(work, "status", "--porcelain")
    assert (
        _git(remote, "show", "master:library/leads/event_watches.json")
        == "watch changed"
    )


def test_refuses_to_push_unrelated_existing_commit(tmp_path: Path) -> None:
    work, _ = _repo(tmp_path)
    (work / "README.md").write_text("committed user work\n", encoding="utf-8")
    _git(work, "commit", "-am", "user commit")
    (work / STATE_PATHS[1]).write_text("changed\n", encoding="utf-8")

    assert publish_daily_state(work)["status"] == "guard_unpushed_commits"


def test_refuses_when_index_is_not_empty(tmp_path: Path) -> None:
    work, _ = _repo(tmp_path)
    (work / "README.md").write_text("staged\n", encoding="utf-8")
    _git(work, "add", "README.md")

    assert publish_daily_state(work)["status"] == "guard_staged_changes"
