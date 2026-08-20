from __future__ import annotations

from query.coverage_gaps import classify, is_concept_node, render_markdown


def test_indirect_only_is_modelling_gap_not_research_gap() -> None:
    """已有公司間接相連 ≠ 沒研究過——誤判會讓選題挖已經挖過的地方。

    事發（2026-08-20）：tech:robotic_actuator 被直接邊計數回報「0 個公司供應商」，
    因而列為最大空白之一；但圖中早有 Boston Dynamics 官方頁面（客戶端印證）載明
    Hyundai Mobis 供應 Atlas actuators。差別只在邊建在 prod: 與公司對公司層級。
    """

    assert classify([], ["co:boston_dynamics"], "tech:robotic_actuator") == "modelling_gap"
    assert classify([], [], "tech:serdes") == "research_gap"
    assert classify(["co:micron_technology"], [], "tech:hbm") == "covered"


def test_concept_nodes_never_counted_as_gaps() -> None:
    """政策／概念節點沒有「誰供應它」這個問題，列進缺口只是雜訊。"""

    assert is_concept_node("tech:export_controls_china")
    assert classify([], [], "tech:sovereign_ai") == "concept"
    # 即使有公司連上去，概念節點仍不進覆蓋統計
    assert classify(["co:nvidia"], [], "tech:agentic_ai") == "concept"
    assert not is_concept_node("tech:robotic_actuator")


def test_render_separates_two_gap_kinds_with_counts() -> None:
    rows = [
        {"node": "tech:serdes", "name": "SerDes", "direct": [], "indirect": [],
         "status": "research_gap"},
        {"node": "tech:robotic_actuator", "name": "Actuator", "direct": [],
         "indirect": ["co:boston_dynamics"], "status": "modelling_gap"},
        {"node": "tech:hbm", "name": "HBM", "direct": ["co:micron_technology"],
         "indirect": [], "status": "covered"},
    ]
    out = "\n".join(render_markdown(rows))
    assert "研究缺口 **1**" in out
    assert "建模待補 **1**" in out
    # 兩種缺口必須分開呈現：下一步動作不同（補研究 vs 補邊）
    assert "## 🟡 建模待補" in out and "## 🔴 研究缺口" in out
    assert "`co:boston_dynamics`" in out
