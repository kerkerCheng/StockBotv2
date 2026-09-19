"""備份入口（scripts/backup_private.py）與 brief 備份計數器的測試。

不測 decision_lab/backup.py 本體（test_private_backup_restore.py 已涵蓋），
只測新增的三塊：status payload 三分語意、renderer 現形規則、files.zip 排除清單。
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from briefing.render import render_today_markdown  # noqa: E402
from briefing.sources import load_backup_status as _backup_status_payload  # noqa: E402
from engine_b.state_files import STATE_PATHS, StateFileError  # noqa: E402


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
        "unbacked_files": 0,
        "unbacked_sample": [],
    }


def test_a_file_created_after_the_last_backup_is_counted_as_not_covered(tmp_path):
    """⚠ **「N 天前備份」答不出「這幾個檔有沒有被收進去」——那是兩個問題。**

    2026-09-07 實測：alpha 的三本假設 ledger（fair value 223.60 的唯一來源）建立於
    09-05／09-06，最後一次備份是 09-04。備份年齡只有 3 天看起來很健康，**覆蓋卻是 0**。
    這正是 L13-2 的形狀：成功與失敗在同一個訊號上同形。
    """
    _write_status(
        tmp_path,
        {
            "backup_id": "20260820T000000Z",
            "created_at": "2026-08-20T00:00:00+00:00",
            "drive": {"status": "uploaded"},
            "restore_verification": {"verified_at": "2026-08-20T01:00:00+00:00"},
        },
    )
    ledger = tmp_path / "alpha" / "valuation" / "COHR.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("{}\n", encoding="utf-8")
    os.utime(ledger, (NOW.timestamp(), NOW.timestamp()))
    # 備份自己的產物不算——不然這個計數器會恆亮（那是 F-26 記過的形狀）
    stale_artifact = tmp_path / "backups" / "20260820T000000Z" / "files.zip"
    stale_artifact.parent.mkdir(parents=True, exist_ok=True)
    stale_artifact.write_text("x", encoding="utf-8")
    os.utime(stale_artifact, (NOW.timestamp(), NOW.timestamp()))

    payload = _backup_status_payload(NOW, private_root=tmp_path)
    assert payload["unbacked_files"] == 1
    assert payload["unbacked_sample"] == ["alpha/valuation/COHR.jsonl"]
    line = next(line for line in _render(payload).splitlines() if "最後一次備份" in line)
    assert "🔴" in line and "1 個 private authority 檔不在這份備份裡" in line


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


def _seed_engine_b_state(root: Path, *, raw_ref: str | None = None) -> None:
    payloads = {
        STATE_PATHS[0]: {
            "schema_version": "2",
            "leads": ({"lead_x": {"trace_attempts_ref": raw_ref}} if raw_ref else {}),
        },
        STATE_PATHS[1]: {"schema_version": "1", "items": [], "log": [], "next_n": 1},
        STATE_PATHS[2]: {"schema_version": 1, "watches": []},
        STATE_PATHS[3]: {"schema_version": 1, "hypotheses": []},
    }
    for relative, payload in payloads.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")


def test_engine_b_archive_contains_exact_state_and_referenced_evidence(tmp_path):
    entrypoint = _load_entrypoint()
    raw_ref = "library/raw/source.txt"
    _seed_engine_b_state(tmp_path, raw_ref=raw_ref)
    raw = tmp_path / raw_ref
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("source", encoding="utf-8")
    archive_path = tmp_path / "engine_b_state.zip"

    count = entrypoint.build_engine_b_state_zip(archive_path, repo_root=tmp_path)

    with zipfile.ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == {*STATE_PATHS, raw_ref}
    assert count == len(STATE_PATHS) + 1
    restore = tmp_path / "restore"
    restore.mkdir()
    assert entrypoint.verify_engine_b_state_zip(
        archive_path, restore_root=restore
    ) == count
    assert (restore / raw_ref).read_text(encoding="utf-8") == "source"


def test_engine_b_archive_fails_on_missing_referenced_evidence(tmp_path):
    entrypoint = _load_entrypoint()
    _seed_engine_b_state(tmp_path, raw_ref="library/raw/missing.txt")

    with pytest.raises(StateFileError, match="引用不存在"):
        entrypoint.build_engine_b_state_zip(
            tmp_path / "engine_b_state.zip", repo_root=tmp_path
        )


def test_engine_b_archive_rejects_private_or_traversal_reference(tmp_path):
    entrypoint = _load_entrypoint()
    _seed_engine_b_state(tmp_path, raw_ref="library/raw/../private/secret.txt")

    with pytest.raises(StateFileError, match="不安全"):
        entrypoint.build_engine_b_state_zip(
            tmp_path / "engine_b_state.zip", repo_root=tmp_path
        )


def test_engine_b_archive_never_includes_private_reference(tmp_path):
    entrypoint = _load_entrypoint()
    private_ref = "library/private/secret.txt"
    _seed_engine_b_state(tmp_path, raw_ref=private_ref)
    secret = tmp_path / private_ref
    secret.parent.mkdir(parents=True, exist_ok=True)
    secret.write_text("secret", encoding="utf-8")
    archive_path = tmp_path / "engine_b_state.zip"

    entrypoint.build_engine_b_state_zip(archive_path, repo_root=tmp_path)

    with zipfile.ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == set(STATE_PATHS)
