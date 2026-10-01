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
    rows = [{"id": "split", "section": "asic", "title": "Parent——coverage-gap addendum"}]
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
    with pytest.raises(ValueError, match="只准動"):
        mig.apply_graph([{**stale[0], "field": "origin_entity"}], session=_Session(), pq2=777, root=tmp_path)
