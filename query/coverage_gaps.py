"""Chokepoint 供給側覆蓋掃描——「哪條瓶頸還沒有人研究過」。

與 `query/bottleneck.py` 的分工：後者在**已研究過的公司之間**排序既有的邊，
明確不做新標的發現；本模組回答互補的另一半——**哪些 chokepoint 節點還沒有供應商**，
是選題（廣度）的輸入。

⚠ 事發（2026-08-20）：第一版用 `MATCH (c:Company)-[]->(n)` 直接數供應商，
`tech:robotic_actuator` 回報 **0 個公司**，於是它被列為「完全沒研究過」的最大空白之一。
但圖中**早已有兩家的逐字證據**：Boston Dynamics 官方頁面（客戶端印證）載明 Hyundai
Mobis「will supply actuators for Atlas」，Schaeffler Q1 2026 法說載明其 rotary actuator
platform「covering ~80% of market demand」。

真正的原因是**邊建在不同層級**：
- `co:hyundai_mobis -[supplies_to]-> co:boston_dynamics`（公司對公司，繞過 chokepoint）
- `co:schaeffler -[develops]-> prod:… -[is_component_of]-> tech:humanoid_robot_systems`

只數直接邊會把**已研究過的領域誤報成空白**，而那正是決定下一步挖哪裡的依據。因此本
模組同時計算直接與間接覆蓋，並把兩者分開呈現：`direct` 是可直接引用的供應關係，
`indirect` 代表「這個領域已有研究，但邊沒接到 chokepoint 節點上」——後者是**建模待補**，
不是研究缺口，兩者的下一步動作完全不同。
"""
from __future__ import annotations

import os
from typing import Any, Iterable, Mapping

CHOKEPOINT_PREFIXES = ("tech:", "mat:", "prod:")

# 這些節點是概念／政策，沒有「誰供應它」這個問題，列進缺口只會製造雜訊。
CONCEPT_SUBSTRINGS = (
    "export_control",
    "sovereign_ai",
    "agentic_ai",
    "lta_framework",
)

# ⚠ 間接路徑必須限定語意，不能用裸的 `[*2..3]`。第一版那樣寫的結果是
# `prod:altus_family`、`tech:3d_scaling`、`tech:dram_production` 都回報同一批六家公司
# （anthropic／openai／lam_research…）——它們是穿過 `tech:ai_compute_buildout` 這類 hub
# 連上的假連結。修好一個方向的誤報卻製造另一個方向，正是 L12 的形狀：不是放寬也不是
# 收緊，是先把「經產品的真實供應路徑」與「穿過需求 hub 的巧合」分開，再各自定規則。
#
# 因此中繼節點限定為 `prod:` 或另一家 Company，且關係型別受限：公司**開發或供應**某個
# 產品／公司，而該產品／公司與此 chokepoint 之間有元件或依賴關係。
COVERAGE_CYPHER = """
MATCH (n)
WHERE any(p IN $prefixes WHERE n.id STARTS WITH p)
OPTIONAL MATCH (direct:Company)-[]->(n)
WITH n, collect(DISTINCT direct.id) AS direct_ids
OPTIONAL MATCH (c:Company)-[r1:DEVELOPS|SUPPLIES_TO|DEPLOYS|PARTNERSHIP_WITH]-(mid)
                -[r2:IS_COMPONENT_OF|ENABLES|DEPENDS_ON|SUPPLIES_TO|DEVELOPS]-(n)
WHERE NOT c.id IN direct_ids
  AND (mid.id STARTS WITH 'prod:' OR mid:Company)
  AND c <> n AND mid <> n AND mid <> c
WITH n, direct_ids, collect(DISTINCT c.id) AS indirect_ids
RETURN n.id AS node, n.name AS name, direct_ids, indirect_ids
ORDER BY size(direct_ids), size(indirect_ids), node
"""


def is_concept_node(node_id: str) -> bool:
    return any(token in node_id for token in CONCEPT_SUBSTRINGS)


def classify(direct: list[str], indirect: list[str], node_id: str) -> str:
    """三態，因為三者的下一步動作不同。"""

    if is_concept_node(node_id):
        return "concept"
    if direct:
        return "covered"
    if indirect:
        return "modelling_gap"
    return "research_gap"


def scan(session) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in session.run(COVERAGE_CYPHER, prefixes=list(CHOKEPOINT_PREFIXES)):
        direct = [x for x in (record["direct_ids"] or []) if x]
        indirect = [x for x in (record["indirect_ids"] or []) if x]
        node_id = record["node"]
        rows.append(
            {
                "node": node_id,
                "name": record["name"],
                "direct": sorted(direct),
                "indirect": sorted(indirect),
                "status": classify(direct, indirect, node_id),
            }
        )
    return rows


def render_markdown(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    rows = list(rows)
    buckets: dict[str, list[Mapping[str, Any]]] = {
        "research_gap": [],
        "modelling_gap": [],
        "covered": [],
        "concept": [],
    }
    for row in rows:
        buckets[row["status"]].append(row)

    out = ["", "# Chokepoint 供給側覆蓋掃描", ""]
    out.append(
        f"節點 {len(rows)}｜🔴 研究缺口 **{len(buckets['research_gap'])}**"
        f"｜🟡 建模待補 **{len(buckets['modelling_gap'])}**"
        f"｜✅ 已覆蓋 {len(buckets['covered'])}"
        f"｜⚪ 概念節點 {len(buckets['concept'])}"
    )
    out.append("")
    out.append(
        "> 🔴 **研究缺口**＝沒有任何公司連到它（直接或間接）——這才是真正該去挖的。\n"
        "> 🟡 **建模待補**＝已有公司經 `prod:` 或公司對公司邊間接相連，代表**這個領域已經研究過**，\n"
        "> 只是邊沒接到 chokepoint 節點上。下一步是補邊（走 graph admission），不是重新研究。\n"
        "> ⚪ 概念／政策節點不適用「誰供應它」，不列入缺口。"
    )

    if buckets["modelling_gap"]:
        out += ["", "## 🟡 建模待補（已研究過，邊沒接上）", ""]
        out.append("| 節點 | 間接相連的公司 |")
        out.append("|---|---|")
        for row in buckets["modelling_gap"]:
            companies = "、".join(f"`{c}`" for c in row["indirect"][:6])
            out.append(f"| `{row['node']}` | {companies} |")

    if buckets["research_gap"]:
        out += ["", "## 🔴 研究缺口（真正的空白）", ""]
        for row in buckets["research_gap"]:
            out.append(f"- `{row['node']}`　{row['name'] or ''}")
    return out


def main() -> int:
    from neo4j import GraphDatabase

    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        print("請設 NEO4J_PASSWORD")
        return 2
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )
    try:
        with driver.session() as session:
            rows = scan(session)
        print("\n".join(render_markdown(rows)))
    finally:
        driver.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
