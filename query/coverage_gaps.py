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
OPTIONAL MATCH (n)-[any_rel]-()
WHERE type(any_rel) <> 'QUOTES'
WITH n, direct_ids, indirect_ids, count(any_rel) AS degree
RETURN n.id AS node, n.name AS name, direct_ids, indirect_ids,
       degree, n.abstraction_level AS abstraction_level
ORDER BY size(direct_ids), size(indirect_ids), node
"""


# ⚠ `degree` 必須排除 `QUOTES`（2026-09-18 V3 交付時發現的回歸）。V1 讓逐字進圖之後，
# 裸的 `-[any_rel]-` 把證據邊也算成結構邊——**188 個節點的 degree 全部虛增**，其中
# `tech:lta_framework` 與 `tech:scale_out_network` **失去了 `isolated` 標記**（結構邊 0、
# 但各有 2 段逐字）。後果不是數字難看：`isolated` 決定「下一步」印哪一句，而
# 「先確認它該掛在 stack 哪一層」與「誰供應它」是兩個不同的研究動作。
# 這是 L17 的形狀——不會壞、不會報錯、測試不會紅，因為沒有任何東西被它逼著回來修。

# ---------------------------------------------------------------------------
# 分桶與走圖共用的常數：**跟著資料走**（L16）。走圖第 7／8 型（`query/graph_walk.py`）從這裡拿，
# 不各自抄一份。⚠ 2026-09-29（Phase 3 Step 3.1c）：本檔的 markdown 與 CLI 退役，只給它們用的固定文字
# （標題、分桶說明、孤立／層兩段註記、APP coverage kind 的標籤與下一步）一併拿掉——走圖的問句與
# 下一步住 `query/graph_walk.py` 的 `QUESTION_TYPES`。
# ---------------------------------------------------------------------------

#: 🔴 桶裡混了兩種東西，下一步完全不同（判準出自 `skills/alpha-status`）。
#: ⚠ 這個切分是**前綴比對**，不是語意判斷——任何人重跑都得到同一組，可被機械重導。
#: `tech:`／`mat:` 是有名有姓、零供應商的子瓶頸；`prod:` 是抽取的副產品，只計數、不列為研究題目。
PRODUCT_NOISE_PREFIX = "prod:"

#: 研究題目的固定模板：它是**排版**不是新判斷（同一個節點永遠得到同一句）。
RESEARCH_QUESTION_TEMPLATE = "誰供應 `{node}`？"

#: `degree=0` ＝這個節點連一條邊都沒有——它還沒接進 stack。下一步是**先確認它該掛在哪**，
#: 不是「去查誰供應它」（走圖第 7 型據此換句）。
#: ⚠ 它**不是分類**——不改變任何節點落在哪一桶。2026-09-10 逐節點查證過，🔴 裡的節點在 `source_ids`、
#: `abstraction_level`、ABOUT 文件數上完全同形，沒有可機械分辨的差異；在沒有事實支撐的地方切一刀，
#: 得到的是會誤報的分類（L16-4）。
ISOLATED_DEGREE = 0


def bucketize(rows: Iterable[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    """依 `classify()` 的三態＋概念節點分桶。順序固定，消費端不必自己排。"""

    buckets: dict[str, list[Mapping[str, Any]]] = {
        "research_gap": [], "modelling_gap": [], "covered": [], "concept": [],
    }
    for row in rows:
        buckets[row["status"]].append(row)
    return buckets


def split_research_gaps(
    rows: Iterable[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    """🔴 桶 → (真正該挖的子瓶頸, 抽取產生的產品名詞)。純前綴比對。"""

    real = [r for r in rows if not str(r["node"]).startswith(PRODUCT_NOISE_PREFIX)]
    noise = [r for r in rows if str(r["node"]).startswith(PRODUCT_NOISE_PREFIX)]
    return real, noise


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
                # 脈絡欄位，不參與分類；缺值時誠實留 None／0，不猜。
                "degree": int(record["degree"] or 0),
                "abstraction_level": record["abstraction_level"],
            }
        )
    return rows


if __name__ == "__main__":
    # ⚠ 2026-09-29（Phase 3 Step 3.1c）：CLI 入口退役——覆蓋缺口改由 `python -m query.graph_walk` 第 7／8 型承載
    # （沒人供應、建模待補；同一個掃描、同一份分桶，照抄不重算）。印退役訊息並 exit 2，而不是安靜 exit 0：
    # 安靜結束會被讀成「沒有缺口」（L13：成功與失敗不得同形）。
    import sys

    print("✗ `python -m query.coverage_gaps` 已於 2026-09-29 退役（Phase 3 Step 3.1c）："
          "改用 `python -m query.graph_walk`（第 7／8 型：沒人供應、建模待補）", file=sys.stderr)
    raise SystemExit(2)
