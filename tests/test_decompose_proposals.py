"""decompose 提案自動鑄號（engine_b/decompose_proposals.py；研究閉環 P∥）。

守的是三道機械判準：不是新錨不鑄、drop 過沒新 lead 不重生、open 滿了不再鑄；以及 `go` 的邊界寫在 hint 裡。
"""
from __future__ import annotations

import pytest

from engine_b import decompose_proposals as dp
from engine_b import todo

KNOWN = {"tech:ai_switch": "AI 光互連／CPO", "mat:rare_earth_magnets": "稀土磁材", "tech:humanoid_robot_systems": "機器人"}
GRAPH = frozenset({"tech:ai_switch", "tech:scale_up_cpo", "mat:rare_earth_magnets"})


def test_breadth_check_is_mechanical_and_names_the_reason() -> None:
    known = dp.breadth_check("tech:ai_switch", known_anchors=KNOWN, graph_nodes=GRAPH)
    assert not known.adds_breadth and known.anchor_known_in_sector == "AI 光互連／CPO" and "深度題" in known.reason
    in_graph = dp.breadth_check("tech:scale_up_cpo", known_anchors=KNOWN, graph_nodes=GRAPH)
    assert not in_graph.adds_breadth and in_graph.node_in_graph is True
    fresh = dp.breadth_check("tech:leo_satellite_bus", known_anchors=KNOWN, graph_nodes=GRAPH)
    assert fresh.adds_breadth and "新錨" in fresh.reason
    unknown_graph = dp.breadth_check("tech:leo_satellite_bus", known_anchors=KNOWN, graph_nodes=None)
    assert unknown_graph.adds_breadth and "圖快照讀不到" in unknown_graph.reason


def test_shipped_sector_anchors_load_and_coverage_nodes_extract() -> None:
    anchors = dp.load_known_anchors()
    assert "mat:rare_earth_magnets" in anchors
    nodes = dp.graph_nodes_from_coverage({"covered": [{"node": "a"}], "research_gaps": ["b"], "concept": [{"node": "c"}]})
    assert nodes == frozenset({"a", "b", "c"})


def test_propose_mints_a_manual_item_whose_go_only_authorizes_the_decompose_run() -> None:
    pool = todo.empty_pool()
    item = dp.propose(pool, system="Starlink V2 Mini 衛星", anchor="tech:leo_satellite_bus",
                      why_new_anchor="需求錨是 LEO 通訊 capex，不是 AI capex 也不是人形放量",
                      lead_ids=["lead_0123456789ab"], layers_estimate=9, known_anchors=KNOWN, graph_nodes=GRAPH)
    assert item["type"] == "manual" and item["ref_id"] == "decompose:starlink_v2_mini"
    assert item["source"] == dp.SOURCE
    for must in ("go＝跑 skills/system-decompose", "不含入圖", "不含 onboard", "lead_0123456789ab", "新錨"):
        assert must in item["hint"]
    # 冪等：同題再提回同一個編號
    again = dp.propose(pool, system="Starlink V2 Mini 衛星", anchor="tech:leo_satellite_bus", why_new_anchor="x",
                       known_anchors=KNOWN, graph_nodes=GRAPH)
    assert again["n"] == item["n"] and len(dp.open_proposals(pool)) == 1


def test_propose_refuses_depth_topics_and_empty_reasons() -> None:
    pool = todo.empty_pool()
    with pytest.raises(dp.DecomposeProposalError, match="深度題"):
        dp.propose(pool, system="GB300 NVL72", anchor="tech:ai_switch", why_new_anchor="x", known_anchors=KNOWN, graph_nodes=GRAPH)
    with pytest.raises(dp.DecomposeProposalError, match="已在圖裡"):
        dp.propose(pool, system="X", anchor="tech:scale_up_cpo", why_new_anchor="x", known_anchors=KNOWN, graph_nodes=GRAPH)
    with pytest.raises(dp.DecomposeProposalError, match="為什麼是新錨"):
        dp.propose(pool, system="X", anchor="tech:new", why_new_anchor="  ", known_anchors=KNOWN, graph_nodes=GRAPH)
    assert dp.open_proposals(pool) == []


def test_dropped_system_is_not_reborn_without_a_new_lead() -> None:
    pool = todo.empty_pool()
    first = dp.propose(pool, system="SMR 核電模組", anchor="tech:smr_module", why_new_anchor="能源 capex",
                       lead_ids=["lead_aaaaaaaaaaaa"], known_anchors=KNOWN, graph_nodes=GRAPH)
    todo.resolve(pool, first["n"], "drop", reason="現在不想開這條")
    with pytest.raises(dp.DecomposeProposalError, match="不重生"):
        dp.propose(pool, system="SMR 核電模組", anchor="tech:smr_module", why_new_anchor="能源 capex",
                   lead_ids=["lead_aaaaaaaaaaaa"], known_anchors=KNOWN, graph_nodes=GRAPH)
    reborn = dp.propose(pool, system="SMR 核電模組", anchor="tech:smr_module", why_new_anchor="能源 capex",
                        lead_ids=["lead_bbbbbbbbbbbb"], known_anchors=KNOWN, graph_nodes=GRAPH)
    assert reborn["n"] != first["n"] and "lead_bbbbbbbbbbbb" in reborn["hint"]


def test_open_proposals_are_capped() -> None:
    pool = todo.empty_pool()
    dp.propose(pool, system="A", anchor="tech:a", why_new_anchor="x", known_anchors=KNOWN, graph_nodes=GRAPH)
    dp.propose(pool, system="B", anchor="tech:b", why_new_anchor="x", known_anchors=KNOWN, graph_nodes=GRAPH)
    with pytest.raises(dp.DecomposeProposalError, match="已達 2"):
        dp.propose(pool, system="C", anchor="tech:c", why_new_anchor="x", known_anchors=KNOWN, graph_nodes=GRAPH)
    assert len(dp.open_proposals(pool)) == dp.MAX_OPEN
