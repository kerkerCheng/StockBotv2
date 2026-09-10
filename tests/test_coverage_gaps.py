from __future__ import annotations

from query.coverage_gaps import (
    ISOLATED_DEGREE, classify, is_concept_node, render_markdown, split_research_gaps,
)


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


def test_isolated_node_gets_a_different_next_step_than_a_real_research_question() -> None:
    """`degree=0` 的節點連 stack 都沒接上——派它去「查誰供應」會找不到落點。

    ⚠ 這**不是**新分類：它不改變任何節點落在哪一桶，只是把節點自己的邊數印出來。
    2026-09-10 逐節點查證過，🔴 裡的節點在 source_ids／abstraction_level／ABOUT 上
    完全同形，沒有可機械分辨的差異——在那裡切一刀只會得到會誤報的分類（L16-4）。
    """

    rows = [
        {"node": "tech:orphan", "name": "Orphan", "direct": [], "indirect": [],
         "status": "research_gap", "degree": ISOLATED_DEGREE,
         "abstraction_level": "network_systems"},
        {"node": "tech:serdes", "name": "SerDes", "direct": [], "indirect": [],
         "status": "research_gap", "degree": 3, "abstraction_level": "device_chip"},
    ]
    out = "\n".join(render_markdown(rows))

    assert "先確認它該掛在 stack 哪一層" in out
    assert "誰供應 `tech:serdes`？" in out
    # 孤立節點不得同時拿到「去查誰供應它」那句
    assert "誰供應 `tech:orphan`？" not in out
    # 兩欄脈絡都要出現在表裡
    assert "network_systems" in out and "device_chip" in out


def test_context_columns_do_not_change_any_bucket() -> None:
    """脈絡欄位不參與分類：同樣的 direct／indirect，分桶結果必須完全不受 degree 影響。"""

    assert classify([], [], "tech:a") == "research_gap"
    rows = [
        {"node": "tech:a", "name": "A", "direct": [], "indirect": [],
         "status": "research_gap", "degree": 0, "abstraction_level": None},
        {"node": "prod:b", "name": "B", "direct": [], "indirect": [],
         "status": "research_gap", "degree": 9, "abstraction_level": "device_chip"},
    ]
    real, noise = split_research_gaps(rows)
    assert [r["node"] for r in real] == ["tech:a"]
    assert [r["node"] for r in noise] == ["prod:b"]
