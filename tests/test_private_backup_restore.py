from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from decision_lab.backup import BackupError, create_private_backup, restore_private_backup
from storage.relational import initialize_private_root


def _private(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    private = repo / "library" / "private"
    initialize_private_root(private, repo_root=repo)
    return repo, private


def _db(path: Path, value: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS facts(value TEXT)")
    conn.execute("DELETE FROM facts")
    conn.execute("INSERT INTO facts VALUES (?)", (value,))
    conn.commit()
    conn.close()


def _value(path: Path):
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT value FROM facts").fetchone()[0]
    finally:
        conn.close()


def test_private_backup_restore_verifies_and_recovers_sqlite(tmp_path: Path) -> None:
    repo, private = _private(tmp_path)
    source = private / "decision_lab" / "decision_lab.db"
    _db(source, "before")
    backup = create_private_backup(
        sources={"decision_lab": source},
        backup_id="20260721T120000Z",
        private_root=private,
        repo_root=repo,
    )
    _db(source, "after")

    restore_private_backup(
        backup,
        targets={"decision_lab": source},
        private_root=private,
        repo_root=repo,
    )

    assert _value(source) == "before"


def test_corrupt_backup_fails_before_target_replace(tmp_path: Path) -> None:
    repo, private = _private(tmp_path)
    source = private / "decision_lab" / "decision_lab.db"
    _db(source, "before")
    backup = create_private_backup(
        sources={"decision_lab": source},
        backup_id="20260721T120000Z",
        private_root=private,
        repo_root=repo,
    )
    (backup / "decision_lab.db").write_bytes(b"corrupt")
    _db(source, "current")

    with pytest.raises(BackupError, match="checksum"):
        restore_private_backup(
            backup,
            targets={"decision_lab": source},
            private_root=private,
            repo_root=repo,
        )

    assert _value(source) == "current"


def test_backup_rotation_keeps_configured_verified_count(tmp_path: Path) -> None:
    repo, private = _private(tmp_path)
    source = private / "decision_lab" / "decision_lab.db"
    _db(source, "value")
    for index in range(4):
        create_private_backup(
            sources={"decision_lab": source},
            backup_id=f"20260721T12000{index}Z",
            private_root=private,
            repo_root=repo,
            retention=3,
        )

    assert len(list((private / "backups").iterdir())) == 3
