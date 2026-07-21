"""Explicit recovery and redacted diagnostic exports; no implicit write side effects。"""
from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter
from pathlib import Path

from storage.relational import validate_private_destination

from .store import DecisionStore


class ExportError(RuntimeError):
    pass


def export_redacted_summary(
    store: DecisionStore,
    destination: Path,
    *,
    repo_root: Path,
) -> Path:
    repo = repo_root.resolve()
    target = destination.resolve()
    export_root = (repo / "diagnostics" / "decision_lab").resolve()
    try:
        target.relative_to(export_root)
    except ValueError as exc:
        raise ExportError(
            "redacted tracked export must stay under diagnostics/decision_lab"
        ) from exc
    if target.suffix.lower() != ".json":
        raise ExportError("redacted export must be JSON")
    if target.exists():
        raise ExportError("redacted export refuses to overwrite an existing file")
    allowed_tables = (
        "decision_cohorts",
        "system_decisions",
        "paper_events",
        "live_choices",
        "outcome_envelopes",
        "research_work_orders",
    )
    violation_counts = Counter(
        violation.split(":", 1)[0]
        for violation in store.lifecycle_invariant_violations()
    )
    payload = {
        "schema": "decision-lab-redacted-summary-v1",
        "counts": {table: store.table_count(table) for table in allowed_tables},
        "lifecycle_invariant_violations": dict(sorted(violation_counts.items())),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def export_full_sqlite(
    source: Path,
    destination: Path,
    *,
    private_root: Path,
    repo_root: Path,
) -> Path:
    private = private_root.resolve()
    source_path = validate_private_destination(
        source.resolve(), private_root=private, repo_root=repo_root.resolve()
    )
    target = validate_private_destination(
        destination.resolve(), private_root=private, repo_root=repo_root.resolve()
    )
    if not source_path.is_file():
        raise ExportError("full export source is missing")
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = validate_private_destination(
        target.with_suffix(target.suffix + ".export.tmp"),
        private_root=private,
        repo_root=repo_root.resolve(),
    )
    if temp.exists():
        temp.unlink()
    source_conn = sqlite3.connect(f"file:{source_path.as_posix()}?mode=ro", uri=True)
    target_conn = sqlite3.connect(temp)
    try:
        source_conn.backup(target_conn)
        if target_conn.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise ExportError("full export integrity check failed")
    finally:
        target_conn.close()
        source_conn.close()
    os.replace(temp, target)
    return target
