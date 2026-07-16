"""Validate approved edge-conflict decisions and project canonical attributes."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if load_dotenv is not None:
    load_dotenv(ROOT / ".env")

from query.edge_conflicts import (
    build_edge_states,
    canonical_json,
    detect_conflicts,
    fetch_assertions,
)


RESOLUTION_SCHEMA = ROOT / "schema" / "edge_resolution.schema.json"
DEFAULT_RESOLUTION_DIR = ROOT / "library" / "resolutions"
ALLOWED_ACTIONS = {
    "choose_value",
    "unknown",
    "split_scope",
    "move_to_observation",
}


class ResolutionValidationError(RuntimeError):
    """Raised before any resolution file or graph projection is changed."""


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResolutionValidationError(f"cannot read resolution JSON {path}: {exc}") from exc


def _validate_approved_at(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ResolutionValidationError("approval approved_at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ResolutionValidationError("approval approved_at must include a timezone")


def _validate_schema(resolution: dict) -> None:
    try:
        import jsonschema

        jsonschema.validate(resolution, _load_json(RESOLUTION_SCHEMA))
    except ImportError as exc:  # pragma: no cover
        raise ResolutionValidationError("jsonschema package is required") from exc
    except Exception as exc:
        raise ResolutionValidationError(
            f"resolution schema validation failed: {getattr(exc, 'message', exc)}"
        ) from exc
    _validate_approved_at(resolution["approved_at"])


def _candidate_map(conflict: dict) -> dict[str, dict]:
    return {candidate["assertion_id"]: candidate for candidate in conflict["candidates"]}


def _validate_decision_against_conflict(decision: dict, conflict: dict) -> None:
    for field in ("conflict_id", "edge_key", "attribute", "candidate_set_hash"):
        if decision.get(field) != conflict.get(field):
            noun = "hash" if field == "candidate_set_hash" else field
            raise ResolutionValidationError(f"proposal {noun} does not match live conflict")

    action = decision.get("action")
    if action not in ALLOWED_ACTIONS:
        raise ResolutionValidationError(f"unsupported resolution action: {action!r}")
    if not isinstance(decision.get("rationale"), str) or not decision["rationale"].strip():
        raise ResolutionValidationError("proposal rationale is required")
    confidence = decision.get("resolved_confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        raise ResolutionValidationError("resolved_confidence must be between 0 and 1")

    candidates = _candidate_map(conflict)
    supporting = decision.get("supporting_assertion_ids")
    rejected = decision.get("rejected_assertion_ids")
    supporting_sources = decision.get("supporting_source_ids")
    if not all(isinstance(value, list) for value in (supporting, rejected, supporting_sources)):
        raise ResolutionValidationError("proposal assertion/source fields must be lists")
    referenced_assertions = set(supporting) | set(rejected)
    missing_assertions = referenced_assertions - set(candidates)
    if missing_assertions:
        raise ResolutionValidationError(
            "proposal references nonexistent assertion ids: "
            + ", ".join(sorted(missing_assertions))
        )
    overlap = set(supporting) & set(rejected)
    if overlap:
        raise ResolutionValidationError(
            "proposal lists assertion as both supporting and rejected: "
            + ", ".join(sorted(overlap))
        )
    available_sources = {
        source_id
        for assertion_id in supporting
        for source_id in candidates[assertion_id].get("source_ids", [])
    }
    missing_sources = set(supporting_sources) - available_sources
    if missing_sources:
        raise ResolutionValidationError(
            "proposal references nonexistent supporting source ids: "
            + ", ".join(sorted(missing_sources))
        )

    selected_value = decision.get("selected_value")
    if action == "choose_value":
        if selected_value is None:
            raise ResolutionValidationError("choose_value requires selected_value")
        if not supporting:
            raise ResolutionValidationError("choose_value requires supporting assertion ids")
        if not supporting_sources:
            raise ResolutionValidationError("choose_value requires supporting source ids")
        selected_canonical = canonical_json(selected_value)
        if selected_canonical not in {
            canonical_json(candidate["value"])
            for candidate in conflict["candidates"]
            if candidate["value"] is not None
        }:
            raise ResolutionValidationError("selected_value is not a live candidate value")
        unsupported = [
            assertion_id
            for assertion_id in supporting
            if canonical_json(candidates[assertion_id]["value"]) != selected_canonical
        ]
        if unsupported:
            raise ResolutionValidationError(
                "supporting assertion does not support selected_value: "
                + ", ".join(sorted(unsupported))
            )
    elif selected_value is not None:
        raise ResolutionValidationError(f"{action} requires selected_value=null")


def _resolution_id(conflict: dict) -> str:
    conflict_digest = conflict["conflict_id"].removeprefix("conflict_")
    return f"resolution_{conflict_digest}_{conflict['candidate_set_hash'][:12]}"


def approve_resolution(
    proposal: dict,
    conflict: dict,
    resolution_dir: str | Path,
    *,
    approved_by: str | None,
    approved_at: str | None,
    replace_stale: bool = False,
) -> dict:
    """Persist one explicitly approved proposal after strict evidence validation."""

    if not approved_by or not approved_at:
        raise ResolutionValidationError(
            "explicit human approval requires approved_by and approved_at"
        )
    _validate_approved_at(approved_at)
    _validate_decision_against_conflict(proposal, conflict)
    resolution = {
        "schema_version": "1",
        "resolution_id": _resolution_id(conflict),
        "conflict_id": conflict["conflict_id"],
        "edge_key": conflict["edge_key"],
        "attribute": conflict["attribute"],
        "candidate_set_hash": conflict["candidate_set_hash"],
        "action": proposal["action"],
        "selected_value": proposal.get("selected_value"),
        "supporting_assertion_ids": proposal["supporting_assertion_ids"],
        "rejected_assertion_ids": proposal["rejected_assertion_ids"],
        "supporting_source_ids": proposal["supporting_source_ids"],
        "rationale": proposal["rationale"],
        "resolved_confidence": proposal["resolved_confidence"],
        "approved_by": approved_by,
        "approved_at": approved_at,
    }
    _validate_schema(resolution)

    directory = Path(resolution_dir)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{conflict['conflict_id']}.json"
    if target.exists() and not replace_stale:
        raise ResolutionValidationError(
            f"resolution already exists: {target}; use replace_stale only after review"
        )
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=f".{conflict['conflict_id']}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(resolution, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary_path, target)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return {
        "path": str(target),
        "resolution": resolution,
        "requires_manual_refactor": resolution["action"]
        in {"split_scope", "move_to_observation"},
    }


def load_resolutions(resolution_dir: str | Path) -> dict[str, dict]:
    directory = Path(resolution_dir)
    if not directory.exists():
        return {}
    resolutions: dict[str, dict] = {}
    for path in sorted(directory.glob("*.json")):
        resolution = _load_json(path)
        _validate_schema(resolution)
        conflict_id = resolution["conflict_id"]
        if conflict_id in resolutions:
            raise ResolutionValidationError(
                f"multiple resolution files for {conflict_id}"
            )
        if path.name != f"{conflict_id}.json":
            raise ResolutionValidationError(
                f"resolution filename must be {conflict_id}.json: {path}"
            )
        resolutions[conflict_id] = resolution
    return resolutions


def _candidate_confidence(attribute_state: dict, value) -> float | None:
    matching = [
        candidate.get("confidence")
        for candidate in attribute_state["candidates"]
        if candidate["value"] is not None
        and canonical_json(candidate["value"]) == canonical_json(value)
        and isinstance(candidate.get("confidence"), (int, float))
    ]
    return max(matching) if matching else None


def _candidate_as_of(attribute_state: dict) -> str | None:
    dates = [
        candidate["published_at"]
        for candidate in attribute_state["candidates"]
        if candidate.get("published_at")
    ]
    return max(dates) if dates else None


def build_projection(
    edge_states: dict[str, dict],
    resolutions: dict[str, dict],
) -> dict[str, dict]:
    """Build conflict-safe canonical attributes without touching Neo4j."""

    projection: dict[str, dict] = {}
    for edge_key, edge in edge_states.items():
        attributes: dict = {}
        open_conflicts: list[str] = []
        metadata: dict[str, dict] = {}
        for attribute, state in edge["attributes"].items():
            if state["status"] == "empty":
                continue
            if state["status"] == "auto":
                value = state["auto_value"]
                attributes[attribute] = value
                metadata[attribute] = {
                    "status": "auto",
                    "candidate_set_hash": state["candidate_set_hash"],
                    "assertion_ids": [
                        candidate["assertion_id"]
                        for candidate in state["candidates"]
                        if candidate["value"] is not None
                    ],
                    "value_confidence": _candidate_confidence(state, value),
                    "as_of": _candidate_as_of(state),
                }
                continue

            resolution = resolutions.get(state["conflict_id"])
            if resolution is None:
                open_conflicts.append(attribute)
                continue
            if resolution["candidate_set_hash"] != state["candidate_set_hash"]:
                open_conflicts.append(attribute)
                metadata[attribute] = {
                    "status": "stale",
                    "resolution_id": resolution["resolution_id"],
                    "approved_candidate_set_hash": resolution["candidate_set_hash"],
                    "current_candidate_set_hash": state["candidate_set_hash"],
                }
                continue
            _validate_decision_against_conflict(resolution, state)
            action = resolution["action"]
            if action == "choose_value":
                attributes[attribute] = resolution["selected_value"]
            metadata[attribute] = {
                "status": "approved",
                "action": action,
                "resolution_id": resolution["resolution_id"],
                "value_confidence": resolution["resolved_confidence"],
                "as_of": resolution["approved_at"],
                "approved_by": resolution["approved_by"],
                "rationale": resolution["rationale"],
            }

        projection[edge_key] = {
            "attributes": attributes,
            "open_conflict_attributes": sorted(open_conflicts),
            "attribute_resolution_meta": metadata,
        }
    return projection


def _driver():
    from neo4j import GraphDatabase

    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise ResolutionValidationError("NEO4J_PASSWORD is required")
    return GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )


def project_graph(
    driver,
    resolution_dir: str | Path = DEFAULT_RESOLUTION_DIR,
    *,
    dry_run: bool = False,
) -> dict:
    """Recompute every canonical edge attribute from assertions and decisions."""

    resolutions = load_resolutions(resolution_dir)
    with driver.session() as session:
        edge_states = build_edge_states(fetch_assertions(session))
        projection = build_projection(edge_states, resolutions)
        actual_edge_keys = {
            record["edge_key"]
            for record in session.run(
                "MATCH ()-[r]->() WHERE r.edge_key IS NOT NULL "
                "RETURN r.edge_key AS edge_key"
            )
        }
        expected_edge_keys = set(edge_states)
        if actual_edge_keys != expected_edge_keys:
            raise ResolutionValidationError(
                "canonical relationship/assertion reconciliation failed; "
                f"missing_relationships={sorted(expected_edge_keys - actual_edge_keys)}, "
                f"relationships_without_assertions={sorted(actual_edge_keys - expected_edge_keys)}"
            )
        conflicts = detect_conflicts(edge_states)
        result = {
            "dry_run": dry_run,
            "edges": len(edge_states),
            "materialized_attributes": sum(
                len(edge["attributes"]) for edge in projection.values()
            ),
            "open_conflicts": sum(
                len(edge["open_conflict_attributes"])
                for edge in projection.values()
            ),
            "derived_conflicts": len(conflicts),
            "valid_resolutions": sum(
                1
                for conflict in conflicts
                if conflict["conflict_id"] in resolutions
                and resolutions[conflict["conflict_id"]]["candidate_set_hash"]
                == conflict["candidate_set_hash"]
            ),
        }
        if dry_run:
            result["projection"] = projection
            return result

        projected_at = datetime.now(timezone.utc).isoformat()

        def apply_projection(transaction) -> None:
            for edge_key, edge_projection in projection.items():
                transaction.run(
                    """
                    MATCH ()-[r]->()
                    WHERE r.edge_key = $edge_key
                    SET r.attributes = $attributes_json,
                        r.open_conflict_attributes = $open_conflict_attributes,
                        r.attribute_resolution_meta_json = $meta_json,
                        r.projected_at = $projected_at
                    """,
                    edge_key=edge_key,
                    attributes_json=json.dumps(
                        edge_projection["attributes"], ensure_ascii=False
                    ),
                    open_conflict_attributes=edge_projection[
                        "open_conflict_attributes"
                    ],
                    meta_json=json.dumps(
                        edge_projection["attribute_resolution_meta"],
                        ensure_ascii=False,
                    ),
                    projected_at=projected_at,
                )

        session.execute_write(apply_projection)
    result["dry_run"] = False
    result["status"] = "projected"
    return result


def _current_conflicts(driver) -> dict[str, dict]:
    with driver.session() as session:
        states = build_edge_states(fetch_assertions(session))
    return {conflict["conflict_id"]: conflict for conflict in detect_conflicts(states)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    project_parser = subparsers.add_parser("project")
    project_parser.add_argument("--resolution-dir", default=str(DEFAULT_RESOLUTION_DIR))
    project_parser.add_argument("--dry-run", action="store_true")

    approve_parser = subparsers.add_parser("approve")
    approve_parser.add_argument("proposal")
    approve_parser.add_argument("--approved-by", required=True)
    approve_parser.add_argument("--approved-at", required=True)
    approve_parser.add_argument("--resolution-dir", default=str(DEFAULT_RESOLUTION_DIR))
    approve_parser.add_argument("--replace-stale", action="store_true")

    args = parser.parse_args()
    driver = _driver()
    try:
        if args.command == "project":
            result = project_graph(
                driver,
                args.resolution_dir,
                dry_run=args.dry_run,
            )
            if args.dry_run:
                result = {key: value for key, value in result.items() if key != "projection"}
        else:
            proposal = _load_json(Path(args.proposal))
            conflicts = _current_conflicts(driver)
            conflict = conflicts.get(proposal.get("conflict_id"))
            if conflict is None:
                raise ResolutionValidationError(
                    "proposal conflict is not currently open"
                )
            approval = approve_resolution(
                proposal,
                conflict,
                args.resolution_dir,
                approved_by=args.approved_by,
                approved_at=args.approved_at,
                replace_stale=args.replace_stale,
            )
            result = {
                "approval": approval,
                "projection": project_graph(driver, args.resolution_dir),
            }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ResolutionValidationError as exc:
        print(f"FAIL CLOSED: {exc}", file=sys.stderr)
        return 1
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
