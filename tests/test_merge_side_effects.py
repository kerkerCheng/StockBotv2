"""入圖副作用（`loader/merge_side_effects.py`；Phase 6 Step 6.2，Phase 4 #32）：載入會改到圖上哪些**既有**值。

守四件事：①直接 SET 的欄位（type／abstraction_level／role）與 SourceDoc 欄位被逐欄比對；②name／aliases／attributes
照 loader 的保留規則算（同一個函式）；③讀不到圖＝`upstream_unavailable`，不是「無副作用」；④測試絆線（AssertionError）不被吞。
"""
from __future__ import annotations

import pytest

from loader.merge_side_effects import (as_loaded, compute_side_effects, has_side_effects, render_lines,
                                       side_effects)


def _doc(**node_overrides) -> dict:
    node = {"id": "mat:widget", "type": "Material", "name": "Widget", "abstraction_level": "materials_substrate",
            "role": None, "aliases": ["W"], "attributes": {"k": 1}, "confidence": 0.8, "source_ids": ["d_s1"]}
    node.update(node_overrides)
    return {"source_doc": {"doc_id": "d", "title": "T", "source_type": "news", "evidence_tier": 3,
                           "origin_entity": "Somebody", "url": "https://example.com/d", "retrieved_at": "2026-08-01"},
            "sources": [], "nodes": [node], "edges": [], "claims": []}


def _graph(**props) -> dict:
    node = {"id": "mat:widget", "type": "Material", "name": "Widget", "abstraction_level": "materials_substrate",
            "role": None, "aliases": ["W"], "attrs": '{"k": 1}', "confidence": 0.8}
    node.update(props)
    return {"nodes": {"mat:widget": node},
            "source_doc": {"title": "T", "source_type": "news", "evidence_tier": 3, "origin_entity": "Somebody",
                           "url": "https://example.com/d", "publisher": None, "storage_permission": None,
                           "permission_basis": None, "section": None, "origin_linkage": None,
                           "published_at": None, "retrieved_at": "2026-08-01"}}


def test_identical_declarations_have_no_side_effects() -> None:
    result = compute_side_effects(_doc(), _graph())
    assert has_side_effects(result) is False
    assert result["node_overwrites"] == [] and result["source_doc_conflicts"] == []


def test_a_declaration_that_differs_from_the_graph_is_an_overwrite() -> None:
    """MERGE_NODE 對 abstraction_level／role 是直接 SET：最後載入者贏——要逐欄印出來。"""
    result = compute_side_effects(_doc(abstraction_level="device_chip", role=None),
                                  _graph(abstraction_level="module_subsystem", role="disruptor"))
    assert has_side_effects(result) is True
    assert {(o["field"], o["graph"], o["after"]) for o in result["node_overwrites"]} == {
        ("abstraction_level", "module_subsystem", "device_chip"), ("role", "disruptor", None)}
    assert any("會被覆寫" in line for line in render_lines(result, doc_id="d"))


def test_names_aliases_and_attributes_follow_the_loader_preservation_rule() -> None:
    """name 保留圖上值（不算覆寫）；別名聯集（列出新增的）；屬性只補圖上沒有的鍵。"""
    result = compute_side_effects(_doc(name="Widget Inc", aliases=["W", "Wdg"], attributes={"k": 9, "new": 2}),
                                  _graph())
    assert result["node_overwrites"] == []
    assert result["alias_unions"] == [{"node": "mat:widget", "graph": ["W"], "added": ["Wdg"]}]
    assert result["attribute_additions"] == [{"node": "mat:widget", "added": {"new": 2}}]


def test_source_doc_conflicts_and_date_regressions_are_reported() -> None:
    doc = _doc()
    doc["source_doc"].update(title="Other title", retrieved_at="2026-07-01")
    result = compute_side_effects(doc, _graph())
    by_field = {c["field"]: c for c in result["source_doc_conflicts"]}
    assert by_field["title"]["graph"] == "T" and by_field["title"]["after"] == "Other title"
    assert by_field["retrieved_at"].get("regression") is True, "retrieved_at 倒退要標出來"


def test_a_coalesced_date_missing_from_the_extraction_is_not_a_conflict() -> None:
    """published_at／retrieved_at 是 coalesce：抽取檔沒帶就保留圖上的值，不算副作用。"""
    doc = _doc()
    doc["source_doc"].pop("retrieved_at")
    assert compute_side_effects(doc, _graph())["source_doc_conflicts"] == []


def test_new_nodes_and_a_new_source_doc_are_not_side_effects() -> None:
    result = compute_side_effects(_doc(), {"nodes": {}, "source_doc": None})
    assert result["new_nodes"] == ["mat:widget"] and result["source_doc_new"] is True
    assert has_side_effects(result) is False


class _BrokenSession:
    def run(self, *_a, **_k):
        raise OSError("connection refused")


class _TripwireSession:
    def run(self, *_a, **_k):
        raise AssertionError("graph must not be read here")


def test_an_unreachable_graph_is_unknown_not_clean() -> None:
    """讀不到圖：`upstream_unavailable`、`has_side_effects` 回 None——**不得**印成「無副作用」（L13）。"""
    result = side_effects(_doc(), _BrokenSession())
    assert result["status"] == "upstream_unavailable"
    assert has_side_effects(result) is None
    assert all("無法核對" in line for line in render_lines(result))


def test_a_test_tripwire_is_not_swallowed_as_unreachable() -> None:
    with pytest.raises(AssertionError):
        side_effects(_doc(), _TripwireSession())


def test_as_loaded_compares_the_canonical_ids_the_loader_will_merge() -> None:
    """抽取檔的別名 id 要先換成 canonical（`identity.entities`）——否則真正會被覆寫的節點沒被比對到（2026-10-03 撞到）。"""
    from identity import entities

    # `entities.load()`：canonical → {aliases: [別名 id…]}；取第一個有別名的
    canonical, alias = next(((c, e["aliases"][0]) for c, e in entities.load().items() if e.get("aliases")))
    assert entities.resolve(alias) == canonical
    doc = _doc(id=alias)
    loaded = as_loaded(doc)
    assert loaded["nodes"][0]["id"] == canonical
    assert doc["nodes"][0]["id"] == alias, "原 doc 不得被改（resolve_document 會原地改，所以先拷貝）"
