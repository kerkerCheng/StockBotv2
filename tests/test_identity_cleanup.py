"""身分清理遷移（`loader/migrate_identity_cleanup.py`；Phase 6 Step 6.2）——夾具，不碰真的抽取檔、名冊或圖。

守五件事：
1. 抽取檔改動：node／edge 端點／claim subject 一起改名；併邊只併 source_ids、被丟的屬性列出來；刪節點時還有邊指著它就拒收。
2. **節點宣告照抄圖上現值**之後，重載的入圖副作用＝0（Phase 4 #32；變異：不照抄 role → 副作用不為 0 → 紅）。
3. 名冊：刪掉被併的 id 之後，origin「OpenLight」經名字比對解析到 canonical（slug `co:openlight` 不再存在）。
4. 證據等級的改後模擬：只換掉被改的那個抽取檔的 assertion（同 doc_id 的 addendum 留著）、端點換成 canonical id。
5. apply 的前置：pq2 編號核對、備份核對，都在任何寫入之前 fail closed。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from loader import migrate_identity_cleanup as mic
from loader.merge_side_effects import as_loaded, compute_side_effects


def _semitoday() -> dict:
    return {
        "source_doc": {"doc_id": "news_doc", "title": "News", "source_type": "news", "evidence_tier": 3,
                       "origin_entity": "Semiconductor Today", "url": "https://example.com/n"},
        "sources": [{"id": "news_doc_s1", "quote": "OpenLight ships to NewPhotonics"}],
        "nodes": [
            {"id": "co:openlight", "type": "Company", "name": "OpenLight Photonics", "abstraction_level": "device_chip",
             "role": None, "aliases": ["OpenLight"], "attributes": {}, "confidence": 0.85, "source_ids": ["news_doc_s1"]},
            {"id": "co:newphotonics", "type": "Company", "name": "NewPhotonics", "abstraction_level": "device_chip",
             "role": None, "aliases": [], "attributes": {}, "confidence": 0.8, "source_ids": ["news_doc_s1"]},
        ],
        "edges": [{"id": "ph3", "src_id": "co:openlight", "relation": "supplies_to", "dst_id": "co:newphotonics",
                   "attributes": {}, "confidence": 0.8, "source_ids": ["news_doc_s1"]}],
        "claims": [{"id": "news_doc_cl1", "subject_id": "co:openlight", "statement": "x"}],
    }


GRAPH_NODES = {
    "co:openlight_photonics": {"type": "Company", "name": "OpenLight", "abstraction_level": "device_chip",
                               "role": "disruptor", "aliases": ["OpenLight Photonics"], "attrs": '{"ticker": null}',
                               "confidence": 0.9},
    "co:newphotonics": {"type": "Company", "name": "NewPhotonics", "abstraction_level": "module_subsystem",
                        "role": "disruptor", "aliases": [], "attrs": '{"ticker": null}', "confidence": 0.9},
}


def test_rename_touches_nodes_edge_ends_and_claim_subjects() -> None:
    new, changes = mic.plan_extraction_edit(_semitoday(), {"rename_ids": {"co:openlight": "co:openlight_photonics"}}, {})
    assert mic.references(new, ["co:openlight"]) == [], "改名漏掉任何一處，節點合併了邊還指著舊 id"
    assert new["edges"][0]["src_id"] == "co:openlight_photonics"
    assert new["claims"][0]["subject_id"] == "co:openlight_photonics"
    assert {c["op"] for c in changes} == {"rename_node", "rename_edge_end", "rename_claim_subject"}


def test_aligned_declarations_reload_without_side_effects() -> None:
    """節點宣告照抄圖上現值 → 重載不會覆寫任何既有值（`co:newphotonics` 的 abstraction_level／role 就是 2026-10-03 dry-run 撞到的）。

    變異：把 `_ALIGN_FIELDS` 拿掉 `role` → 這條紅。"""
    ops = {"rename_ids": {"co:openlight": "co:openlight_photonics"}, "align_nodes_to_graph": True}
    new, changes = mic.plan_extraction_edit(_semitoday(), ops, GRAPH_NODES)
    graph_state = {"nodes": {k: dict(v, id=k) for k, v in GRAPH_NODES.items()}, "source_doc": None}
    result = compute_side_effects(as_loaded(new), graph_state)
    assert result["node_overwrites"] == [], result["node_overwrites"]
    canonical = next(n for n in new["nodes"] if n["id"] == "co:openlight_photonics")
    assert canonical["role"] == "disruptor" and canonical["name"] == "OpenLight"
    assert canonical["aliases"] == ["OpenLight Photonics", "OpenLight"], "別名：圖上在前、聯集進舊 id 的"
    assert any(c["op"] == "align_node_to_graph" and c["node"] == "co:newphotonics" for c in changes)


def test_without_alignment_the_reload_would_overwrite() -> None:
    """對照：不照抄就有副作用——上一條測試量到的 0 不是恆真。"""
    new, _ = mic.plan_extraction_edit(_semitoday(), {"rename_ids": {"co:openlight": "co:openlight_photonics"}}, {})
    graph_state = {"nodes": {k: dict(v, id=k) for k, v in GRAPH_NODES.items()}, "source_doc": None}
    assert compute_side_effects(as_loaded(new), graph_state)["node_overwrites"]


def _lumentum() -> dict:
    return {
        "source_doc": {"doc_id": "lite_doc", "title": "Call", "source_type": "transcript", "evidence_tier": 1,
                       "origin_entity": "Lumentum"},
        "sources": [{"id": "lite_doc_s8", "quote": "capacity in Thailand (Nava)"},
                    {"id": "lite_doc_s9", "quote": "EML pull"}],
        "nodes": [{"id": "co:nava_thailand", "type": "Company", "name": "Nava", "abstraction_level": "foundry_packaging",
                   "role": "foundry", "aliases": [], "attributes": {}, "confidence": 0.9, "source_ids": ["lite_doc_s8"]}],
        "edges": [
            {"id": "e7", "src_id": "co:lumentum", "relation": "supplies_to", "dst_id": "tech:cloud_transceiver_1_6t",
             "attributes": {"qualification_status": "designed_in"}, "confidence": 0.9,
             "source_ids": ["lite_doc_s8", "lite_doc_s9"]},
            {"id": "e27", "src_id": "co:lumentum", "relation": "supplies_to", "dst_id": "co:nava_thailand",
             "attributes": {"qualification_status": "qualified"}, "confidence": 0.9, "source_ids": ["lite_doc_s8"]},
            {"id": "e28", "src_id": "co:nava_thailand", "relation": "supplies_to", "dst_id": "tech:cloud_transceiver_1_6t",
             "attributes": {"qualification_status": "qualified"}, "confidence": 0.9, "source_ids": ["lite_doc_s8"]},
        ],
        "claims": [],
    }


def test_retiring_a_company_merges_its_edge_into_the_owner_and_lists_dropped_attributes() -> None:
    ops = {"delete_edges": ["e27"], "merge_edges": [{"id": "e28", "into": "e7"}], "delete_nodes": ["co:nava_thailand"]}
    new, changes = mic.plan_extraction_edit(_lumentum(), ops, {})
    assert [e["id"] for e in new["edges"]] == ["e7"] and new["nodes"] == []
    merge = next(c for c in changes if c["op"] == "merge_edge")
    assert merge["source_ids_added"] == [] and merge["attributes_dropped"] == {"qualification_status": "qualified"}
    assert mic.references(new, ["co:nava_thailand"]) == []


def test_deleting_a_node_that_an_edge_still_points_at_is_refused() -> None:
    with pytest.raises(mic.IdentityCleanupError, match="還有邊"):
        mic.plan_extraction_edit(_lumentum(), {"delete_nodes": ["co:nava_thailand"]}, {})


def _registry() -> dict:
    return {"version": 1, "companies": [
        {"company_id": "co:lumentum", "research_ticker": "LITE", "display_name": "Lumentum Holdings Inc.",
         "name_aliases": ["Lumentum"]},
        {"company_id": "co:openlight", "research_ticker": None, "display_name": "OpenLight Photonics Inc.",
         "name_aliases": ["OpenLight"]},
        {"company_id": "co:openlight_photonics", "research_ticker": None, "display_name": "OpenLight Photonics Inc.",
         "name_aliases": ["OpenLight"]},
        {"company_id": "co:nava_thailand", "research_ticker": None},
    ]}


def test_after_the_merge_the_openlight_origin_resolves_to_the_canonical_id() -> None:
    """合併前「OpenLight」靠 slug 解析到 co:openlight；名冊刪掉它之後靠 name_aliases 的整串比對解析到 canonical。"""
    from query.bottleneck import company_id_for_origin

    spec = {"remove": ["co:openlight", "co:nava_thailand"],
            "set": {"co:openlight_photonics": {"_note": "合併（pq2 [{pq2}]）"}}}
    before = mic.registry_from_json(_registry())
    assert company_id_for_origin("OpenLight", before) == "co:openlight"
    new, changes = mic.plan_registry_edit(_registry(), spec, pq2=777)
    after = mic.registry_from_json(new)
    assert company_id_for_origin("OpenLight", after) == "co:openlight_photonics"
    assert not after.has_company("co:openlight") and not after.has_company("co:nava_thailand")
    note = next(c for c in new["companies"] if c["company_id"] == "co:openlight_photonics")["_note"]
    assert "[777]" in note and "{pq2}" not in note
    assert {c["op"] for c in changes} == {"remove", "set"}


def test_registry_edit_refuses_an_id_that_is_already_gone() -> None:
    with pytest.raises(mic.IdentityCleanupError, match="已經遷移過"):
        mic.plan_registry_edit({"version": 1, "companies": []}, {"remove": ["co:openlight"]})


def test_rows_after_edit_keeps_the_addendum_and_uses_canonical_ids() -> None:
    """只換掉被改的那個抽取檔的 assertion；同 doc_id 的 addendum 不重載、它的列留著（2026-10-03 dry-run 撞到）。"""
    before = _lumentum()
    after, _ = mic.plan_extraction_edit(
        before, {"delete_edges": ["e27"], "merge_edges": [{"id": "e28", "into": "e7"}],
                 "delete_nodes": ["co:nava_thailand"]}, {})
    rows = [{"assertion_id": f"lite_doc_{e['id']}", "src": e["src_id"], "relation": e["relation"], "dst": e["dst_id"],
             "attributes": "{}", "confidence": 0.9, "origin": "Lumentum", "source_type": "transcript",
             "origin_linkage": None, "source_doc_id": "lite_doc", "published_at": "2026-02-03"} for e in before["edges"]]
    rows.append({"assertion_id": "lite_doc_cov5_1", "src": "co:lumentum", "relation": "supplies_to",
                 "dst": "tech:optical_scale_up", "attributes": "{}", "confidence": 0.9, "origin": "Lumentum",
                 "source_type": "transcript", "origin_linkage": None, "source_doc_id": "lite_doc",
                 "published_at": "2026-02-03"})
    new_rows, _quotes = mic.rows_after_edit(rows, {}, {"lite_doc": (before, after)}, ["co:nava_thailand"])
    ids = sorted(r["assertion_id"] for r in new_rows)
    assert ids == ["lite_doc_cov5_1", "lite_doc_e7"], ids
    assert all(r["src"] != "co:nava_thailand" and r["dst"] != "co:nava_thailand" for r in new_rows)


def test_evidence_changes_list_appearing_and_vanishing_edges() -> None:
    before = {("a", "r", "b"): "externally_corroborated", ("x", "r", "y"): "self_reported"}
    after = {("a", "r", "b"): "counterparty_joint"}
    assert mic.evidence_changes(before, after) == [
        {"edge": ["a", "r", "b"], "before": "externally_corroborated", "after": "counterparty_joint"},
        {"edge": ["x", "r", "y"], "before": "self_reported", "after": None}]


def test_apply_checks_the_pq2_number_before_any_write(tmp_path: Path) -> None:
    pool = tmp_path / "todo_pool.json"
    manifest = {"pq2_ref": "identity-cleanup:2026-10-03"}
    pool.write_text(json.dumps({"schema_version": 2, "next_n": 3, "log": [], "items": [
        {"n": 1, "type": "manual", "ref_id": "identity-cleanup:2026-10-03", "title": "t", "resolution": None},
        {"n": 2, "type": "ra_admission", "ref_id": "identity-cleanup:2026-10-03", "title": "t", "resolution": None},
    ]}), encoding="utf-8")
    assert mic.check_approval(1, manifest, pool_path=pool)["n"] == 1
    with pytest.raises(mic.IdentityCleanupError, match="不是本 manifest"):
        mic.check_approval(2, manifest, pool_path=pool)
    with pytest.raises(mic.IdentityCleanupError, match="不存在或已結案"):
        mic.check_approval(9, manifest, pool_path=pool)


def test_apply_needs_a_non_empty_graph_export(tmp_path: Path) -> None:
    with pytest.raises(mic.IdentityCleanupError, match="找不到 Neo4j 匯出或為空"):
        mic.check_backup(tmp_path)
    (tmp_path / "neo4j_export.json").write_text("", encoding="utf-8")
    with pytest.raises(mic.IdentityCleanupError, match="找不到 Neo4j 匯出或為空"):
        mic.check_backup(tmp_path)


def test_apply_without_pq2_or_backup_is_a_usage_error() -> None:
    with pytest.raises(SystemExit):
        mic.main(["--apply"])


def test_the_committed_manifest_is_well_formed() -> None:
    """repo 裡那份 manifest：決定與名冊刪除一致、每個決定有理由、nava 的處置附一手原文。"""
    manifest = mic.load_manifest(mic.DEFAULT_MANIFEST)
    assert mic.old_ids(manifest) == ["co:nava_thailand", "co:openlight"]
    nava = manifest["decisions"]["co:nava_thailand"]
    assert nava["into"] == "co:lumentum" and any("Navanakorn" in e["quote"] for e in nava["evidence"])
