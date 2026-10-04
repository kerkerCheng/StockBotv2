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
    hold,
    holder,
    is_stale,
    mark_run_finished,
    release,
    run_finished_at,
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


def test_nested_hold_leaves_the_outer_session_lock_untouched(lock_path) -> None:
    """Phase 6 #17：外層 session 先用 writer_guard 取得 interactive 鎖，工具內部再進 hold——
    結束後外層的鎖要原封不動（TTL 不縮短、不被拆）。修前的工具自己 acquire（續期成 15 分）再 release（刪檔），
    2026-10-03 [671] 結束時把使用者的鎖拆了，[672] 寫 lead registry 時沒有持鎖。"""
    outer = acquire("interactive", ttl_minutes=120, purpose="使用者的 session", path=lock_path)
    with hold("interactive", ttl_minutes=15, purpose="遷移工具", path=lock_path) as acquired:
        assert acquired is False
        assert holder(lock_path) == outer
    assert holder(lock_path) == outer


def test_standalone_hold_acquires_and_releases(lock_path) -> None:
    with hold("interactive", ttl_minutes=15, purpose="遷移工具", path=lock_path) as acquired:
        assert acquired is True
        assert holder(lock_path)["purpose"] == "遷移工具"
    assert holder(lock_path) is None


def test_hold_releases_its_own_lock_even_when_the_body_fails(lock_path) -> None:
    with pytest.raises(RuntimeError):
        with hold("interactive", path=lock_path):
            raise RuntimeError("遷移中止")
    assert holder(lock_path) is None


def test_hold_still_blocks_another_owner(lock_path) -> None:
    daily = acquire("scheduled", purpose="daily", path=lock_path)
    with pytest.raises(WriterLockHeld):
        with hold("interactive", path=lock_path):
            pass  # pragma: no cover — 進不來
    assert holder(lock_path) == daily


def test_hold_takes_over_a_stale_lock_of_the_same_owner(lock_path) -> None:
    """過期的同 owner 鎖不算「外層還在」——照常接手、結束釋放（否則一把崩潰留下的鎖會讓工具永遠不持鎖）。"""
    past = datetime.now(timezone.utc) - timedelta(hours=3)
    acquire("interactive", ttl_minutes=1, path=lock_path, now=past)
    with hold("interactive", path=lock_path) as acquired:
        assert acquired is True
        assert not is_stale(holder(lock_path))
    assert holder(lock_path) is None


def test_lock_path_is_inside_repo_and_gitignored() -> None:
    """sandbox impact review 斷言：鎖檔在 repo 內（workspace-write 已涵蓋，
    不需新的 outside-sandbox rule），且被 .gitignore 排除（機器狀態不進 Git）。"""
    from pathlib import Path

    from engine_b.writer_lock import LOCK_PATH, _ROOT

    assert LOCK_PATH.is_relative_to(_ROOT)
    gitignore = (_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "library/leads/.writer_lock.json" in gitignore


# ---------------------------------------------------------------------------
# 「這輪跑完了」標記（2026-09-12）——與鎖同性質、同一個原子寫檔路徑。


def test_run_marker_roundtrips_and_stays_timezone_aware(tmp_path) -> None:
    marker = tmp_path / ".daily_run_finished.json"
    assert run_finished_at(marker) is None, "沒有標記＝還沒跑完"

    payload = mark_run_finished(status="pushed", path=marker)
    back = run_finished_at(marker)

    assert payload["status"] == "pushed"
    assert back is not None and back.tzinfo is not None, "naive 時間會在跨時區比較時靜默錯"


def test_corrupt_run_marker_fails_closed(tmp_path) -> None:
    """讀不出來就當成還沒跑完。一個解析不出時間的標記若被當成『跑完了』，
    它就是一把永久開著的門——而門開著不會有任何東西叫。"""
    marker = tmp_path / ".daily_run_finished.json"
    marker.write_text("{not json", encoding="utf-8")

    assert run_finished_at(marker) is None


def test_run_marker_records_failed_runs_too(tmp_path) -> None:
    """語意是『跑完了』不是『成功了』（L12）：避讓窗防的是同時寫，與成敗無關。
    成敗留在 status 裡供人看，但不參與避讓判斷。"""
    marker = tmp_path / ".daily_run_finished.json"
    mark_run_finished(status="push_failed", path=marker)

    assert run_finished_at(marker) is not None
