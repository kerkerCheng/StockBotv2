"""Side-effect-free relational helpers and private-runtime boundary checks."""
from __future__ import annotations

import csv
import os
import sqlite3
import stat
import subprocess
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterator, Sequence


class PrivateStorageError(RuntimeError):
    """A private runtime destination failed closed."""


def _resolved(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _is_reparse_point(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = path.stat(follow_symlinks=False).st_file_attributes
    except (AttributeError, FileNotFoundError, OSError):
        return False
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


@lru_cache(maxsize=1)
def _current_windows_sid() -> str:
    result = subprocess.run(
        ["whoami", "/user", "/fo", "csv", "/nh"],
        check=True,
        capture_output=True,
        text=True,
    )
    row = next(csv.reader([result.stdout.strip()]))
    if len(row) < 2 or not row[1].startswith("S-"):
        raise PrivateStorageError("cannot determine current Windows SID")
    return row[1]


@lru_cache(maxsize=1)
def _current_windows_account() -> str:
    result = subprocess.run(
        ["whoami"],
        check=True,
        capture_output=True,
        text=True,
    )
    account = result.stdout.strip()
    if not account:
        raise PrivateStorageError("cannot determine current Windows account")
    return account


def _windows_owner(path: Path) -> str:
    escaped = str(path).replace("'", "''")
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"(Get-Acl -LiteralPath '{escaped}').Owner",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    owner = result.stdout.strip()
    if not owner:
        raise PrivateStorageError("cannot determine private root owner")
    return owner


def _set_owner_only(path: Path) -> None:
    if os.name == "nt":
        sid = _current_windows_sid()
        result = subprocess.run(
            [
                "icacls",
                str(path),
                "/inheritance:r",
                "/grant:r",
                f"*{sid}:(OI)(CI)F",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise PrivateStorageError(
                f"failed to apply owner-only ACL: {result.stderr.strip()}"
            )
        return
    path.chmod(0o700)


def verify_owner_only(path: Path) -> bool:
    """Return whether ``path`` has no broad write-capable principal.

    Codex on Windows runs under a managed sandbox identity while the workspace is
    owned by the interactive user.  The sandbox adds inherited local SIDs so a
    literal one-ACE check would either reject every real workspace or remove the
    owner's access.  We therefore reject broad Windows principals and accept the
    owner/admin/system plus inherited managed-workspace identities.  POSIX keeps
    the stricter 0700 check.
    """
    path = _resolved(path)
    if not path.exists():
        return False
    if os.name != "nt":
        return stat.S_IMODE(path.stat().st_mode) & 0o077 == 0

    sid = _current_windows_sid().lower()
    account = _current_windows_account().lower()
    try:
        owner = _windows_owner(path).lower()
    except (OSError, subprocess.SubprocessError, PrivateStorageError):
        return False
    result = subprocess.run(
        ["icacls", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        return False
    acl_lines: list[str] = []
    for index, raw_line in enumerate(result.stdout.splitlines()):
        line = raw_line.strip()
        if not line or line.lower().startswith(("successfully ", "failed ")):
            continue
        if index == 0 and line.lower().startswith(str(path).lower()):
            line = line[len(str(path)) :].strip()
        if line:
            acl_lines.append(line)
    if not acl_lines:
        return False
    broad_principals = {
        "everyone",
        "builtin\\users",
        "builtin\\guests",
        "nt authority\\authenticated users",
        "nt authority\\interactive",
        "s-1-1-0",
        "s-1-5-11",
        "s-1-5-32-545",
        "s-1-5-32-546",
    }
    has_authorized_principal = False
    for line in acl_lines:
        principal = line.split(":", 1)[0].strip().lower()
        upper = line.upper()
        if principal in broad_principals and any(
            right in upper for right in ("(F)", "(M)", "(W)")
        ):
            return False
        if principal in {
            account,
            sid,
            owner,
            "nt authority\\system",
            "builtin\\administrators",
        }:
            has_authorized_principal = True
            continue
        if "codexsandbox" in principal:
            has_authorized_principal = True
            continue
        if principal.startswith("s-1-5-21-") and "(I)" in upper:
            # Managed workspace capability SIDs are unresolved local SIDs and
            # inherited from the workspace ACL. Explicit unknown SIDs fail.
            has_authorized_principal = True
            continue
        # Named principals not covered above may be another interactive user.
        if any(right in upper for right in ("(F)", "(M)", "(W)")):
            return False
    return has_authorized_principal


def _default_public_roots() -> tuple[Path, ...]:
    roots = []
    public = os.environ.get("PUBLIC")
    if public:
        roots.append(_resolved(Path(public)))
    return tuple(roots)


def _validate_location(
    destination: Path,
    *,
    private_root: Path,
    repo_root: Path,
    public_roots: Sequence[Path],
) -> None:
    destination = _resolved(destination)
    private_root = _resolved(private_root)
    repo_root = _resolved(repo_root)

    for public_root in public_roots:
        if _within(destination, _resolved(public_root)):
            raise PrivateStorageError("private runtime destination is under a public path")

    if not _within(destination, private_root):
        if _within(destination, repo_root):
            raise PrivateStorageError("private runtime destination is a repository path")
        raise PrivateStorageError("private runtime destination is outside private root")

    approved_repo_enclave = repo_root / "library" / "private"
    if _within(private_root, repo_root) and not _within(
        private_root, approved_repo_enclave
    ):
        raise PrivateStorageError("private root is an unapproved repository path")

    cursor = destination
    while _within(cursor, private_root):
        if cursor.exists() and _is_reparse_point(cursor):
            raise PrivateStorageError("private runtime destination contains a symlink/reparse point")
        if cursor == private_root:
            break
        cursor = cursor.parent


def initialize_private_root(
    private_root: Path,
    *,
    repo_root: Path,
    public_roots: Sequence[Path] | None = None,
) -> Path:
    """Create a private root once; existing roots must already be owner-only."""
    private_root = _resolved(private_root)
    public = tuple(public_roots) if public_roots is not None else _default_public_roots()
    _validate_location(
        private_root,
        private_root=private_root,
        repo_root=repo_root,
        public_roots=public,
    )
    existed = private_root.exists()
    if existed and not private_root.is_dir():
        raise PrivateStorageError("private root must be a directory")
    if existed and not verify_owner_only(private_root):
        raise PrivateStorageError("existing private root is not owner-only")
    if not existed:
        private_root.mkdir(parents=True, exist_ok=False)
        _set_owner_only(private_root)
        if not verify_owner_only(private_root):
            raise PrivateStorageError("failed to establish owner-only private root")
    return private_root


def validate_private_destination(
    destination: Path,
    *,
    private_root: Path,
    repo_root: Path,
    public_roots: Sequence[Path] | None = None,
) -> Path:
    """Validate an already initialized private authority destination."""
    private_root = _resolved(private_root)
    public = tuple(public_roots) if public_roots is not None else _default_public_roots()
    _validate_location(
        destination,
        private_root=private_root,
        repo_root=repo_root,
        public_roots=public,
    )
    if not verify_owner_only(private_root):
        raise PrivateStorageError("private root is not owner-only")
    return _resolved(destination)


def connect_sqlite(path: Path, *, create: bool = True) -> sqlite3.Connection:
    """Open SQLite with the connection semantics shared by private stores."""
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
    elif not path.is_file():
        raise PrivateStorageError(f"SQLite authority is missing: {path}")
    mode = "rwc" if create else "rw"
    conn = sqlite3.connect(
        f"file:{path.as_posix()}?mode={mode}",
        uri=True,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def immediate_transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run one local-writer transaction with explicit rollback semantics."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.rollback()
        raise
    else:
        conn.commit()
