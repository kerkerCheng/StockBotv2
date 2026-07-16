"""Freeze, verify, and replay the extraction corpus with global graph identities.

The extraction files are the migration ground truth. A manifest freezes their
repo-relative paths and SHA-256 hashes before any graph mutation. The live
migration refuses graph provenance that is absent from the manifest, requires a
Neo4j dump, clears the legacy relationship/Claim identity layer in one
transaction, and replays every frozen document through ``load_to_neo4j.load``.

Examples::

    python loader/migrate_replay_identity.py \
        --build-manifest loader/manifests/phase1-engine-a-corpus.json

    python loader/migrate_replay_identity.py \
        --manifest loader/manifests/phase1-engine-a-corpus.json --dry-run

    python loader/migrate_replay_identity.py \
        --manifest loader/manifests/phase1-engine-a-corpus.json \
        --backup-dump backups/neo4j-before-phase1.dump
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is present in normal installs
    load_dotenv = None

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if load_dotenv is not None:
    load_dotenv(ROOT / ".env")

from loader.load_to_neo4j import load
from loader.validate import validate


MANIFEST_SCHEMA_VERSION = "1"


class ManifestVerificationError(RuntimeError):
    """Raised when the frozen corpus or live graph fails closed preflight."""


@dataclass(frozen=True)
class VerifiedDocument:
    doc_id: str
    relative_path: str
    sha256: str
    path: Path
    data: dict


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestVerificationError(f"cannot read JSON {path}: {exc}") from exc


def _resolve_inside(root: Path, relative_path: str) -> Path:
    root = root.resolve()
    candidate = (root / Path(relative_path)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ManifestVerificationError(
            f"manifest path escapes repo root: {relative_path}"
        ) from exc
    return candidate


def build_manifest(
    repo_root: str | Path,
    extraction_dir: str | Path = "extractions",
) -> dict:
    """Build a deterministic manifest for every extraction JSON in the corpus."""

    root = Path(repo_root).resolve()
    corpus_dir = _resolve_inside(root, Path(extraction_dir).as_posix())
    if not corpus_dir.is_dir():
        raise ManifestVerificationError(f"extraction directory not found: {corpus_dir}")

    documents: list[dict] = []
    seen_doc_ids: set[str] = set()
    for path in sorted(corpus_dir.glob("*.json"), key=lambda item: item.name.lower()):
        data = _load_json(path)
        try:
            doc_id = data["source_doc"]["doc_id"]
        except (KeyError, TypeError) as exc:
            raise ManifestVerificationError(f"missing source_doc.doc_id: {path}") from exc
        if not isinstance(doc_id, str) or not doc_id:
            raise ManifestVerificationError(f"invalid source_doc.doc_id: {path}")
        if doc_id in seen_doc_ids:
            raise ManifestVerificationError(f"duplicate doc_id in corpus: {doc_id}")
        seen_doc_ids.add(doc_id)
        documents.append(
            {
                "doc_id": doc_id,
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256(path),
            }
        )

    if not documents:
        raise ManifestVerificationError(f"no extraction JSON files found: {corpus_dir}")
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "corpus_root": corpus_dir.relative_to(root).as_posix(),
        "documents": documents,
    }


def write_manifest(manifest: dict, path: str | Path) -> None:
    """Write a manifest in a stable, reviewable representation."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def verify_manifest(
    repo_root: str | Path,
    manifest_path: str | Path,
) -> list[VerifiedDocument]:
    """Verify exact corpus membership, hashes, doc IDs, schema, and references."""

    root = Path(repo_root).resolve()
    manifest = _load_json(Path(manifest_path))
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ManifestVerificationError(
            f"unsupported manifest schema_version: {manifest.get('schema_version')!r}"
        )
    corpus_root = manifest.get("corpus_root")
    entries = manifest.get("documents")
    if not isinstance(corpus_root, str) or not isinstance(entries, list):
        raise ManifestVerificationError("manifest requires corpus_root and documents")

    corpus_dir = _resolve_inside(root, corpus_root)
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in corpus_dir.glob("*.json")
    }
    manifest_paths = {
        entry.get("path")
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    }
    if len(manifest_paths) != len(entries):
        raise ManifestVerificationError("manifest contains duplicate or invalid paths")
    if actual_paths != manifest_paths:
        added = sorted(actual_paths - manifest_paths)
        deleted = sorted(manifest_paths - actual_paths)
        raise ManifestVerificationError(
            f"corpus membership changed; added={added}, deleted={deleted}"
        )

    verified: list[VerifiedDocument] = []
    seen_doc_ids: set[str] = set()
    for entry in entries:
        relative_path = entry.get("path")
        expected_doc_id = entry.get("doc_id")
        expected_hash = entry.get("sha256")
        if not all(isinstance(value, str) and value for value in (
            relative_path,
            expected_doc_id,
            expected_hash,
        )):
            raise ManifestVerificationError(f"invalid manifest entry: {entry!r}")
        path = _resolve_inside(root, relative_path)
        actual_hash = _sha256(path)
        if actual_hash != expected_hash:
            raise ManifestVerificationError(
                f"hash mismatch for {relative_path}: expected {expected_hash}, got {actual_hash}"
            )
        data = _load_json(path)
        actual_doc_id = data.get("source_doc", {}).get("doc_id")
        if actual_doc_id != expected_doc_id:
            raise ManifestVerificationError(
                f"doc_id mismatch for {relative_path}: expected {expected_doc_id}, got {actual_doc_id}"
            )
        if actual_doc_id in seen_doc_ids:
            raise ManifestVerificationError(f"duplicate doc_id in manifest: {actual_doc_id}")
        seen_doc_ids.add(actual_doc_id)

        hard_errors = [error for error in validate(str(path)) if not error.startswith("WARN")]
        if hard_errors:
            raise ManifestVerificationError(
                f"validation failed for {relative_path}: " + " | ".join(hard_errors)
            )
        verified.append(
            VerifiedDocument(
                doc_id=actual_doc_id,
                relative_path=relative_path,
                sha256=actual_hash,
                path=path,
                data=data,
            )
        )
    return verified


def _referenced_source_ids(documents: Iterable[VerifiedDocument]) -> set[str]:
    return {
        source_id
        for document in documents
        for collection in ("nodes", "edges", "claims")
        for item in document.data.get(collection, [])
        for source_id in item.get("source_ids", [])
    }


def reconcile_source_ids(
    manifest_source_ids: set[str],
    graph_source_ids: set[str],
    reviewed_graph_only: set[str] | None = None,
) -> dict[str, list[str]]:
    """Report missing graph evidence and reject provenance outside the corpus."""

    graph_only = sorted(graph_source_ids - manifest_source_ids)
    manifest_only = sorted(manifest_source_ids - graph_source_ids)
    reviewed = reviewed_graph_only or set()
    if reviewed and reviewed != set(graph_only):
        raise ManifestVerificationError(
            "reviewed graph-provenance exception set does not exactly match live graph_only; "
            f"reviewed_only={sorted(reviewed - set(graph_only))}, "
            f"unreviewed={sorted(set(graph_only) - reviewed)}"
        )
    if graph_only and not reviewed:
        raise ManifestVerificationError(
            "graph provenance has no manifest document: " + ", ".join(graph_only)
        )
    return {
        "manifest_only": manifest_only,
        "graph_only": graph_only,
        "reviewed_graph_only": sorted(reviewed),
    }


def load_reconciliation_exceptions(
    path: str | Path,
    *,
    manifest_sha256: str,
) -> set[str]:
    """Load an exact, versioned exception set tied to one frozen manifest."""

    data = _load_json(Path(path))
    if data.get("schema_version") != "1":
        raise ManifestVerificationError("unsupported reconciliation exception schema")
    if data.get("manifest_sha256") != manifest_sha256:
        raise ManifestVerificationError(
            "reconciliation exceptions were approved for a different manifest"
        )
    entries = data.get("exceptions")
    if not isinstance(entries, list):
        raise ManifestVerificationError("reconciliation exceptions must be a list")
    source_ids: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ManifestVerificationError("invalid reconciliation exception entry")
        source_id = entry.get("source_id")
        reason = entry.get("reason")
        if entry.get("disposition") != "drop_legacy_residue":
            raise ManifestVerificationError(
                f"unsupported reconciliation disposition for {source_id!r}"
            )
        if not isinstance(source_id, str) or not source_id:
            raise ManifestVerificationError("reconciliation exception missing source_id")
        if not isinstance(reason, str) or not reason.strip():
            raise ManifestVerificationError(
                f"reconciliation exception missing reason: {source_id}"
            )
        if source_id in source_ids:
            raise ManifestVerificationError(
                f"duplicate reconciliation exception: {source_id}"
            )
        source_ids.add(source_id)
    return source_ids


def _graph_source_ids(session) -> set[str]:
    records = session.run(
        """
        CALL () {
          MATCH (n)
          WHERE n.source_ids IS NOT NULL
          UNWIND n.source_ids AS source_id
          RETURN source_id
          UNION
          MATCH ()-[r]->()
          WHERE r.source_ids IS NOT NULL
          UNWIND r.source_ids AS source_id
          RETURN source_id
        }
        RETURN DISTINCT source_id
        """
    )
    return {record["source_id"] for record in records if record["source_id"]}


def _default_driver_factory():
    try:
        from neo4j import GraphDatabase
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ManifestVerificationError("neo4j package is required") from exc

    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise ManifestVerificationError("NEO4J_PASSWORD is required")
    return GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )


def _migration_summary(documents: list[VerifiedDocument]) -> dict[str, int | bool]:
    return {
        "documents": len(documents),
        "nodes": sum(len(document.data.get("nodes", [])) for document in documents),
        "edges": sum(len(document.data.get("edges", [])) for document in documents),
        "claims": sum(len(document.data.get("claims", [])) for document in documents),
    }


def migrate(
    repo_root: str | Path,
    manifest_path: str | Path,
    *,
    dry_run: bool = False,
    backup_dump: str | Path | None = None,
    reconciliation_exceptions: str | Path | None = None,
    driver_factory: Callable[[], object] = _default_driver_factory,
) -> dict:
    """Verify and replay the frozen corpus; dry-run never opens Neo4j."""

    root = Path(repo_root).resolve()
    documents = verify_manifest(root, manifest_path)
    result: dict = {"dry_run": dry_run, **_migration_summary(documents)}
    manifest_sha256 = _sha256(Path(manifest_path))
    result["manifest_sha256"] = manifest_sha256
    result["referenced_source_ids"] = len(_referenced_source_ids(documents))
    if dry_run:
        return result

    if backup_dump is None:
        raise ManifestVerificationError("live migration requires --backup-dump")
    backup_path = Path(backup_dump).resolve()
    if not backup_path.is_file() or backup_path.stat().st_size == 0:
        raise ManifestVerificationError(f"Neo4j dump not found or empty: {backup_path}")
    result["backup_dump"] = str(backup_path)
    result["backup_sha256"] = _sha256(backup_path)

    driver = driver_factory()
    try:
        with driver.session() as session:
            graph_source_ids = _graph_source_ids(session)
            reviewed_graph_only = (
                load_reconciliation_exceptions(
                    reconciliation_exceptions,
                    manifest_sha256=manifest_sha256,
                )
                if reconciliation_exceptions is not None
                else None
            )
            reconciliation = reconcile_source_ids(
                _referenced_source_ids(documents),
                graph_source_ids,
                reviewed_graph_only=reviewed_graph_only,
            )
            result["pre_replay_manifest_only_source_ids"] = reconciliation[
                "manifest_only"
            ]
            result["dropped_reviewed_legacy_source_ids"] = reconciliation[
                "reviewed_graph_only"
            ]

            def replay(transaction) -> None:
                # Claims, ABOUT edges, legacy domain relationships, and any
                # previous assertions form one replaceable identity layer.
                transaction.run("MATCH ()-[r]->() DELETE r")
                transaction.run(
                    "MATCH (n) WHERE n:Claim OR n:EdgeAssertion DETACH DELETE n"
                )
                # Rebuild node source unions from the frozen corpus instead of
                # retaining the legacy non-APOC overwrite result.
                transaction.run(
                    "MATCH (n:Entity) WHERE NOT n:Claim SET n.source_ids = []"
                )
                for document in documents:
                    load(document.data, transaction, use_apoc=False)

            session.execute_write(replay)
    finally:
        driver.close()

    result["dry_run"] = False
    result["status"] = "replayed"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Freeze or replay the Engine A extraction corpus."
    )
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--build-manifest")
    parser.add_argument("--manifest")
    parser.add_argument("--backup-dump")
    parser.add_argument("--reconciliation-exceptions")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        if args.build_manifest:
            manifest = build_manifest(args.repo_root)
            write_manifest(manifest, args.build_manifest)
            print(
                json.dumps(
                    {
                        "status": "manifest_written",
                        "path": str(Path(args.build_manifest).resolve()),
                        "documents": len(manifest["documents"]),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if not args.manifest:
            parser.error("--manifest is required unless --build-manifest is used")
        result = migrate(
            args.repo_root,
            args.manifest,
            dry_run=args.dry_run,
            backup_dump=args.backup_dump,
            reconciliation_exceptions=args.reconciliation_exceptions,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ManifestVerificationError as exc:
        print(f"FAIL CLOSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
