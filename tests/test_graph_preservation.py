from __future__ import annotations

import ast
from pathlib import Path

import pytest

from decision_lab.adapters.graph import (
    GraphQueryRejected,
    Neo4jReadOnlyQueryPort,
    fixture_fingerprint,
    live_graph_delta_diagnostic,
)


class NeverRunDriver:
    def session(self, **_kwargs):
        raise AssertionError("write-like query must be rejected before opening a session")


def _fixture_graph() -> dict:
    return {
        "fixture_id": "fixture:decision-lab-preservation-v1",
        "nodes": [
            {
                "id": "co:sivers_semiconductors",
                "labels": ["Company", "Entity"],
                "properties": {"ticker": "SIVE.ST"},
            },
            {
                "id": "tech:cw_laser",
                "labels": ["Entity", "TechNode"],
                "properties": {"name": "CW laser"},
            },
        ],
        "edges": [
            {
                "edge_key": "edge:sive-cw",
                "src_id": "co:sivers_semiconductors",
                "dst_id": "tech:cw_laser",
                "type": "SUPPLIES",
                "properties": {"confidence": 0.6},
            }
        ],
        "constraints": [{"name": "entity_id_unique", "type": "UNIQUENESS"}],
        "indexes": [{"name": "entity_id", "labelsOrTypes": ["Entity"]}],
    }


def test_decision_lab_has_no_graph_write_capability_and_fixture_is_unchanged() -> None:
    before = _fixture_graph()
    after = _fixture_graph()
    port = Neo4jReadOnlyQueryPort(NeverRunDriver())

    with pytest.raises(GraphQueryRejected):
        port.query("MATCH (n) SET n.decision_lab = true RETURN n")

    assert fixture_fingerprint(before) == fixture_fingerprint(after)
    assert not hasattr(port, "write")


def test_live_graph_external_delta_is_diagnostic_not_a_false_failure() -> None:
    before = _fixture_graph()
    before["fixture_id"] = "live:before"
    after = _fixture_graph()
    after["fixture_id"] = "live:after"
    after["nodes"].append(
        {
            "id": "co:external_agent_company",
            "labels": ["Company", "Entity"],
            "properties": {"ticker": "OTHER"},
        }
    )
    after["edges"][0]["properties"]["confidence"] = 0.7

    diagnostic = live_graph_delta_diagnostic(
        before,
        after,
        attribution_by_stable_id={"edge:sive-cw": "parallel_research_agent"},
    )

    assert diagnostic["mode"] == "diagnostic_only"
    assert diagnostic["automatic_repair"] is False
    assert diagnostic["attributed_changes"] == 1
    assert diagnostic["external_or_unattributed_changes"] == 1
    assert {
        (item["stable_id"], item["attribution"])
        for item in diagnostic["changes"]
    } == {
        ("edge:sive-cw", "parallel_research_agent"),
        ("co:external_agent_company", "external_or_unattributed"),
    }


def test_live_graph_delta_rejects_non_string_attribution() -> None:
    with pytest.raises(ValueError, match="non-empty stable IDs"):
        live_graph_delta_diagnostic(
            _fixture_graph(),
            _fixture_graph(),
            attribution_by_stable_id={"edge:sive-cw": 42},  # type: ignore[dict-item]
        )


def test_decision_lab_source_tree_never_imports_graph_writers() -> None:
    root = Path(__file__).resolve().parents[1] / "decision_lab"
    forbidden = ("loader.load_to_neo4j", "loader.edge_resolution")
    imported: set[str] = set()
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
                imported.update(f"{node.module}.{alias.name}" for alias in node.names)

    assert not any(
        module == prefix or module.startswith(prefix + ".")
        for module in imported
        for prefix in forbidden
    )
