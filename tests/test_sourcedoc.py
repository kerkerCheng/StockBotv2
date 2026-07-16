"""Tests for SourceDoc provenance and graph-backed L8 diversity."""

from __future__ import annotations

import json
from pathlib import Path

from loader.load_to_neo4j import load
from loader.migrate_replay_identity import build_manifest, write_manifest
from loader.migrate_sourcedoc import migrate_sourcedocs
from loader.validate import validate
from thesis.generate_lane_memo import _source_diversity_from_session


class RecordingSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def run(self, query: str, **params):
        self.calls.append((query, params))
        return []


def _document(
    doc_id: str,
    *,
    origin_entity: str | None = "Issuer A",
    source_ids: list[str] | None = None,
) -> dict:
    source_ids = source_ids or [f"{doc_id}_s1"]
    return {
        "schema_version": "0.1",
        "source_doc": {
            "doc_id": doc_id,
            "title": f"{doc_id} title",
            "url": "https://example.test/source",
            "origin_entity": origin_entity,
            "publisher": "Example Publisher",
            "published_at": "2026-07-01",
            "retrieved_at": "2026-07-02",
            "source_type": "filing",
            "evidence_tier": 1,
            "storage_permission": "repo_excerpt",
            "permission_basis": "Public filing; excerpt retained for verification.",
        },
        "sources": [
            {"id": source_id, "locator": f"p.{index}", "quote": "Evidence quote"}
            for index, source_id in enumerate(source_ids, start=1)
        ],
        "nodes": [
            {
                "id": "co:supplier",
                "type": "Company",
                "name": "Supplier",
                "abstraction_level": "device_chip",
                "role": "bottleneck_supplier",
                "aliases": [],
                "attributes": {},
                "confidence": 0.8,
                "source_ids": source_ids,
            },
            {
                "id": "co:customer",
                "type": "Company",
                "name": "Customer",
                "abstraction_level": "module_subsystem",
                "role": "leader",
                "aliases": [],
                "attributes": {},
                "confidence": 0.8,
                "source_ids": source_ids,
            },
        ],
        "edges": [
            {
                "id": "e1",
                "src_id": "co:supplier",
                "dst_id": "co:customer",
                "relation": "supplies_to",
                "attributes": {},
                "confidence": 0.7,
                "source_ids": source_ids,
            }
        ],
        "claims": [
            {
                "id": "cl1",
                "statement": "Supplier has begun qualification.",
                "subject_id": "co:supplier",
                "demand_proof_level": "guided",
                "disproof_condition": "Qualification is cancelled.",
                "confidence": 0.7,
                "source_ids": source_ids,
            }
        ],
    }


def _write_extraction(root: Path, doc: dict) -> Path:
    extraction_dir = root / "extractions"
    extraction_dir.mkdir(exist_ok=True)
    path = extraction_dir / f"{doc['source_doc']['doc_id']}.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_load_creates_sourcedoc_and_cites_from_claim_and_assertion() -> None:
    session = RecordingSession()

    load(_document("doc_a"), session)

    source_query, source_params = next(
        (query, params)
        for query, params in session.calls
        if "MERGE (sd:SourceDoc" in query
    )
    assert source_params == {
        "id": "doc_a",
        "title": "doc_a title",
        "source_type": "filing",
        "evidence_tier": 1,
        "origin_entity": "Issuer A",
        "url": "https://example.test/source",
        "publisher": "Example Publisher",
        "published_at": "2026-07-01",
        "retrieved_at": "2026-07-02",
        "storage_permission": "repo_excerpt",
        "permission_basis": "Public filing; excerpt retained for verification.",
    }
    assert "sd.storage_permission" in source_query

    assertion_query = next(
        query for query, _ in session.calls if "MERGE (ea:EdgeAssertion" in query
    )
    claim_query = next(
        query for query, _ in session.calls if "MERGE (cl:Claim:Entity" in query
    )
    assert "MERGE (ea)-[:CITES]->(sd)" in assertion_query
    assert "MERGE (cl)-[:CITES]->(sd)" in claim_query


def test_relationship_source_unions_remain_document_and_quote_granular() -> None:
    session = RecordingSession()
    load(_document("doc_a", source_ids=["doc_a_s1", "doc_a_s2"]), session)
    load(_document("doc_b", source_ids=["doc_b_s1"]), session)

    relationship_calls = [
        (query, params)
        for query, params in session.calls
        if "MERGE (a)-[r:SUPPLIES_TO" in query
    ]
    assert [params["source_doc_ids"] for _, params in relationship_calls] == [
        ["doc_a"],
        ["doc_b"],
    ]
    assert relationship_calls[0][1]["source_ids"] == ["doc_a_s1", "doc_a_s2"]
    assert all("CASE WHEN source_doc_id IN acc" in query for query, _ in relationship_calls)

    cites = [
        params["source_doc_id"]
        for query, params in session.calls
        if "MERGE (ea:EdgeAssertion" in query and "CITES" in query
    ]
    assert cites == ["doc_a", "doc_b"]


def test_missing_origin_still_loads_but_warns(tmp_path: Path) -> None:
    doc = _document("doc_a", origin_entity=None)
    path = _write_extraction(tmp_path, doc)
    session = RecordingSession()

    errors = validate(str(path))
    load(doc, session)

    assert any(error.startswith("WARN") and "origin_entity" in error for error in errors)
    source_params = next(
        params for query, params in session.calls if "MERGE (sd:SourceDoc" in query
    )
    assert source_params["origin_entity"] is None


class _SingleResult:
    def __init__(self, value: dict) -> None:
        self.value = value

    def single(self):
        return self.value


class _DiversitySession:
    def __init__(self) -> None:
        self.query = ""
        self.params: dict = {}

    def run(self, query: str, **params):
        self.query = query
        self.params = params
        return _SingleResult(
            {
                "total_source_docs": 17,
                "evidence_documents": 7,
                "origin_entities": [
                    "Enablence Technologies",
                    "Sivers Semiconductors",
                    "aleabitoreddit",
                    "silicon_matter_substack",
                ],
            }
        )


def test_source_diversity_is_derived_from_cites_and_ignores_null_origins() -> None:
    session = _DiversitySession()

    result = _source_diversity_from_session(session, "co:sivers_semiconductors")

    assert result["evidence_documents"] == 7
    assert result["origin_entities"] == [
        "Enablence Technologies",
        "Sivers Semiconductors",
        "aleabitoreddit",
        "silicon_matter_substack",
    ]
    assert session.params == {"company_id": "co:sivers_semiconductors"}
    assert "EdgeAssertion" in session.query
    assert "[:CITES]" in session.query
    assert "origin_entity IS NOT NULL" in session.query


def test_sourcedoc_migration_dry_run_uses_frozen_manifest_only(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _write_extraction(root, _document("doc_a"))
    manifest_path = root / "manifest.json"
    write_manifest(build_manifest(root), manifest_path)

    def forbidden_driver_factory():
        raise AssertionError("dry-run must not connect to Neo4j")

    result = migrate_sourcedocs(
        root,
        manifest_path,
        dry_run=True,
        driver_factory=forbidden_driver_factory,
    )

    assert result == {
        "dry_run": True,
        "documents": 1,
        "edge_assertions": 1,
        "claims": 1,
        "cites": 2,
    }
