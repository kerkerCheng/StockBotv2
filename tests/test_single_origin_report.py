"""Derived single-origin/orphan evidence report tests."""

from __future__ import annotations

from query.single_origin_report import classify_rows, render_report


def _row(
    element_id: str,
    *,
    kind: str = "edge",
    origins: list[str] | None = None,
    source_doc_count: int = 1,
    assertion_count: int = 1,
    orphan_reason: str | None = None,
) -> dict:
    return {
        "kind": kind,
        "element_id": element_id,
        "summary": element_id,
        "company_ids": ["co:sivers_semiconductors"],
        "origin_entities": origins or [],
        "source_doc_ids": ["doc_a"] if source_doc_count else [],
        "source_doc_count": source_doc_count,
        "assertion_ids": ["doc_a_e1"] if assertion_count else [],
        "assertion_count": assertion_count,
        "orphan_reason": orphan_reason,
    }


def test_two_independent_origins_disappear_from_single_origin_list() -> None:
    rows = [
        _row("edge:single", origins=["Issuer A"]),
        _row("edge:corroborated", origins=["Issuer A", "Issuer B"]),
    ]

    result = classify_rows(rows)

    assert [row["element_id"] for row in result["single_origin"]] == ["edge:single"]
    assert result["orphans"] == []


def test_missing_claim_or_edge_provenance_is_reported_as_orphan() -> None:
    rows = [
        _row(
            "claim:no-cites",
            kind="claim",
            origins=[],
            source_doc_count=0,
            assertion_count=0,
            orphan_reason="claim_no_cites",
        ),
        _row(
            "edge:no-assertion",
            origins=[],
            source_doc_count=0,
            assertion_count=0,
            orphan_reason="relationship_no_assertion",
        ),
        _row(
            "edge:assertion-no-cites",
            origins=[],
            source_doc_count=0,
            assertion_count=1,
            orphan_reason="assertion_no_cites",
        ),
    ]

    result = classify_rows(rows)

    assert result["single_origin"] == []
    assert {row["orphan_reason"] for row in result["orphans"]} == {
        "claim_no_cites",
        "relationship_no_assertion",
        "assertion_no_cites",
    }


def test_empty_rows_render_cleanly_and_exit_semantics_remain_successful() -> None:
    report = render_report(classify_rows([]), company_id=None)

    assert "Single-origin evidence: 0" in report
    assert "Orphan provenance: 0" in report
    assert "No single-origin or orphan evidence." in report
