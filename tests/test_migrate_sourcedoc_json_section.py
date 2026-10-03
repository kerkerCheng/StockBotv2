"""SourceDoc section／title 寫回抽取 JSON 的一次性工具（Phase 4 Step 4.2e）。

釘住：只動兩欄而且文字層級只換那一個值（各檔排版不同）、section 以圖為準、title 以母文件為準、判不出就跳過、
收據綁定的舊版先歸檔（更正走廊的規矩）、回填後重載 addendum 檔 section 仍在且 title 是母文件、寫圖只動「圖落後」那幾筆。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from loader import migrate_sourcedoc_json_section as mig
from loader.load_to_neo4j import load
from loader.sourcedoc_sync import drift, json_source_docs


class _Session:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def run(self, query: str, **params):
        self.calls.append((query, params))
        return [{"value": params.get("value")}] if "SET sd." in query else []


def _doc(doc_id: str, *, title: str, section=None, sort_keys=False, indent=2, ascii_only=False) -> str:
    source_doc = {"doc_id": doc_id, "title": title, "source_type": "filing", "evidence_tier": 1,
                  "origin_entity": "Issuer", "url": "https://example.com/doc", "storage_permission": "repo_full",
                  "permission_basis": "Public filing retained for research"}
    if section is not None:
        source_doc["section"] = section
    payload = {"schema_version": "0.1", "source_doc": source_doc, "sources": [], "nodes": [], "edges": [], "claims": []}
    return json.dumps(payload, ensure_ascii=ascii_only, indent=indent, sort_keys=sort_keys) + "\n"


@pytest.mark.parametrize("sort_keys, indent, ascii_only", [(False, 2, False), (True, 2, False), (False, 1, False),
                                                           (True, 1, True)])
def test_text_edit_changes_only_the_two_fields_and_keeps_the_layout(sort_keys, indent, ascii_only) -> None:
    raw = _doc("d", title="母文件——addendum", sort_keys=sort_keys, indent=indent, ascii_only=ascii_only)
    new = mig.edit_source_doc_text(raw, {"title": "母文件", "section": "photonics"})
    after = json.loads(new)
    expected = json.loads(raw)
    expected["source_doc"].update({"title": "母文件", "section": "photonics"})
    assert after == expected
    # 其他行一個位元組都沒動：只多一行 section、title 那一行換值
    old_lines, new_lines = raw.splitlines(), new.splitlines()
    assert len(new_lines) == len(old_lines) + 1
    assert sum(1 for line in new_lines if line not in old_lines) == 2
    if sort_keys:   # 鍵排序的檔照排序位置插
        keys = list(after["source_doc"])
        assert keys == sorted(keys)


def test_plan_takes_section_from_the_graph_and_title_from_the_parent_file() -> None:
    json_docs = {
        "split": [{"file": "split.json", "section": None, "title": "Parent"},
                  {"file": "split_coverage_addendum_x.json", "section": None, "title": "Parent——coverage-gap addendum"}],
        "pair": [{"file": "pair_a.json", "section": None, "title": "A——addendum（第 1 輪）"},
                 {"file": "pair_b.json", "section": None, "title": "B——addendum（第 2 輪）"}],
        "graph_only": [{"file": "graph_only.json", "section": None, "title": "G"}],
    }
    rows = [{"id": "split", "section": "asic", "title": "Parent——coverage-gap addendum"},
            {"id": "pair", "section": None, "title": "A"},
            {"id": "graph_only", "section": "photonics", "title": "G"}]
    plan = mig.plan_json_edits(rows, json_docs)
    edits = {(e["file"], e["field"]): e["after"] for e in plan["edits"]}
    assert edits == {("split.json", "section"): "asic", ("split_coverage_addendum_x.json", "section"): "asic",
                     ("split_coverage_addendum_x.json", "title"): "Parent",
                     ("graph_only.json", "section"): "photonics"}
    assert any("pair" in line and "判不出" in line for line in plan["skipped"])   # 兩個都像 addendum：不猜


def test_apply_json_archives_receipt_bound_versions_and_reload_keeps_section_and_parent_title(tmp_path: Path) -> None:
    ext = tmp_path / "extractions"
    ext.mkdir()
    (ext / "split.json").write_text(_doc("split", title="Parent"), encoding="utf-8")
    (ext / "split_coverage_addendum_x.json").write_text(_doc("split", title="Parent——coverage-gap addendum"),
                                                        encoding="utf-8")
    receipts = tmp_path / "library" / "private" / "intake_state"
    receipts.mkdir(parents=True)
    (receipts / "split.json").write_text("{}", encoding="utf-8")
    # 圖那一列也帶 origin_entity（Phase 6 Step 6.3d 起它是同步欄位；與 JSON 同值＝這一欄沒有落差）
    rows = [{"id": "split", "section": "asic", "title": "Parent——coverage-gap addendum", "origin_entity": "Issuer"}]
    plan = mig.plan_json_edits(rows, json_source_docs(ext))
    result = mig.apply_json(plan, root=tmp_path, receipts_dir=receipts)

    assert result["files"] == 2 and len(result["archived"]) == 1                    # 只有綁收據的 split.json 歸檔
    archived = tmp_path / result["archived"][0]
    assert json.loads(archived.read_text(encoding="utf-8"))["source_doc"].get("section") is None   # 歸檔的是改動前
    manifest = json.loads((tmp_path / result["manifest"]).read_text(encoding="utf-8"))
    assert {f["file"] for f in manifest["files"]} == {"extractions/split.json",
                                                       "extractions/split_coverage_addendum_x.json"}
    assert mig.plan_json_edits(rows, json_source_docs(ext))["edits"] == []        # 冪等

    # 重載 addendum 檔：section 仍在、title 是母文件（loader 契約不動，是輸入對齊了）
    session = _Session()
    load(json.loads((ext / "split_coverage_addendum_x.json").read_text(encoding="utf-8")), session)
    _, params = next((q, p) for q, p in session.calls if "MERGE (sd:SourceDoc" in q)
    assert params["section"] == "asic" and params["title"] == "Parent"
    # 回填之後：重建會遺失的 0；圖仍掛 addendum 標題＝圖落後 JSON（等核准改圖）
    state = drift(rows, json_source_docs(ext))
    assert state["danger"] == [] and [(d["doc_id"], d["field"]) for d in state["stale"]] == [("split", "title")]


def test_apply_graph_only_touches_stale_fields_and_checks_the_current_value(tmp_path: Path) -> None:
    stale = [{"doc_id": "split", "field": "title", "kind": "graph_behind_json",
              "graph": "Parent——addendum", "json": "Parent"}]
    session = _Session()
    result = mig.apply_graph(stale, session=session, pq2=777, root=tmp_path)
    query, params = session.calls[0]
    assert "SET sd.title = $value" in query and "coalesce(sd.title, '') = coalesce($expected_before, '')" in query
    assert params == {"doc_id": "split", "expected_before": "Parent——addendum", "value": "Parent"}
    manifest = json.loads((tmp_path / result["manifest"]).read_text(encoding="utf-8"))
    assert manifest["pq2"] == 777 and manifest["writes"][0]["written"] is True
    # 只准動 sourcedoc_sync.FIELDS（section／title／origin_entity——後者 Phase 6 Step 6.3d 起）；清單外的一律拒絕
    with pytest.raises(ValueError, match="只准動"):
        mig.apply_graph([{**stale[0], "field": "url"}], session=_Session(), pq2=777, root=tmp_path)
    session = _Session()
    mig.apply_graph([{**stale[0], "field": "origin_entity", "graph": "Old", "json": "New"}], session=session, pq2=777,
                    root=tmp_path, manifest_name="origin.json")
    assert "SET sd.origin_entity = $value" in session.calls[0][0]


def test_origin_entity_disagreeing_across_files_aligns_to_the_graph_value() -> None:
    """同一個 doc_id 的兩份抽取檔 origin 互異（重建時載入順序決定結果）：對齊圖上現值；圖上的值不是其中之一就不猜。"""
    json_docs = {"iqe": [{"file": "iqe.json", "section": None, "title": "T", "origin_entity": "A and B (long note)"},
                         {"file": "iqe_addendum.json", "section": None, "title": "T", "origin_entity": "A / B (joint)"}],
                 "odd": [{"file": "odd.json", "section": None, "title": "T", "origin_entity": "X"},
                         {"file": "odd_addendum.json", "section": None, "title": "T", "origin_entity": "Y"}]}
    rows = [{"id": "iqe", "section": None, "title": "T", "origin_entity": "A / B (joint)"},
            {"id": "odd", "section": None, "title": "T", "origin_entity": "Z"}]
    plan = mig.plan_json_edits(rows, json_docs)
    assert [(e["file"], e["field"], e["after"]) for e in plan["edits"]] == [("iqe.json", "origin_entity", "A / B (joint)")]
    assert any("odd" in line and "不猜" in line for line in plan["skipped"])


def test_drift_counts_origin_entity_and_the_graph_query_follows_fields(tmp_path: Path) -> None:
    from loader.sourcedoc_sync import FIELDS, GRAPH_CYPHER, summary_line

    assert "origin_entity" in FIELDS and all(f"sd.{f} AS {f}" in GRAPH_CYPHER for f in FIELDS)
    for name, origin in (("a.json", "One"), ("a_addendum.json", "Two")):
        (tmp_path / name).write_text(json.dumps({"source_doc": {"doc_id": "a", "title": "T", "origin_entity": origin}}),
                                     encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps({"source_doc": {"doc_id": "b", "title": "T", "origin_entity": "New"}}),
                                     encoding="utf-8")
    state = drift([{"id": "a", "title": "T", "origin_entity": "One"}, {"id": "b", "title": "T", "origin_entity": "Old"}],
                  json_source_docs(tmp_path))
    assert [(d["doc_id"], d["field"], d["kind"]) for d in state["danger"]] == [("a", "origin_entity", "json_files_disagree")]
    assert [(d["doc_id"], d["field"]) for d in state["stale"]] == [("b", "origin_entity")]
    assert "origin 1" in summary_line(state)


def _corrections(tmp_path: Path) -> dict:
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"kind": "sourcedoc_corrections", "pq2_ref": "sourcedoc-origin-sync:test", "corrections": [
        {"doc_id": "paper", "field": "origin_entity", "before": "Third-party Research",
         "after": "MDPI Micromachines（綜述）", "why": "期刊綜述"}]}), encoding="utf-8")
    return mig.load_corrections(path)


def test_corrections_edit_every_file_of_the_doc_and_require_the_declared_before(tmp_path: Path) -> None:
    """base＋addendum 兩份都要改成同一個值（否則 SourceDocSync 紅）；任何一份或圖上的現值不是宣告的 before 就拒收。"""
    manifest = _corrections(tmp_path)
    json_docs = {"paper": [{"file": "paper.json", "origin_entity": "Third-party Research"},
                           {"file": "paper_addendum.json", "origin_entity": "Third-party Research"}]}
    rows = [{"id": "paper", "origin_entity": "Third-party Research"}]
    planned = mig.plan_corrections(manifest, json_docs, rows)
    assert [e["file"] for e in planned["edits"]] == ["paper.json", "paper_addendum.json"]
    assert planned["graph"] == [{"doc_id": "paper", "field": "origin_entity", "kind": "declared_correction",
                                 "graph": "Third-party Research", "json": "MDPI Micromachines（綜述）"}]
    with pytest.raises(ValueError, match="不是宣告的 before"):
        mig.plan_corrections(manifest, json_docs, [{"id": "paper", "origin_entity": "Somebody else"}])
    drifted = {"paper": [dict(json_docs["paper"][0]), {"file": "paper_addendum.json", "origin_entity": "Other"}]}
    with pytest.raises(ValueError, match="不是宣告的 before"):
        mig.plan_corrections(manifest, drifted, rows)


def test_corrections_need_the_exact_pq2_ref(tmp_path: Path) -> None:
    from engine_b import todo

    pool = todo.empty_pool()
    mine = todo.upsert(pool, item_type="manual", ref_id="sourcedoc-origin-sync:test", title="更正")
    title_sync = todo.upsert(pool, item_type="manual", ref_id="sourcedoc-title-sync:2026-10-01", title="title")
    pool_path = tmp_path / "todo_pool.json"
    todo.save(pool, pool_path)
    assert mig.check_graph_approval(mine["n"], pool_path=pool_path, ref_id="sourcedoc-origin-sync:test")
    with pytest.raises(ValueError, match="不是本工具掛的"):
        mig.check_graph_approval(title_sync["n"], pool_path=pool_path, ref_id="sourcedoc-origin-sync:test")


def _media_entry(seen_in: str = "paper", origin: str = "MDPI Micromachines") -> dict:
    return {"origin": origin, "kind": "media", "corroborates": False, "seen_in": seen_in, "note": "測試"}


def test_correction_evidence_changes_reclassify_with_the_new_origin_and_pending_publisher(tmp_path: Path) -> None:
    """更正 origin、並跟著登記發布者之後重算：解析不到 → 登記的媒體＝媒體轉述（同級）——預告要逐條列出來。"""
    manifest = _corrections(tmp_path)
    rows = [{"src": "tech:a", "relation": "enables", "dst": "tech:b", "attributes": "{}", "confidence": 0.8,
             "origin": "Third-party Research", "source_type": "paper", "origin_linkage": None,
             "source_doc_id": "paper", "published_at": None, "assertion_id": "paper_e1"}]
    manifest["corrections"][0]["after"] = "MDPI Micromachines（Chen et al. 2025 綜述）"
    manifest["publishers_add"] = [_media_entry()]
    pending = mig.plan_publishers_add(manifest)
    changes = mig.correction_evidence_changes(rows, manifest, quotes_by_assertion={},
                                              publishers_after=mig.publishers_with(pending))
    assert changes == [{"edge": ["tech:a", "enables", "tech:b"], "before": "needs_review", "after": "media_relay"}]
    # 沒有跟著登記：新 origin 仍解析不到，等級不變——預告不得假裝已經登記了
    assert mig.correction_evidence_changes(rows, manifest, quotes_by_assertion={}) == []


def test_publishers_add_must_match_the_corrected_origin_and_is_not_registered_early(tmp_path: Path) -> None:
    """登記必須對得上 seen_in 那份文件**更正後**的 origin（L18）；已登記、類別亂寫、對不上的一律拒收。"""
    manifest = _corrections(tmp_path)
    manifest["corrections"][0]["after"] = "MDPI Micromachines（Chen et al. 2025 綜述）"
    for bad, message in (({**_media_entry(), "corroborates": True}, "不合規"),
                         (_media_entry(seen_in="elsewhere"), "不是這次更正後"),
                         (_media_entry(origin="Reuters"), "已登記")):
        manifest["publishers_add"] = [bad]
        with pytest.raises(ValueError, match=message):
            mig.plan_publishers_add(manifest)


def test_insert_publishers_keeps_the_one_line_per_entry_layout() -> None:
    raw = ('{\n  "schema_version": 1,\n  "publishers": [\n'
           '    {"origin": "A", "kind": "industry_research", "corroborates": true, "seen_in": "a"},\n'
           '    {"origin": "M", "kind": "media", "corroborates": false, "seen_in": "m"}\n  ]\n}\n')
    out = mig.insert_publishers(raw, [_media_entry(seen_in="paper", origin="N")])
    data = json.loads(out)
    assert [p["origin"] for p in data["publishers"]] == ["A", "M", "N"]
    assert out.splitlines()[:4] == raw.splitlines()[:4], "前面的行一個位元組都不動"


def test_apply_graph_refuses_a_number_that_is_not_this_tools_open_item(tmp_path: Path) -> None:
    """R2-a N6：`--apply-graph` 寫圖前核對編號——不存在／已結案、型別不是 manual、ref_id 不是本工具掛的，一律拒絕（沒有寫入）。"""
    from engine_b import todo

    pool = todo.empty_pool()
    mine = todo.upsert(pool, item_type="manual", ref_id="sourcedoc-title-sync:2026-10-01", title="對齊圖上 11 份 title")
    other_manual = todo.upsert(pool, item_type="manual", ref_id="something-else", title="別的事")
    ra = todo.upsert(pool, item_type="ra_admission", ref_id="ra_" + "0" * 32, title="RA")
    pool_path = tmp_path / "todo_pool.json"
    todo.save(pool, pool_path)
    assert mig.check_graph_approval(mine["n"], pool_path=pool_path)["ref_id"] == "sourcedoc-title-sync:2026-10-01"
    for n, message in ((9999, "不存在或已結案"), (other_manual["n"], "不是本工具掛的"), (ra["n"], "不是本工具掛的")):
        with pytest.raises(ValueError, match=message):
            mig.check_graph_approval(n, pool_path=pool_path)
    todo.resolve(pool, mine["n"], "drop", reason="測試")
    todo.save(pool, pool_path)
    with pytest.raises(ValueError, match="不存在或已結案"):
        mig.check_graph_approval(mine["n"], pool_path=pool_path)
