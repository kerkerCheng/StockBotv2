"""RA draft 的 `private_context[]`（2026-10-21 批次二 E6；failure log #90；Q3 A）。

券商報告讀到的內容不得進公開 repo：用結構分開兩種語意（L12）——可公開的研究敘述住 `report`，不可公開來源讀到的脈絡住
`private_context`。後者只在私有區（action 紀錄本身就在 library/private/research_actions）、決策區塊照印給使用者看、核准的
仍是同一份內容（進 digest）；公開入圖報告（library/intake，會 commit）只印段數與雜湊。不靠字串偵測（L16 末句）。
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from intake import actions as research_actions

BASIS = "Official public filing retained for private research"
SECRET = "券商估 2027 年份額 35%，目標價 480"
SOURCE = "某券商 2026-10-15 產業報告 p.12"


def _extraction(doc_id: str = "pc_doc") -> dict:
    sid = f"{doc_id}_s1"
    return {
        "schema_version": "0.1",
        "source_doc": {"doc_id": doc_id, "title": "PC doc", "source_type": "filing", "evidence_tier": 1,
                       "origin_entity": "AXT, Inc.", "storage_permission": "repo_full", "permission_basis": BASIS,
                       "url": "https://example.com/pc"},
        "sources": [{"id": sid, "locator": "p1", "quote": "AXT ships InP substrates."}],
        "nodes": [{"id": "co:axt", "type": "Company", "name": "AXT", "abstraction_level": "materials_substrate",
                   "confidence": 0.9, "source_ids": [sid]},
                  {"id": "mat:pc_layer", "type": "Material", "name": "PC layer",
                   "abstraction_level": "materials_substrate", "confidence": 0.9, "source_ids": [sid]}],
        "edges": [{"id": "e1", "src_id": "co:axt", "dst_id": "mat:pc_layer", "relation": "supplies_to",
                   "confidence": 0.8, "source_ids": [sid]}],
        "claims": [],
    }


def _payload(private_context: list[dict] | None) -> dict:
    extraction = _extraction()
    payload = {
        "schema_version": research_actions.ACTION_PAYLOAD_SCHEMA,
        "action_slug": "pc-action",
        "report": {"title": "PC title", "why_now": "w", "findings": "公開的研究發現", "search_summary": "s",
                   "l8_notes": "l8", "counterevidence_and_gaps": "c"},
        "documents": [{"doc_id": extraction["source_doc"]["doc_id"], "extraction": extraction, "raw_payload": {},
                       "storage_permission": "repo_full", "permission_basis": BASIS, "validation_warnings": []}],
    }
    if private_context is not None:
        payload["private_context"] = private_context
    return payload


PRIVATE = [{"source": SOURCE, "text": SECRET}]


def _applied(record: dict) -> dict:
    applied = copy.deepcopy(record)
    applied["state"] = "applying"
    applied["execution"]["report"] = {"status": "pending"}
    for item in applied["execution"]["documents"]:
        item["status"] = "complete"
    return applied


def test_private_context_is_top_level_optional_and_enters_the_digest() -> None:
    plain, private = _payload(None), _payload(PRIVATE)
    research_actions.validate_normalized_payload(plain)
    research_actions.validate_normalized_payload(private)
    assert research_actions.canonical_action_digest(plain) != research_actions.canonical_action_digest(private)
    request = {"schema_version": research_actions.ACTION_PAYLOAD_SCHEMA, "action_slug": "pc-action",
               "report": private["report"], "private_context": PRIVATE,
               "documents": [{"extraction_json": json.dumps(_extraction()), "storage_permission": "repo_full",
                              "permission_basis": BASIS}]}
    assert research_actions.parse_action_request(json.dumps(request))["private_context"] == PRIVATE


@pytest.mark.parametrize("bad", [[], [{"source": SOURCE}], [{"source": " ", "text": SECRET}],
                                 [{"source": SOURCE, "text": SECRET, "url": "x"}], "text"])
def test_malformed_private_context_is_rejected(bad) -> None:
    with pytest.raises(ValueError, match="private_context"):
        research_actions.validate_normalized_payload(_payload(bad))


def test_the_decision_packet_shows_the_text_and_the_public_report_only_counts_it(tmp_path: Path) -> None:
    record = research_actions.create_action(_payload(PRIVATE), root=tmp_path)
    packet = research_actions.render_review_packet(record)
    assert SECRET in packet and SOURCE in packet
    public = research_actions._full_report(_applied(record))
    assert SECRET not in public and SOURCE not in public
    assert "有私有脈絡 1 段" in public
    assert research_actions.private_context_digest(PRIVATE) in public
    # 沒有私有脈絡的包：兩邊都不多一段（舊紀錄的 packet 逐字不變由 test_layer_enumerations 守著）
    plain = research_actions.create_action(_payload(None), root=tmp_path / "plain")
    assert "私有脈絡" not in research_actions.render_review_packet(plain)
    assert "私有脈絡" not in research_actions._full_report(_applied(plain))


def test_published_public_file_never_contains_the_private_text(tmp_path: Path) -> None:
    record = research_actions.create_action(_payload(PRIVATE), root=tmp_path)
    result = research_actions.publish_action_reports(_applied(record), root=tmp_path)
    assert result["public_path"] and result["public_path"].startswith("library/intake/")
    text = (tmp_path / result["public_path"]).read_text(encoding="utf-8")
    assert SECRET not in text and "有私有脈絡 1 段" in text
    stored = (tmp_path / "library" / "private" / "research_actions" / f"{record['action_id']}.json").read_text(
        encoding="utf-8")
    assert SECRET in stored                                   # 原文只住私有區


def test_private_context_survives_compaction_on_the_private_record(tmp_path: Path) -> None:
    record = research_actions.create_action(_payload(PRIVATE), root=tmp_path)
    applied = _applied(record)
    applied["state"] = "applied"
    applied["execution"]["report"] = {"status": "complete"}
    compacted = research_actions.compact_applied_payload(applied)
    assert compacted["payload"] is None and compacted["private_context"] == PRIVATE
    research_actions.save_action(compacted, root=tmp_path)
    reread = research_actions.read_action(record["action_id"], root=tmp_path)
    assert SECRET in research_actions.render_review_packet(reread)


def test_prepare_carries_private_context_into_the_frozen_action(tmp_path: Path, monkeypatch) -> None:
    """正式入口（`_prepare_research_action_impl`）把 draft 的 private_context 帶進凍結的 payload——漏帶就等於沒有這一欄。"""
    from intake import application

    def fake_prepare(extraction_json, storage_permission, permission_basis, **_):
        doc = json.loads(extraction_json)
        return {"status": "prepared", "doc_id": doc["source_doc"]["doc_id"], "document": doc,
                "raw_payload": {}, "warnings": []}

    monkeypatch.setattr(application, "_prepare_extraction_impl", fake_prepare)
    monkeypatch.setattr(application, "_merge_side_effect_receipt", lambda documents: None)
    request = {"schema_version": research_actions.ACTION_PAYLOAD_SCHEMA, "action_slug": "pc-action",
               "report": _payload(None)["report"], "focus_company_id": "co:axt", "private_context": PRIVATE,
               "documents": [{"extraction_json": json.dumps(_extraction()), "storage_permission": "repo_full",
                              "permission_basis": BASIS}]}
    result = application._prepare_research_action_impl(json.dumps(request), root=tmp_path)
    assert result["status"] == "ready", result
    assert SECRET in result["review_packet"]
    stored = research_actions.read_action(result["action_id"], root=tmp_path)
    assert stored["payload"]["private_context"] == PRIVATE
