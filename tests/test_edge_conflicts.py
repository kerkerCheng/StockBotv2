"""Evidence-conflict detector, resolver, and projector contracts."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from loader.edge_resolution import (
    ResolutionValidationError,
    approve_resolution,
    build_projection,
    load_resolutions,
)
from query.edge_conflicts import build_edge_states, detect_conflicts, sort_conflicts


EDGE_KEY = "edge:test"


def _assertion(
    assertion_id: str,
    value,
    *,
    attribute: str = "sole_source",
    confidence: float = 0.7,
    source_id: str | None = None,
) -> dict:
    source_id = source_id or f"{assertion_id}_s1"
    return {
        "id": assertion_id,
        "edge_key": EDGE_KEY,
        "src_id": "co:supplier",
        "relation": "supplies_to",
        "dst_id": "co:customer",
        "attributes": {attribute: value},
        "confidence": confidence,
        "source_ids": [source_id],
        "source_doc_id": assertion_id.rsplit("_", 1)[0],
        "origin_entity": "Issuer",
        "evidence_tier": 1,
        "published_at": "2026-07-01",
    }


def _attribute_state(assertions: list[dict], attribute: str = "sole_source") -> dict:
    return build_edge_states(assertions)[EDGE_KEY]["attributes"][attribute]


def _proposal(conflict: dict, *, action: str = "choose_value", selected_value=False) -> dict:
    return {
        "conflict_id": conflict["conflict_id"],
        "edge_key": conflict["edge_key"],
        "attribute": conflict["attribute"],
        "candidate_set_hash": conflict["candidate_set_hash"],
        "action": action,
        "selected_value": selected_value,
        "supporting_assertion_ids": ["doc_b_e1"],
        "rejected_assertion_ids": ["doc_a_e1"],
        "supporting_source_ids": ["doc_b_e1_s1"],
        "rationale": "Customer-side evidence is in the intended scope.",
        "resolved_confidence": 0.8,
    }


@pytest.mark.parametrize(
    ("values", "expected_status", "expected_value"),
    [
        ([True, True], "auto", True),
        ([None, True], "auto", True),
        ([True, False], "open", None),
    ],
)
def test_detector_materializes_only_unambiguous_values(
    values, expected_status: str, expected_value
) -> None:
    assertions = [
        _assertion(f"doc_{index}_e1", value)
        for index, value in enumerate(values, start=1)
    ]

    state = _attribute_state(assertions)

    assert state["status"] == expected_status
    assert state.get("auto_value") == expected_value


def test_detector_never_uses_confidence_as_a_tie_breaker() -> None:
    assertions = [
        _assertion("supplier_e1", True, confidence=0.9),
        _assertion("customer_e1", False, confidence=0.75),
    ]

    state = _attribute_state(assertions)

    assert state["status"] == "open"
    assert {candidate["value"] for candidate in state["candidates"]} == {True, False}


def test_approved_resolution_projects_value_and_new_evidence_makes_it_stale(
    tmp_path: Path,
) -> None:
    assertions = [
        _assertion("doc_a_e1", True),
        _assertion("doc_b_e1", False),
    ]
    states = build_edge_states(assertions)
    conflict = detect_conflicts(states)[0]
    proposal = _proposal(conflict)

    result = approve_resolution(
        proposal,
        conflict,
        tmp_path,
        approved_by="Cheng",
        approved_at="2026-07-16T00:00:00Z",
    )
    projection = build_projection(states, load_resolutions(tmp_path))[EDGE_KEY]

    assert result["requires_manual_refactor"] is False
    assert projection["attributes"]["sole_source"] is False
    assert projection["open_conflict_attributes"] == []
    assert projection["attribute_resolution_meta"]["sole_source"]["status"] == "approved"

    changed_states = build_edge_states(
        assertions + [_assertion("doc_c_e1", True, confidence=0.95)]
    )
    stale_projection = build_projection(
        changed_states, load_resolutions(tmp_path)
    )[EDGE_KEY]
    assert "sole_source" not in stale_projection["attributes"]
    assert stale_projection["open_conflict_attributes"] == ["sole_source"]
    assert stale_projection["attribute_resolution_meta"]["sole_source"]["status"] == "stale"


def test_unknown_resolution_records_decision_without_inventing_value(tmp_path: Path) -> None:
    states = build_edge_states(
        [_assertion("doc_a_e1", True), _assertion("doc_b_e1", False)]
    )
    conflict = detect_conflicts(states)[0]
    proposal = _proposal(conflict, action="unknown", selected_value=None)

    approve_resolution(
        proposal,
        conflict,
        tmp_path,
        approved_by="Cheng",
        approved_at="2026-07-16T00:00:00Z",
    )
    projection = build_projection(states, load_resolutions(tmp_path))[EDGE_KEY]

    assert "sole_source" not in projection["attributes"]
    assert projection["open_conflict_attributes"] == []
    assert projection["attribute_resolution_meta"]["sole_source"]["action"] == "unknown"
    assert "Customer-side evidence" in projection["attribute_resolution_meta"]["sole_source"]["rationale"]


def test_invalid_proposals_never_write_resolution_file(tmp_path: Path) -> None:
    states = build_edge_states(
        [_assertion("doc_a_e1", True), _assertion("doc_b_e1", False)]
    )
    conflict = detect_conflicts(states)[0]

    bad_assertion = _proposal(conflict)
    bad_assertion["supporting_assertion_ids"] = ["missing_e1"]
    with pytest.raises(ResolutionValidationError, match="assertion"):
        approve_resolution(
            bad_assertion,
            conflict,
            tmp_path,
            approved_by="Cheng",
            approved_at="2026-07-16T00:00:00Z",
        )

    bad_source = _proposal(conflict)
    bad_source["supporting_source_ids"] = ["missing_s1"]
    with pytest.raises(ResolutionValidationError, match="source"):
        approve_resolution(
            bad_source,
            conflict,
            tmp_path,
            approved_by="Cheng",
            approved_at="2026-07-16T00:00:00Z",
        )

    stale = _proposal(conflict)
    stale["candidate_set_hash"] = "stale"
    with pytest.raises(ResolutionValidationError, match="hash"):
        approve_resolution(
            stale,
            conflict,
            tmp_path,
            approved_by="Cheng",
            approved_at="2026-07-16T00:00:00Z",
        )

    with pytest.raises(ResolutionValidationError, match="approval"):
        approve_resolution(
            _proposal(conflict),
            conflict,
            tmp_path,
            approved_by=None,
            approved_at=None,
        )

    assert list(tmp_path.glob("*.json")) == []


def test_split_scope_is_persisted_but_requires_manual_refactor(tmp_path: Path) -> None:
    states = build_edge_states(
        [_assertion("doc_a_e1", True), _assertion("doc_b_e1", False)]
    )
    conflict = detect_conflicts(states)[0]
    proposal = _proposal(conflict, action="split_scope", selected_value=None)

    result = approve_resolution(
        proposal,
        conflict,
        tmp_path,
        approved_by="Cheng",
        approved_at="2026-07-16T00:00:00Z",
    )

    assert result["requires_manual_refactor"] is True


def test_conflict_queue_prioritizes_active_thesis_and_high_risk_attributes() -> None:
    sole_source = detect_conflicts(
        build_edge_states(
            [_assertion("a_e1", True), _assertion("b_e1", False)]
        )
    )[0]
    qualification = detect_conflicts(
        build_edge_states(
            [
                _assertion("c_e1", "sampling", attribute="qualification_status"),
                _assertion("d_e1", "qualified", attribute="qualification_status"),
            ]
        )
    )[0]
    qualification["edge_key"] = "edge:active"

    ordered = sort_conflicts(
        [sole_source, qualification], active_edge_keys={"edge:active"}
    )

    assert ordered[0]["edge_key"] == "edge:active"
    assert ordered[1]["attribute"] == "sole_source"
