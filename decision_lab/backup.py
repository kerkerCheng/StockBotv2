"""Owner-only SQLite recovery backup/restore with checksums and bounded rotation。"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
from pathlib import Path
from typing import Mapping

from storage.relational import validate_private_destination


class BackupError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    manifest = {"backup_id": backup_id, "files": {}}
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

    backups = sorted(path for path in root.iterdir() if path.is_dir())
    for stale in backups[:-retention]:
        resolved = validate_private_destination(
            stale.resolve(), private_root=private, repo_root=repo_root.resolve()
        )
        if resolved == destination:
            continue
        manifest_path = resolved / "manifest.json"
        if not manifest_path.is_file():
            raise BackupError(f"refusing to rotate unverified directory: {resolved.name}")
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
    try:
        manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupError("backup manifest is missing or invalid") from exc
    prepared: list[tuple[Path, Path]] = []
    try:
        for name, raw_target in targets.items():
            entry = manifest.get("files", {}).get(name)
            if not isinstance(entry, dict):
                raise BackupError(f"backup does not contain source: {name}")
            source = validate_private_destination(
                backup / entry["filename"],
                private_root=private,
                repo_root=repo_root.resolve(),
            )
            if _sha256(source) != entry.get("sha256"):
                raise BackupError(f"backup checksum mismatch: {name}")
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
            prepared.append((temp, target))
        for temp, target in prepared:
            os.replace(temp, target)
    finally:
        for temp, _ in prepared:
            if temp.exists():
                temp.unlink()
