"""Derive edge-attribute conflicts from EdgeAssertion evidence.

The conflict queue is intentionally computed on demand. EdgeAssertions and
SourceDocs are the evidence truth; approved JSON files are the only persisted
decisions. No mutable conflict registry exists.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

ROOT = Path(__file__).resolve().parent.parent
if load_dotenv is not None:
    load_dotenv(ROOT / ".env")


_Q_ASSERTIONS = """
MATCH (assertion:EdgeAssertion)
OPTIONAL MATCH (assertion)-[:CITES]->(source_doc:SourceDoc)
RETURN assertion.id AS id,
       assertion.edge_key AS edge_key,
       assertion.src_id AS src_id,
       assertion.relation AS relation,
       assertion.dst_id AS dst_id,
       assertion.attributes AS attributes_json,
       assertion.confidence AS confidence,
       assertion.source_ids AS source_ids,
       assertion.source_doc_id AS source_doc_id,
       source_doc.origin_entity AS origin_entity,
       source_doc.evidence_tier AS evidence_tier,
       source_doc.published_at AS published_at
ORDER BY assertion.edge_key, assertion.id
"""


def canonical_json(value) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def conflict_id(edge_key: str, attribute: str) -> str:
    identity = canonical_json([edge_key, attribute])
    return "conflict_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _candidate_set_hash(candidates: list[dict]) -> str:
    identity = [
        {
            "assertion_id": candidate["assertion_id"],
            "value": candidate["value"],
        }
        for candidate in sorted(candidates, key=lambda item: item["assertion_id"])
    ]
    return hashlib.sha256(canonical_json(identity).encode("utf-8")).hexdigest()


def fetch_assertions(session) -> list[dict]:
    """Read every assertion with its SourceDoc evidence metadata."""

    assertions: list[dict] = []
    for record in session.run(_Q_ASSERTIONS):
        raw_attributes = record["attributes_json"]
        if isinstance(raw_attributes, str):
            try:
                attributes = json.loads(raw_attributes)
            except json.JSONDecodeError:
                attributes = {}
        elif isinstance(raw_attributes, dict):
            attributes = raw_attributes
        else:
            attributes = {}
        assertions.append(
            {
                "id": record["id"],
                "edge_key": record["edge_key"],
                "src_id": record["src_id"],
                "relation": record["relation"],
                "dst_id": record["dst_id"],
                "attributes": attributes,
                "confidence": record["confidence"],
                "source_ids": list(record["source_ids"] or []),
                "source_doc_id": record["source_doc_id"],
                "origin_entity": record["origin_entity"],
                "evidence_tier": record["evidence_tier"],
                "published_at": record["published_at"],
            }
        )
    return assertions


def build_edge_states(assertions: Iterable[dict]) -> dict[str, dict]:
    """Group assertions and classify every explicit attribute candidate set."""

    grouped: dict[str, list[dict]] = defaultdict(list)
    for assertion in assertions:
        grouped[assertion["edge_key"]].append(assertion)

    states: dict[str, dict] = {}
    for edge_key, edge_assertions in sorted(grouped.items()):
        first = edge_assertions[0]
        attribute_names = sorted(
            {
                attribute
                for assertion in edge_assertions
                for attribute in assertion.get("attributes", {})
            }
        )
        attribute_states: dict[str, dict] = {}
        for attribute in attribute_names:
            candidates = []
            for assertion in edge_assertions:
                if attribute not in assertion.get("attributes", {}):
                    continue
                candidates.append(
                    {
                        "assertion_id": assertion["id"],
                        "value": assertion["attributes"][attribute],
                        "confidence": assertion.get("confidence"),
                        "source_ids": list(assertion.get("source_ids", [])),
                        "source_doc_id": assertion.get("source_doc_id"),
                        "origin_entity": assertion.get("origin_entity"),
                        "evidence_tier": assertion.get("evidence_tier"),
                        "published_at": assertion.get("published_at"),
                    }
                )
            candidates.sort(key=lambda item: item["assertion_id"])
            distinct_non_null: dict[str, object] = {}
            for candidate in candidates:
                if candidate["value"] is None:
                    continue
                distinct_non_null.setdefault(
                    canonical_json(candidate["value"]), candidate["value"]
                )
            if not distinct_non_null:
                status = "empty"
            elif len(distinct_non_null) == 1:
                status = "auto"
            else:
                status = "open"

            state = {
                "edge_key": edge_key,
                "src_id": first.get("src_id"),
                "relation": first.get("relation"),
                "dst_id": first.get("dst_id"),
                "attribute": attribute,
                "conflict_id": conflict_id(edge_key, attribute),
                "candidate_set_hash": _candidate_set_hash(candidates),
                "status": status,
                "candidates": candidates,
                "distinct_non_null_values": list(distinct_non_null.values()),
            }
            if status == "auto":
                state["auto_value"] = next(iter(distinct_non_null.values()))
            attribute_states[attribute] = state

        states[edge_key] = {
            "edge_key": edge_key,
            "src_id": first.get("src_id"),
            "relation": first.get("relation"),
            "dst_id": first.get("dst_id"),
            "assertion_ids": sorted(assertion["id"] for assertion in edge_assertions),
            "attributes": attribute_states,
        }
    return states


def detect_conflicts(edge_states: dict[str, dict]) -> list[dict]:
    conflicts = [
        state
        for edge in edge_states.values()
        for state in edge["attributes"].values()
        if state["status"] == "open"
    ]
    return sort_conflicts(conflicts)


def _numeric_gap(conflict: dict) -> float:
    values = [
        value
        for value in conflict.get("distinct_non_null_values", [])
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    return max(values) - min(values) if len(values) >= 2 else 0


def _risk_score(conflict: dict, active_edge_keys: set[str]) -> tuple:
    attribute = conflict["attribute"]
    active = conflict["edge_key"] in active_edge_keys
    score = 100 if active else 0
    if attribute == "sole_source":
        score += 50
    elif attribute == "substitutability":
        score += 30
        if _numeric_gap(conflict) >= 2:
            score += 10
    elif attribute == "structural_lead_time_weeks":
        score += 20
    elif attribute == "qualification_status":
        score += 5
    return (score, _numeric_gap(conflict), conflict["conflict_id"])


def sort_conflicts(
    conflicts: Iterable[dict],
    *,
    active_edge_keys: set[str] | None = None,
) -> list[dict]:
    """Prioritize active-thesis and high-risk attributes; never rank by confidence."""

    active = active_edge_keys or set()
    return sorted(
        conflicts,
        key=lambda conflict: _risk_score(conflict, active),
        reverse=True,
    )


def format_conflict_report(edge_states: dict[str, dict]) -> str:
    conflicts = detect_conflicts(edge_states)
    lines = ["# Edge Evidence Conflict Report", ""]
    lines.append(
        f"Edges: {len(edge_states)} | Open conflicts: {len(conflicts)}"
    )
    if not conflicts:
        lines.extend(["", "No open edge-attribute conflicts."])
        return "\n".join(lines) + "\n"
    for conflict in conflicts:
        lines.extend(
            [
                "",
                f"## `{conflict['conflict_id']}`",
                "",
                f"- Edge: `{conflict['edge_key']}` "
                f"(`{conflict.get('src_id')}` -[{conflict.get('relation')}]-> "
                f"`{conflict.get('dst_id')}`)",
                f"- Attribute: `{conflict['attribute']}`",
                f"- Candidate set: `{conflict['candidate_set_hash']}`",
            ]
        )
        for candidate in conflict["candidates"]:
            lines.append(
                f"- `{candidate['assertion_id']}` → "
                f"`{canonical_json(candidate['value'])}`; "
                f"confidence={candidate.get('confidence')}; "
                f"origin={candidate.get('origin_entity') or 'unknown'}; "
                f"sources={candidate.get('source_ids') or []}"
            )
    return "\n".join(lines) + "\n"


def _driver():
    from neo4j import GraphDatabase

    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("NEO4J_PASSWORD is required")
    return GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit all derived states as JSON")
    args = parser.parse_args()
    driver = _driver()
    try:
        with driver.session() as session:
            states = build_edge_states(fetch_assertions(session))
    finally:
        driver.close()
    if args.json:
        print(json.dumps(states, ensure_ascii=False, indent=2))
    else:
        print(format_conflict_report(states), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
