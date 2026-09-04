"""Owner-only SQLite recovery backup/restore with checksums and bounded rotation。"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from storage.relational import validate_private_destination


class BackupError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _sqlite_backup(source: Path, destination: Path) -> None:
    source_conn = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    target_conn = sqlite3.connect(destination)
    try:
        source_conn.backup(target_conn)
        check = target_conn.execute("PRAGMA integrity_check").fetchone()
        if check != ("ok",):
            raise BackupError("SQLite backup integrity check failed")
    finally:
        target_conn.close()
        source_conn.close()


def _verified_manifest(backup: Path) -> dict:
    try:
        manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupError("backup manifest is missing or invalid") from exc
    if not isinstance(manifest, dict) or manifest.get("backup_id") != backup.name:
        raise BackupError("backup manifest identity is invalid")
    try:
        datetime.fromisoformat(str(manifest["created_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError) as exc:
        raise BackupError("backup manifest created_at is invalid") from exc
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise BackupError("backup manifest files are invalid")
    for name, entry in files.items():
        filename = entry.get("filename") if isinstance(entry, dict) else None
        if (
            not isinstance(name, str)
            or not isinstance(filename, str)
            or not re.fullmatch(r"[A-Za-z0-9._-]+", filename)
        ):
            raise BackupError("backup manifest filename is invalid")
        source = (backup / filename).resolve()
        if source.parent != backup or not source.is_file():
            raise BackupError(f"backup file is missing or escapes its directory: {name}")
        if _sha256(source) != entry.get("sha256"):
            raise BackupError(f"backup checksum mismatch: {name}")
    return manifest


def create_private_backup(
    *,
    sources: Mapping[str, Path],
    backup_id: str,
    private_root: Path,
    repo_root: Path,
    retention: int = 3,
) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", backup_id):
        raise BackupError("backup_id contains unsafe characters")
    if isinstance(retention, bool) or not isinstance(retention, int) or retention < 1:
        raise BackupError("retention must be a positive integer")
    private = private_root.resolve()
    root = validate_private_destination(
        private / "backups", private_root=private, repo_root=repo_root.resolve()
    )
    root.mkdir(parents=True, exist_ok=True)
    destination = validate_private_destination(
        root / backup_id, private_root=private, repo_root=repo_root.resolve()
    )
    if destination.exists():
        raise BackupError("backup already exists")
    destination.mkdir()
    manifest = {
        "backup_id": backup_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": {},
    }
    try:
        for name, raw_source in sorted(sources.items()):
            if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
                raise BackupError("backup source name is unsafe")
            source = validate_private_destination(
                raw_source.resolve(), private_root=private, repo_root=repo_root.resolve()
            )
            if not source.is_file():
                raise BackupError(f"backup source missing: {name}")
            target = destination / f"{name}.db"
            _sqlite_backup(source, target)
            manifest["files"][name] = {
                "filename": target.name,
                "sha256": _sha256(target),
                "source_relative": source.relative_to(private).as_posix(),
            }
        (destination / "manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    except BaseException:
        shutil.rmtree(destination)
        raise

    verified_backups: list[tuple[str, Path]] = []
    for candidate in root.iterdir():
        if not candidate.is_dir():
            continue
        resolved = validate_private_destination(
            candidate.resolve(), private_root=private, repo_root=repo_root.resolve()
        )
        verified = _verified_manifest(resolved)
        verified_backups.append((str(verified["created_at"]), resolved))
    verified_backups.sort(key=lambda item: (item[0], item[1].name))
    for _, resolved in verified_backups[:-retention]:
        if resolved == destination:
            continue
        shutil.rmtree(resolved)
    return destination


def restore_private_backup(
    backup_dir: Path,
    *,
    targets: Mapping[str, Path],
    private_root: Path,
    repo_root: Path,
) -> None:
    private = private_root.resolve()
    backup = validate_private_destination(
        backup_dir.resolve(), private_root=private, repo_root=repo_root.resolve()
    )
    manifest = _verified_manifest(backup)
    prepared: list[tuple[Path, Path, Path | None]] = []
    replaced: list[tuple[Path, Path | None]] = []
    try:
        for name, raw_target in targets.items():
            entry = manifest.get("files", {}).get(name)
            if not isinstance(entry, dict):
                raise BackupError(f"backup does not contain source: {name}")
            filename = entry["filename"]
            source = validate_private_destination(
                backup / filename,
                private_root=private,
                repo_root=repo_root.resolve(),
            )
            target = validate_private_destination(
                raw_target.resolve(), private_root=private, repo_root=repo_root.resolve()
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = validate_private_destination(
                target.with_suffix(target.suffix + ".restore.tmp"),
                private_root=private,
                repo_root=repo_root.resolve(),
            )
            if temp.exists():
                temp.unlink()
            _sqlite_backup(source, temp)
            rollback: Path | None = None
            if target.exists():
                if not target.is_file():
                    raise BackupError(f"restore target is not a file: {name}")
                rollback = validate_private_destination(
                    target.with_suffix(target.suffix + ".restore.rollback"),
                    private_root=private,
                    repo_root=repo_root.resolve(),
                )
                if rollback.exists():
                    rollback.unlink()
                shutil.copy2(target, rollback)
            prepared.append((temp, target, rollback))
        try:
            for temp, target, rollback in prepared:
                os.replace(temp, target)
                replaced.append((target, rollback))
        except BaseException as replace_error:
            rollback_error: BaseException | None = None
            for target, rollback in reversed(replaced):
                try:
                    if rollback is None:
                        if target.exists():
                            target.unlink()
                    else:
                        os.replace(rollback, target)
                except BaseException as exc:  # pragma: no cover - catastrophic filesystem failure
                    rollback_error = rollback_error or exc
            if rollback_error is not None:
                raise BackupError("restore failed and rollback was incomplete") from rollback_error
            raise replace_error
    finally:
        for temp, _, rollback in prepared:
            for artifact in (temp, rollback):
                if artifact is not None and artifact.exists():
                    artifact.unlink()
