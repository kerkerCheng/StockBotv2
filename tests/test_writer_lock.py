"""Writer lock（ROADMAP #2，2026-09-02）：兩個 writer 併發時第二個被擋。

驗收條件（ROADMAP）：模擬兩個 writer 併發時會被擋下；lock stale-tolerant
（崩潰的 session 不得永久卡住）。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from engine_b.writer_lock import (
    WriterLockHeld,
    acquire,
    holder,
    is_stale,
    release,
)


@pytest.fixture()
def lock_path(tmp_path):
    return tmp_path / ".writer_lock.json"


def test_second_writer_is_blocked(lock_path) -> None:
    acquire("scheduled", purpose="daily", path=lock_path)
    with pytest.raises(WriterLockHeld) as exc:
        acquire("interactive", path=lock_path)
    assert exc.value.holder["owner"] == "scheduled"


def test_same_owner_renews_instead_of_blocking(lock_path) -> None:
    first = acquire("interactive", ttl_minutes=10, path=lock_path)
    second = acquire("interactive", ttl_minutes=10, path=lock_path)
    assert second["expires_at"] >= first["expires_at"]


def test_stale_lock_is_taken_over_with_audit(lock_path) -> None:
    past = datetime.now(timezone.utc) - timedelta(hours=3)
    acquire("scheduled", ttl_minutes=1, path=lock_path, now=past)
    assert is_stale(holder(lock_path))
    taken = acquire("interactive", path=lock_path)
    assert taken["owner"] == "interactive"
    assert taken["superseded"]["owner"] == "scheduled"


def test_corrupt_lock_file_is_stale_not_permanent(lock_path) -> None:
    lock_path.write_text("{not json", encoding="utf-8")
    current = holder(lock_path)
    assert current == {"invalid": True}
    assert is_stale(current)
    taken = acquire("scheduled", path=lock_path)
    assert taken["superseded"]["invalid"] is True


def test_release_only_own_lock(lock_path) -> None:
    acquire("scheduled", path=lock_path)
    assert release("interactive", path=lock_path) is False
    assert holder(lock_path)["owner"] == "scheduled"
    assert release("scheduled", path=lock_path) is True
    assert holder(lock_path) is None
    # 釋放不存在的鎖是 no-op，不是錯誤。
    assert release("scheduled", path=lock_path) is False


def test_anyone_can_clear_stale_lock(lock_path) -> None:
    past = datetime.now(timezone.utc) - timedelta(hours=3)
    acquire("scheduled", ttl_minutes=1, path=lock_path, now=past)
    assert release("interactive", path=lock_path) is True
    assert holder(lock_path) is None


def test_lock_path_is_inside_repo_and_gitignored() -> None:
    """sandbox impact review 斷言：鎖檔在 repo 內（workspace-write 已涵蓋，
    不需新的 outside-sandbox rule），且被 .gitignore 排除（機器狀態不進 Git）。"""
    from pathlib import Path

    from engine_b.writer_lock import LOCK_PATH, _ROOT

    assert LOCK_PATH.is_relative_to(_ROOT)
    gitignore = (_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "library/leads/.writer_lock.json" in gitignore
