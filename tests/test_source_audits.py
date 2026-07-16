"""Versioned source-audit ledger projection."""

from __future__ import annotations

import pytest

from loader.project_source_audits import build_projection


def _entry(*, audit_id: str = "audit-one", status: str = "active") -> dict:
    return {
        "schema_version": "1.0",
        "audit_id": audit_id,
        "status": status,
        "source_doc_ids": ["doc-a", "doc-b"],
        "opened_at": "2026-07-12",
        "reason": "Restatement pending",
        "review_by": "2026-08-27",
        "evidence_ref": "GitHub Issue #2",
    }


def test_active_audit_projects_durable_source_doc_status() -> None:
    projection = build_projection([_entry()])

    assert projection["doc-a"]["source_under_audit"] is True
    assert projection["doc-a"]["audit_id"] == "audit-one"
    assert "Restatement pending" in projection["doc-a"]["audit_note"]


def test_same_source_doc_cannot_have_two_current_audit_entries() -> None:
    with pytest.raises(ValueError, match="multiple audit entries"):
        build_projection([_entry(), _entry(audit_id="audit-two")])
