"""Daily state finalizer：本機驗證與 lock lifecycle，不含 Git／網路能力。"""
from __future__ import annotations

import json
from pathlib import Path

from engine_b.state_files import STATE_PATHS
from engine_b.writer_lock import acquire, holder
from scripts.finalize_daily_state import finalize_daily_state


def _seed_state(root: Path) -> None:
    payloads = {
        STATE_PATHS[0]: {"schema_version": "2", "leads": {}},
        STATE_PATHS[1]: {"schema_version": "1", "items": [], "log": [], "next_n": 1},
        STATE_PATHS[2]: {"schema_version": 1, "watches": []},
        STATE_PATHS[3]: {"schema_version": 1, "hypotheses": []},
    }
    for relative, payload in payloads.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")


def test_state_pathset_is_exactly_the_four_local_authorities() -> None:
    assert STATE_PATHS == (
        "library/leads/pending_leads.json",
        "library/leads/todo_pool.json",
        "library/leads/event_watches.json",
        "library/leads/hypotheses.json",
    )


def test_every_local_state_path_is_explicitly_gitignored() -> None:
    ignore_lines = {
        line.strip()
        for line in (Path(__file__).resolve().parent.parent / ".gitignore")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert set(STATE_PATHS).issubset(ignore_lines)


def test_finalizer_validates_all_state_and_releases_scheduled_lock(tmp_path: Path) -> None:
    _seed_state(tmp_path)
    lock = tmp_path / ".writer_lock.json"
    marker = tmp_path / ".daily_run_finished.json"
    acquire("scheduled", path=lock)

    result = finalize_daily_state(tmp_path, lock_path=lock, marker_path=marker)

    assert result["status"] == "finalized"
    assert result["writer_lock_released"] is True
    assert {row["path"] for row in result["state_files"]} == set(STATE_PATHS)
    assert holder(lock) is None
    saved_marker = json.loads(marker.read_text(encoding="utf-8"))
    assert saved_marker["status"] == "finalized"


def test_invalid_state_still_releases_own_lock_and_marks_failure(tmp_path: Path) -> None:
    _seed_state(tmp_path)
    (tmp_path / STATE_PATHS[2]).write_text("not json", encoding="utf-8")
    lock = tmp_path / ".writer_lock.json"
    marker = tmp_path / ".daily_run_finished.json"
    acquire("scheduled", path=lock)

    result = finalize_daily_state(tmp_path, lock_path=lock, marker_path=marker)

    assert result["status"] == "state_invalid"
    assert result["writer_lock_released"] is True
    assert holder(lock) is None
    assert json.loads(marker.read_text(encoding="utf-8"))["status"] == "state_invalid"


def test_finalizer_has_no_git_subprocess_or_network_surface() -> None:
    source = (Path(__file__).resolve().parent.parent / "scripts" /
              "finalize_daily_state.py").read_text(encoding="utf-8")
    for forbidden in (
        "import subprocess",
        "from subprocess",
        "subprocess.run",
        "import requests",
        "urllib",
        "git push",
        "http://",
        "https://",
    ):
        assert forbidden not in source
