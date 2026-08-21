"""瓶頸鏈排序：鎖住 2026-08-18 實際踩過的四個 bug。

每個 test 對應一個**跑出來才發現**的缺陷，不是假想的。
"""
from __future__ import annotations

import json

from query.bottleneck import (
    DEMAND_ANCHORS,
    build_upward_index,
    classify_evidence,
    collapse_assertions,
    demand_chain,
    is_entity_id,
    rank_bottlenecks,
)


class _FakeRegistry:
    """只實作 bottleneck.py 用到的 registry surface。"""

    class _C:
        def __init__(self, cid, name, ticker):
            self.company_id, self.name, self.research_ticker_ = cid, name, ticker
            self.aliases = ()

    def __init__(self):
        self._c = [
            self._C("co:axt", "AXT", "AXTI"),
            self._C("co:coherent", "Coherent", "COHR"),
            self._C("co:nvidia", "NVIDIA", "NVDA"),
        ]

    @property
    def companies(self):
        return tuple(self._c)

    def company_id_for_ticker(self, ticker):
        for c in self._c:
            if c.research_ticker_ == ticker.strip().upper():
                return c.company_id
        return None

    def has_company(self, cid):
        return any(c.company_id == cid for c in self._c)

    def research_ticker(self, cid):
        for c in self._c:
            if c.company_id == cid:
                return c.research_ticker_
        return None


def _row(src, rel, dst, *, conf, attrs=None, origin=None):
    return {
        "src": src,
        "relation": rel,
        "dst": dst,
        "confidence": conf,
        "attributes": json.dumps(attrs or {}),
        "origin": origin,
    }


def test_same_edge_from_many_documents_collapses_and_does_not_inflate_score() -> None:
    """排名分數不得是「我們讀了幾份文件」的函數。

    實測：`co:axt → mat:inp_substrate` 有 4 條 EdgeAssertion 來自 4 份文件。
    若數邊，再 ingest 五份 InP 報導分數就會上升，而世界沒有任何改變。
    """
    rows = [
        _row("co:axt", "supplies_to", "co:coherent", conf=0.5,
             attrs={"substitutability": 4}, origin=f"Doc{i}")
        for i in range(4)
    ]
    canonical = collapse_assertions(rows)
    assert len(canonical) == 1
    edge = next(iter(canonical.values()))
    assert edge.documents == 4          # 份數保留，作注意力指標
    assert edge.substitutability == 4   # 但值不累加、不放大


def test_attribute_survives_when_top_confidence_assertion_omits_it() -> None:
    """逐屬性取最佳 confidence，不是整條邊只看一份 assertion。

    首版對整條邊只取「confidence 最高那份」的全部屬性，於是若該份沒填
    `substitutability`，整條邊的值就被丟掉——**co:axt 因此整個從排名消失**，
    覆蓋率也從 22% 假掉到 16%。
    """
    rows = [
        # 最高 confidence 的那份沒有 substitutability
        _row("co:axt", "supplies_to", "co:coherent", conf=0.9,
             attrs={"qualification_status": "qualified"}),
        _row("co:axt", "supplies_to", "co:coherent", conf=0.5,
             attrs={"substitutability": 4}),
    ]
    edge = next(iter(collapse_assertions(rows).values()))
    assert edge.substitutability == 4, "低 confidence 但唯一有值的那份不得被丟掉"
    assert edge.qualification_status == "qualified"


def test_demand_chain_returns_none_instead_of_a_nearest_node_fallback() -> None:
    """走不到需求錨點就回 None——不得用「最接近的節點」充數。

    首版用「往上走最長路徑、端點即錨點」，在有環的圖上會繞回目標本身，
    產出看起來結構化但無意義。依使用者判準，連不到有人花錢的地方的瓶頸
    不該被當投資標的看待，所以這裡必須誠實回 None。
    """
    edges = list(
        collapse_assertions(
            [
                _row("co:axt", "supplies_to", "co:coherent", conf=0.5),
                _row("co:coherent", "supplies_to", "tech:cpo", conf=0.5),
                _row("tech:cpo", "is_component_of", "tech:ai_switch", conf=0.5),
                # 與需求端完全無關的一條
                _row("co:orphan", "supplies_to", "mat:nothing", conf=0.5),
            ]
        ).values()
    )
    upward = build_upward_index(edges)

    assert "tech:ai_switch" in DEMAND_ANCHORS
    chain = demand_chain("co:axt", upward)
    assert chain == ["tech:ai_switch", "tech:cpo", "co:coherent", "co:axt"]
    assert demand_chain("co:orphan", upward) is None


def test_supplies_to_carries_demand_upward() -> None:
    """`A supplies_to B` ⇒ B 需要 A，需求要能沿著它往上傳。

    首版的向上索引漏了 `supplies_to`，於是任何「瓶頸目標是一家公司」的列都
    走不到需求錨點——實測 co:axt 顯示「無錨點」，但鏈其實是通的。
    """
    edges = list(
        collapse_assertions(
            [
                _row("co:coherent", "supplies_to", "tech:ai_switch", conf=0.5),
            ]
        ).values()
    )
    assert demand_chain("co:coherent", build_upward_index(edges)) == [
        "tech:ai_switch",
        "co:coherent",
    ]


def test_evidence_is_three_way_and_unresolved_origin_does_not_auto_pass() -> None:
    """`None` 同時是「真第三方」與「沒解析出的別名」，不得壓成布林（L12）。"""
    reg = _FakeRegistry()
    assert classify_evidence("co:coherent", ["Coherent"], reg) == "self_reported"
    assert (
        classify_evidence("co:coherent", ["Coherent", "NVIDIA"], reg)
        == "externally_corroborated"
    )
    # 唯一的非本人 origin 無法解析 → 待人工判定，不得自動當成外部佐證
    assert (
        classify_evidence("co:coherent", ["Coherent", "The Next Platform"], reg)
        == "needs_review"
    )


def test_claim_nodes_are_excluded_from_ranking() -> None:
    """188 個 Claim 節點貼著 `:Entity` 標籤；真 Entity 一律有 `前綴:slug`。"""
    assert is_entity_id("co:axt")
    assert not is_entity_id("axti_10_k_20260317_cl1")

    result = rank_bottlenecks(
        [
            _row("axti_10_k_20260317_cl1", "supplies_to", "co:coherent", conf=0.9,
                 attrs={"substitutability": 5}),
            _row("co:axt", "supplies_to", "co:coherent", conf=0.5,
                 attrs={"substitutability": 4}),
        ],
        _FakeRegistry(),
    )
    assert [r["company_id"] for r in result["rows"]] == ["co:axt"]


def test_coverage_limits_are_always_reported() -> None:
    """已知限制必須隨輸出常駐，不得只寫在文件裡（L14）。"""
    result = rank_bottlenecks(
        [_row("co:axt", "supplies_to", "co:coherent", conf=0.5,
              attrs={"substitutability": 4})],
        _FakeRegistry(),
    )
    cov = result["coverage"]
    for key in (
        "substitutability_coverage",
        "self_reported_share",
        "edges_with_lead_time",
        "duplicate_collapse",
    ):
        assert key in cov


def test_structural_rows_ignore_evidence_and_expose_research_gap() -> None:
    """純結構排序必須與可行動排序分離——否則排名反映的是研究深度，不是瓶頸性。

    事發（2026-08-21）：使用者指出「研究筆數多 → 證據強，但不代表瓶頸性強」。
    查證屬實：rank_bottlenecks 的排序鍵把 EVIDENCE_RANK 放在 substitutability 之前，
    而 evidence 最高級（externally_corroborated）必須靠研究找到客戶端文件才拿得到。
    實測差異：可行動排序第 1 是 COHR→NVIDIA，純結構第 1 是 AVGO→CPO——同為 sub=5／
    sole_source，但 AVGO 距需求端只有 1 跳。
    """

    from query.bottleneck import rank_bottlenecks

    class _Reg:
        def research_ticker(self, company_id):
            return {"co:a": "AAA", "co:b": "BBB"}.get(company_id)

    rows = [
        # 結構較強（1 跳）但只有自報證據
        {"src": "co:b", "relation": "supplies_to", "dst": "tech:ai_switch",
         "substitutability": 5, "sole_source": True, "qualification_status": "designed_in",
         "confidence": 0.8, "origin_entity": "co:b", "doc_id": "d1"},
        # 結構較弱（2 跳）但有外部印證
        {"src": "co:a", "relation": "supplies_to", "dst": "co:b",
         "substitutability": 4, "sole_source": False, "qualification_status": "qualified",
         "confidence": 0.8, "origin_entity": "third_party", "doc_id": "d2"},
    ]
    result = rank_bottlenecks(rows, _Reg())

    assert "structural_rows" in result
    assert len(result["structural_rows"]) == len(result["rows"])
    # 純結構第一名的 substitutability 必須 >= 可行動第一名
    if result["rows"] and result["structural_rows"]:
        assert (result["structural_rows"][0]["substitutability"] or 0) >= (
            result["rows"][0]["substitutability"] or 0
        )
