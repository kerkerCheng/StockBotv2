"""Safe tracked-runtime → private Engine C cutover with reconciliation。"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from storage.relational import initialize_private_root, validate_private_destination

from .db import _ensure_sqlite_schema
from .manual_observations import append_manual_observation


CUTOVER_VERSION = "engine-c-private-v1"


@dataclass(frozen=True)
class CutoverReport:
    version: str
    source_sha256: str
    source_counts: dict[str, int]
    destination_relative: str
    destination_sha256: str | None
    reconciliation: dict[str, Any]
    pointer_switched: bool


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _count(conn: sqlite3.Connection, table: str) -> int:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]) if exists else 0


def _source_inventory(source: Path) -> tuple[str, dict[str, int]]:
    if not source.is_file():
        raise FileNotFoundError(source)
    conn = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    try:
        counts = {
            table: _count(conn, table)
            for table in (
                "financial_snapshots",
                "manual_fields",
                "consensus_coverage_observations",
            )
        }
    finally:
        conn.close()
    return _sha256(source), counts


def plan_cutover(
    source: Path,
    *,
    private_root: Path,
    repo_root: Path,
) -> CutoverReport:
    source_sha, counts = _source_inventory(source.resolve())
    relative = f"engine_c/stockbot-{CUTOVER_VERSION}-{source_sha[:12]}.db"
    return CutoverReport(
        version=CUTOVER_VERSION,
        source_sha256=source_sha,
        source_counts=counts,
        destination_relative=relative,
        destination_sha256=None,
        reconciliation={"status": "planned"},
        pointer_switched=False,
    )


def apply_cutover(
    source: Path,
    *,
    private_root: Path,
    repo_root: Path,
    author: str = "legacy_engine_c_migration",
    failure_at: str | None = None,
) -> CutoverReport:
    repo = repo_root.resolve()
    private = initialize_private_root(private_root.resolve(), repo_root=repo)
    planned = plan_cutover(source, private_root=private, repo_root=repo)
    pointer = private / "runtime_pointer.json"
    if pointer.is_file():
        try:
            current = json.loads(pointer.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("existing Engine C runtime pointer is invalid") from exc
        if (
            current.get("version") == CUTOVER_VERSION
            and current.get("source_sha256") == planned.source_sha256
            and current.get("engine_c") == planned.destination_relative
        ):
            active = validate_private_destination(
                private / planned.destination_relative,
                private_root=private,
                repo_root=repo,
            )
            if not active.is_file():
                raise RuntimeError("existing Engine C runtime pointer target is missing")
            return CutoverReport(
                version=planned.version,
                source_sha256=planned.source_sha256,
                source_counts=planned.source_counts,
                destination_relative=planned.destination_relative,
                destination_sha256=_sha256(active),
                reconciliation={"status": "already_active"},
                pointer_switched=True,
            )
        raise RuntimeError("Engine C is already cut over; recutover requires explicit migration")
    destination = validate_private_destination(
        private / planned.destination_relative,
        private_root=private,
        repo_root=repo,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = validate_private_destination(
        destination.with_suffix(".cutover.tmp"),
        private_root=private,
        repo_root=repo,
    )
    if temp.exists():
        temp.unlink()
    source_conn: sqlite3.Connection | None = None
    target_conn: sqlite3.Connection | None = None
    try:
        source_conn = sqlite3.connect(f"file:{source.resolve().as_posix()}?mode=ro", uri=True)
        source_conn.row_factory = sqlite3.Row
        target_conn = sqlite3.connect(temp)
        target_conn.row_factory = sqlite3.Row
        source_conn.backup(target_conn)
        if failure_at == "after_copy":
            raise RuntimeError("injected failure after copy")
        _ensure_sqlite_schema(target_conn)
        manual_rows = target_conn.execute(
            """
            SELECT ticker, field_name, value, source_note, updated_at
            FROM manual_fields ORDER BY ticker, field_name
            """
        ).fetchall()
        for row in manual_rows:
            if not row["source_note"]:
                raise RuntimeError(
                    f"manual field lacks provenance: {row['ticker']}:{row['field_name']}"
                )
            append_manual_observation(
                target_conn,
                ticker=row["ticker"],
                field_name=row["field_name"],
                value=row["value"],
                source_ref=row["source_note"],
                as_of=row["updated_at"],
                author=author,
                commit=False,
            )
        target_conn.commit()
        if failure_at == "after_manual":
            raise RuntimeError("injected failure after manual migration")
        destination_counts = {
            table: _count(target_conn, table)
            for table in (
                "financial_snapshots",
                "manual_fields",
                "consensus_coverage_observations",
                "manual_observations",
            )
        }
        reconciliation = {
            "financial_snapshots": destination_counts["financial_snapshots"]
            == planned.source_counts["financial_snapshots"],
            "manual_fields": destination_counts["manual_fields"]
            == planned.source_counts["manual_fields"],
            "consensus_coverage_observations": destination_counts[
                "consensus_coverage_observations"
            ]
            == planned.source_counts["consensus_coverage_observations"],
            "manual_observations": destination_counts["manual_observations"]
            == planned.source_counts["manual_fields"],
            "destination_counts": destination_counts,
        }
        if not all(value for key, value in reconciliation.items() if key != "destination_counts"):
            raise RuntimeError("Engine C cutover reconciliation failed")
        if failure_at == "after_reconcile":
            raise RuntimeError("injected failure after reconciliation")
        target_conn.close()
        target_conn = None
        source_conn.close()
        source_conn = None
        os.replace(temp, destination)
        destination_sha = _sha256(destination)
        if failure_at == "before_pointer":
            raise RuntimeError("injected failure before pointer switch")
        pointer = validate_private_destination(
            private / "runtime_pointer.json",
            private_root=private,
            repo_root=repo,
        )
        pointer_temp = validate_private_destination(
            private / "runtime_pointer.tmp",
            private_root=private,
            repo_root=repo,
        )
        pointer_temp.write_text(
            json.dumps(
                {
                    "version": CUTOVER_VERSION,
                    "engine_c": planned.destination_relative,
                    "engine_c_sha256": destination_sha,
                    "source_sha256": planned.source_sha256,
                },
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        os.replace(pointer_temp, pointer)
        return CutoverReport(
            version=planned.version,
            source_sha256=planned.source_sha256,
            source_counts=planned.source_counts,
            destination_relative=planned.destination_relative,
            destination_sha256=destination_sha,
            reconciliation=reconciliation,
            pointer_switched=True,
        )
    finally:
        if target_conn is not None:
            target_conn.close()
        if source_conn is not None:
            source_conn.close()
        if temp.exists():
            temp.unlink()


def report_json(report: CutoverReport) -> str:
    return json.dumps(asdict(report), ensure_ascii=False, sort_keys=True, indent=2)
