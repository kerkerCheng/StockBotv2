"""Explicit recovery and redacted diagnostic exports; no implicit write side effects。

⚠ 2026-09-04 由 `decision_lab/export.py` 搬到 `shared/`：備份與 export 是
infrastructure，Engine C 的 private ledger 也適用同一套規則，不該只有 Engine D 有。

搬遷時把 `from .store import DecisionStore` 換成下面的窄 Protocol——它實際只用到
**兩個方法**，import 整個 `DecisionStore` 只是為了一個型別註解，卻會讓 `shared`
反向依賴 Engine D（`test_upstream_layers_do_not_import_engine_d` 會紅）。
窄 port 同時把「這支 export 需要 store 提供什麼」寫成可讀的契約，
形狀照 `decision_lab/workflow_ports.py`（repo 裡唯一真正的 port）。
"""
from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Protocol

from storage.relational import validate_private_destination


class ExportableStore(Protocol):
    """export 對 store 的**全部**需求。多一個方法都要先問這裡放不放得下。"""

    def lifecycle_invariant_violations(self) -> list[str]: ...

    def table_count(self, table: str) -> int: ...


class ExportError(RuntimeError):
    pass


def export_redacted_summary(
    store: ExportableStore,
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
