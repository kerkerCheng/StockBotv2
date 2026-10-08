"""供貨邊的主詞要在引文裡（2026-10-08，Phase 7 failure log #14；plan 2026-10-08-001 D4）。

事發兩次：MP 的磁材供貨邊掛了 Noveon、USA Rare Earth **自己的**新聞稿（引文沒有 MP），把 MP 的 substitutability 由 4 下修到 3；
Harmonic Drive 的諧波減速機供貨邊掛了一段講綠的諧波的引文。「有競爭者在量產」被做成被評公司的供貨 assertion（L6 被繞過、L12）。
新包在 prepare 擋；圖上存量由層計數器「供貨主詞不在引文」現形（2026-10-08 真圖 27 條）。
"""
from __future__ import annotations

import json
from pathlib import Path

from identity.registry import CompanyIdentity, IdentityRegistry
from intake import actions as research_actions
from intake import application

BASIS = "Official public filing retained for private research"
REGISTRY = IdentityRegistry(version=1, companies=(
    CompanyIdentity("co:mp_materials", "MP", display_name="MP Materials Corp.", name_aliases=("MP Materials",)),
    CompanyIdentity("co:noveon", None, display_name="Noveon Magnetics Inc.", name_aliases=("Noveon",)),
    CompanyIdentity("co:nameless", None),
))


def _payload(*, origin: str, src: str, quote: str, relation: str = "supplies_to") -> dict:
    extraction = {
        "schema_version": "0.1",
        "source_doc": {"doc_id": "doc1", "title": "T", "source_type": "press_release", "evidence_tier": 2,
                       "origin_entity": origin, "storage_permission": "repo_full", "permission_basis": BASIS,
                       "url": "https://example.com/doc1"},
        "sources": [{"id": "doc1_s1", "quote": quote}],
        "nodes": [],
        "edges": [{"id": "e1", "src_id": src, "relation": relation, "dst_id": "mat:rare_earth_magnets",
                   "confidence": 0.8, "attributes": {"substitutability": 3}, "source_ids": ["doc1_s1"]}],
        "claims": [],
    }
    return {"documents": [{"doc_id": "doc1", "extraction": extraction}]}


def test_a_competitor_press_release_cannot_carry_the_subjects_supply_edge() -> None:
    """Noveon 的新聞稿、引文沒有 MP → 拒收，並指路寫成競爭者自己的供貨邊。"""
    check = research_actions.check_supply_subjects(
        _payload(origin="Noveon Magnetics", src="co:mp_materials",
                 quote="Noveon was the first company to reshore full-scale production of sintered rare earth magnets"),
        registry=REGISTRY)
    assert check["status"] == "rejected" and "競爭者自己的供貨邊" in check["rejections"][0]


def test_named_quotes_self_reports_and_other_relations_pass() -> None:
    named = _payload(origin="Federation of American Scientists", src="co:mp_materials",
                     quote="MP Materials will expand magnet manufacturing to 10,000 tons")
    self_report = _payload(origin="Noveon Magnetics", src="co:noveon",
                           quote="We were the first company to reshore sintered magnet production")
    other = _payload(origin="Noveon Magnetics", src="co:mp_materials", quote="no names here", relation="competes_with")
    for payload in (named, self_report, other):
        assert research_actions.check_supply_subjects(payload, registry=REGISTRY)["status"] == "ok"


def test_a_subject_without_name_forms_is_a_prerequisite_not_a_rejection() -> None:
    check = research_actions.check_supply_subjects(
        _payload(origin="Noveon Magnetics", src="co:nameless", quote="someone supplies magnets"), registry=REGISTRY)
    assert check["status"] == "ok" and "先補名冊" in check["prerequisites"][0]


def test_prepare_returns_the_rejection_before_any_record_exists(tmp_path: Path, monkeypatch) -> None:
    payload = _payload(origin="Noveon Magnetics", src="co:mp_materials", quote="Noveon reshored magnet production")
    request = {"schema_version": research_actions.ACTION_PAYLOAD_SCHEMA, "action_slug": "mp-action",
               "report": {"title": "t", "why_now": "w", "findings": "f", "search_summary": "s", "l8_notes": "l",
                          "counterevidence_and_gaps": "c"},
               "focus_company_id": "co:mp_materials",
               "documents": [{"extraction_json": json.dumps(payload["documents"][0]["extraction"]),
                              "storage_permission": "repo_full", "permission_basis": BASIS}]}

    def fake_prepare(extraction_json, storage_permission, permission_basis, **_):
        doc = json.loads(extraction_json)
        return {"status": "prepared", "doc_id": doc["source_doc"]["doc_id"], "document": doc,
                "raw_payload": {}, "warnings": []}

    monkeypatch.setattr(application, "_prepare_extraction_impl", fake_prepare)
    result = application._prepare_research_action_impl(json.dumps(request), root=tmp_path)
    assert result["status"] == "rejected" and "沒具名主詞" in result["error"]
    assert any("co:mp_materials" in p for p in result["problems"])
    assert list(research_actions.iter_actions(root=tmp_path)) == []


def test_the_layer_counter_counts_the_existing_ones_and_says_unmeasured_for_old_artifacts() -> None:
    from query.layer_stats import _count

    assert _count(None) == "未量" and _count([]) == "0" and _count(["a", "b"]) == "2"
