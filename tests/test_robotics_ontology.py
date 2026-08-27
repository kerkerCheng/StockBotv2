from __future__ import annotations

import json
import re
from pathlib import Path

from loader.validate import validate


ROOT = Path(__file__).resolve().parents[1]


def test_neo4j_setup_prewarms_every_relation_in_vocab() -> None:
    vocab = json.loads((ROOT / "schema" / "vocab.json").read_text(encoding="utf-8"))
    setup = (ROOT / "schema" / "neo4j_setup.cypher").read_text(encoding="utf-8")
    prewarmed = set(re.findall(r"\[:([A-Z][A-Z_]*)\]", setup))

    assert {relation.upper() for relation in vocab["relation"]} <= prewarmed


def test_robotics_mini_slice_is_in_all_vocab_surfaces(tmp_path: Path) -> None:
    vocab = json.loads((ROOT / "schema" / "vocab.json").read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "schema" / "intermediate_format.schema.json").read_text(encoding="utf-8")
    )
    node_schema = schema["properties"]["nodes"]["items"]["properties"]
    edge_schema = schema["properties"]["edges"]["items"]["properties"]

    levels = {"deployment_workflow", "robot_system", "robot_subsystem"}
    roles = {"robot_oem", "robot_operator", "robot_component_supplier"}
    relations = {"develops", "deploys", "offered_under"}
    assert levels <= set(vocab["abstraction_level"])
    assert levels <= set(node_schema["abstraction_level"]["enum"])
    assert roles <= set(vocab["role"])
    assert roles <= set(node_schema["role"]["enum"])
    assert relations <= set(vocab["relation"])
    assert relations <= set(edge_schema["relation"]["enum"])

    prompt = (ROOT / "prompts" / "extract_system.md").read_text(encoding="utf-8")
    for term in levels | roles | relations:
        assert f"`{term}`" in prompt

    extraction = {
        "schema_version": "0.1",
        "source_doc": {
            "doc_id": "robotics_ontology_test",
            "title": "Robotics ontology test",
            "url": "https://example.com/robotics",
            "origin_entity": "Example Robotics",
            "published_at": "2026-01-01",
            "retrieved_at": "2026-07-29",
            "storage_permission": "repo_excerpt",
            "permission_basis": "Synthetic test fixture.",
            "source_type": "ir_deck",
            "evidence_tier": 1,
        },
        "sources": [
            {
                "id": "robotics_ontology_test_s1",
                "locator": "test",
                "quote": "Example Robotics deploys Robot One under RaaS.",
            }
        ],
        "nodes": [
            {
                "id": "co:example_robotics",
                "type": "Company",
                "name": "Example Robotics",
                "abstraction_level": "robot_system",
                "role": "robot_oem",
                "aliases": [],
                "attributes": {},
                "confidence": 0.9,
                "source_ids": ["robotics_ontology_test_s1"],
            },
            {
                "id": "prod:robot_one",
                "type": "Product",
                "name": "Robot One",
                "abstraction_level": "robot_system",
                "role": None,
                "aliases": [],
                "attributes": {},
                "confidence": 0.9,
                "source_ids": ["robotics_ontology_test_s1"],
            },
            {
                "id": "tech:raas",
                "type": "TechNode",
                "name": "Robotics-as-a-Service",
                "abstraction_level": "deployment_workflow",
                "role": None,
                "aliases": ["RaaS"],
                "attributes": {},
                "confidence": 0.9,
                "source_ids": ["robotics_ontology_test_s1"],
            },
        ],
        "edges": [
            {
                "id": "robotics_ontology_test_e1",
                "src_id": "co:example_robotics",
                "dst_id": "prod:robot_one",
                "relation": "develops",
                "attributes": {},
                "confidence": 0.75,
                "source_ids": ["robotics_ontology_test_s1"],
            },
            {
                "id": "robotics_ontology_test_e2",
                "src_id": "prod:robot_one",
                "dst_id": "tech:raas",
                "relation": "offered_under",
                "attributes": {},
                "confidence": 0.75,
                "source_ids": ["robotics_ontology_test_s1"],
            },
        ],
        "claims": [],
    }
    path = tmp_path / "robotics_ontology_test.json"
    path.write_text(json.dumps(extraction), encoding="utf-8")
    errors = validate(str(path))

    # 本測試問的是「robotics 字彙在每個 surface 都合法嗎」，不是「這家公司存不存在」。
    # co:example_robotics 是刻意的合成 fixture，本來就不該進 identity registry，
    # 所以 registry 未命中的 WARN 是預期輸出，不是失敗。硬錯誤才是。
    hard = [e for e in errors if not e.startswith("WARN")]
    assert hard == []
    assert all("不在 config/company_identity.json" in e for e in errors), errors


def test_every_vocab_term_exists_in_the_json_schema_enum() -> None:
    """vocab 與 JSON Schema 是兩個字彙表面，必須同步。

    事發（2026-08-06）：`constrained_by` 加進 vocab、加進 neo4j_setup 預熱、
    counter-path 判定也讀到了，validate 卻仍然擋下來——因為
    intermediate_format.schema.json 有自己的 relation enum。既有測試只檢查某個
    robotics slice 出現在各表面，沒有任何東西保證「vocab 有的，schema 也有」。
    這道測試就是那個保證。
    """

    vocab = json.loads((ROOT / "schema" / "vocab.json").read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "schema" / "intermediate_format.schema.json").read_text(encoding="utf-8")
    )
    node_schema = schema["properties"]["nodes"]["items"]["properties"]
    edge_schema = schema["properties"]["edges"]["items"]["properties"]
    claim_schema = schema["properties"]["claims"]["items"]["properties"]
    source_doc_schema = schema["properties"]["source_doc"]["properties"]

    surfaces = {
        "node_type": node_schema["type"]["enum"],
        "abstraction_level": node_schema["abstraction_level"]["enum"],
        "role": node_schema["role"]["enum"],
        "relation": edge_schema["relation"]["enum"],
        "demand_proof_level": claim_schema["demand_proof_level"]["enum"],
        "source_type": source_doc_schema["source_type"]["enum"],
    }
    drift = {
        key: sorted(set(vocab[key]) - set(enum))
        for key, enum in surfaces.items()
        if set(vocab[key]) - set(enum)
    }
    assert not drift, (
        "以下字彙在 schema/vocab.json 有、但 intermediate_format.schema.json 沒有；"
        f"validate 會擋下合法資料：{drift}"
    )


def test_counter_path_relations_are_real_relations() -> None:
    vocab = json.loads((ROOT / "schema" / "vocab.json").read_text(encoding="utf-8"))

    assert set(vocab["counter_path_relation"]) <= set(vocab["relation"])
