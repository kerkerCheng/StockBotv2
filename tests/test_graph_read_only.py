from __future__ import annotations

import pytest

from shared.graph_port import (
    GraphQueryRejected,
    Neo4jReadOnlyQueryPort,
    ReadOnlyCredential,
    fixture_fingerprint,
)


class _Result:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def data(self) -> list[dict]:
        return self._rows


class _Session:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.queries: list[tuple[str, dict]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def run(self, cypher: str, **params):
        self.queries.append((cypher, params))
        return _Result(self.rows)


class _Driver:
    def __init__(self, rows: list[dict]) -> None:
        self.session_instance = _Session(rows)
        self.session_kwargs: dict = {}

    def session(self, **kwargs):
        self.session_kwargs = kwargs
        return self.session_instance


def test_query_port_only_exposes_read_and_uses_read_access_mode() -> None:
    driver = _Driver([{"id": "co:coherent"}])
    port = Neo4jReadOnlyQueryPort(driver, database="neo4j")

    assert port.query("MATCH (n:Entity) RETURN n.id AS id") == [
        {"id": "co:coherent"}
    ]
    assert driver.session_kwargs["default_access_mode"] == "READ"
    assert not hasattr(port, "write")
    assert not hasattr(port, "execute")


@pytest.mark.parametrize(
    "cypher",
    [
        "CREATE (n:Entity {id: 'co:x'})",
        "MATCH (n) SET n.changed = true RETURN n",
        "MATCH (n) DETACH DELETE n",
        "MERGE (n:Entity {id: 'co:x'}) RETURN n",
        "CALL apoc.create.node(['Entity'], {}) YIELD node RETURN node",
        "CALL db.labels() YIELD label RETURN label",
        "WITH 1 AS x CALL db.createLabel('Injected') RETURN x",
    ],
)
def test_write_queries_fail_closed_before_reaching_driver(cypher: str) -> None:
    driver = _Driver([])
    port = Neo4jReadOnlyQueryPort(driver)

    with pytest.raises(GraphQueryRejected):
        port.query(cypher)

    assert driver.session_instance.queries == []


def test_read_only_credential_scope_is_explicit_and_secret_repr_is_redacted() -> None:
    credential = ReadOnlyCredential(
        uri="bolt://fixture:7687", username="reader", password="canary-secret"
    )

    assert credential.scope == "read-only"
    assert "canary-secret" not in repr(credential)


def test_fixture_fingerprint_is_canonical_and_rejects_live_snapshot() -> None:
    snapshot_a = {
        "fixture_id": "fixture:graph-v1",
        "nodes": [
            {"id": "co:b", "labels": ["Entity"], "properties": {"name": "B"}},
            {"id": "co:a", "labels": ["Company", "Entity"], "properties": {"name": "A"}},
        ],
        "edges": [
            {
                "edge_key": "edge:1",
                "src_id": "co:a",
                "dst_id": "co:b",
                "type": "SUPPLIES",
                "properties": {"confidence": 0.8},
            }
        ],
        "constraints": [{"name": "entity_id_unique", "type": "UNIQUENESS"}],
        "indexes": [{"name": "entity_id", "labelsOrTypes": ["Entity"]}],
    }
    snapshot_b = dict(snapshot_a, nodes=list(reversed(snapshot_a["nodes"])))

    assert fixture_fingerprint(snapshot_a) == fixture_fingerprint(snapshot_b)
    assert len(fixture_fingerprint(snapshot_a)) == 64
    with pytest.raises(ValueError, match="isolated fixture"):
        fixture_fingerprint(dict(snapshot_a, fixture_id="live:neo4j"))
