"""Neo4j 唯讀 query port 與 isolated-fixture fingerprint。"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping


class GraphQueryRejected(ValueError):
    """Cypher 不符合唯讀 boundary。"""


_WRITE_PATTERN = re.compile(
    r"\b(CREATE|MERGE|SET|DELETE|DETACH|REMOVE|DROP|FOREACH|LOAD\s+CSV)\b"
    r"|\bCALL\s+APOC\.(CREATE|MERGE|PERIODIC|REFAC|TRIGGER)\b",
    re.IGNORECASE,
)
_READ_PREFIX = re.compile(r"^\s*(MATCH|OPTIONAL\s+MATCH|RETURN|WITH|UNWIND|SHOW|CALL\s+DB\.)\b", re.IGNORECASE)


@dataclass(frozen=True)
class ReadOnlyCredential:
    uri: str
    username: str
    password: str = field(repr=False)
    scope: str = field(default="read-only", init=False)


class Neo4jReadOnlyQueryPort:
    """只暴露 read query；driver 層另以 read access mode 防禦。"""

    def __init__(self, driver: Any, *, database: str | None = None):
        self._driver = driver
        self._database = database

    def query(self, cypher: str, **params: Any) -> list[dict[str, Any]]:
        normalized = cypher.strip()
        if not normalized or ";" in normalized:
            raise GraphQueryRejected("only one non-empty read query is allowed")
        if _WRITE_PATTERN.search(normalized) or not _READ_PREFIX.search(normalized):
            raise GraphQueryRejected("graph query port accepts read-only Cypher")
        session_kwargs: dict[str, Any] = {"default_access_mode": "READ"}
        if self._database:
            session_kwargs["database"] = self._database
        with self._driver.session(**session_kwargs) as session:
            return list(session.run(normalized, **params).data())


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        items = [_canonical(item) for item in value]
        return sorted(
            items,
            key=lambda item: json.dumps(
                item, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ),
        )
    return value


def fixture_fingerprint(snapshot: Mapping[str, Any]) -> str:
    """只為 isolated fixed fixture 產生 canonical equality fingerprint。"""

    fixture_id = snapshot.get("fixture_id")
    if not isinstance(fixture_id, str) or not fixture_id.startswith("fixture:"):
        raise ValueError("fingerprint equality is restricted to an isolated fixture")
    required = {"nodes", "edges", "constraints", "indexes"}
    missing = sorted(required - set(snapshot))
    if missing:
        raise ValueError(f"fixture snapshot missing: {', '.join(missing)}")
    payload = json.dumps(
        _canonical(dict(snapshot)),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
