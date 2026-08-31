"""瓶頸鏈排序：在**已研究過的公司**中，排出誰最可能是真瓶頸。

設計依據 `docs/brainstorms/2026-08-18-alpha-live-user-sized-requirements.md` §8。

使用者的模型（2026-08-18）：

> CPO 是 AI SERVER 的瓶頸，InP 是 CPO 的瓶頸，瓶頸相連要能連到真的市場有在放 CapEx 的地方。
> 要是真的市場有在投資的點，不然一個沒人用的技術的瓶頸，好像也沒用。

因此每一列回答三件事：**卡在哪條邊、那條邊多難繞過、往上接到誰在花錢**。

## 三個刻意的設計限制

1. **不算加權綜合分數。** 綜合分數是未經量測的新機制（D6），且會把「證據強度」與
   「瓶頸強度」壓成一個數字（L12）。這裡只做**確定性排序**並攤開所有成分，
   排序鍵是 `(證據等級, substitutability, sole_source, qualification)`。

2. **先以 `(src, relation, dst)` 去重，每組取最高 confidence，不加總。**
   實測 `co:axt → mat:inp_substrate` 有 4 條 EdgeAssertion 來自 4 份文件；
   若數邊，分數就變成「我們讀了幾份文件」的函數——再 ingest 五份 InP 報導，
   分數就上升而世界沒有改變。`documents` 欄位保留該計數，但它只作**注意力**指標，
   **不參與排序**。

3. **證據等級是排名上限。** 只有供應商自評 sub=5 的邊，不得排在有客戶端印證的 sub=4
   之前。實測 58 條帶 `substitutability` 的邊有 50% 只有供應商自報 origin
   （`scripts/audit_sole_source_independence.py --all-bottleneck`）。

## 已知限制（隨輸出常駐，不得只寫在文件裡）

- `substitutability` 覆蓋率僅 22%（91/423 assertion）；排名必然偏向已被抽取過的邊。
- `structural_lead_time_weeks` 實質為空（17 筆有欄位、僅 1 個真值）。
  「難替代」與「換掉要多久」是兩件事，**本排名不含後者**。
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

# 向下（找瓶頸）的邊型：只有這些的 substitutability 有意義。
DOWNSTREAM_RELATIONS = ("depends_on", "supplies_to", "constrained_by")
# 向上（找需求端）的邊型：這些邊的 substitutability 恆為 None，本來就不該有。
UPSTREAM_RELATIONS = ("enables", "is_component_of")

# 進入排名的最低替代難度。3 以下不算瓶頸，只是普通供應關係。
MIN_SUBSTITUTABILITY = 4

# 需求錨點（封閉字彙，會隨圖成長而擴充——擴充改這裡，不要改演算法）。
#
# ⚠ 首版用「往上走最長路徑，端點即錨點」的啟發式，**產出是垃圾**：圖裡有環，
# 最長路徑會繞回目標本身（實測 co:lumentum 的鏈走成
# `… → tech:ai_compute_buildout → co:lumentum`，真正的需求端出現在中間），
# 而且端點常是 `tech:semicon_manuf_equipment` 這種上游設備，不是需求。
# **看起來很結構化、實際無意義的欄位比沒有這一欄危險**，所以改成明確列舉 ＋ 最短路徑。
#
# 判準（使用者 2026-08-18）：「要是真的市場有在投資的點，不然一個沒人用的技術的瓶頸，
# 好像也沒用。」所以錨點必須是**有人在花錢買的終端需求**，不是任何上游節點。
DEMAND_ANCHORS = frozenset(
    {
        "tech:ai_compute_buildout",
        "tech:ai_switch",
        "tech:scale_up_network",
        "tech:optical_scale_up",
    }
)

# 五級（2026-08-30，使用者核准 [270]）。設計動機：三級制**過度懲罰自報**——客戶端印證
# 常與重定價事件同日到達（COHR 實測 Shadow 42.76 → 印證日 68+），等印證＝系統性遲到；
# 而「已收預付款」「審計客戶%」這類自報的金流／審計事實難以偽造，不該與敘述性自報同級。
# `self_reported_costly` 用「出自 filing（審計／法律責任文件）」當確定性 proxy：
# filing 裡也有行銷語，但法律責任使其系統性更貴——proxy 的限制明講，不假裝是語意判斷。
# `counterparty_joint`：聯合公告的複合 origin（"IQE plc / Tower Semiconductor"）單一字串
# 解析必然失敗，先前整級掉到 needs_review——雙方具名的公告證據力僅次於純客戶端，修正之。
EVIDENCE_RANK = {
    "externally_corroborated": 4,
    "counterparty_joint": 3,
    "self_reported_costly": 2,
    "needs_review": 1,
    "self_reported": 0,
}
EVIDENCE_LABEL = {
    "externally_corroborated": "外部印證",
    "counterparty_joint": "雙方聯合",
    "self_reported_costly": "自報·filing",
    "needs_review": "待判定",
    "self_reported": "供應商自報",
}
QUALIFICATION_RANK = {"qualified": 3, "qualifying": 2, "designed_in": 2, "sampling": 1}


def parse_attributes(raw: Any) -> dict:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return {}
    return raw if isinstance(raw, dict) else {}


def is_entity_id(node_id: Any) -> bool:
    """真 Entity 的 id 是 `前綴:slug`。

    ⚠ 圖裡有 188 個 Claim 節點貼著 `:Entity` 標籤（id 形如 `<doc_id>_cl1`），
    任何 `MATCH (n:Entity)` 都會多撈到它們。真 Entity 有 223 個且 100% 有前綴，
    所以用前綴過濾是可靠的（2026-08-18 實測）。
    """
    return ":" in str(node_id or "")


def company_id_for_origin(origin: str | None, registry) -> str | None:
    """把 SourceDoc 的 `origin_entity`（人類公司名）解析成 `co:*`。

    ⚠ 解析失敗一律回 None，**不得當成「不同源」**——那會讓供應商自報悄悄通過檢查，
    正是 L8／L11 要防的 laundering。順序由嚴到寬，兩個以上候選就不猜（L15）。
    """
    if not origin:
        return None
    text = str(origin).strip()
    if not text:
        return None
    by_ticker = registry.company_id_for_ticker(text)
    if by_ticker:
        return by_ticker
    slug = "co:" + text.lower().replace(" ", "_").replace(".", "").replace(",", "")
    if registry.has_company(slug):
        return slug
    needle = text.casefold()
    hits = {
        c.company_id
        for c in registry.companies
        if needle == str(getattr(c, "name", "") or "").casefold()
        or needle in {str(a).casefold() for a in (getattr(c, "aliases", None) or ())}
    }
    return hits.pop() if len(hits) == 1 else None


def _origin_mentions(origin: str, registry) -> set[str]:
    """origin 字串中被具名的 registry 公司集合（word-boundary、名稱長度 ≥4 防誤中）。

    供聯合公告偵測用：複合 origin（"IQE plc / Tower Semiconductor (joint announcement)"）
    無法整串解析成單一公司，但其中的具名仍是確定性可比對的。
    """
    text = str(origin)
    hits: set[str] = set()
    for company in registry.companies:
        names = [str(getattr(company, "name", "") or "")]
        names += [str(a) for a in (getattr(company, "aliases", None) or ())]
        for name in names:
            if len(name) < 4:
                continue
            if re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.IGNORECASE):
                hits.add(company.company_id)
                break
    return hits


def classify_evidence(
    subject: str,
    origins: Iterable[str | None],
    registry,
    filing_origins: frozenset | set = frozenset(),
) -> str:
    """五分，取各 origin 所能支持的最高等級。

    `None` 同時可能是「真的第三方媒體」（schema §7 接受）與「沒解析出來的子公司／別名」
    （不接受）——兩者結論相反，不得壓成一個布林（L12）。解析失敗的 origin 再過一道
    聯合公告偵測（字串內具名 ≥2 家 registry 公司且含 subject 以外者）才落 needs_review。
    `filing_origins`：來自 source_type=='filing' 文件的 origin 集合（costly proxy）。
    """
    seen = {o for o in origins if o}
    resolved = {o: company_id_for_origin(o, registry) for o in seen}
    best = "self_reported"

    def _lift(level: str) -> None:
        nonlocal best
        if EVIDENCE_RANK[level] > EVIDENCE_RANK[best]:
            best = level

    for origin, cid in resolved.items():
        if cid and cid != subject:
            _lift("externally_corroborated")
        elif cid is None:
            mentions = _origin_mentions(origin, registry)
            if len(mentions) >= 2 and (mentions - {subject}):
                _lift("counterparty_joint")
            else:
                _lift("needs_review")
        else:  # cid == subject：自報
            if origin in filing_origins:
                _lift("self_reported_costly")
    return best


@dataclass
class CanonicalEdge:
    src: str
    relation: str
    dst: str
    substitutability: int | None = None
    sole_source: bool | None = None
    qualification_status: str | None = None
    ramp_execution: int | None = None
    lead_time_weeks: int | None = None
    confidence: float = 0.0
    documents: int = 0
    origins: set = field(default_factory=set)
    filing_origins: set = field(default_factory=set)
    evidence: str = "self_reported"


def collapse_assertions(rows: Iterable[Mapping[str, Any]]) -> dict[tuple, CanonicalEdge]:
    """把 EdgeAssertion 收斂成 canonical edge。

    同一條 (src, relation, dst) 可能有多份文件各講一次。**取最高 confidence 那一份的
    屬性值，不加總、不平均**——加總會讓分數變成 ingestion 量的函數；平均會讓一份低品質
    文件稀釋一份一手 filing。`documents` 記下份數但不參與排序。
    """
    grouped: dict[tuple, CanonicalEdge] = {}
    # ⚠ **逐屬性**記最佳 confidence，不是整條邊記一個。首版對整條邊只取
    # 「confidence 最高那份 assertion」的全部屬性，於是若該份剛好沒填
    # `substitutability`，整條邊的值就被丟掉——實測 co:axt 因此整個從排名消失，
    # 覆蓋率也從 22%（assertion 層）假掉到 16%（edge 層）。
    # 正確語意是「對這個屬性發言過的文件裡，最可信的那一份怎麼說」。
    attr_conf: dict[tuple, dict[str, float]] = defaultdict(dict)

    def _take(key: tuple, edge: CanonicalEdge, name: str, value: Any, conf: float) -> None:
        if value is None:
            return
        if conf <= attr_conf[key].get(name, -1.0):
            return
        attr_conf[key][name] = conf
        setattr(edge, name, value)

    for row in rows:
        src, rel, dst = row.get("src"), row.get("relation"), row.get("dst")
        if not (is_entity_id(src) and is_entity_id(dst)):
            continue
        key = (str(src), str(rel), str(dst))
        attrs = parse_attributes(row.get("attributes"))
        conf = float(row.get("confidence") or 0.0)
        edge = grouped.get(key)
        if edge is None:
            edge = CanonicalEdge(src=str(src), relation=str(rel), dst=str(dst))
            grouped[key] = edge
        edge.documents += 1
        edge.confidence = max(edge.confidence, conf)
        if row.get("origin"):
            edge.origins.add(str(row["origin"]))
            if str(row.get("source_type") or "") == "filing":
                edge.filing_origins.add(str(row["origin"]))

        sub = attrs.get("substitutability")
        _take(key, edge, "substitutability",
              int(sub) if isinstance(sub, (int, float)) and not isinstance(sub, bool) else None,
              conf)
        ramp = attrs.get("ramp_execution")
        _take(key, edge, "ramp_execution",
              int(ramp) if isinstance(ramp, (int, float)) and not isinstance(ramp, bool) else None,
              conf)
        lt = attrs.get("structural_lead_time_weeks")
        _take(key, edge, "lead_time_weeks",
              int(lt) if isinstance(lt, (int, float)) and not isinstance(lt, bool) else None,
              conf)
        _take(key, edge, "qualification_status", attrs.get("qualification_status"), conf)
        if attrs.get("sole_source") is not None:
            _take(key, edge, "sole_source", bool(attrs["sole_source"]), conf)
    return grouped


def build_upward_index(edges: Iterable[CanonicalEdge]) -> dict[str, set[str]]:
    """node → 誰需要它（需求方向）。

    向上與向下是不同邊型，這個不對稱是刻意的、不需要改 schema：
    `A depends_on B` ⇒ B 被 A 需要；`A is_component_of B` ⇒ A 被 B 需要；
    `A enables B` ⇒ A 被 B 需要。向上的邊沒有也不該有 `substitutability`。
    """
    upward: dict[str, set[str]] = defaultdict(set)
    for e in edges:
        if e.relation == "depends_on":
            # A depends_on B ⇒ B 被 A 需要
            upward[e.dst].add(e.src)
        elif e.relation == "supplies_to":
            # A supplies_to B ⇒ A 被 B 需要。
            # ⚠ 這條首版漏了，於是任何「瓶頸目標是一家公司」的列都走不到需求錨點
            # （實測 co:axt supplies_to co:coherent 顯示「無錨點」，但 Coherent 供 CPO、
            # CPO 供 ai_switch，鏈其實是通的）。`supplies_to` 同時出現在向下（帶
            # substitutability）與向上（需求傳遞）兩個索引裡是正確的——它本來就是
            # 一條有方向的供需邊，兩邊問的問題不同。
            upward[e.src].add(e.dst)
        elif e.relation in UPSTREAM_RELATIONS:
            upward[e.src].add(e.dst)
    return upward


def demand_chain(
    target: str,
    upward: Mapping[str, set[str]],
    anchors: Iterable[str] = DEMAND_ANCHORS,
    max_depth: int = 8,
) -> list[str] | None:
    """從瓶頸標的往上走到**明確登記的需求錨點**，回傳最短的一條鏈；走不到回 None。

    用 BFS 取最短路徑而非 DFS 取最長：最短路徑是「這個瓶頸離錢最近有幾層」，
    可解釋；最長路徑在有環的圖上只是亂走（首版的教訓，見 DEMAND_ANCHORS 註解）。

    **走不到就是走不到，回 None。** 依使用者判準，連不到有人花錢的地方的瓶頸，
    不該被當成投資標的看待——這裡不得用「最接近的節點」充數。
    """
    anchor_set = set(anchors)
    if target in anchor_set:
        return [target]
    queue: list[tuple[str, list[str]]] = [(target, [target])]
    visited = {target}
    while queue:
        node, path = queue.pop(0)
        if len(path) > max_depth:
            continue
        for parent in sorted(upward.get(node, ())):
            if parent in visited:
                continue
            visited.add(parent)
            new_path = path + [parent]
            if parent in anchor_set:
                return list(reversed(new_path))
            queue.append((parent, new_path))
    return None


def rank_bottlenecks(
    rows: Iterable[Mapping[str, Any]],
    registry,
    *,
    min_substitutability: int = MIN_SUBSTITUTABILITY,
) -> dict[str, Any]:
    """輸出「公司 × 瓶頸邊」的排序，附鏈路、需求錨點與證據等級。"""
    rows = list(rows)
    canonical = collapse_assertions(rows)
    edges = list(canonical.values())
    for edge in edges:
        edge.evidence = classify_evidence(
            edge.src, edge.origins, registry, filing_origins=edge.filing_origins
        )

    upward = build_upward_index(edges)
    scored = []
    for edge in edges:
        if edge.relation not in DOWNSTREAM_RELATIONS:
            continue
        if not edge.src.startswith("co:"):
            continue
        if (edge.substitutability or 0) < min_substitutability:
            continue
        # ⚠ 從**公司**往上走，不是從瓶頸節點。這一列問的是「這家公司的產出有沒有人
        # 在花錢買」，不是「這個材料有沒有人要」。首版從 `edge.dst` 走，於是
        # co:lumentum 那列的鏈路繞經 co:coherent——對 `mat:inp_substrate` 而言正確，
        # 但那不是這一列在問的問題。
        chain = demand_chain(edge.src, upward)
        scored.append(
            {
                "company_id": edge.src,
                "ticker": registry.research_ticker(edge.src),
                "relation": edge.relation,
                "bottleneck": edge.dst,
                "substitutability": edge.substitutability,
                "sole_source": bool(edge.sole_source),
                "qualification_status": edge.qualification_status,
                "ramp_execution": edge.ramp_execution,
                "lead_time_weeks": edge.lead_time_weeks,
                "evidence": edge.evidence,
                "confidence": edge.confidence,
                "documents": edge.documents,
                "chain": chain,
                "demand_anchor": chain[0] if chain else None,
                "demand_hops": (len(chain) - 1) if chain else None,
            }
        )

    # 排序鍵刻意有明確的優先序，不是加權綜合分數（那會是未經量測的新機制，D6）。
    # 需求錨點可達性排最前：依使用者判準，連不到有人花錢的地方的瓶頸沒有投資意義。
    #
    # ⚠ evidence 排在 substitutability 之前是**刻意的**，但只對「現在能投什麼」成立：
    # 證據弱的邊不能拿來下注。代價是這份排序同時被「我們挖得多深」影響——`evidence`
    # 的三級（self_reported → needs_review → externally_corroborated）中，最高級必須
    # 靠研究去找到客戶端或第三方文件才拿得到，預設每條邊都是 self_reported。
    # 2026-08-21 使用者指出：「研究筆數多 → 證據強，但不代表瓶頸性強」——屬實。
    # 因此另出 `structural_rows`，見下。
    scored.sort(
        key=lambda r: (
            1 if r["demand_anchor"] else 0,
            EVIDENCE_RANK.get(r["evidence"], 0),
            r["substitutability"] or 0,
            1 if r["sole_source"] else 0,
            QUALIFICATION_RANK.get(str(r["qualification_status"]), 0),
            -(r["demand_hops"] if r["demand_hops"] is not None else 99),
        ),
        reverse=True,
    )

    # 純結構排序：只看瓶頸本身有多卡，**完全不看證據等級**。
    # 兩份排序回答不同問題，不可互換：
    #   rows            → 「現在能投什麼」（證據夠強才可行動）
    #   structural_rows → 「該去補誰的證據」（結構很卡但證據沒跟上的，是研究最高 ROI）
    # 實測差異（2026-08-21）：現行排序第 1 是 COHR→NVIDIA，純結構第 1 是 AVGO→CPO
    # ——同為 sub=5／sole_source，但 AVGO 距需求端只有 1 跳，它排在後面純粹因為
    # evidence 還是 needs_review。另有 LITE→UHP laser（sub=5、sole_source）因
    # self_reported 幾乎在現行排序中看不到。
    structural = sorted(
        scored,
        key=lambda r: (
            1 if r["demand_anchor"] else 0,
            r["substitutability"] or 0,
            1 if r["sole_source"] else 0,
            -(r["demand_hops"] if r["demand_hops"] is not None else 99),
            QUALIFICATION_RANK.get(str(r["qualification_status"]), 0),
        ),
        reverse=True,
    )

    with_sub = [e for e in edges if e.substitutability is not None]
    return {
        "rows": scored,
        "structural_rows": structural,
        "coverage": {
            "assertions": len(rows),
            "canonical_edges": len(canonical),
            "edges_with_substitutability": len(with_sub),
            "substitutability_coverage": (
                len(with_sub) / len(canonical) if canonical else 0.0
            ),
            "edges_with_lead_time": sum(
                1 for e in edges if e.lead_time_weeks is not None
            ),
            "self_reported_share": (
                sum(1 for e in with_sub if e.evidence == "self_reported") / len(with_sub)
                if with_sub
                else 0.0
            ),
            "duplicate_collapse": len(rows) - len(canonical),
        },
    }


def fetch_assertions(session) -> list[dict[str, Any]]:
    return session.run(
        """
        MATCH (e:EdgeAssertion)
        OPTIONAL MATCH (d:SourceDoc {id: e.source_doc_id})
        RETURN e.src_id AS src, e.relation AS relation, e.dst_id AS dst,
               e.attributes AS attributes, e.confidence AS confidence,
               d.origin_entity AS origin, d.source_type AS source_type
        """
    ).data()


def render_markdown(result: Mapping[str, Any]) -> str:
    cov = result["coverage"]
    out = ["# 瓶頸鏈排序（在已研究過的公司中排序，不是發現新標的）\n"]
    out.append(
        f"- EdgeAssertion {cov['assertions']} → canonical edge {cov['canonical_edges']}"
        f"（去重收斂 {cov['duplicate_collapse']} 筆）"
    )
    out.append(
        f"- `substitutability` 覆蓋 {cov['edges_with_substitutability']}"
        f"/{cov['canonical_edges']}（{cov['substitutability_coverage']:.0%}）"
        f"｜其中僅供應商自報 {cov['self_reported_share']:.0%}"
    )
    out.append(f"- `structural_lead_time_weeks` 有值：{cov['edges_with_lead_time']} 條")
    out.append(
        "\n🔴 **已知限制，解讀前必讀：**\n"
        f"1. 覆蓋率 {cov['substitutability_coverage']:.0%}——排名必然偏向已被抽取過的邊，"
        "沒填的邊是隱形的。\n"
        "2. **本排名不含 lead time**（換掉一個供應商要多久）。「難替代」與「換掉要多久」"
        "是兩件事：第二供應商若半年可合格，sub=5 也很脆。\n"
        "3. `documents` 是注意力指標，**不參與排序**——否則分數會變成「我們讀了幾份文件」。\n"
    )
    if not result["rows"]:
        out.append("\n（無符合門檻的瓶頸邊）")
        return "\n".join(out)

    out.append("\n| # | 標的 | 卡在哪 | 替代難度 | 證據 | 合格狀態 | 文件 | 需求錨點 |")
    out.append("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(result["rows"], 1):
        ticker = r["ticker"] or "—"
        sole = "｜sole_source" if r["sole_source"] else ""
        out.append(
            f"| {i} | {r['company_id']}（{ticker}） | {r['relation']} → `{r['bottleneck']}` "
            f"| {r['substitutability']}/5{sole} | {EVIDENCE_LABEL[r['evidence']]} "
            f"| {r['qualification_status'] or '—'} | {r['documents']} "
            f"| {r['demand_anchor'] or '🔴 無'} |"
        )

    structural = result.get("structural_rows") or []
    if structural:
        out.append(
            "\n## 純結構排序（只看多卡，**不看證據**）\n\n"
            "> 上表回答「**現在能投什麼**」——證據不夠強的邊不能拿來下注，所以 evidence "
            "排在 substitutability 之前。代價是它同時被「我們挖得多深」影響：`evidence` "
            "的最高級必須靠研究找到客戶端或第三方文件才拿得到，預設每條邊都是 "
            "`self_reported`。\n>\n"
            "> 本表回答「**該去補誰的證據**」——結構很卡但證據沒跟上的邊，是研究投入的"
            "最高 ROI。兩份排序用途不同，不可互換。"
        )
        out.append("\n| # | 標的 | 卡在哪 | 替代難度 | 距需求端 | 目前證據 | 落差 |")
        out.append("|---|---|---|---|---|---|---|")
        rank_in_actionable = {
            id(r): i for i, r in enumerate(result["rows"], 1)
        }
        for i, r in enumerate(structural[:10], 1):
            ticker = r["ticker"] or "—"
            sole = "｜sole_source" if r["sole_source"] else ""
            hops = r["demand_hops"] if r["demand_hops"] is not None else "—"
            actionable_rank = rank_in_actionable.get(id(r))
            gap = ""
            if actionable_rank and actionable_rank - i >= 2:
                gap = f"⬆ 可行動排序第 {actionable_rank}——補證據可翻上來"
            out.append(
                f"| {i} | {r['company_id']}（{ticker}） | {r['relation']} → "
                f"`{r['bottleneck']}` | {r['substitutability']}/5{sole} | {hops} 跳 "
                f"| {EVIDENCE_LABEL[r['evidence']]} | {gap} |"
            )
        out.append(
            "\n⚠ **本表不含「瓶頸業務占該公司多少」**。同為 `sub=5`，大型多角化公司的"
            "單一瓶頸邊對其整體營收影響可能很小（研究它接近研究 beta），小型專業廠則"
            "接近純曝險。判斷投資意義時必須另看市值、營收結構與分析師覆蓋度——"
            "那些資料在 Engine C，不在本排序內。"
        )

    out.append("\n## 需求鏈（誰在花錢 → 這家公司）\n")
    for i, r in enumerate(result["rows"], 1):
        out.append(
            f"{i}. **{r['company_id']}** {r['relation']} `{r['bottleneck']}`"
        )
        if r["chain"]:
            out.append(f"   {' → '.join(r['chain'])}　（距需求端 {r['demand_hops']} 跳）")
        else:
            out.append(
                "   🔴 **走不到任何已登記的需求錨點**——可能是鏈路真的斷了，"
                "也可能是 `DEMAND_ANCHORS` 還沒登記到這個領域。不得當作已錨定使用。"
            )
    return "\n".join(out)


def load_sector_map(path: str = "config/sector_anchors.json") -> dict[str, Any]:
    """錨→產業對照（SSOT：config/sector_anchors.json）。讀不到時 fail-soft 空表——
    所有錨落到自成一組，分組仍可用只是粗。"""

    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"sectors": {}, "correlation_notes": []}


def group_rows_by_sector(
    result: Mapping[str, Any], sector_map: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """把 rank_bottlenecks 的兩份排序依 demand anchor 聚成產業組（A 案）。

    分組解決**可視性**不解決可比性：各組內維持原有排序，組與組之間的分數
    不可比較（證據密度不同）。未映射的錨自成一組（不靜默丟失）；無錨列
    「🔴 無需求錨」——那是該補研究的訊號，不是雜訊。
    """

    sector_map = sector_map or load_sector_map()
    anchor_to_sector: dict[str, str] = {}
    for sector, anchors in (sector_map.get("sectors") or {}).items():
        for anchor in anchors:
            anchor_to_sector[str(anchor)] = str(sector)

    def bucket(row: Mapping[str, Any]) -> str:
        anchor = row.get("demand_anchor")
        if not anchor:
            return "🔴 無需求錨"
        return anchor_to_sector.get(str(anchor), f"（未映射錨）{anchor}")

    grouped: dict[str, dict[str, list]] = {}
    for key in ("rows", "structural_rows"):
        for row in result.get(key) or ():
            grouped.setdefault(bucket(row), {"rows": [], "structural_rows": []})[
                key
            ].append(dict(row))
    return {
        "sectors": grouped,
        "correlation_notes": list(sector_map.get("correlation_notes") or ()),
    }


def render_by_sector(result: Mapping[str, Any], *, top_n: int = 3) -> str:
    """分組呈現：每產業各自 top-N（可行動）＋純結構第一名。"""

    grouped = group_rows_by_sector(result)
    lines = ["# 瓶頸排序（產業別分組——解決可視性，分數不可跨組比較）", ""]
    for note in grouped["correlation_notes"]:
        lines.append(f"> ⚠ {note}")
    if grouped["correlation_notes"]:
        lines.append("")
    # 空產業組要現形（prompt 契約）：configured 但零列的組是 sub 覆蓋缺口，不是省略對象。
    configured = list((load_sector_map().get("sectors") or {}).keys())
    empty = [s for s in configured if s not in grouped["sectors"]]
    if empty:
        lines.append(
            "🔴 **空產業組（sub 覆蓋未及，研究缺口）**：" + "、".join(empty)
        )
        lines.append("")
    for sector, buckets in sorted(
        grouped["sectors"].items(), key=lambda kv: -len(kv[1]["rows"])
    ):
        lines.append(f"## {sector}（可行動 {len(buckets['rows'])} 條）")
        for row in buckets["rows"][:top_n]:
            sole = "｜sole_source" if row.get("sole_source") else ""
            lines.append(
                f"- {row['company_id']}（{row.get('ticker') or '—'}）"
                f" {row['relation']} → `{row['bottleneck']}`"
                f"｜sub {row.get('substitutability')}{sole}"
                f"｜{row.get('evidence')}"
            )
        structural = buckets["structural_rows"]
        if structural:
            top = structural[0]
            lines.append(
                f"  ↳ 純結構第一（該去補證據的）：{top['company_id']}"
                f" → `{top['bottleneck']}`"
            )
        lines.append("")
    return "\n".join(lines)


def render_what_if(
    baseline: Mapping[str, Any], overlaid: Mapping[str, Any],
    hypothesis_rows: list, *, top_n: int = 10,
) -> str:
    """what-if 排序 diff：**只比純結構排序**（structural_rows，evidence-blind）。

    「若為真」問的是陳述的真值，不是證據狀態——所以用不看證據的那份排序。
    可行動排序刻意不比：假設永不參與 evidence 分級，讓它進可行動排序等於
    讓未驗證陳述假裝有證據（硬邊界）。輸出必標「若為真」。
    """

    def positions(result: Mapping[str, Any]) -> dict[tuple, int]:
        return {
            (r["company_id"], r["bottleneck"]): i + 1
            for i, r in enumerate(result.get("structural_rows") or ())
        }

    before, after = positions(baseline), positions(overlaid)
    lines = [
        "# What-if 排序 diff（純結構、若為真——不是證據判斷，不進任何預設輸出）",
        "",
        f"疊加假設邊 {len(hypothesis_rows)} 條（origin 固定 `(hypothesis)`）。",
        "",
    ]
    moved = []
    for key, pos_after in list(after.items())[:max(top_n * 3, 30)]:
        pos_before = before.get(key)
        if pos_before is None:
            moved.append((key, "（新進結構排序）", pos_after))
        elif pos_before != pos_after:
            moved.append((key, f"#{pos_before}→", pos_after))
    moved.sort(key=lambda item: item[2])
    if not moved:
        lines.append("**結構排序無變化**——若為真也不改變任何相對位置；安心 park，不值得花力氣追平行證據。")
    else:
        lines.append("| 標的→瓶頸 | 變化 | 疊加後名次 |")
        lines.append("|---|---|---|")
        for (company, bottleneck), delta, pos in moved[:top_n]:
            lines.append(f"| {company} → `{bottleneck}` | {delta} | #{pos} |")
        lines.append("")
        lines.append("名次有動＝值得投入平行驗證（B1 免費一手／B2 fact-check trigger）；入圖仍走原檔 admission。")
    return "\n".join(lines)


def main() -> int:
    import argparse
    import sys
    import warnings
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    warnings.filterwarnings("ignore")
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    from identity.registry import get_registry

    parser = argparse.ArgumentParser(description="瓶頸鏈排序")
    parser.add_argument(
        "--by-sector", action="store_true",
        help="產業別分組呈現（demand anchor 聚類；預設輸出不受影響）",
    )
    parser.add_argument(
        "--what-if", metavar="HYP_ID", nargs="*", default=None,
        help="疊加截圖假設層（engine_b/hypotheses.py）輸出純結構排序 diff；"
             "不帶 id＝全部 active 假設。永不影響預設輸出。",
    )
    parser.add_argument("--top-n", type=int, default=3)
    args = parser.parse_args()

    load_dotenv()
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        print("請設 NEO4J_PASSWORD", file=sys.stderr)
        return 2
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )
    try:
        with driver.session() as session:
            rows = fetch_assertions(session)
    finally:
        driver.close()
    result = rank_bottlenecks(rows, get_registry())
    if args.what_if is not None:
        from engine_b.hypotheses import load_store, overlay_assertions

        hyp_rows = overlay_assertions(load_store(), hypothesis_ids=args.what_if or None)
        if not hyp_rows:
            print("（沒有 active 假設可疊加；先用 python -m engine_b.hypotheses add 建立）")
            return 0
        overlaid = rank_bottlenecks(list(rows) + hyp_rows, get_registry())
        print(render_what_if(result, overlaid, hyp_rows, top_n=max(args.top_n, 10)))
    elif args.by_sector:
        print(render_by_sector(result, top_n=args.top_n))
    else:
        print(render_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
