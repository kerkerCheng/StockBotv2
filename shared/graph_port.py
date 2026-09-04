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
    r"|\bCALL\b",
    re.IGNORECASE,
)
_READ_PREFIX = re.compile(
    r"^\s*(MATCH|OPTIONAL\s+MATCH|RETURN|WITH|UNWIND|SHOW)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ReadOnlyCredential:
    uri: str
    username: str
    password: str = field(repr=False)
    scope: str = field(default="read-only", init=False)


class Neo4jReadOnlyQueryPort:
    """只暴露無 procedure 的 read query；RBAC credential 仍是最終防線。"""

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


def live_graph_delta_diagnostic(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    attribution_by_stable_id: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Compare live snapshots by stable ID without asserting equality or repairing。

    Live Neo4j may legitimately change while another research agent ingests data.
    This helper therefore emits an attributed diagnostic only; exact equality is
    intentionally reserved for :func:`fixture_fingerprint`.
    """

    def indexed(snapshot: Mapping[str, Any], field: str, key: str) -> dict[str, Any]:
        if field not in snapshot:
            raise ValueError(f"live graph snapshot missing: {field}")
        raw = snapshot[field]
        if not isinstance(raw, list):
            raise ValueError(f"live graph snapshot {field} must be a list")
        result: dict[str, Any] = {}
        for item in raw:
            if not isinstance(item, Mapping) or not isinstance(item.get(key), str):
                raise ValueError(f"live graph snapshot {field} lacks stable {key}")
            stable_id = str(item[key])
            if stable_id in result:
                raise ValueError(f"duplicate live graph stable ID: {stable_id}")
            result[stable_id] = _canonical(dict(item))
        return result

    attributed = dict(attribution_by_stable_id or {})
    if any(
        not isinstance(key, str)
        or not key
        or not isinstance(value, str)
        or not value
        for key, value in attributed.items()
    ):
        raise ValueError("graph delta attribution requires non-empty stable IDs and actors")
    changes: list[dict[str, str]] = []
    for field, key in (("nodes", "id"), ("edges", "edge_key")):
        left = indexed(before, field, key)
        right = indexed(after, field, key)
        for stable_id in sorted(set(left) | set(right)):
            if stable_id not in left:
                change = "added"
            elif stable_id not in right:
                change = "removed"
            elif left[stable_id] != right[stable_id]:
                change = "changed"
            else:
                continue
            changes.append(
                {
                    "kind": field[:-1],
                    "stable_id": stable_id,
                    "change": change,
                    "attribution": attributed.get(stable_id, "external_or_unattributed"),
                }
            )
    return {
        "mode": "diagnostic_only",
        "automatic_repair": False,
        "changes": changes,
        "attributed_changes": sum(
            item["attribution"] != "external_or_unattributed" for item in changes
        ),
        "external_or_unattributed_changes": sum(
            item["attribution"] == "external_or_unattributed" for item in changes
        ),
    }
