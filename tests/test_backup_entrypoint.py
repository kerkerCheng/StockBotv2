"""備份入口（scripts/backup_private.py）與 brief 備份計數器的測試。

不測 decision_lab/backup.py 本體（test_private_backup_restore.py 已涵蓋），
只測新增的三塊：status payload 三分語意、renderer 現形規則、files.zip 排除清單。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from decision_lab.brief import _backup_status_payload, render_today_markdown  # noqa: E402


def _load_entrypoint():
    spec = importlib.util.spec_from_file_location(
        "backup_private", ROOT / "scripts" / "backup_private.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)


def _write_status(private_root: Path, payload: dict) -> None:
    backups = private_root / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    (backups / "last_backup.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_payload_none_when_no_private_root(tmp_path):
    assert _backup_status_payload(NOW, private_root=tmp_path / "missing") is None


def test_payload_never_when_no_status_file(tmp_path):
    assert _backup_status_payload(NOW, private_root=tmp_path) == {"status": "never"}


def test_payload_invalid_when_status_unreadable(tmp_path):
    backups = tmp_path / "backups"
    backups.mkdir()
    (backups / "last_backup.json").write_text("not json", encoding="utf-8")
    assert _backup_status_payload(NOW, private_root=tmp_path) == {"status": "invalid"}
    _write_status(tmp_path, {"backup_id": "x"})  # 缺 created_at
    assert _backup_status_payload(NOW, private_root=tmp_path) == {"status": "invalid"}


def test_payload_ok_reports_age_drive_and_verification(tmp_path):
    _write_status(
        tmp_path,
        {
            "backup_id": "20260820T000000Z",
            "created_at": "2026-08-20T00:00:00+00:00",
            "drive": {"status": "uploaded"},
            "restore_verification": {"verified_at": "2026-08-20T01:00:00+00:00"},
        },
    )
    payload = _backup_status_payload(NOW, private_root=tmp_path)
    assert payload == {
        "status": "ok",
        "age_days": 10,
        "backup_id": "20260820T000000Z",
        "drive_status": "uploaded",
        "restore_verified": True,
    }


def _render(backup_status) -> str:
    return render_today_markdown(
        {
            "action_needed": False,
            "attention": "MONITOR",
            "reason": "test",
            "backup_status": backup_status,
        }
    )


def test_renderer_never_and_invalid_are_red_and_visible():
    assert "🔴 最後一次備份：從未備份" in _render({"status": "never"})
    assert "🔴 最後一次備份：狀態檔無法解讀" in _render({"status": "invalid"})
    # surface 不提供（None）→ 整行略過，不與「從未備份」混用
    assert "備份" not in _render(None)


def test_renderer_fresh_verified_uploaded_backup_is_not_red():
    line = next(
        line
        for line in _render(
            {
                "status": "ok",
                "age_days": 1,
                "drive_status": "uploaded",
                "restore_verified": True,
            }
        ).splitlines()
        if "最後一次備份" in line
    )
    assert "🔴" not in line
    assert "Drive ✓" in line and "restore 已驗證" in line


def test_renderer_stale_or_undelivered_backup_is_red():
    stale = _render(
        {"status": "ok", "age_days": 8, "drive_status": "uploaded", "restore_verified": True}
    )
    assert "🔴 最後一次備份：8 天前" in stale
    undelivered = _render(
        {"status": "ok", "age_days": 0, "drive_status": "auth_expired", "restore_verified": True}
    )
    # markdown_text 會轉義底線，斷言轉義後的實際輸出
    assert "Drive 🔴 auth\\_expired" in undelivered
    assert "🔴 最後一次備份：0 天前" in undelivered


def test_files_zip_members_exclude_recoverable_and_live(tmp_path):
    entrypoint = _load_entrypoint()
    (tmp_path / "models").mkdir()
    (tmp_path / "models" / "weights.bin").write_bytes(b"x")
    (tmp_path / "backups").mkdir()
    (tmp_path / "backups" / "last_backup.json").write_text("{}")
    (tmp_path / "gdrive_oauth").mkdir()
    (tmp_path / "gdrive_oauth" / "token.json").write_text("{}")
    (tmp_path / "decision_lab").mkdir()
    live_db = tmp_path / "decision_lab" / "decision_lab.db"
    live_db.write_bytes(b"live")
    (tmp_path / "decision_lab" / "decision_lab.db-wal").write_bytes(b"wal")
    keep_json = tmp_path / "decision_lab" / "assessment_x.json"
    keep_json.write_text("{}")
    keep_root = tmp_path / "runtime_pointer.json"
    keep_root.write_text("{}")

    members = {
        rel.as_posix()
        for _, rel in entrypoint.iter_files_zip_members(
            tmp_path, live_dbs={live_db.resolve()}
        )
    }
    assert members == {"decision_lab/assessment_x.json", "runtime_pointer.json"}
