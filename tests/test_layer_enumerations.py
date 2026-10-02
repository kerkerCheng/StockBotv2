"""RA request 頂層選填 `layer_enumerations[]` 與 prepare 當下的「在本包」核對（Phase 4 Step 4.2a）。

釘住：頂層選填、進 digest、封閉字彙、兩種失敗原因分開（名冊無名可比＝前置不拒收；引文真的沒具名＝拒收）、
origin_role 不符只警告、核對收據存在紀錄上且壓縮後留著、`_validate_record` 不依賴名冊、舊紀錄 packet 逐字不變。
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from intake import actions as research_actions
from intake import application

BASIS = "Official public filing retained for private research"


def _extraction(doc_id: str = "layer_doc", *, origin: str = "Global Semi Research",
                quotes: dict[str, str] | None = None, suppliers=("co:axt", "co:sumitomo_electric")) -> dict:
    quotes = quotes if quotes is not None else {
        "co:axt": "AXT holds about 36% of InP substrate supply.",
        "co:sumitomo_electric": "Sumitomo holds about 42%.",
    }
    nodes = [{"id": "mat:test_layer", "type": "Material", "name": "Test layer", "abstraction_level": "materials_substrate",
              "confidence": 0.9, "source_ids": [f"{doc_id}_s1"]}]
    edges, sources = [], []
    for index, supplier in enumerate(suppliers, start=1):
        sid = f"{doc_id}_s{index}"
        nodes.append({"id": supplier, "type": "Company", "name": supplier, "abstraction_level": "materials_substrate",
                      "confidence": 0.9, "source_ids": [sid]})
        edges.append({"id": f"e{index}", "src_id": supplier, "dst_id": "mat:test_layer", "relation": "supplies_to",
                      "confidence": 0.8, "source_ids": [sid]})
        sources.append({"id": sid, "locator": f"p{index}", "quote": quotes.get(supplier, "")})
    return {
        "schema_version": "0.1",
        "source_doc": {"doc_id": doc_id, "title": "Layer doc", "source_type": "industry_report", "evidence_tier": 3,
                       "origin_entity": origin, "storage_permission": "repo_full", "permission_basis": BASIS,
                       "url": "https://example.com/layer"},
        "sources": sources, "nodes": nodes, "edges": edges, "claims": [],
    }


def _payload(extraction: dict, enumerations: list[dict] | None) -> dict:
    payload = {
        "schema_version": research_actions.ACTION_PAYLOAD_SCHEMA,
        "action_slug": "layer-action",
        "report": {"title": "Layer title", "why_now": "w", "findings": "f", "search_summary": "s",
                   "l8_notes": "l8", "counterevidence_and_gaps": "c"},
        "documents": [{"doc_id": extraction["source_doc"]["doc_id"], "extraction": extraction, "raw_payload": {},
                       "storage_permission": "repo_full", "permission_basis": BASIS, "validation_warnings": []}],
    }
    if enumerations is not None:
        payload["layer_enumerations"] = enumerations
    return payload


def _enum(suppliers=("co:axt", "co:sumitomo_electric"), *, role: str = "industry_report",
          relation: str = "supplies_to") -> dict:
    return {"node": "mat:test_layer", "suppliers": list(suppliers), "relation": relation, "origin_role": role}


def test_layer_enumerations_are_top_level_optional_and_enter_the_digest() -> None:
    plain = _payload(_extraction(), None)
    with_enum = _payload(_extraction(), [_enum()])
    research_actions.validate_normalized_payload(plain)
    research_actions.validate_normalized_payload(with_enum)
    assert (research_actions.canonical_action_digest(plain)
            != research_actions.canonical_action_digest(with_enum))   # 核准邊界：宣告本身被 digest 凍結
    request = {"schema_version": research_actions.ACTION_PAYLOAD_SCHEMA, "action_slug": "layer-action",
               "report": with_enum["report"], "layer_enumerations": [_enum()],
               "documents": [{"extraction_json": json.dumps(_extraction()), "storage_permission": "repo_full",
                              "permission_basis": BASIS}]}
    assert research_actions.parse_action_request(json.dumps(request))["layer_enumerations"] == [_enum()]
    # 放進 report 仍是未知欄位（report 是 exact fields，舊紀錄靠它）
    request["report"] = dict(request["report"], layer_enumerations=[_enum()])
    with pytest.raises(ValueError, match="unknown"):
        research_actions.parse_action_request(json.dumps(request))


@pytest.mark.parametrize("field, value", [("relation", "competes_with"), ("origin_role", "blog")])
def test_unregistered_vocab_is_rejected(field: str, value: str) -> None:
    bad = dict(_enum(), **{field: value})
    with pytest.raises(ValueError, match="未登記"):
        research_actions.validate_normalized_payload(_payload(_extraction(), [bad]))


def test_supplier_not_in_package_is_rejected(tmp_path: Path) -> None:
    payload = _payload(_extraction(), [_enum(("co:axt", "co:lumentum"))])
    check = research_actions.check_layer_enumerations(payload)
    assert check["status"] == "rejected"
    assert any("co:lumentum 不在本包" in r for r in check["rejections"])
    with pytest.raises(ValueError, match="核對失敗"):
        research_actions.create_action(payload, root=tmp_path)


def test_quote_that_does_not_name_the_supplier_is_rejected_with_its_reason(tmp_path: Path) -> None:
    extraction = _extraction(quotes={"co:axt": "AXT ships substrates.", "co:sumitomo_electric": "we hold 42% share"})
    check = research_actions.check_layer_enumerations(_payload(extraction, [_enum()]))
    assert check["status"] == "rejected"
    assert any("co:sumitomo_electric 那條邊的引文沒有具名它" in r for r in check["rejections"])
    assert check["prerequisites"] == []


def test_registry_without_a_name_is_a_prerequisite_not_a_rejection(tmp_path: Path) -> None:
    """名冊無名可比（不在名冊、或在名冊但沒有任何名字）≠ 引文沒具名——前者先補名冊，不拒收（INV-3）。"""
    suppliers = ("co:axt", "co:nava_thailand", "co:brand_new_supplier")
    extraction = _extraction(suppliers=suppliers, quotes={"co:axt": "AXT ships.", "co:nava_thailand": "Nava ships.",
                                                          "co:brand_new_supplier": "NewCo ships."})
    payload = _payload(extraction, [_enum(suppliers)])
    record = research_actions.create_action(payload, root=tmp_path)
    check = record["layer_enumeration_check"]
    status = {row["company_id"]: row["status"] for row in check["results"][0]["suppliers"]}
    assert status == {"co:axt": "named", "co:nava_thailand": "registry_has_no_name",
                      "co:brand_new_supplier": "registry_has_no_name"}
    assert len(check["prerequisites"]) == 2 and check["rejections"] == []
    packet = research_actions.render_review_packet(record)
    assert "## 層列舉" in packet and "名冊無名可比" in packet and "引文具名 ✓" in packet
    assert "不授權入圖" in packet


def test_names_shared_with_another_company_are_a_prerequisite_not_a_rejection(tmp_path: Path) -> None:
    """R2-a N1：`co:openlight`／`co:openlight_photonics` 是同一家的兩個 id（plan §14 #11），名冊寫法全部共用——
    比對對兩家都不算。引文逐字寫「OpenLight」仍比不到，這是 identity 待決，不是「引文沒具名」（L12：不得壓成同一個失敗）。"""
    suppliers = ("co:axt", "co:openlight_photonics")
    extraction = _extraction(suppliers=suppliers, quotes={"co:axt": "AXT ships.",
                                                          "co:openlight_photonics": "OpenLight supplies the PIC."})
    record = research_actions.create_action(_payload(extraction, [_enum(suppliers)]), root=tmp_path)
    check = record["layer_enumeration_check"]
    status = {row["company_id"]: row["status"] for row in check["results"][0]["suppliers"]}
    assert status == {"co:axt": "named", "co:openlight_photonics": "registry_names_shared"}
    assert check["rejections"] == [] and any("共用" in p for p in check["prerequisites"])
    assert "identity 待決" in research_actions.render_review_packet(record)


def test_stored_records_stay_readable_after_the_vocab_changes(tmp_path: Path, monkeypatch) -> None:
    """R2-a N4：字彙檔日後改名或移除某個值，帶著它的舊紀錄照樣讀得出來（publish／status／complete-ra 都讀紀錄）；
    新的 request 仍照當下字彙核對。"""
    record = research_actions.create_action(_payload(_extraction(), [_enum()]), root=tmp_path)
    applied = copy.deepcopy(record)
    applied["state"] = "applied"
    applied["execution"]["report"] = {"status": "complete"}
    for item in applied["execution"]["documents"]:
        item["status"] = "complete"
    compacted = research_actions.compact_applied_payload(applied)
    compacted["action_id"] = "ra_" + "1" * 32                     # 另存一筆壓縮後的（層列舉住在紀錄頂層）
    research_actions.save_action(compacted, root=tmp_path)
    original = research_actions._vocab_values

    def renamed(key: str):
        values = original(key)
        return tuple(v for v in values if v != "supplies_to") + (("ships_to",) if key == "layer_enumeration_relations" else ())

    monkeypatch.setattr(research_actions, "_vocab_values", renamed)
    fresh = research_actions.read_action(record["action_id"], root=tmp_path)             # 層列舉在 payload 裡
    assert fresh["payload"]["layer_enumerations"] == [_enum()]
    assert research_actions.read_action(compacted["action_id"], root=tmp_path)["layer_enumerations"] == [_enum()]
    with pytest.raises(ValueError, match="未登記"):
        research_actions.validate_normalized_payload(_payload(_extraction(doc_id="layer_doc_new"), [_enum()]))


def test_apply_report_prints_the_same_publisher_line_as_the_packet(tmp_path: Path) -> None:
    """R2-a N8：packet 與 apply 寫出的報告共用同一個「發文者」行（兩處各寫一份就會不一致）。"""
    record = research_actions.create_action(_payload(_extraction(), None), root=tmp_path)
    line = "發文者：origin=Global Semi Research ｜ source_type=industry_report ｜ tier=3"
    assert line in research_actions.render_review_packet(record)
    assert line in research_actions._full_report(record)


def test_origin_role_mismatch_only_warns(tmp_path: Path) -> None:
    # 宣告 industry_report，但發文者其實是列舉的供應商之一（AXT 自家文件）→ 只警告
    payload = _payload(_extraction(origin="AXT, Inc."), [_enum()])
    record = research_actions.create_action(payload, root=tmp_path)
    warnings = record["layer_enumeration_check"]["warnings"]
    assert any("就是列舉的供應商 co:axt" in w for w in warnings)
    # 宣告 supplier_self，但發文者解析不到任一家 → 只警告
    record = research_actions.create_action(_payload(_extraction(doc_id="layer_doc_2"), [_enum(role="supplier_self")]),
                                            root=tmp_path)
    assert any("supplier_self" in w for w in record["layer_enumeration_check"]["warnings"])


def test_check_receipt_survives_compaction_and_record_validation_ignores_the_registry(tmp_path: Path,
                                                                                    monkeypatch) -> None:
    record = research_actions.create_action(_payload(_extraction(), [_enum()]), root=tmp_path)
    applied = copy.deepcopy(record)
    applied["state"] = "applied"
    applied["execution"]["report"] = {"status": "complete"}
    for item in applied["execution"]["documents"]:
        item["status"] = "complete"
    compacted = research_actions.compact_applied_payload(applied)
    assert compacted["payload"] is None and compacted["layer_enumerations"] == [_enum()]
    assert "## 層列舉" in research_actions.render_review_packet(compacted)

    # 名冊之後改了（這裡用「比對函式壞掉」模擬）：紀錄照樣讀得出來——核對只在 prepare 跑一次
    import query.bottleneck as bottleneck

    def boom(*_a, **_k):
        raise AssertionError("record validation must not consult the registry")

    monkeypatch.setattr(bottleneck, "quote_names_company", boom)
    research_actions.save_action(compacted, root=tmp_path)
    assert research_actions.read_action(record["action_id"], root=tmp_path)["layer_enumerations"] == [_enum()]


def test_new_manifest_carries_publisher_fields_and_packet_prints_them(tmp_path: Path) -> None:
    record = research_actions.create_action(_payload(_extraction(), None), root=tmp_path)
    item = record["document_manifest"][0]
    assert (item["origin_entity"], item["source_type"], item["evidence_tier"]) == (
        "Global Semi Research", "industry_report", 3)
    packet = research_actions.render_review_packet(record)
    assert "發文者：origin=Global Semi Research ｜ source_type=industry_report ｜ tier=3" in packet
    assert "## 層列舉" not in packet                                         # 沒宣告就整節不印


def test_packet_resolves_the_origin_with_the_single_owner_so_a_registered_publisher_is_not_unresolved(
        tmp_path: Path) -> None:
    """2026-10-01 Step 4.8 實跑撞到：層列舉的 origin 原本只認名冊公司，登記的產業研究（Global Semi Research）在 packet 上
    印成「解析不到」——審包的人會以為它不算印證。改走 `query.origin_resolution.resolve_origin`（4.3 的唯一 owner，L16）。"""
    payload = _payload(_extraction(), [_enum()])
    check = research_actions.check_layer_enumerations(payload)
    origin = check["results"][0]["origins"][0]
    # GSR 2026-10-03 起登記為 media（Phase 6 Step 6.3b）——本測試守的是「登記的發布者不得印成解析不到」，類別照實印
    assert (origin["origin_kind"], origin["publisher_kind"], origin["resolved"]) == ("publisher", "media", None)
    record = research_actions.create_action(payload, root=tmp_path)
    packet = research_actions.render_review_packet(record)
    assert "origin「Global Semi Research」→ 登記的發布者（media）" in packet
    assert "origin「Global Semi Research」→ 解析不到" not in packet


OLD_RECORD = {
    "action_id": "ra_" + "0" * 32,
    "action_digest": "a" * 64,
    "created_at": "2026-09-01T00:00:00+00:00",
    "expires_at": "2026-10-01T00:00:00+00:00",
    "payload": {"report": {
        "title": "Old title", "why_now": "Old why", "findings": "Old findings",
        "search_summary": "Old search", "l8_notes": "Old L8", "counterevidence_and_gaps": "Old gaps"}},
    "document_manifest": [{
        "doc_id": "old_doc", "title": "Old doc", "url": "https://example.com/old",
        "storage_permission": "repo_full", "permission_basis": "basis",
        "node_count": 1, "edge_count": 2, "claim_count": 0, "validation_warnings": ["w1"]}],
}
#: 2026-10-01 以改動前的 `render_review_packet` 對 OLD_RECORD 渲染的逐字結果（scratchpad p4_golden_packet.py）。
OLD_PACKET = (
    "# Old title\n\n- Research Action: `ra_00000000000000000000000000000000`\n- Digest: "
    "`aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`\n- Prepared (UTC): "
    "`2026-09-01T00:00:00+00:00`\n- Approval expires (UTC): `2026-10-01T00:00:00+00:00`\n\n## 為何此時入圖\n\nOld why"
    "\n\n## 研究發現\n\nOld findings\n\n## 文件清單\n\n- `old_doc` — Old doc; storage=`repo_full`; nodes=1, edges=2, "
    "claims=0\n  - URL: https://example.com/old\n  - Validation warning: w1\n\n## 搜尋過程摘要\n\nOld search\n\n"
    "## L8 確認備註\n\nOld L8\n\n## 反向證據與缺口\n\nOld gaps\n\n## 核准指示\n\n若核准，請明確回覆同意套用 "
    "`ra_00000000000000000000000000000000`；session 必須使用上方完整 digest 呼叫 apply。\n"
)


def test_old_record_packet_renders_byte_for_byte_unchanged() -> None:
    assert research_actions.render_review_packet(OLD_RECORD) == OLD_PACKET


def test_prepare_returns_each_rejection_reason(tmp_path: Path) -> None:
    extraction = _extraction(quotes={"co:axt": "AXT ships.", "co:sumitomo_electric": "we lead"})
    request = {"schema_version": research_actions.ACTION_PAYLOAD_SCHEMA, "action_slug": "layer-action",
               "report": _payload(extraction, None)["report"], "layer_enumerations": [_enum()],
               "documents": [{"extraction_json": json.dumps(extraction), "storage_permission": "repo_full",
                              "permission_basis": BASIS}]}
    original = application._prepare_extraction_impl

    def fake_prepare(extraction_json, storage_permission, permission_basis, **_):
        doc = json.loads(extraction_json)
        return {"status": "prepared", "doc_id": doc["source_doc"]["doc_id"], "document": doc,
                "raw_payload": {}, "warnings": []}

    application._prepare_extraction_impl = fake_prepare
    try:
        result = application._prepare_research_action_impl(json.dumps(request), root=tmp_path)
    finally:
        application._prepare_extraction_impl = original
    assert result["status"] == "rejected"
    assert any("co:sumitomo_electric 那條邊的引文沒有具名它" in p for p in result["problems"])
