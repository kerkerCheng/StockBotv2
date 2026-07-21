from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path

import pytest

from engine_c.cutover import apply_cutover, plan_cutover
from engine_c.db import _ensure_sqlite_schema, sqlite_path
from storage.relational import initialize_private_root


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _legacy_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    conn.execute(
        """
        INSERT INTO financial_snapshots (ticker, snapshot_date, fetched_at)
        VALUES ('TEST', '2026-07-01', '2026-07-01T00:00:00+00:00')
        """
    )
    conn.execute(
        """
        INSERT INTO manual_fields (ticker, field_name, value, source_note, updated_at)
        VALUES ('TEST', 'backlog', '$10m', 'TEST 10-K', '2026-07-01T00:00:00+00:00')
        """
    )
    conn.execute(
        """
        INSERT INTO consensus_coverage_observations (
            ticker, observation_date, analyst_count, source, data_status, fetched_at
        ) VALUES ('TEST', '2026-07-01', 2, 'fixture', 'observed', '2026-07-01T00:00:00+00:00')
        """
    )
    conn.commit()
    conn.close()


def test_dry_run_does_not_create_private_runtime_and_apply_reconciles(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "engine_c" / "stockbot.db"
    private = repo / "library" / "private"
    _legacy_db(source)
    source_sha = _sha(source)

    planned = plan_cutover(source, private_root=private, repo_root=repo)

    assert planned.pointer_switched is False
    assert not private.exists()

    report = apply_cutover(source, private_root=private, repo_root=repo)
    active = sqlite_path(repo_root=repo, private_root=private)

    assert report.pointer_switched is True
    assert report.source_sha256 == source_sha
    assert _sha(source) == source_sha
    assert active == private / report.destination_relative
    conn = sqlite3.connect(active)
    try:
        assert conn.execute("SELECT COUNT(*) FROM financial_snapshots").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM manual_observations").fetchone()[0] == 1
        manual = conn.execute(
            "SELECT source_ref, as_of, author FROM manual_observations"
        ).fetchone()
        assert manual == ("TEST 10-K", "2026-07-01T00:00:00+00:00", "legacy_engine_c_migration")
    finally:
        conn.close()


@pytest.mark.parametrize(
    "failure_at", ["after_copy", "after_manual", "after_reconcile", "before_pointer"]
)
def test_cutover_failure_never_publishes_partial_pointer(
    tmp_path: Path, failure_at: str
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "engine_c" / "stockbot.db"
    private = repo / "library" / "private"
    _legacy_db(source)

    with pytest.raises(RuntimeError, match="injected"):
        apply_cutover(
            source,
            private_root=private,
            repo_root=repo,
            failure_at=failure_at,
        )

    assert not (private / "runtime_pointer.json").exists()
    assert source.exists()


def test_runtime_authority_files_are_not_in_git_index() -> None:
    repo = Path(__file__).resolve().parent.parent
    tracked = subprocess.run(
        ["git", "ls-files", "engine_c/stockbot.db", "paper_portfolio/config.json", "paper_portfolio/transactions.csv"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    assert tracked == []
    ignore = (repo / ".gitignore").read_text(encoding="utf-8")
    assert "engine_c/stockbot.db" in ignore
    assert "paper_portfolio/transactions.csv" in ignore
