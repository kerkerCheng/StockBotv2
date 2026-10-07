"""備份入口（scripts/backup_private.py）與備份計數器 payload 的測試。

不測 decision_lab/backup.py 本體（test_private_backup_restore.py 已涵蓋），
只測：status payload 三分語意、還原驗證兩件事分開、Drive 最後成功上傳跨 run 保留、files.zip 排除清單。
渲染（現形規則）只有心跳段 1 一份，測試在 `tests/test_heartbeat_phase1.py`（舊 `briefing/render.py` 2026-10-06 刪除）。
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
            "drive_last_uploaded": {"name": "z.zip", "uploaded_at": "2026-08-20T00:30:00+00:00"},
            "restore_verification": {"backup_id": "20260820T000000Z",
                                     "verified_at": "2026-08-20T01:00:00+00:00"},
        },
    )
    payload = _backup_status_payload(NOW, private_root=tmp_path)
    assert payload == {
        "status": "ok",
        "age_days": 10,
        "backup_id": "20260820T000000Z",
        "drive_status": "uploaded",
        "drive_last_uploaded_days": 10,
        "restore_verified_current": True,
        "restore_verified_days": 10,
        "unbacked_files": 0,
        "unbacked_sample": [],
    }


def test_verification_of_an_older_backup_is_not_this_backup(tmp_path):
    """⚠ 2026-10-06 實測：唯一一次 restore 驗證是 09-19 那份（早已輪替掉），心跳卻每天印「還原驗證 有」。
    「曾經驗過」與「這一份驗過」是兩件事（L12）。"""
    _write_status(
        tmp_path,
        {
            "backup_id": "20260829T000000Z",
            "created_at": "2026-08-29T00:00:00+00:00",
            "drive": {"status": "skipped"},
            "restore_verification": {"backup_id": "20260819T000000Z",
                                     "verified_at": "2026-08-19T01:00:00+00:00"},
        },
    )
    payload = _backup_status_payload(NOW, private_root=tmp_path)
    assert payload["restore_verified_current"] is False
    assert payload["restore_verified_days"] == 11
    # 從沒成功上傳過：None（「本機沒有紀錄」），不是 0 天
    assert payload["drive_status"] == "skipped" and payload["drive_last_uploaded_days"] is None


def test_last_successful_upload_survives_a_failed_run():
    entrypoint = _load_entrypoint()
    ok = {"status": "uploaded", "name": "a.zip", "file_id": "f1", "uploaded_at": "2026-10-06T00:00:00+00:00",
          "bytes": 1, "rotated_out": []}
    first = entrypoint._last_uploaded(ok, {})
    assert first == {"name": "a.zip", "file_id": "f1", "uploaded_at": "2026-10-06T00:00:00+00:00"}
    # 下一次 auth 過期：drive 記這次的失敗，最後成功那份照留（否則「異地那份多舊」答不出來）
    assert entrypoint._last_uploaded({"status": "auth_expired"}, {"drive_last_uploaded": first}) == first
    assert entrypoint._last_uploaded({"status": "skipped"}, {}) is None


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


def test_outer_zip_clears_leftovers_from_a_killed_upload(tmp_path, monkeypatch):
    """R2 2026-10-06 Finding B：上傳途中被 daily 的 timeout 強殺時 `finally` 不會跑，那份 zip 會留下、
    rotation 又只掃目錄——下一輪打包前先清掉同前綴的殘留，別的檔不碰。"""
    entrypoint = _load_entrypoint()
    backups = tmp_path / "backups"
    backup_dir = backups / "20261007T000000Z"
    backup_dir.mkdir(parents=True)
    (backup_dir / "manifest.json").write_text("{}", encoding="utf-8")
    leftover = backups / f"{entrypoint.DRIVE_ZIP_PREFIX}20261006T000000Z.zip"
    leftover.write_bytes(b"partial")
    unrelated = backups / "keep.zip"
    unrelated.write_bytes(b"x")
    monkeypatch.setattr(entrypoint, "BACKUPS", backups)

    built = entrypoint._build_outer_zip(backup_dir)

    assert not leftover.exists() and unrelated.exists()
    with zipfile.ZipFile(built) as archive:
        assert archive.namelist() == ["20261007T000000Z/manifest.json"]


def test_token_write_back_is_atomic(tmp_path, monkeypatch):
    """R2 2026-10-06 Finding C：寫到一半被殺不得留下壞掉的 token——換檔前被打斷時舊 token 原封不動。"""
    entrypoint = _load_entrypoint()
    token = tmp_path / "token.json"
    token.write_text('{"refresh_token": "old"}', encoding="utf-8")
    monkeypatch.setattr(entrypoint, "TOKEN_PATH", token)

    class _Creds:
        def to_json(self):
            return '{"refresh_token": "new"}'

    def _killed(*_args):
        raise KeyboardInterrupt("換檔前被強殺")

    # 只換掉這個 module 物件自己的 `os`（入口是獨立載入的），不動全域 os.replace
    monkeypatch.setattr(entrypoint, "os", type("_Os", (), {"replace": staticmethod(_killed)}))
    with pytest.raises(KeyboardInterrupt):
        entrypoint._write_token(_Creds())
    assert json.loads(token.read_text(encoding="utf-8")) == {"refresh_token": "old"}

    monkeypatch.setattr(entrypoint, "os", os)
    entrypoint._write_token(_Creds())
    assert json.loads(token.read_text(encoding="utf-8")) == {"refresh_token": "new"}
    assert not token.with_name("token.json.tmp").exists()


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


# ---------------------------------------------------------------------------
# Drive 上傳重試（2026-10-07：daily ⑯ 撞到 Google 端 HTTP 500「Internal Error」，手動補傳一次就過）
# ---------------------------------------------------------------------------

class _HttpError(Exception):
    """形狀同 googleapiclient 的 HttpError：`resp.status` 是 HTTP 狀態碼。"""

    def __init__(self, status: int):
        super().__init__(f"HttpError {status}")
        self.resp = type("Resp", (), {"status": status})()


class _Call:
    def __init__(self, outcome):
        self.outcome = outcome

    def execute(self):
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


class _FakeFiles:
    """create 依序吐出 outcomes（例外或回傳值）；list／update 給輪替用。"""

    def __init__(self, create_outcomes, list_outcomes=None):
        self.create_outcomes = list(create_outcomes)
        self.list_outcomes = list(list_outcomes or [{"files": []}])
        self.creates = 0

    def create(self, **_kw):
        self.creates += 1
        return _Call(self.create_outcomes.pop(0))

    def list(self, **_kw):
        return _Call(self.list_outcomes.pop(0) if len(self.list_outcomes) > 1 else self.list_outcomes[0])

    def update(self, **_kw):
        return _Call({})


class _FakeService:
    def __init__(self, files):
        self._files = files

    def files(self):
        return self._files


def _drive_fixture(tmp_path, monkeypatch, files):
    entrypoint = _load_entrypoint()
    token = tmp_path / "token.json"
    token.write_text("{}", encoding="utf-8")
    zip_path = tmp_path / "stockbotv2_backup_x.zip"
    zip_path.write_bytes(b"PK\x05\x06" + b"\x00" * 18)
    monkeypatch.setattr(entrypoint, "TOKEN_PATH", token)
    monkeypatch.setattr(entrypoint, "_drive_service", lambda: (_FakeService(files), object()))
    monkeypatch.setattr(entrypoint, "_ensure_drive_folder", lambda service: "folder-1")
    monkeypatch.setattr(entrypoint, "_write_token", lambda creds: None)
    return entrypoint, zip_path


def test_a_transient_500_is_retried_and_the_upload_succeeds(tmp_path, monkeypatch):
    files = _FakeFiles([_HttpError(500), _HttpError(503), {"id": "f1", "name": "x.zip", "size": "22"}])
    entrypoint, zip_path = _drive_fixture(tmp_path, monkeypatch, files)
    waits: list[float] = []
    out = entrypoint.upload_backup_to_drive(zip_path, sleep=waits.append)
    assert out["status"] == "uploaded" and out["retries"] == 2 and files.creates == 3
    assert waits == list(entrypoint.DRIVE_RETRY_DELAYS_SECONDS)


def test_a_non_transient_error_is_not_retried(tmp_path, monkeypatch):
    """403（權限）與一般 4xx 要人處理——重試只會拖時間。"""
    files = _FakeFiles([_HttpError(403)])
    entrypoint, zip_path = _drive_fixture(tmp_path, monkeypatch, files)
    waits: list[float] = []
    out = entrypoint.upload_backup_to_drive(zip_path, sleep=waits.append)
    assert out["status"] == "delivery_failed" and out["transient"] is False and files.creates == 1 and waits == []


def test_retries_run_out_and_the_failure_still_shows(tmp_path, monkeypatch):
    files = _FakeFiles([_HttpError(500)] * 3)
    entrypoint, zip_path = _drive_fixture(tmp_path, monkeypatch, files)
    out = entrypoint.upload_backup_to_drive(zip_path, sleep=lambda _s: None)
    assert out["status"] == "delivery_failed" and out["transient"] is True and files.creates == 3


def test_a_rotation_failure_after_a_good_upload_is_not_an_upload_failure(tmp_path, monkeypatch):
    """備份已經在雲端了：輪替失敗另記 rotation_error，不把整份標成上傳失敗（那會讓「最後一次成功上傳」停在舊的那份）。"""
    files = _FakeFiles([{"id": "f1", "name": "x.zip", "size": "22"}], list_outcomes=[_HttpError(403)])
    entrypoint, zip_path = _drive_fixture(tmp_path, monkeypatch, files)
    out = entrypoint.upload_backup_to_drive(zip_path, sleep=lambda _s: None)
    assert out["status"] == "uploaded" and "rotation_error" in out and files.creates == 1


def test_connection_drops_count_as_transient():
    entrypoint = _load_entrypoint()
    assert entrypoint._is_transient(ConnectionResetError("reset"))
    assert entrypoint._is_transient(TimeoutError("slow"))
    assert not entrypoint._is_transient(FileNotFoundError("zip gone"))
    assert not entrypoint._is_transient(_HttpError(404))
