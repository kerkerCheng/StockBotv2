"""從環境變數建立 Engine D default read-only runtime。"""
from __future__ import annotations

import os
from typing import Any

from decision_lab.adapters.graph import Neo4jReadOnlyQueryPort

from .adapters import DefaultRuntimeProvider


def _graph_port_from_environment() -> tuple[Neo4jReadOnlyQueryPort | None, Any | None]:
    uri = os.environ.get("NEO4J_URI", "").strip()
    username = os.environ.get("NEO4J_DECISION_READER_USER", "").strip()
    password = os.environ.get("NEO4J_DECISION_READER_PASSWORD", "")
    database = os.environ.get("NEO4J_DATABASE", "").strip() or None
    if not uri or not username or not password:
        return None, None
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(uri, auth=(username, password))
    except Exception:
        return None, None
    return Neo4jReadOnlyQueryPort(driver, database=database), driver


def build_default_runtime_provider() -> DefaultRuntimeProvider:
    """建立本機 operational provider；缺 credentials 時誠實降級。"""

    graph_port, _driver = _graph_port_from_environment()
    return DefaultRuntimeProvider(graph_port=graph_port)


__all__ = ["build_default_runtime_provider"]
