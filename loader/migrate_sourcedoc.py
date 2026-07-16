"""Backfill SourceDoc/CITES from the U2 frozen extraction manifest."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Callable

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if load_dotenv is not None:
    load_dotenv(ROOT / ".env")

from loader.load_to_neo4j import evidence_id, load
from loader.migrate_replay_identity import (
    ManifestVerificationError,
    VerifiedDocument,
    verify_manifest,
)


def _default_driver_factory():
    try:
        from neo4j import GraphDatabase
    except ImportError as exc:  # pragma: no cover
        raise ManifestVerificationError("neo4j package is required") from exc
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise ManifestVerificationError("NEO4J_PASSWORD is required")
    return GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )


def _expected_ids(documents: list[VerifiedDocument]) -> tuple[set[str], set[str], set[str]]:
    source_docs = {document.doc_id for document in documents}
    edge_assertions = {
        evidence_id(document.doc_id, edge["id"])
        for document in documents
        for edge in document.data.get("edges", [])
    }
    claims = {
        evidence_id(document.doc_id, claim["id"])
        for document in documents
        for claim in document.data.get("claims", [])
    }
    return source_docs, edge_assertions, claims


def _collect_ids(session, label: str) -> set[str]:
    records = session.run(f"MATCH (n:`{label}`) RETURN n.id AS id")
    return {record["id"] for record in records}


def _assert_u2_identity_layer(session, documents: list[VerifiedDocument]) -> None:
    expected_source_docs, expected_assertions, expected_claims = _expected_ids(documents)
    actual_assertions = _collect_ids(session, "EdgeAssertion")
    actual_claims = _collect_ids(session, "Claim")
    existing_source_docs = _collect_ids(session, "SourceDoc")
    if actual_assertions != expected_assertions:
        raise ManifestVerificationError(
            "U2 EdgeAssertion set does not match frozen manifest; "
            f"missing={sorted(expected_assertions - actual_assertions)}, "
            f"extra={sorted(actual_assertions - expected_assertions)}"
        )
    if actual_claims != expected_claims:
        raise ManifestVerificationError(
            "U2 Claim set does not match frozen manifest; "
            f"missing={sorted(expected_claims - actual_claims)}, "
            f"extra={sorted(actual_claims - expected_claims)}"
        )
    if not existing_source_docs.issubset(expected_source_docs):
        raise ManifestVerificationError(
            "graph has SourceDoc outside frozen manifest: "
            + ", ".join(sorted(existing_source_docs - expected_source_docs))
        )


def _ensure_constraints(session) -> None:
    session.run(
        "CREATE CONSTRAINT edge_assertion_id_unique IF NOT EXISTS "
        "FOR (ea:EdgeAssertion) REQUIRE ea.id IS UNIQUE"
    ).consume()
    session.run(
        "CREATE CONSTRAINT source_doc_id_unique IF NOT EXISTS "
        "FOR (sd:SourceDoc) REQUIRE sd.id IS UNIQUE"
    ).consume()


def _count_bad_citations(session, label: str) -> int:
    record = session.run(
        f"""
        MATCH (evidence:`{label}`)
        OPTIONAL MATCH (evidence)-[citation:CITES]->(:SourceDoc)
        WITH evidence, count(citation) AS citation_count
        WHERE citation_count <> 1
        RETURN count(evidence) AS bad_count
        """
    ).single()
    return record["bad_count"] if record else 0


def migrate_sourcedocs(
    repo_root: str | Path,
    manifest_path: str | Path,
    *,
    dry_run: bool = False,
    driver_factory: Callable[[], object] = _default_driver_factory,
) -> dict:
    """Backfill SourceDoc/CITES; dry-run verifies the manifest without Neo4j."""

    documents = verify_manifest(repo_root, manifest_path)
    result = {
        "dry_run": dry_run,
        "documents": len(documents),
        "edge_assertions": sum(
            len(document.data.get("edges", [])) for document in documents
        ),
        "claims": sum(
            len(document.data.get("claims", [])) for document in documents
        ),
    }
    result["cites"] = result["edge_assertions"] + result["claims"]
    if dry_run:
        return result

    driver = driver_factory()
    try:
        with driver.session() as session:
            _ensure_constraints(session)
            _assert_u2_identity_layer(session, documents)

            def backfill(transaction) -> None:
                for document in documents:
                    load(document.data, transaction, use_apoc=False)

            session.execute_write(backfill)

            expected_source_docs, _, _ = _expected_ids(documents)
            actual_source_docs = _collect_ids(session, "SourceDoc")
            if actual_source_docs != expected_source_docs:
                raise ManifestVerificationError(
                    "SourceDoc reconciliation failed; "
                    f"missing={sorted(expected_source_docs - actual_source_docs)}, "
                    f"extra={sorted(actual_source_docs - expected_source_docs)}"
                )
            bad_assertion_cites = _count_bad_citations(session, "EdgeAssertion")
            bad_claim_cites = _count_bad_citations(session, "Claim")
            if bad_assertion_cites or bad_claim_cites:
                raise ManifestVerificationError(
                    "CITES reconciliation failed; "
                    f"EdgeAssertion={bad_assertion_cites}, Claim={bad_claim_cites}"
                )
    finally:
        driver.close()

    result["dry_run"] = False
    result["status"] = "backfilled"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill SourceDoc/CITES from the U2 frozen manifest."
    )
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        result = migrate_sourcedocs(
            args.repo_root,
            args.manifest,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ManifestVerificationError as exc:
        print(f"FAIL CLOSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
