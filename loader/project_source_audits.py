"""Project versioned source-audit lifecycle state onto SourceDoc nodes.

Extraction JSON stays immutable replay ground truth. A later credibility event
is mutable research state, so it lives in a separate versioned ledger and is
materialized onto SourceDoc for graph queries and evidence manifests.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable

from jsonschema import Draft202012Validator, FormatChecker

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = ROOT / "schema" / "source_audit.schema.json"
DEFAULT_LEDGER_DIR = ROOT / "library" / "source_audits"


def load_entries(ledger_dir: Path = DEFAULT_LEDGER_DIR) -> list[dict]:
    if not ledger_dir.is_dir():
        raise ValueError(f"source-audit ledger directory is missing: {ledger_dir}")
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    entries: list[dict] = []
    for path in sorted(ledger_dir.glob("*.json")):
        entry = json.loads(path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(entry), key=lambda error: list(error.path))
        if errors:
            detail = "; ".join(error.message for error in errors)
            raise ValueError(f"invalid source-audit ledger {path.name}: {detail}")
        entry["ledger_path"] = path.relative_to(ROOT).as_posix()
        entries.append(entry)
    return entries


def build_projection(entries: Iterable[dict]) -> dict[str, dict]:
    projection: dict[str, dict] = {}
    for entry in entries:
        note = (
            f"{entry['opened_at']}: {entry['reason']}; "
            f"review_by={entry.get('review_by') or 'unscheduled'}; "
            f"evidence={entry['evidence_ref']}"
        )
        for source_doc_id in entry["source_doc_ids"]:
            if source_doc_id in projection:
                raise ValueError(
                    f"SourceDoc {source_doc_id} has multiple audit entries: "
                    f"{projection[source_doc_id]['audit_id']} and {entry['audit_id']}"
                )
            projection[source_doc_id] = {
                "source_doc_id": source_doc_id,
                "source_under_audit": entry["status"] == "active",
                "audit_status": entry["status"],
                "audit_id": entry["audit_id"],
                "audit_note": note,
                "audit_review_by": entry.get("review_by"),
                "audit_ledger_path": entry.get("ledger_path"),
            }
    return projection


def project(driver, *, ledger_dir: Path = DEFAULT_LEDGER_DIR, dry_run: bool = False) -> dict:
    entries = load_entries(ledger_dir)
    projection = build_projection(entries)
    with driver.session() as session:
        existing = {
            row["id"]
            for row in session.run(
                "MATCH (sd:SourceDoc) WHERE sd.id IN $ids RETURN sd.id AS id",
                ids=sorted(projection),
            )
        }
        missing = sorted(set(projection) - existing)
        if missing:
            raise ValueError(f"source-audit ledger references missing SourceDocs: {missing}")
        if not dry_run:
            def apply(transaction) -> None:
                transaction.run(
                    """
                    MATCH (sd:SourceDoc)
                    WHERE sd.source_audit_managed = true
                    REMOVE sd.source_under_audit, sd.audit_status, sd.audit_id,
                           sd.audit_note, sd.audit_review_by, sd.audit_ledger_path
                    SET sd.source_audit_managed = false
                    """
                )
                for values in projection.values():
                    transaction.run(
                        """
                        MATCH (sd:SourceDoc {id: $source_doc_id})
                        SET sd.source_under_audit = $source_under_audit,
                            sd.audit_status = $audit_status,
                            sd.audit_id = $audit_id,
                            sd.audit_note = $audit_note,
                            sd.audit_review_by = $audit_review_by,
                            sd.audit_ledger_path = $audit_ledger_path,
                            sd.source_audit_managed = true
                        """,
                        **values,
                    )

            session.execute_write(apply)
    return {
        "status": "dry_run" if dry_run else "projected",
        "entries": len(entries),
        "source_docs": len(projection),
        "active": sum(row["source_under_audit"] for row in projection.values()),
        "projection": projection if dry_run else None,
    }


def main() -> int:
    from neo4j import GraphDatabase

    parser = argparse.ArgumentParser(description="Project source-audit ledger to Neo4j")
    parser.add_argument("--ledger-dir", type=Path, default=DEFAULT_LEDGER_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        print("NEO4J_PASSWORD is required", file=sys.stderr)
        return 1
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )
    try:
        result = project(driver, ledger_dir=args.ledger_dir, dry_run=args.dry_run)
    finally:
        driver.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
