"""Durable Research Action lifecycle, privacy, and report-routing proofs."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from mcp_server import graph_mcp
from intake import provenance as intake
from intake import actions as research_actions


BASIS = "Official public filing retained for private research"


def _extraction(
    doc_id: str = "action_doc", *, permission: str = "repo_full", title: str = "Test doc"
) -> dict:
    return {
        "schema_version": "0.1",
        "source_doc": {
            "doc_id": doc_id,
            "title": title,
            "source_type": "filing",
            "evidence_tier": 1,
            "origin_entity": "Test Issuer",
            "storage_permission": permission,
            "permission_basis": BASIS,
            "url": "https://example.com/report",
        },
        "sources": [],
        "nodes": [],
        "edges": [],
        "claims": [],
    }


def _report(marker: str = "ordinary") -> dict:
    return {
        "title": f"Research title {marker}",
        "why_now": f"Why now {marker}",
        "findings": f"Findings {marker}",
        "search_summary": f"Search summary {marker}",
        "l8_notes": f"L8 notes {marker}",
        "counterevidence_and_gaps": f"Counterevidence {marker}",
    }


def _normalized_document(
    doc_id: str = "action_doc",
    *,
    permission: str = "repo_full",
    raw_text: str | None = None,
) -> dict:
    extraction = _extraction(doc_id, permission=permission)
    return {
        "doc_id": doc_id,
        "extraction": extraction,
        "raw_payload": {"raw_text": raw_text} if raw_text is not None else {},
        "storage_permission": permission,
        "permission_basis": BASIS,
        "validation_warnings": [],
    }


def _payload(*documents: dict, marker: str = "ordinary") -> dict:
    return {
        "schema_version": research_actions.ACTION_PAYLOAD_SCHEMA,
        "action_slug": "test-action",
        "report": _report(marker),
        "documents": list(documents or [_normalized_document()]),
    }


def _request_json() -> str:
    document = _normalized_document()
    return json.dumps(
        {
            "schema_version": research_actions.ACTION_PAYLOAD_SCHEMA,
            "action_slug": "test-action",
            "report": _report(),
            "documents": [
                {
                    "extraction_json": json.dumps(document["extraction"]),
                    "storage_permission": "repo_full",
                    "permission_basis": BASIS,
                    "raw_text": "licensed raw",
                }
            ],
        }
    )


def _request_for_docs(*doc_ids: str) -> str:
    documents = []
    for doc_id in doc_ids:
        extraction = _extraction(doc_id)
        documents.append(
            {
                "extraction_json": json.dumps(extraction),
                "storage_permission": "repo_full",
                "permission_basis": BASIS,
                "raw_text": f"licensed raw for {doc_id}",
            }
        )
    return json.dumps(
        {
            "schema_version": research_actions.ACTION_PAYLOAD_SCHEMA,
            "action_slug": "multi-doc-action",
            "report": _report(),
            "documents": documents,
        }
    )


def _durable_fake_loader(calls: list[str], *, fail_once: set[str] | None = None):
    failed: set[str] = set()

    def load(
        extraction_json: str,
        storage_permission: str,
        permission_basis: str,
        *,
        root: Path,
        **raw_payload,
    ) -> dict:
        extraction = json.loads(extraction_json)
        doc_id = extraction["source_doc"]["doc_id"]
        calls.append(doc_id)
        if fail_once and doc_id in fail_once and doc_id not in failed:
            failed.add(doc_id)
            return {
                "status": "pending_graph",
                "doc_id": doc_id,
                "error": "simulated graph outage",
                "resolved_paths": [],
                "finalize_eligible": False,
            }
        provenance = intake.publish_provenance(
            doc_id, extraction, raw_payload, root=root
        )
        intake.mark_graph_complete(doc_id, extraction, root=root)
        return {
            "status": "loaded_or_already_complete",
            "doc_id": doc_id,
            "resolved_paths": provenance["paths"],
            "open_conflict_ids": [],
            "stale_resolution_ids": [],
            "finalize_eligible": provenance["finalize_eligible"],
            "extraction_sha256": intake.canonical_extraction_hash(extraction),
            "counts": {"nodes": 0, "edges": 0, "claims": 0},
            "warnings": [],
        }

    return load


def test_request_contract_is_strict_and_digest_is_canonical() -> None:
    parsed = research_actions.parse_action_request(_request_json())
    assert parsed["action_slug"] == "test-action"

    bad = json.loads(_request_json())
    bad["report"]["typo"] = "must not disappear"
    with pytest.raises(ValueError, match="unknown"):
        research_actions.parse_action_request(json.dumps(bad))

    left = _payload(_normalized_document())
    right = json.loads(json.dumps(left))
    right = {key: right[key] for key in reversed(list(right))}
    assert research_actions.canonical_action_digest(
        left
    ) == research_actions.canonical_action_digest(right)
    right["report"]["findings"] = "changed"
    assert research_actions.canonical_action_digest(
        left
    ) != research_actions.canonical_action_digest(right)


def test_create_exact_status_and_list_have_distinct_disclosure_levels(
    tmp_path: Path,
) -> None:
    raw_secret = "RAW_SENTINEL_MUST_NOT_RETURN"
    report_marker = "REPORT_SENTINEL_EXPECTED_ONLY_BY_ID"
    payload = _payload(_normalized_document(raw_text=raw_secret))
    payload["report"]["findings"] = report_marker
    record = research_actions.create_action(
        payload,
        root=tmp_path,
    )

    exact = research_actions.action_status(record["action_id"], root=tmp_path)
    listing = research_actions.list_action_statuses(root=tmp_path)
    exact_json = json.dumps(exact, ensure_ascii=False)
    list_json = json.dumps(listing, ensure_ascii=False)

    assert exact["state"] == "ready"
    assert exact["age_seconds"] >= 0
    assert report_marker in exact["review_packet"]
    assert raw_secret not in exact_json
    assert report_marker not in list_json
    assert "extraction" not in list_json
    assert listing["actions"][0]["digest_prefix"] == record["action_digest"][:12]
    assert listing["actions"][0]["age_seconds"] >= 0


def test_expired_ready_payload_compacts_on_later_prepare_not_status(
    tmp_path: Path,
) -> None:
    started = datetime(2026, 7, 1, tzinfo=timezone.utc)
    first = research_actions.create_action(_payload(), root=tmp_path, now=started)
    expired_at = started + research_actions.READY_TTL + timedelta(seconds=1)

    status = research_actions.action_status(
        first["action_id"], root=tmp_path, now=expired_at
    )
    assert status["state"] == "expired"
    assert research_actions.read_action(first["action_id"], root=tmp_path)["payload"]

    research_actions.create_action(
        _payload(_normalized_document("second_doc")),
        root=tmp_path,
        now=expired_at,
    )
    compacted = research_actions.read_action(first["action_id"], root=tmp_path)
    assert compacted["state"] == "expired"
    assert compacted["payload"] is None
    assert compacted["review"] == {"title": "Research title ordinary"}


def test_explicit_cleanup_compacts_expired_ready_payload(tmp_path: Path) -> None:
    started = datetime(2026, 7, 1, tzinfo=timezone.utc)
    record = research_actions.create_action(_payload(), root=tmp_path, now=started)

    result = research_actions.cleanup_expired_actions(
        root=tmp_path,
        now=started + research_actions.READY_TTL + timedelta(seconds=1),
    )

    assert result == {"status": "ok", "compacted_count": 1}
    stored = research_actions.read_action(record["action_id"], root=tmp_path)
    assert stored["state"] == "expired"
    assert stored["payload"] is None


def test_active_action_quota_fails_without_partial_publication(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(research_actions, "MAX_NONTERMINAL_ACTIONS", 1)
    research_actions.create_action(_payload(), root=tmp_path)

    with pytest.raises(ValueError, match="staging is full"):
        research_actions.create_action(
            _payload(_normalized_document("second_doc")), root=tmp_path
        )
    assert len(list(research_actions.iter_actions(root=tmp_path))) == 1


def test_live_action_lock_rejects_concurrency_and_stale_lock_is_reclaimed(
    tmp_path: Path,
) -> None:
    record = research_actions.create_action(_payload(), root=tmp_path)
    with research_actions.action_lock(record["action_id"], root=tmp_path):
        with pytest.raises(research_actions.ActionBusyError):
            with research_actions.action_lock(record["action_id"], root=tmp_path):
                pass

    stale = datetime.now(timezone.utc) - research_actions.LOCK_TTL - timedelta(seconds=1)
    lock_path = (
        tmp_path
        / "library"
        / "private"
        / "research_actions"
        / "locks"
        / f"{record['action_id']}.lock"
    )
    lock_path.write_text(
        json.dumps({"token": "stale", "acquired_at": stale.isoformat()}),
        encoding="utf-8",
    )
    with research_actions.action_lock(record["action_id"], root=tmp_path):
        assert lock_path.exists()
    assert not lock_path.exists()


def _mark_documents_complete(record: dict) -> dict:
    for index, execution in enumerate(record["execution"]["documents"]):
        doc = record["document_manifest"][index]
        execution["status"] = "complete"
        execution["result"] = {
            "status": "loaded_or_already_complete",
            "doc_id": doc["doc_id"],
            "resolved_paths": (
                []
                if doc["storage_permission"] == "local_only"
                else [f"extractions/{doc['doc_id']}.json"]
            ),
            "open_conflict_ids": [],
        }
    record["state"] = "partial"
    return record


def test_mixed_report_keeps_full_prose_private_and_stub_server_only(
    tmp_path: Path,
) -> None:
    marker = "PRIVATE_REPORT_SENTINEL"
    record = research_actions.create_action(
        _payload(
            _normalized_document("public_doc"),
            _normalized_document("private_doc", permission="local_only"),
            marker=marker,
        ),
        root=tmp_path,
    )
    record = _mark_documents_complete(record)

    report = research_actions.publish_action_reports(record, root=tmp_path)
    public_text = (tmp_path / report["public_path"]).read_text(encoding="utf-8")
    private_text = (tmp_path / report["private_path"]).read_text(encoding="utf-8")

    assert marker not in public_text
    assert "private_doc" not in public_text
    assert "public_doc" in public_text
    assert marker in private_text
    assert "private_doc" in private_text
    assert "Server-verified apply receipt" in private_text
    assert "- State: `partial`" not in private_text
    assert "## 下一步" not in private_text


@pytest.mark.parametrize(
    ("permissions", "expect_public", "expect_private"),
    [
        (("repo_full",), True, False),
        (("local_only",), False, True),
        (("repo_full", "local_only"), True, True),
    ],
)
def test_report_routing_by_strictest_permission(
    tmp_path: Path,
    permissions: tuple[str, ...],
    expect_public: bool,
    expect_private: bool,
) -> None:
    documents = [
        _normalized_document(f"doc_{index}", permission=permission)
        for index, permission in enumerate(permissions)
    ]
    record = _mark_documents_complete(
        research_actions.create_action(_payload(*documents), root=tmp_path)
    )
    report = research_actions.publish_action_reports(record, root=tmp_path)
    assert bool(report["public_path"]) is expect_public
    assert bool(report["private_path"]) is expect_private


def test_applied_compaction_keeps_review_and_receipts_but_drops_source_bodies(
    tmp_path: Path,
) -> None:
    record = research_actions.create_action(
        _payload(_normalized_document(raw_text="private duplicate")), root=tmp_path
    )
    record = _mark_documents_complete(record)
    record["execution"]["report"] = research_actions.publish_action_reports(
        record, root=tmp_path
    )
    record["state"] = "applied"

    compacted = research_actions.compact_applied_payload(copy.deepcopy(record))
    assert compacted["payload"] is None
    assert compacted["review"] == _report()
    assert compacted["execution"]["documents"][0]["result"]["doc_id"] == "action_doc"


def test_completed_local_only_action_does_not_remain_in_actionable_list(
    tmp_path: Path,
) -> None:
    record = research_actions.create_action(
        _payload(_normalized_document(permission="local_only")), root=tmp_path
    )
    record = _mark_documents_complete(record)
    record["execution"]["report"] = research_actions.publish_action_reports(
        record, root=tmp_path
    )
    record["state"] = "applied"
    record["git"]["status"] = "not_required"
    record = research_actions.compact_applied_payload(record)
    research_actions.save_action(record, root=tmp_path)

    listing = research_actions.list_action_statuses(root=tmp_path)
    exact = research_actions.action_status(record["action_id"], root=tmp_path)

    assert listing["actions"] == []
    assert exact["next_action"].startswith("No action required")


def test_unknown_record_major_fails_closed(tmp_path: Path) -> None:
    record = research_actions.create_action(_payload(), root=tmp_path)
    path = (
        tmp_path
        / "library"
        / "private"
        / "research_actions"
        / f"{record['action_id']}.json"
    )
    stored = json.loads(path.read_text(encoding="utf-8"))
    stored["schema_version"] = "research-action-record/v2"
    path.write_text(json.dumps(stored), encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported"):
        research_actions.read_action(record["action_id"], root=tmp_path)


def test_malformed_same_version_record_fails_closed(tmp_path: Path) -> None:
    record = research_actions.create_action(_payload(), root=tmp_path)
    path = (
        tmp_path
        / "library"
        / "private"
        / "research_actions"
        / f"{record['action_id']}.json"
    )
    stored = json.loads(path.read_text(encoding="utf-8"))
    del stored["execution"]["documents"]
    path.write_text(json.dumps(stored), encoding="utf-8")

    with pytest.raises(ValueError, match="execution document"):
        research_actions.read_action(record["action_id"], root=tmp_path)


def test_prepare_validates_every_document_without_graph_or_publication(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        graph_mcp,
        "_driver",
        lambda: (_ for _ in ()).throw(AssertionError("graph must not be opened")),
    )
    monkeypatch.setattr(
        graph_mcp,
        "publish_provenance",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("prepare must not publish provenance")
        ),
    )

    prepared = graph_mcp._prepare_research_action_impl(
        _request_for_docs("first_doc", "second_doc"), root=tmp_path
    )

    assert prepared["status"] == "ready"
    assert prepared["document_count"] == 2
    assert prepared["action_id"] in prepared["review_packet"]
    assert not (tmp_path / "extractions").exists()
    assert not (tmp_path / "library" / "raw").exists()


def test_prepare_rejects_whole_action_when_later_document_is_invalid(
    tmp_path: Path,
) -> None:
    request = json.loads(_request_for_docs("first_doc", "second_doc"))
    broken = json.loads(request["documents"][1]["extraction_json"])
    broken["source_doc"]["doc_id"] = "../escape"
    request["documents"][1]["extraction_json"] = json.dumps(broken)

    result = graph_mcp._prepare_research_action_impl(
        json.dumps(request), root=tmp_path
    )

    assert result["status"] == "rejected"
    assert result["document_index"] == 1
    assert list(research_actions.iter_actions(root=tmp_path)) == []


def test_apply_partial_retry_skips_completed_document_and_compacts_payload(
    tmp_path: Path,
) -> None:
    prepared = graph_mcp._prepare_research_action_impl(
        _request_for_docs("first_doc", "second_doc"), root=tmp_path
    )
    calls: list[str] = []
    loader = _durable_fake_loader(calls, fail_once={"second_doc"})

    partial = graph_mcp._apply_research_action_impl(
        prepared["action_id"],
        prepared["action_digest"],
        root=tmp_path,
        load_document=loader,
    )
    applied = graph_mcp._apply_research_action_impl(
        prepared["action_id"],
        prepared["action_digest"],
        root=tmp_path,
        load_document=loader,
    )

    assert partial["status"] == "partial"
    assert partial["completed_document_count"] == 1
    assert applied["status"] == "applied"
    assert calls == ["first_doc", "second_doc", "second_doc"]
    stored = research_actions.read_action(prepared["action_id"], root=tmp_path)
    assert stored["state"] == "applied"
    assert stored["payload"] is None
    assert stored["git"]["status"] == "pending"
    assert len(stored["git"]["eligible_paths"]) == 5
    assert (
        research_actions.action_status(prepared["action_id"], root=tmp_path)[
            "review_packet"
        ]
        == prepared["review_packet"]
    )


def test_apply_digest_mismatch_and_replay_do_not_reload(
    tmp_path: Path,
) -> None:
    prepared = graph_mcp._prepare_research_action_impl(
        _request_for_docs("single_doc"), root=tmp_path
    )
    calls: list[str] = []
    loader = _durable_fake_loader(calls)

    mismatch = graph_mcp._apply_research_action_impl(
        prepared["action_id"], "0" * 64, root=tmp_path, load_document=loader
    )
    applied = graph_mcp._apply_research_action_impl(
        prepared["action_id"],
        prepared["action_digest"],
        root=tmp_path,
        load_document=loader,
    )
    replay = graph_mcp._apply_research_action_impl(
        prepared["action_id"],
        prepared["action_digest"],
        root=tmp_path,
        load_document=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("replay must not reload")
        ),
    )

    assert mismatch["status"] == "rejected"
    assert calls == ["single_doc"]
    assert applied["status"] == "applied"
    assert replay["status"] == "applied"
    assert replay["replayed"] is True


def test_report_failure_retry_only_publishes_missing_report(
    tmp_path: Path, monkeypatch
) -> None:
    prepared = graph_mcp._prepare_research_action_impl(
        _request_for_docs("report_doc"), root=tmp_path
    )
    calls: list[str] = []
    loader = _durable_fake_loader(calls)
    real_publish = research_actions.publish_action_reports
    attempts = 0

    def fail_once(record, *, root):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("simulated report disk failure")
        return real_publish(record, root=root)

    monkeypatch.setattr(research_actions, "publish_action_reports", fail_once)
    partial = graph_mcp._apply_research_action_impl(
        prepared["action_id"],
        prepared["action_digest"],
        root=tmp_path,
        load_document=loader,
    )
    applied = graph_mcp._apply_research_action_impl(
        prepared["action_id"],
        prepared["action_digest"],
        root=tmp_path,
        load_document=loader,
    )

    assert partial["status"] == "partial"
    assert partial["error"]["code"] == "report_publish_failed"
    assert applied["status"] == "applied"
    assert calls == ["report_doc"]
    assert attempts == 2


def test_unexpected_apply_exception_returns_redacted_recovery_envelope(
    tmp_path: Path, monkeypatch
) -> None:
    prepared = graph_mcp._prepare_research_action_impl(
        _request_for_docs("unexpected_doc"), root=tmp_path
    )
    loader = _durable_fake_loader([])

    def explode(*_args, **_kwargs):
        raise AssertionError("SENSITIVE_CLIENT_PROSE")

    monkeypatch.setattr(research_actions, "publish_action_reports", explode)
    result = graph_mcp._apply_research_action_impl(
        prepared["action_id"],
        prepared["action_digest"],
        root=tmp_path,
        load_document=loader,
    )

    assert result["status"] == "partial"
    assert result["error"] == {
        "code": "action_apply_internal",
        "message": "AssertionError",
    }
    assert "SENSITIVE_CLIENT_PROSE" not in json.dumps(result)


def test_tampered_prepared_payload_fails_before_loader(tmp_path: Path) -> None:
    prepared = graph_mcp._prepare_research_action_impl(
        _request_for_docs("tamper_doc"), root=tmp_path
    )
    path = (
        tmp_path
        / "library"
        / "private"
        / "research_actions"
        / f"{prepared['action_id']}.json"
    )
    record = json.loads(path.read_text(encoding="utf-8"))
    record["payload"]["report"]["findings"] = "silently changed"
    path.write_text(json.dumps(record), encoding="utf-8")

    result = graph_mcp._apply_research_action_impl(
        prepared["action_id"],
        prepared["action_digest"],
        root=tmp_path,
        load_document=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("tampered payload must not load")
        ),
    )

    assert result["status"] == "rejected"
    assert "integrity" in result["error"]
