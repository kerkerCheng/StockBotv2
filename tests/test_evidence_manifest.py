"""Lane Memo evidence-envelope validation and evidence-scoped gates."""

from __future__ import annotations

import copy

import pytest

from thesis.evidence_manifest import evaluate_evidence_gates, validate_envelope


def _inventory(*, edge_origin: str = "Customer Co") -> dict:
    return {
        "focus_company": {"id": "co:focus", "name": "Focus Co"},
        "company_origin_entities": ["Focus Co", "Customer Co", "Third Party", "Research Org"],
        "claims": {
            "claim:one": {
                "id": "claim:one",
                "statement": "Demand is guided higher.",
                "source_ids": ["claim_s1"],
                "source_doc_id": "claim_doc",
                "origin_entity": "Research Org",
            }
        },
        "edges": {
            "edge:A": {
                "edge_key": "edge:A",
                "src_id": "co:focus",
                "src_name": "Focus Co",
                "relation": "supplies_to",
                "dst_id": "co:customer",
                "dst_name": "Customer Co",
                "attributes": {"sole_source": True, "qualification_status": "qualified"},
                "open_conflict_attributes": [],
                "attribute_resolution_meta": {},
                "assertions": {
                    "doc_a_e1": {
                        "id": "doc_a_e1",
                        "attributes": {"sole_source": True, "qualification_status": "qualified"},
                        "source_ids": ["doc_a_s1"],
                        "source_doc_id": "doc_a",
                        "origin_entity": edge_origin,
                    }
                },
            },
            "edge:B": {
                "edge_key": "edge:B",
                "src_id": "co:other",
                "src_name": "Other Supplier",
                "relation": "supplies_to",
                "dst_id": "co:focus",
                "dst_name": "Focus Co",
                "attributes": {},
                "open_conflict_attributes": ["sole_source"],
                "attribute_resolution_meta": {},
                "assertions": {
                    "doc_b_e1": {
                        "id": "doc_b_e1",
                        "attributes": {"sole_source": True},
                        "source_ids": ["doc_b_s1"],
                        "source_doc_id": "doc_b",
                        "origin_entity": "Other Supplier",
                    }
                },
            },
        },
        "sources": {
            "claim_s1": {
                "id": "claim_s1",
                "locator": "p.1",
                "quote": "Demand will increase.",
                "source_doc_id": "claim_doc",
                "origin_entity": "Research Org",
            },
            "doc_a_s1": {
                "id": "doc_a_s1",
                "locator": "p.2",
                "quote": "Customer confirms this is the only qualified source.",
                "source_doc_id": "doc_a",
                "origin_entity": edge_origin,
            },
            "doc_b_s1": {
                "id": "doc_b_s1",
                "locator": "p.3",
                "quote": "Supplier describes itself as sole source.",
                "source_doc_id": "doc_b",
                "origin_entity": "Other Supplier",
            },
        },
    }


def _claim_item(ref: str = "E1") -> dict:
    return {
        "evidence_ref": ref,
        "type": "claim",
        "claim_id": "claim:one",
        "edge_key": None,
        "attributes": [],
        "assertion_ids": [],
        "source_ids": ["claim_s1"],
        "purpose": "demand driver",
    }


def _edge_item(
    ref: str = "E2",
    *,
    edge_key: str = "edge:A",
    attribute: str = "sole_source",
    assertion_id: str = "doc_a_e1",
    source_id: str = "doc_a_s1",
) -> dict:
    return {
        "evidence_ref": ref,
        "type": "edge",
        "claim_id": None,
        "edge_key": edge_key,
        "attributes": [attribute] if attribute else [],
        "assertion_ids": [assertion_id],
        "source_ids": [source_id],
        "purpose": "bottleneck evidence",
    }


def _envelope(items: list[dict] | None = None, markdown: str | None = None) -> dict:
    items = items or [_claim_item(), _edge_item()]
    markdown = markdown or "# Memo\nDemand is rising [E1]. Sole-source evidence [E2]."
    return {"memo_markdown": markdown, "evidence_items": items}


def test_valid_manifest_resolves_claim_edge_assertion_source_and_quote() -> None:
    result = validate_envelope(_envelope(), _inventory())

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["resolved_evidence"][1]["edge"]["edge_key"] == "edge:A"
    assert result["resolved_evidence"][1]["sources"][0]["quote"].startswith("Customer confirms")


@pytest.mark.parametrize(
    "mutation",
    ["missing_edge", "wrong_assertion", "wrong_source", "missing_claim"],
)
def test_manifest_rejects_ids_outside_or_mismatched_to_context(mutation: str) -> None:
    envelope = _envelope()
    if mutation == "missing_edge":
        envelope["evidence_items"][1]["edge_key"] = "edge:missing"
    elif mutation == "wrong_assertion":
        envelope["evidence_items"][1]["assertion_ids"] = ["doc_b_e1"]
    elif mutation == "wrong_source":
        envelope["evidence_items"][1]["source_ids"] = ["doc_b_s1"]
    else:
        envelope["evidence_items"][0]["claim_id"] = "claim:missing"

    result = validate_envelope(envelope, _inventory())

    assert result["ok"] is False
    assert result["errors"]


@pytest.mark.parametrize(
    "envelope",
    [
        _envelope(markdown="# Memo\nOnly [E1] appears."),
        _envelope(items=[_claim_item("E1")], markdown="# Memo\nReferences [E1] and [E2]."),
    ],
)
def test_markdown_and_manifest_refs_must_align_both_directions(envelope: dict) -> None:
    result = validate_envelope(envelope, _inventory())

    assert result["ok"] is False
    assert any("Markdown" in error or "evidence_ref" in error for error in result["errors"])


def test_unreferenced_open_edge_does_not_block_this_memo() -> None:
    envelope = _envelope(
        items=[_claim_item("E1"), _edge_item("E2", attribute="qualification_status")]
    )
    validation = validate_envelope(envelope, _inventory())

    gate = evaluate_evidence_gates(validation, _inventory())

    assert gate["promotion_pass"] is True
    assert not any("edge:B" in blocker for blocker in gate["promotion_blockers"])


def test_cited_lower_risk_conflict_is_annotated_without_blocking() -> None:
    inventory = _inventory()
    inventory["edges"]["edge:A"]["open_conflict_attributes"] = [
        "qualification_status"
    ]
    envelope = _envelope(
        items=[_claim_item("E1"), _edge_item("E2", attribute="qualification_status")]
    )
    validation = validate_envelope(envelope, inventory)

    gate = evaluate_evidence_gates(validation, inventory)

    assert gate["promotion_pass"] is True
    assert any(note["code"] == "open_conflict" for note in gate["annotations"]["E2"])


def test_cited_open_high_risk_attribute_blocks_promotion() -> None:
    envelope = _envelope(
        items=[
            _claim_item("E1"),
            _edge_item(
                "E2",
                edge_key="edge:B",
                assertion_id="doc_b_e1",
                source_id="doc_b_s1",
            ),
        ]
    )
    validation = validate_envelope(envelope, _inventory())

    gate = evaluate_evidence_gates(validation, _inventory())

    assert gate["promotion_pass"] is False
    assert any(note["code"] == "open_conflict" for note in gate["annotations"]["E2"])


def test_company_wide_diversity_does_not_hide_edge_level_self_report() -> None:
    inventory = _inventory(edge_origin="Focus Co")
    validation = validate_envelope(_envelope(), inventory)

    gate = evaluate_evidence_gates(validation, inventory)

    assert gate["promotion_pass"] is False
    assert any(
        note["code"] == "single_origin_self_report" and note["severity"] == "weak"
        for note in gate["annotations"]["E2"]
    )


def test_customer_side_source_is_not_marked_self_report_weak() -> None:
    inventory = _inventory(edge_origin="Customer Co")
    validation = validate_envelope(_envelope(), inventory)

    gate = evaluate_evidence_gates(validation, inventory)

    assert not any(
        note["code"] == "single_origin_self_report"
        for note in gate["annotations"].get("E2", [])
    )


def test_unknown_resolution_cannot_be_used_as_confirmed_bottleneck() -> None:
    inventory = _inventory()
    edge = inventory["edges"]["edge:A"]
    edge["attributes"].pop("sole_source")
    edge["attribute_resolution_meta"]["sole_source"] = {
        "status": "approved",
        "action": "unknown",
        "resolution_id": "resolution_x",
    }
    validation = validate_envelope(_envelope(), inventory)

    gate = evaluate_evidence_gates(validation, inventory)

    assert gate["promotion_pass"] is False
    assert any(note["code"] == "resolved_unknown" for note in gate["annotations"]["E2"])


def test_selected_source_requires_a_verbatim_quote_for_auditable_sidecar() -> None:
    inventory = _inventory()
    inventory["sources"]["doc_a_s1"]["quote"] = None

    result = validate_envelope(_envelope(), inventory)

    assert result["ok"] is False
    assert any("quote" in error.lower() for error in result["errors"])


def test_cited_source_under_audit_blocks_promotion_for_claim_or_edge() -> None:
    inventory = _inventory()
    inventory["sources"]["claim_s1"]["source_doc"] = {
        "id": "claim_doc",
        "source_under_audit": True,
        "audit_note": "Restatement pending",
    }
    validation = validate_envelope(_envelope(), inventory)

    gate = evaluate_evidence_gates(validation, inventory)

    assert gate["promotion_pass"] is False
    assert any(
        note["code"] == "source_under_audit"
        for note in gate["annotations"]["E1"]
    )
