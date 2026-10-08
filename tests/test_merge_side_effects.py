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


# ---------------------------------------------------------------------------
# 入圖後證據等級會變的邊（Phase 6 Step 6.4）：照 loader 的 MERGE 語意在記憶體裡併進當下的圖
# ---------------------------------------------------------------------------

def _graph_rows() -> list[dict]:
    base = {"attributes": "{}", "confidence": 0.8, "source_type": "news", "published_at": "2026-06-01"}
    return [
        {**base, "assertion_id": "d_e1", "src": "co:lumentum", "relation": "supplies_to", "dst": "tech:x",
         "origin": "NVIDIA", "origin_linkage": None, "source_doc_id": "d"},
        {**base, "assertion_id": "d_e2", "src": "co:lumentum", "relation": "supplies_to", "dst": "tech:y",
         "origin": "NVIDIA", "origin_linkage": None, "source_doc_id": "d"},
        {**base, "assertion_id": "o_e1", "src": "co:nvidia", "relation": "depends_on", "dst": "tech:x",
         "origin": "NVIDIA", "origin_linkage": None, "source_doc_id": "o"},
    ]


def _packet_doc() -> dict:
    """同一份文件 d 的更正版：e1 多連一段具名 Lumentum 的逐字、s1 逐字改寫；e2 不在新版（舊 assertion 留著）；新邊 e3。"""
    return {"source_doc": {"doc_id": "d", "title": "T", "source_type": "press_release", "evidence_tier": 2,
                           "origin_entity": "NVIDIA", "url": "https://example.com/d", "origin_linkage": None},
            "sources": [{"id": "d_s1", "quote": "NVIDIA signed a multiyear supply agreement"},
                        {"id": "d_s3", "quote": "NVIDIA will purchase lasers from Lumentum"}],
            "nodes": [],
            "edges": [{"id": "e1", "src_id": "co:lumentum", "relation": "supplies_to", "dst_id": "tech:x",
                       "confidence": 0.9, "attributes": {}, "source_ids": ["d_s1", "d_s3"]},
                      {"id": "e3", "src_id": "co:lumentum", "relation": "supplies_to", "dst_id": "tech:z",
                       "confidence": 0.9, "attributes": {}, "source_ids": ["d_s3"]}],
            "claims": []}


def test_rows_after_load_follow_the_loader_merge_semantics() -> None:
    """assertion 以 evidence_id 覆寫、舊版有新版沒有的留著、SourceDoc 欄位直接 SET 到同一份文件的每一筆、
    Source 逐字 coalesce、QUOTES 連結只增不減——與 `loader.load_to_neo4j.load` 同一套（預告不得比真的載入樂觀）。"""
    from loader.merge_side_effects import rows_after_load

    links = {"d_e1": ["d_s1"], "d_e2": ["d_s2"], "o_e1": ["o_s1"]}
    source_quotes = {"d_s1": "old wording", "d_s2": "NVIDIA buys lasers", "o_s1": "NVIDIA needs lasers"}
    doc = _packet_doc()
    doc["source_doc"]["origin_linkage"] = "independent"
    rows, quotes = rows_after_load(_graph_rows(), links, source_quotes, [doc])
    by_id = {r["assertion_id"]: r for r in rows}
    assert set(by_id) == {"d_e1", "d_e2", "o_e1", "d_e3"}                       # e2 留著、e3 新增
    assert by_id["d_e2"]["origin_linkage"] == "independent"                      # SourceDoc SET 到同一份文件的舊 assertion
    assert by_id["d_e2"]["source_type"] == "press_release" and by_id["o_e1"]["source_type"] == "news"
    assert by_id["d_e1"]["published_at"] == "2026-06-01"                         # 抽取檔沒帶日期：coalesce 留圖上值
    assert quotes["d_e1"] == ["NVIDIA signed a multiyear supply agreement", "NVIDIA will purchase lasers from Lumentum"]
    assert quotes["d_e2"] == ["NVIDIA buys lasers"] and quotes["d_e3"] == ["NVIDIA will purchase lasers from Lumentum"]


def test_evidence_after_load_lists_every_edge_whose_label_would_change() -> None:
    """補回一段具名引文 → 那條邊待判定 → 外部印證；新邊 before=None；沒動的邊不列。"""
    from identity.registry import CompanyIdentity, IdentityRegistry
    from loader.merge_side_effects import evidence_after_load

    registry = IdentityRegistry(version=1, companies=(
        CompanyIdentity("co:lumentum", "LITE", display_name="Lumentum Holdings Inc.", name_aliases=("Lumentum",)),
        CompanyIdentity("co:nvidia", "NVDA", display_name="NVIDIA Corporation", name_aliases=("NVIDIA",))))
    state = {"rows": _graph_rows(), "links": {"d_e1": ["d_s1"], "d_e2": ["d_s2"], "o_e1": ["o_s1"]},
             "source_quotes": {"d_s1": "old wording", "d_s2": "NVIDIA buys lasers", "o_s1": "NVIDIA needs lasers"}}
    changes = evidence_after_load(state, [_packet_doc()], registry)
    assert changes == [
        {"edge": ["co:lumentum", "supplies_to", "tech:x"], "before": "needs_review",
         "after": "externally_corroborated", "after_withheld": []},
        {"edge": ["co:lumentum", "supplies_to", "tech:z"], "before": None, "after": "externally_corroborated",
         "after_withheld": []},
    ]


def test_evidence_lines_say_unknown_out_loud_and_print_each_change() -> None:
    from loader.merge_side_effects import evidence_lines

    assert evidence_lines(None) == []                                             # 舊紀錄沒有這一段：不印
    unknown = evidence_lines({"status": "upstream_unavailable", "reason": "連不上圖"})
    assert len(unknown) == 1 and "無法核對" in unknown[0] and "不是「不會變」" in unknown[0]
    assert evidence_lines({"status": "checked", "changes": []}) == ["- 入圖後沒有任何一條邊的證據等級會變"]
    lines = evidence_lines({"status": "checked", "changes": [
        {"edge": ["co:a", "supplies_to", "tech:x"], "before": "externally_corroborated", "after": "needs_review",
         "after_withheld": ["unnamed"]},
        {"edge": ["co:a", "supplies_to", "tech:z"], "before": None, "after": "self_reported", "after_withheld": []}]})
    assert lines[0] == "- 入圖後證據等級會變的邊 2 條："
    assert "外部印證 → 待判定（沒升外部印證：引文沒具名主詞）" in lines[1] and "新邊 → 供應商自報" in lines[2]


class _IdSession:
    """`graph_increment` 只查「這些 id 在不在圖上」。"""

    def __init__(self, on_graph):
        self.on_graph = set(on_graph)

    def run(self, _cypher, ids=()):
        return [{"id": i} for i in ids if i in self.on_graph]


def test_graph_increment_counts_what_the_graph_gains_not_what_the_documents_declare() -> None:
    """更正走廊的形狀（[699]）：新版整份重宣告既有節點與邊——增量只算圖上沒有的（2026-10-08，failure log #17）。"""
    from loader.merge_side_effects import graph_increment, increment_line

    doc = _packet_doc()
    doc["nodes"] = [{"id": "co:lumentum", "type": "Company", "name": "Lumentum"},
                    {"id": "tech:x", "type": "Technology", "name": "X"},
                    {"id": "tech:z", "type": "Technology", "name": "Z"}]
    doc["claims"] = [{"id": "d_c1", "text": "舊 claim"}, {"id": "d_c2", "text": "新 claim"}]
    state = {"rows": _graph_rows(), "links": {"d_e1": ["d_s1"], "d_e2": ["d_s2"], "o_e1": ["o_s1"]},
             "source_quotes": {"d_s1": "old wording", "d_s2": "NVIDIA buys lasers", "o_s1": "NVIDIA needs lasers"}}
    increment = graph_increment(state, [doc], _IdSession({"co:lumentum", "tech:x", "d_c1"}))
    assert increment == {
        "status": "checked",
        "nodes": {"new": ["tech:z"], "declared": 3},
        "edges": {"new": [["co:lumentum", "supplies_to", "tech:z"]], "declared": 2},   # e1 已在圖上
        "claims": {"new": ["d_c2"], "declared": 2},
    }
    assert increment_line(increment) == "新增 1 節點、1 邊、1 claims（另 4 筆已在圖上或逐字保留）"
    assert increment_line(None) is None
    assert increment_line({"status": "upstream_unavailable", "reason": "連不上圖"}).startswith("增量無法核對（連不上圖）")
