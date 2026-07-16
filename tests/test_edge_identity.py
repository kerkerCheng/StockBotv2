"""Characterization and contract tests for Engine A identity replay."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from loader.load_to_neo4j import edge_key, load
from loader.migrate_replay_identity import (
    ManifestVerificationError,
    build_manifest,
    migrate,
    reconcile_source_ids,
    verify_manifest,
    write_manifest,
)
from loader.validate import validate


class RecordingSession:
    """Small Neo4j-session test double that records Cypher and parameters."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def run(self, query: str, **params):
        self.calls.append((query, params))
        return []


def _document(doc_id: str, *, sole_source: bool = True) -> dict:
    source_id = f"{doc_id}_s1"
    return {
        "schema_version": "0.1",
        "source_doc": {
            "doc_id": doc_id,
            "title": f"{doc_id} title",
            "source_type": "filing",
            "evidence_tier": 1,
            "origin_entity": doc_id,
        },
        "sources": [
            {"id": source_id, "locator": "p.1", "quote": "Example quote"}
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
                "source_ids": [source_id],
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
                "source_ids": [source_id],
            },
        ],
        "edges": [
            {
                "id": "e1",
                "src_id": "co:supplier",
                "dst_id": "co:customer",
                "relation": "supplies_to",
                "attributes": {"sole_source": sole_source},
                "confidence": 0.7,
                "source_ids": [source_id],
            }
        ],
        "claims": [
            {
                "id": "cl1",
                "statement": "The supply relationship is constrained.",
                "subject_id": "e1",
                "demand_proof_level": "guided",
                "disproof_condition": "A second supplier qualifies.",
                "confidence": 0.7,
                "source_ids": [source_id],
            }
        ],
    }


def _write_extraction(root: Path, doc: dict, name: str | None = None) -> Path:
    extraction_dir = root / "extractions"
    extraction_dir.mkdir(exist_ok=True)
    path = extraction_dir / (name or f"{doc['source_doc']['doc_id']}.json")
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_edge_key_uses_the_canonical_triple() -> None:
    first = edge_key("co:supplier", "supplies_to", "co:customer")

    assert first == edge_key("co:supplier", "SUPPLIES_TO", "co:customer")
    assert first != edge_key("co:supplier", "depends_on", "co:customer")
    assert first != edge_key("co:customer", "supplies_to", "co:supplier")


def test_two_documents_preserve_assertions_without_overwriting_attributes() -> None:
    session = RecordingSession()
    load(_document("doc_a", sole_source=True), session)
    load(_document("doc_b", sole_source=False), session)

    relationship_calls = [
        (query, params)
        for query, params in session.calls
        if "MERGE (a)-[r:SUPPLIES_TO" in query
    ]
    assertion_calls = [
        (query, params)
        for query, params in session.calls
        if "MERGE (ea:EdgeAssertion" in query
    ]

    assert len(relationship_calls) == 2
    assert {params["edge_key"] for _, params in relationship_calls} == {
        edge_key("co:supplier", "supplies_to", "co:customer")
    }
    assert all("{edge_key: $edge_key}" in query for query, _ in relationship_calls)
    assert all("r.source_ids" in query and "r.source_doc_ids" in query for query, _ in relationship_calls)
    assert all(params["attributes_json"] == "{}" for _, params in relationship_calls)

    assert len(assertion_calls) == 2
    assert {params["assertion_id"] for _, params in assertion_calls} == {
        "doc_a_e1",
        "doc_b_e1",
    }
    candidates = {
        params["assertion_id"]: json.loads(params["attributes_json"])
        for _, params in assertion_calls
    }
    assert candidates == {
        "doc_a_e1": {"sole_source": True},
        "doc_b_e1": {"sole_source": False},
    }


def test_claim_ids_are_global_and_edge_subjects_use_edge_key() -> None:
    session = RecordingSession()
    load(_document("doc_a"), session)

    claim_calls = [
        (query, params)
        for query, params in session.calls
        if "MERGE (cl:Claim:Entity" in query
    ]
    assert len(claim_calls) == 1
    query, params = claim_calls[0]
    assert params["id"] == "doc_a_cl1"
    assert params["local_id"] == "cl1"
    assert params["subject_kind"] == "edge"
    assert params["subject_edge_key"] == edge_key(
        "co:supplier", "supplies_to", "co:customer"
    )
    assert "MERGE (cl)-[:ABOUT]" not in query


def test_node_subject_claim_keeps_about_relationship() -> None:
    doc = _document("doc_a")
    doc["claims"][0]["subject_id"] = "co:customer"
    session = RecordingSession()

    load(doc, session)

    query, params = next(
        (query, params)
        for query, params in session.calls
        if "MERGE (cl:Claim:Entity" in query
    )
    assert params["subject_kind"] == "node"
    assert params["subject_node_id"] == "co:customer"
    assert "MERGE (cl)-[:ABOUT]->(s)" in query


def test_legacy_lead_time_is_rejected_with_migration_guidance(tmp_path: Path) -> None:
    legacy = _document("doc_a")
    legacy["edges"][0]["attributes"]["lead_time_weeks"] = 12
    legacy_path = _write_extraction(tmp_path, legacy)

    errors = validate(str(legacy_path))

    assert any("lead_time_weeks" in error for error in errors)
    assert any("structural_lead_time_weeks" in error for error in errors)

    current = copy.deepcopy(legacy)
    del current["edges"][0]["attributes"]["lead_time_weeks"]
    current["edges"][0]["attributes"]["structural_lead_time_weeks"] = 12
    current_path = _write_extraction(tmp_path, current, "current.json")
    assert not [error for error in validate(str(current_path)) if not error.startswith("WARN")]


def test_reference_sample_uses_global_sources_and_current_lead_time_schema() -> None:
    sample = Path(__file__).resolve().parent.parent / "samples" / "cpo_external_laser_source.json"

    assert not [error for error in validate(str(sample)) if not error.startswith("WARN")]


@pytest.mark.parametrize("mutation", ["add", "delete", "modify"])
def test_manifest_detects_corpus_changes(tmp_path: Path, mutation: str) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    first_path = _write_extraction(root, _document("doc_a"))
    manifest_path = root / "migration-manifest.json"
    write_manifest(build_manifest(root), manifest_path)

    if mutation == "add":
        _write_extraction(root, _document("doc_b"))
    elif mutation == "delete":
        first_path.unlink()
    else:
        changed = _document("doc_a")
        changed["source_doc"]["title"] = "changed"
        _write_extraction(root, changed)

    with pytest.raises(ManifestVerificationError):
        verify_manifest(root, manifest_path)


def test_dry_run_verifies_manifest_without_opening_neo4j(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _write_extraction(root, _document("doc_a"))
    manifest_path = root / "migration-manifest.json"
    write_manifest(build_manifest(root), manifest_path)

    def forbidden_driver_factory():
        raise AssertionError("dry-run must not create a Neo4j driver")

    result = migrate(
        root,
        manifest_path,
        dry_run=True,
        driver_factory=forbidden_driver_factory,
    )

    assert result["dry_run"] is True
    assert result["documents"] == 1
    assert result["edges"] == 1
    assert result["claims"] == 1


def test_graph_provenance_outside_manifest_fails_closed() -> None:
    with pytest.raises(ManifestVerificationError, match="graph provenance"):
        reconcile_source_ids(
            manifest_source_ids={"doc_a_s1"},
            graph_source_ids={"doc_a_s1", "orphan_s1"},
        )

    report = reconcile_source_ids(
        manifest_source_ids={"doc_a_s1", "doc_b_s1"},
        graph_source_ids={"doc_a_s1"},
    )
    assert report["manifest_only"] == ["doc_b_s1"]
    assert report["graph_only"] == []


def test_exact_reviewed_reconciliation_exceptions_allow_legacy_residue() -> None:
    report = reconcile_source_ids(
        manifest_source_ids={"doc_a_s1"},
        graph_source_ids={"doc_a_s1", "legacy_s1"},
        reviewed_graph_only={"legacy_s1"},
    )

    assert report["graph_only"] == ["legacy_s1"]
    assert report["reviewed_graph_only"] == ["legacy_s1"]

    with pytest.raises(ManifestVerificationError, match="exception set"):
        reconcile_source_ids(
            manifest_source_ids={"doc_a_s1"},
            graph_source_ids={"doc_a_s1"},
            reviewed_graph_only={"stale_exception_s1"},
        )
