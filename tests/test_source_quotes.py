"""逐字必須跟著載入進圖（V1 / L18）。

事發（2026-09-18）：`loader/load_to_neo4j.py` 有六個 `MERGE_*`（node／edge／source_doc／
edge_assertion／node_claim／edge_claim）**卻獨缺 sources**。`quote` 在
`schema/intermediate_format.schema.json` 有定義、抽取端有產出、`loader/validate.py` 會檢查，
然後在 MERGE 那一步被靜默丟掉——**1,105 段逐字（192,055 字元）一段都沒進圖**，
`EdgeAssertion.source_ids`／`Claim.source_ids` 全部是指不到東西的懸空字串。

後果不是少一個欄位，是**下游結構上不可能發現 label 錯了**（L18）。實測代價：重判一個
relation 的 82 條邊，29 條要改、8 條逐字根本不支持任何關係，全部靠繞過工具直接讀
`extractions/*.json` 才發現。
"""
from __future__ import annotations

import json
from pathlib import Path

from loader.load_to_neo4j import LINK_QUOTES, MERGE_SOURCE, evidence_id, load


class _RecordingSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def run(self, query: str, **params):
        self.calls.append((query, params))
        return []

    def queries_matching(self, needle: str) -> list[dict]:
        return [p for q, p in self.calls if needle in q]


def _doc() -> dict:
    return {
        "schema_version": "0.1",
        "source_doc": {"doc_id": "d1", "title": "t", "source_type": "filing",
                       "evidence_tier": 1, "origin_entity": "o"},
        "sources": [
            {"id": "d1_s1", "locator": "p.1", "quote": "A supplies B, per the contract."},
            {"id": "d1_s2", "locator": "p.2", "quote": None},   # 沒有逐字也要建節點
        ],
        "nodes": [
            {"id": "co:a", "type": "Company", "name": "A", "abstraction_level": "device_chip",
             "role": "bottleneck_supplier", "aliases": [], "attributes": {},
             "confidence": 0.8, "source_ids": ["d1_s1"]},
            {"id": "co:b", "type": "Company", "name": "B", "abstraction_level": "module_subsystem",
             "role": "leader", "aliases": [], "attributes": {},
             "confidence": 0.8, "source_ids": ["d1_s1"]},
        ],
        "edges": [
            {"id": "e1", "src_id": "co:a", "dst_id": "co:b", "relation": "supplies_to",
             "attributes": {}, "confidence": 0.7, "source_ids": ["d1_s1", "d1_s2"]},
        ],
        "claims": [
            {"id": "cl1", "statement": "s", "subject_id": "co:a",
             "demand_proof_level": "guided", "disproof_condition": "x",
             "confidence": 0.7, "source_ids": ["d1_s1"]},
        ],
    }


def test_sources_are_merged_so_the_verbatim_reaches_the_graph() -> None:
    s = _RecordingSession()
    load(_doc(), s)
    merged = s.queries_matching("MERGE (s:Source")
    assert len(merged) == 2, "每一筆 source 都要進圖，含沒有 quote 的那筆"
    by_id = {m["id"]: m for m in merged}
    assert by_id["d1_s1"]["quote"] == "A supplies B, per the contract."
    assert by_id["d1_s2"]["quote"] is None
    assert all(m["source_doc_id"] == "d1" for m in merged)


def test_source_ids_stop_being_dangling_for_all_three_carriers() -> None:
    """節點、邊斷言、claim **三種載體都帶 source_ids，三種都要接**。

    只接其中一兩種就是「機制只認得我當初那個案例」（L17-3 的對稱面）——
    而且不會有任何東西變紅，因為沒有人在檢查它。
    """
    s = _RecordingSession()
    load(_doc(), s)
    linked = {tuple(p["id"] for _ in [0])[0]: p["source_ids"]
              for p in s.queries_matching("MERGE (n)-[:QUOTES]->(s)")}
    assert "co:a" in linked and "co:b" in linked, "節點要接"
    assert evidence_id("d1", "e1") in linked, "邊斷言要接"
    assert evidence_id("d1", "cl1") in linked, "claim 要接"
    assert linked[evidence_id("d1", "e1")] == ["d1_s1", "d1_s2"]


def test_existing_source_ids_field_is_untouched() -> None:
    """⚠ V1 宣稱「純新增」：既有欄位一個字都不能動。

    `source_ids` 是既有消費端讀的東西（`graph_context._fmt_sources` 等）。
    新增一條可走訪的邊不得順手改寫它——否則 V1 就不是純新增，
    而「既有輸出逐位不變」那條驗收也就不再可否證。
    """
    s = _RecordingSession()
    load(_doc(), s)
    ea = s.queries_matching("MERGE (ea:EdgeAssertion")
    assert ea and ea[0]["source_ids"] == ["d1_s1", "d1_s2"]
    nodes = s.queries_matching("MERGE (n:Entity")
    assert nodes and all("source_ids" in n for n in nodes)


def test_reloading_an_existing_doc_must_not_wipe_a_quote() -> None:
    """`Source` 是證據不是投影：`quote`／`locator` 用 coalesce 保留既有值。

    同一個坑踩過兩次——`SourceDoc.published_at` 被空值洗掉（回填的日期是 as-of 投影的
    唯一時間線索），以及 L17 事發裡 `MERGE_NODE` 重載時靜默覆蓋 `name`。
    """
    assert "coalesce($quote, s.quote)" in MERGE_SOURCE
    assert "coalesce($locator, s.locator)" in MERGE_SOURCE
    # 不得把 quote 直接 SET 成參數
    assert "s.quote = $quote" not in MERGE_SOURCE


def test_link_quotes_never_creates_a_source_it_cannot_find() -> None:
    """`LINK_QUOTES` 只 MATCH 不 MERGE Source——接不到就是接不到，不得憑空造一個空證據。"""
    assert "MATCH (s:Source)" in LINK_QUOTES
    assert "MERGE (s:Source" not in LINK_QUOTES


def test_backfill_script_reuses_the_loader_cypher_instead_of_rewriting_it() -> None:
    """同一個寫入語意不得有第二份實作——重造品會立刻開始偏離（L16）。"""
    src = (Path(__file__).resolve().parent.parent
           / "scripts" / "backfill_source_quotes.py").read_text(encoding="utf-8")
    assert "from loader.load_to_neo4j import" in src
    assert "MERGE_SOURCE" in src and "LINK_QUOTES" in src
    assert "MERGE (s:Source" not in src, "回填腳本不得自己寫一份 Cypher"


def test_every_extraction_carries_verbatim_worth_loading() -> None:
    """母體的現況檢查：抽取檔裡真的有逐字可載，否則本機制是空轉（L17-3：偵測做了誰消費）。

    ⚠ 只斷言「有」，**不寫死條數**——現況數字會過期，判準不會。
    """
    root = Path(__file__).resolve().parent.parent / "extractions"
    quoted = 0
    for path in root.glob("*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        quoted += sum(1 for s in doc.get("sources", []) if s.get("quote"))
    assert quoted > 0, "抽取檔裡一段逐字都沒有 —— 那 V1 載的是空氣"
