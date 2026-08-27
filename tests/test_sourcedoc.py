"""Tests for SourceDoc provenance and graph-backed L8 diversity."""

from __future__ import annotations

import json
from pathlib import Path

from loader.load_to_neo4j import _execute, load
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


class _ConsumableResult:
    def __init__(self) -> None:
        self.consumed = False

    def consume(self) -> None:
        self.consumed = True


class _LazyWriteSession:
    def __init__(self) -> None:
        self.result = _ConsumableResult()

    def run(self, query: str, **params):
        return self.result


def test_execute_consumes_lazy_neo4j_writes() -> None:
    session = _LazyWriteSession()

    returned = _execute(session, "CREATE (:SourceDoc {id: $id})", id="doc_a")

    assert returned is session.result
    assert session.result.consumed is True


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
        "section": None,
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


def test_self_reported_sole_source_warns(tmp_path: Path) -> None:
    doc = _document("doc_a", origin_entity="Supplier")
    doc["edges"][0]["attributes"]["sole_source"] = True
    path = _write_extraction(tmp_path, doc)

    errors = validate(str(path))

    warnings = [
        error
        for error in errors
        if error.startswith("WARN") and "sole_source" in error
    ]
    assert len(warnings) == 1
    assert "e1" in warnings[0]
    assert "verified_by_absence" in warnings[0]


def test_supplier_alias_match_also_warns(tmp_path: Path) -> None:
    doc = _document("doc_a", origin_entity="Supplier Photonics AB")
    doc["nodes"][0]["aliases"] = ["Supplier Photonics"]
    doc["edges"][0]["attributes"]["sole_source"] = True
    path = _write_extraction(tmp_path, doc)

    errors = validate(str(path))

    assert any(
        error.startswith("WARN") and "sole_source" in error for error in errors
    )


def test_customer_confirmed_sole_source_does_not_warn(tmp_path: Path) -> None:
    doc = _document("doc_a", origin_entity="Customer")
    doc["edges"][0]["attributes"]["sole_source"] = True
    path = _write_extraction(tmp_path, doc)

    errors = validate(str(path))

    assert not any(
        error.startswith("WARN") and "sole_source" in error for error in errors
    )


def test_self_report_without_sole_source_does_not_warn(tmp_path: Path) -> None:
    doc = _document("doc_a", origin_entity="Supplier")
    path = _write_extraction(tmp_path, doc)

    errors = validate(str(path))

    assert not any(
        error.startswith("WARN") and "sole_source" in error for error in errors
    )


def test_self_reported_sole_source_survives_technode_wrapping(tmp_path: Path) -> None:
    """把 issuer 包裝成 TechNode 不該繞過 L8。

    事發（2026-08-27）：NVDA Q2 FY2027 CFO commentary 的自動抽取產出
    `tech:ai_cloud_platform -depends_on-> tech:nvidia_ai_infrastructure` 且
    `sole_source=true`，validate 完全靜默通過。三個原因疊在一起：
    (a) 只認 type=="Company"；(b) 只查 src，但 depends_on 的獲益方是 dst；
    (c) 名稱用雙向子字串比對，而 "NVIDIA AI Data Center Infrastructure" 與
    "NVIDIA Corporation" 互相都不是對方的子字串。
    """
    doc = _document("doc_a", origin_entity="Supplier Corporation")
    doc["nodes"].append(
        {
            "id": "tech:supplier_platform",
            "type": "TechNode",
            "name": "Supplier Integrated Platform",
            "abstraction_level": "network_systems",
            "role": None,
            "aliases": [],
            "attributes": {},
            "confidence": 0.8,
            "source_ids": ["doc_a_s1"],
        }
    )
    doc["edges"].append(
        {
            "id": "e2",
            "src_id": "co:customer",
            "dst_id": "tech:supplier_platform",
            "relation": "depends_on",
            "attributes": {"sole_source": True},
            "confidence": 0.7,
            "source_ids": ["doc_a_s1"],
        }
    )
    path = _write_extraction(tmp_path, doc)

    errors = validate(str(path))

    warnings = [e for e in errors if e.startswith("WARN") and "sole_source" in e]
    assert len(warnings) == 1
    assert "e2" in warnings[0]
    assert "tech:supplier_platform" in warnings[0]


def test_issuer_admitting_own_dependency_does_not_warn(tmp_path: Path) -> None:
    """issuer 自承「我依賴某供應商」是不利益陳述，方向上不該觸發自報警告。

    sole_source 替誰背書要看 relation 方向：supplies_to 抬高 src，depends_on 抬高 dst。
    把兩者都當成 src 檢查，會同時漏抓真正的自吹並誤抓這種可信的自承。
    """
    doc = _document("doc_a", origin_entity="Customer")
    doc["edges"].append(
        {
            "id": "e2",
            "src_id": "co:customer",
            "dst_id": "co:supplier",
            "relation": "depends_on",
            "attributes": {"sole_source": True},
            "confidence": 0.7,
            "source_ids": ["doc_a_s1"],
        }
    )
    path = _write_extraction(tmp_path, doc)

    errors = validate(str(path))

    assert not any(e.startswith("WARN") and "sole_source" in e for e in errors)


def test_unregistered_company_id_warns(tmp_path: Path) -> None:
    """co:* 未在 identity registry 時必須現形，不得靜默入圖。

    這道檢查同時攔兩種東西：把類別詞或未具名實體實體化成公司的抽取幻覺
    （co:nvidia_direct_customers_csp、co:unnamed_ai_research_deployment_co），
    以及真公司尚未 onboard。兩者的正當結局不同，所以是 WARN 而非 ERROR——
    由人分流，validate 不代決。
    """
    doc = _document("doc_a")
    doc["nodes"].append(
        {
            "id": "co:definitely_not_in_registry",
            "type": "Company",
            "name": "Direct Customers — CSPs",
            "abstraction_level": "end_demand",
            "role": "adjacent_silicon",
            "aliases": [],
            "attributes": {},
            "confidence": 0.8,
            "source_ids": ["doc_a_s1"],
        }
    )
    path = _write_extraction(tmp_path, doc)

    errors = validate(str(path))

    hits = [e for e in errors if "co:definitely_not_in_registry" in e]
    assert len(hits) == 1
    assert hits[0].startswith("WARN")
    assert "company_identity.json" in hits[0]


def test_registered_company_id_does_not_warn(tmp_path: Path) -> None:
    """registry 內的 co:* 不得觸發警告——否則這道檢查會變成恆亮的雜訊。"""
    doc = _document("doc_a")
    doc["nodes"].append(
        {
            "id": "co:nvidia",
            "type": "Company",
            "name": "NVIDIA Corporation",
            "abstraction_level": "device_chip",
            "role": "leader",
            "aliases": ["NVIDIA"],
            "attributes": {},
            "confidence": 0.9,
            "source_ids": ["doc_a_s1"],
        }
    )
    path = _write_extraction(tmp_path, doc)

    errors = validate(str(path))

    assert not any("co:nvidia" in e and "company_identity.json" in e for e in errors)
