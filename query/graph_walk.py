"""`python -m query.graph_walk` — 走圖：每天從圖上報出「該去研究的洞」。

## 為什麼需要它

讀圖（`query.structure` ＋ 讀圖 ledger）是新中心（決定紀錄 G2、G5），但它只回答「這一層我讀懂了沒」；
**「下一個該讀哪一層、該補哪一格」沒有人問**——先前散在 coverage 頁（沒人供應、建模待補）、重複節點頁、
讀圖 artifact 的「該重讀」三處，而且沒有一處會說「這一層繞不過、只有兩三家，還沒人讀過」。
服務的目標是 `AGENTS.md` 那一句：**某個集中需求把量灌進一層薄的供應商**——所以第一型就是
「硬需求下的薄層，還沒有人讀」。

## 它明確不做的事（違反即 NO_GO，plan 2026-09-25-001 §0 第 7 條）

- **不排序、不打分、不 gate。** 九型各自回「命中／母體」，**沒有跨型別合成的任何數字、沒有 top-N、
  沒有「最該研究的洞」**。型別順序（`QUESTION_TYPES`）是閱讀順序，不是價值判斷；型別內按節點 id
  （第 5 型按 lead 首見時間，舊的先）——索引，不是名次。
- **零 LLM、零推理。** 每一型都是對圖（或 leads、讀圖 ledger）的確定性查詢。
- **不寫任何 authority。** 純讀；APP artifact（`graph_walk` kind）是可重建的 derived cache。
- 走圖第 1–3 型用 sub≥4 與「1–3 家」定義**問句母體**——它決定「要不要問這一題」，不決定任何一檔的
  去留、排名或尺寸；「只有 1 家」量到的是我們讀了誰的文件（決定紀錄 §1.1），不是瓶頸性證據。

## 母體規則（L14-4：恆亮＝零鑑別力）

每型輸出 `hit_n／scope_n`。母體 ≥10 的型別命中率 ≥50% 就是恆亮——要收窄母體（不是刪型別），
收窄後仍 ≥50% 交給使用者（plan §7）。母體 <10 的型別只印不判。

## 分層

本模組的函式是純的（輸入由呼叫端給）；唯一的組裝點是 `collect()`：它讀圖、讀 leads，並向
`alpha.providers.structure_readings.reading_status_rows` 取第 4 型的讀圖狀態——**那是讀圖 artifact
同一份算法**，不在這裡重算（L16）。`query/` 其餘模組不 import `alpha/`（`tests/test_layer_separation.py`）。

用法：

    python -m query.graph_walk            # markdown
    python -m query.graph_walk --json     # 給 APP／稽核用
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from query.bottleneck import (  # noqa: E402
    EVIDENCE_LABEL, CanonicalEdge, build_upward_index, demand_chain,
)
from query.structure import build_structure  # noqa: E402

#: 需求側「繞不過」的門檻——與讀圖 plan §0.2 的「需求側繞不過的節點」同一個定義。
#: ⚠ 它是**問句母體**的定義，不是瓶頸判準（見檔頭）。
DEMAND_UNAVOIDABLE_MIN_SUB = 4
#: 「薄層」＝供給側 1–3 家（第 1 型）。0 家是第 7 型的事，不在這裡重複問。
THIN_LAYER_MAX_SUPPLIERS = 3
#: 外部印證的證據等級（`query.bottleneck.classify_evidence` 的字彙；不在這裡重判）。
CORROBORATED_EVIDENCE = frozenset({"externally_corroborated", "counterparty_joint"})
#: 「往下供貨」的對象前綴（第 6 型母體）。
DOWNSTREAM_PREFIXES = ("tech:", "mat:", "prod:")
#: 母體多大才判恆亮（plan §7「母體規則」）。
SCOPE_JUDGE_MIN = 10
#: 命中率達此即恆亮。
ALWAYS_ON_RATE = 0.5
#: lead 在這兩個狀態才算「正在研究的線索」（第 5 型母體；與佇列段 `triaged_go_leads` 同一組）。
ACTIVE_LEAD_STATUSES = frozenset({"triaged_go", "researching"})


@dataclass(frozen=True)
class QuestionType:
    key: str
    short: str
    #: 印給人看的問句模板（型別層級的說明；每筆命中另有自己的一句）。
    question: str
    scope_rule: str
    hit_rule: str
    next_action: str


#: **封閉字彙，順序＝閱讀順序，不是價值判斷。** 加一型要先答：它指得出哪一個研究動作、
#: 母體多大、實測命中率多少（L14-4）。
QUESTION_TYPES: tuple[QuestionType, ...] = (
    QuestionType(
        "thin_layer_unread", "薄層沒人讀",
        "`{node}` 繞不過、供應商只有 {n} 家，還沒有人讀過",
        "需求側至少一條 sub≥4 的節點", "供給側 1–3 家，且沒有任何單位的現行讀圖",
        "python -m query.structure <node> --quotes → 寫讀圖（alpha structure-reading <node> --add）"),
    QuestionType(
        "sole_supplier_self_reported", "獨家且自報",
        "`{node}` 繞不過、圖上只有 `{co}` 一家，證據只有它自己說",
        "需求側至少一條 sub≥4 的節點", "供給側恰 1 家，且那條邊的證據不是外部印證／雙方聯合",
        "從客戶端或第三方找第二家或印證（source-trace）"),
    QuestionType(
        "supply_unfilled", "供給側未填",
        "`{node}` 繞不過，但 {n} 家供應商的可替代性都沒填——判不出護城河還是量",
        "需求側至少一條 sub≥4、且供給側 ≥1 家的節點", "供給側每一條邊的 substitutability 都沒填",
        "補供給側 substitutability（研究，入圖走 pq2）"),
    QuestionType(
        "reading_stale", "讀圖該重讀",
        "`{node}`（{unit}）的讀圖跟圖不一致或過期：{summary}",
        "現行讀圖（節點, 單位）", "圖那一側判 stale 或已過期（stale_low 不算）",
        "python -m alpha structure-reading <node> --unit <unit> --check → 重讀"),
    QuestionType(
        "lead_not_in_graph", "lead 點名不在圖",
        "lead `{lead_id}` 點名 {companies}，圖上沒有",
        "triaged_go／researching 且有具名公司的 lead", "至少一家 registry 解析得到、但圖上沒有節點的公司",
        "onboard 評估（company-onboard）"),
    QuestionType(
        "supplier_no_anchor", "供貨走不到錨",
        "`{co}` 有往下供貨，但走不到任何需求錨",
        "有往下 supplies_to（tech／mat／prod）的公司", "從這家公司往上走不到任何已登記的需求錨",
        "補需求鏈，或確認它不屬本題材"),
    QuestionType(
        "no_supplier", "沒人供應",
        "誰供應 `{node}`？（圖上 0 家）",
        "非概念的 tech／mat 節點（coverage 掃描）", "沒有任何公司直接或間接連到它（coverage 🔴；prod: 抽取副產品只計數）",
        "找供應商；孤立節點先確認它該掛在 stack 哪一層"),
    QuestionType(
        "modelling_gap", "建模待補",
        "`{node}` 有研究但邊沒接到它",
        "非概念的 tech／mat／prod 節點（coverage 掃描）", "只有公司經 prod:／公司對公司間接相連（coverage 🟡）",
        "補邊（入圖走 pq2），不是重新研究"),
    QuestionType(
        "duplicate_node", "重複節點",
        "`{a}` 與 `{b}` 可能是同一個節點",
        "掃描的非公司實體節點（duplicate_nodes）", "registry 從沒提過的候選對（每對算一筆）",
        "判定同一個 → pq2 ra_admission"),
)
QUESTION_TYPE_KEYS: tuple[str, ...] = tuple(q.key for q in QUESTION_TYPES)
QUESTION_BY_KEY: dict[str, QuestionType] = {q.key: q for q in QUESTION_TYPES}

TITLE = "走圖：該去研究的洞"

THIS_IS_NOT: tuple[str, ...] = (
    "不是排序：沒有跨型別合成的數字、沒有 top-N、沒有「最該研究的洞」。型別順序是閱讀順序；型別內按節點 id（lead 按首見時間）。",
    "不是結論：每一筆是一個**問句**，指得出下一個研究動作；答案要由研究（互動 session）去找。",
    "不是 filter：「需求側 sub≥4」「1–3 家」定義的是要不要問這一題，不決定任何一檔的去留、排名或尺寸。",
    "「只有 1 家」量到的是我們讀了誰的文件，不是瓶頸性證據（決定紀錄 §1.1）。",
    "只能從**圖裡既有的節點**往回看；圖裡沒有的層要由上而下拆解一個真實系統（system-decompose），選題由使用者決定。",
    "本 APP 不重算：每一格都是 materialize 當下 `python -m query.graph_walk` 的輸出照抄。",
)


# ---------------------------------------------------------------------------
# 各型（純函式）
# ---------------------------------------------------------------------------

def _layer_nodes(edges: Sequence[CanonicalEdge]) -> list[str]:
    return sorted({n for e in edges for n in (e.src, e.dst) if n.startswith(DOWNSTREAM_PREFIXES)})


def layer_questions(edges: Sequence[CanonicalEdge], *,
                    read_nodes: Iterable[str]) -> dict[str, dict[str, Any]]:
    """第 1–3 型：需求側繞不過的節點，供給側長什麼樣。**邊一次載入、每個節點各建一次視角。**"""
    read = set(read_nodes)
    thin: list[dict[str, Any]] = []
    sole: list[dict[str, Any]] = []
    unfilled: list[dict[str, Any]] = []
    scope_unavoidable = 0
    scope_with_supply = 0
    for node in _layer_nodes(edges):
        view = build_structure(node, edges)
        hard = [e for e in view.angles.get("demand_side", ())
                if e.substitutability is not None and e.substitutability >= DEMAND_UNAVOIDABLE_MIN_SUB]
        if not hard:
            continue
        scope_unavoidable += 1
        supply = view.angles.get("supply_side", [])
        suppliers = sorted({e.src for e in supply})
        demand = [f"{e.src} {e.relation} {e.dst}（sub {e.substitutability}）" for e in hard]
        if 1 <= len(suppliers) <= THIN_LAYER_MAX_SUPPLIERS and node not in read:
            thin.append({"subject": node, "suppliers": suppliers, "demand": demand,
                         "text": QUESTION_BY_KEY["thin_layer_unread"].question.format(node=node, n=len(suppliers))})
        if len(suppliers) == 1:
            evidence = {e.evidence for e in supply}
            if not evidence & CORROBORATED_EVIDENCE:
                co = suppliers[0]
                labels = "／".join(sorted(EVIDENCE_LABEL.get(str(v), str(v)) for v in evidence))
                sole.append({"subject": node, "supplier": co, "evidence": sorted(str(v) for v in evidence),
                             "evidence_label": labels, "demand": demand,
                             "text": QUESTION_BY_KEY["sole_supplier_self_reported"].question.format(node=node, co=co)})
        if suppliers:
            scope_with_supply += 1
            if all(e.substitutability is None for e in supply):
                unfilled.append({"subject": node, "suppliers": suppliers, "demand": demand,
                                 "text": QUESTION_BY_KEY["supply_unfilled"].question.format(
                                     node=node, n=len(suppliers))})
    return {
        "thin_layer_unread": {"hits": thin, "scope_n": scope_unavoidable},
        "sole_supplier_self_reported": {"hits": sole, "scope_n": scope_unavoidable},
        "supply_unfilled": {"hits": unfilled, "scope_n": scope_with_supply},
    }


def reading_stale(reading_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """第 4 型：現行讀圖裡，圖那一側判該重讀的。`reading_rows` 由讀圖 provider 給（同一份算法）。

    ⚠ 只看 `needs_reread_by_graph`：watch 那一側（客戶出新文件、反證被判觸及）是佇列段
    `fired_reading_reread` 的事，在這裡再算一次就是同一件事兩個計數器。
    """
    current = [r for r in reading_rows if r.get("reading_id")]
    hits = []
    for row in sorted(current, key=lambda r: (str(r.get("node")), str(r.get("unit")))):
        if not row.get("needs_reread_by_graph"):
            continue
        summary = str(row.get("reason") or row.get("status") or "")
        hits.append({"subject": row["node"], "unit": row.get("unit"), "status": row.get("status"),
                     "reading_id": row.get("reading_id"), "summary": summary,
                     "text": QUESTION_BY_KEY["reading_stale"].question.format(
                         node=row["node"], unit=row.get("unit"), summary=summary)})
    # 撤回到沒有現行的那幾列不是母體（沒有讀圖可以過期），但要現形（INV-3）。
    withdrawn = sorted(f"{r.get('node')}（{r.get('unit') or '全部單位'}）" for r in reading_rows if not r.get("reading_id"))
    return {"hits": hits, "scope_n": len(current), "extra": {"withdrawn": withdrawn}}


def lead_not_in_graph(leads: Mapping[str, Mapping[str, Any]] | Iterable[Mapping[str, Any]], *,
                      graph_nodes: Iterable[str], registry: Any) -> dict[str, Any]:
    """第 5 型：正在研究的 lead 點名了圖上沒有的公司。

    ⚠ **「ID 沒解析對」與「圖中真無此公司」分開計**（INV-1）：registry 解析不到的名字不算命中，
    但計數與名字另外列出（INV-3：不得靜默丟棄）。
    """
    graph = set(graph_nodes)
    rows = leads.values() if isinstance(leads, Mapping) else leads
    scope: list[Mapping[str, Any]] = []
    for lead in rows:
        if str(lead.get("status") or "") not in ACTIVE_LEAD_STATUSES:
            continue
        ids = list((lead.get("entities") or {}).get("company_ids") or ())
        if ids:
            scope.append(lead)
    hits: list[dict[str, Any]] = []
    unresolved: set[str] = set()
    no_first_seen: list[str] = []
    for lead in scope:
        entities = lead.get("entities") or {}
        missing = []
        for cid in sorted(set(entities.get("company_ids") or ())):
            if not registry.has_company(cid):
                unresolved.add(cid)
            elif cid not in graph:
                missing.append(cid)
        for ticker in entities.get("tickers") or ():
            if registry.company_id_for_ticker(str(ticker)) is None:
                unresolved.add(str(ticker))
        if not missing:
            continue
        first_seen = lead.get("first_seen")
        if not first_seen:
            no_first_seen.append(str(lead.get("lead_id")))
        hits.append({"subject": str(lead.get("lead_id")), "companies": missing, "first_seen": first_seen,
                     "title": lead.get("title"),
                     "text": QUESTION_BY_KEY["lead_not_in_graph"].question.format(
                         lead_id=lead.get("lead_id"), companies="、".join(f"`{c}`" for c in missing))})
    # 首見時間舊的先；缺值排最後並計數，不補假日期（INV-6）。
    hits.sort(key=lambda h: (h["first_seen"] is None, str(h["first_seen"] or ""), h["subject"]))
    return {"hits": hits, "scope_n": len(scope),
            "extra": {"unresolved_names": sorted(unresolved), "no_first_seen": sorted(no_first_seen)}}


def supplier_no_anchor(edges: Sequence[CanonicalEdge], *,
                       anchors: Iterable[str] | None = None) -> dict[str, Any]:
    """第 6 型：有往下供貨（tech／mat／prod）的公司，走不到任何需求錨。

    ⚠ 母體刻意收窄到「有往下供貨的公司」（plan A5）：照字面問「所有節點走不走得到錨」是 51%、恆亮。
    """
    upward = build_upward_index(edges)
    suppliers = sorted({e.src for e in edges if e.relation == "supplies_to"
                        and e.src.startswith("co:") and e.dst.startswith(DOWNSTREAM_PREFIXES)})
    targets: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        if e.relation == "supplies_to" and e.src in suppliers and e.dst.startswith(DOWNSTREAM_PREFIXES):
            targets[e.src].append(e.dst)
    hits = [{"subject": co, "supplies": sorted(set(targets[co])),
             "text": QUESTION_BY_KEY["supplier_no_anchor"].question.format(co=co)}
            for co in suppliers if not demand_chain(co, upward, anchors=anchors)]
    return {"hits": hits, "scope_n": len(suppliers)}


def coverage_questions(coverage_rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """第 7、8 型：沿用 `query.coverage_gaps` 的分桶（不重新分類，L16）。"""
    from query.coverage_gaps import (
        ISOLATED_DEGREE, PRODUCT_NOISE_PREFIX, RESEARCH_QUESTION_TEMPLATE, bucketize, split_research_gaps,
    )

    buckets = bucketize(coverage_rows)
    real, noise = split_research_gaps(buckets["research_gap"])
    non_concept = [r for r in coverage_rows if r["status"] != "concept"]
    no_supplier_scope = [r for r in non_concept if not str(r["node"]).startswith(PRODUCT_NOISE_PREFIX)]
    no_supplier = []
    for row in sorted(real, key=lambda r: r["node"]):
        isolated = row.get("degree") == ISOLATED_DEGREE
        no_supplier.append({
            "subject": row["node"], "name": row.get("name"), "abstraction_level": row.get("abstraction_level"),
            "degree": row.get("degree"), "isolated": isolated,
            # 孤立節點的下一步不是「誰供應它」——它連 stack 都還沒接上（coverage 同一句）。
            "text": ("`{node}` 連一條邊都沒有：先確認它該掛在 stack 哪一層".format(node=row["node"])
                     if isolated else RESEARCH_QUESTION_TEMPLATE.format(node=row["node"]) + "（圖上 0 家）"),
        })
    modelling = [{"subject": r["node"], "name": r.get("name"), "indirect": list(r.get("indirect") or ()),
                  "text": QUESTION_BY_KEY["modelling_gap"].question.format(node=r["node"])}
                 for r in sorted(buckets["modelling_gap"], key=lambda r: r["node"])]
    return {
        "no_supplier": {"hits": no_supplier, "scope_n": len(no_supplier_scope),
                        "extra": {"product_noise": sorted(r["node"] for r in noise),
                                  "concept": sorted(r["node"] for r in buckets["concept"])}},
        "modelling_gap": {"hits": modelling, "scope_n": len(non_concept)},
    }


def duplicate_questions(duplicate_buckets: Mapping[str, Sequence[Mapping[str, Any]]], *,
                        node_total: int) -> dict[str, Any]:
    """第 9 型：沿用 `query.duplicate_nodes` 的候選與 registry 分桶；只收 `unmentioned`（registry 從沒提過）。"""
    hits = []
    for pair in sorted(duplicate_buckets.get("unmentioned") or (), key=lambda p: tuple(p["pair"])):
        a, b = pair["pair"]
        hits.append({"subject": f"{a}|{b}", "pair": [a, b], "rules": list(pair.get("rules") or ()),
                     "same_abstraction_level": pair.get("same_abstraction_level"),
                     "left": pair.get("left"), "right": pair.get("right"),
                     "text": QUESTION_BY_KEY["duplicate_node"].question.format(a=a, b=b)})
    mentioned = sorted("|".join(p["pair"]) for p in duplicate_buckets.get("mentioned") or ())
    return {"hits": hits, "scope_n": int(node_total), "extra": {"registry_mentioned": mentioned}}


def walk(*, edges: Sequence[CanonicalEdge], graph_nodes: Iterable[str],
         reading_rows: Sequence[Mapping[str, Any]] | None,
         leads: Mapping[str, Mapping[str, Any]] | Iterable[Mapping[str, Any]] | None,
         registry: Any,
         coverage_rows: Sequence[Mapping[str, Any]],
         duplicate_buckets: Mapping[str, Sequence[Mapping[str, Any]]], duplicate_node_total: int,
         anchors: Iterable[str] | None = None) -> dict[str, Any]:
    """九型一次走完。**每型各自一格，沒有任何跨型別合成的數字。**

    `reading_rows`／`leads` 給 `None` ＝ 這次沒讀到那個 authority：該型印 `upstream_unavailable`，
    不印 0（INV-3）。
    """
    graph = sorted(set(graph_nodes))
    readings = list(reading_rows) if reading_rows is not None else None
    read_nodes = {str(r["node"]) for r in readings or () if r.get("reading_id")}
    parts: dict[str, dict[str, Any] | None] = {}
    parts.update(layer_questions(edges, read_nodes=read_nodes))
    parts["reading_stale"] = reading_stale(readings) if readings is not None else None
    parts["lead_not_in_graph"] = (lead_not_in_graph(leads, graph_nodes=graph, registry=registry)
                                  if leads is not None else None)
    parts["supplier_no_anchor"] = supplier_no_anchor(edges, anchors=anchors)
    parts.update(coverage_questions(coverage_rows))
    parts["duplicate_node"] = duplicate_questions(duplicate_buckets, node_total=duplicate_node_total)
    if readings is None:
        # 第 1 型的「沒有現行讀圖」要讀 ledger；讀不到就不能宣稱「沒人讀過」。
        parts["thin_layer_unread"] = None

    questions = []
    for order, qt in enumerate(QUESTION_TYPES, start=1):
        part = parts.get(qt.key)
        base = {"key": qt.key, "order": order, "short": qt.short, "question": qt.question,
                "scope_rule": qt.scope_rule, "hit_rule": qt.hit_rule, "next_action": qt.next_action}
        if part is None:
            questions.append({**base, "hit_n": None, "scope_n": None, "judged": False, "rate": None,
                              "always_on": None, "hits": [], "extra": {},
                              "absence": {"kind": "upstream_unavailable",
                                          "reason": "這次沒讀到這一型的 authority（讀圖 ledger 或 leads）——不是 0"}})
            continue
        hit_n, scope_n = len(part["hits"]), int(part["scope_n"])
        judged = scope_n >= SCOPE_JUDGE_MIN
        rate = (hit_n / scope_n) if scope_n else None
        questions.append({**base, "hit_n": hit_n, "scope_n": scope_n, "judged": judged,
                          "rate": None if rate is None else round(rate, 4),
                          "always_on": (rate is not None and rate >= ALWAYS_ON_RATE) if judged else None,
                          "hits": part["hits"], "extra": part.get("extra") or {}, "absence": None})
    return {"title": TITLE, "questions": questions, "graph_nodes": graph,
            "this_is_not": list(THIS_IS_NOT),
            "rules": {"scope_judge_min": SCOPE_JUDGE_MIN, "always_on_rate": ALWAYS_ON_RATE,
                      "demand_unavoidable_min_sub": DEMAND_UNAVOIDABLE_MIN_SUB,
                      "thin_layer_max_suppliers": THIN_LAYER_MAX_SUPPLIERS}}


# ---------------------------------------------------------------------------
# 組裝（唯一連圖、讀 ledger 的地方）
# ---------------------------------------------------------------------------

_GRAPH_NODES_CYPHER = "MATCH (n) WHERE n.id IS NOT NULL RETURN DISTINCT n.id AS id"


def _driver():
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    load_dotenv()
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("請設 NEO4J_PASSWORD（走圖要讀圖）")
    return GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )


def collect(*, today: date | None = None, as_of: date | None = None) -> dict[str, Any]:
    """讀圖（一次連線）＋ leads ＋ 讀圖 ledger → `walk()`。

    ⚠ 這是 `query/` 裡**唯一** import `alpha/` 的地方（讀圖狀態的算法住讀圖 provider，
    與讀圖 artifact 同一份；`tests/test_layer_separation.py` 守這個例外只有一個）。
    """
    from identity import entities
    from identity.registry import get_registry
    from query.bottleneck import fetch_assertions
    from query.coverage_gaps import scan as scan_coverage
    from query.duplicate_nodes import bucketize, pair_candidates
    from query.duplicate_nodes import scan as scan_duplicates
    from query.structure import _classify_edges

    driver = _driver()
    try:
        with driver.session() as session:
            # 同一個 session 掃四題：邊、全部節點 id、coverage、重複節點——只連一次圖。
            rows = fetch_assertions(session)
            graph_nodes = [r["id"] for r in session.run(_GRAPH_NODES_CYPHER)]
            coverage_rows = scan_coverage(session)
            duplicate_rows = scan_duplicates(session)
    finally:
        driver.close()
    edges = _classify_edges(rows)
    duplicate_buckets = bucketize(pair_candidates(duplicate_rows), entities.load())

    reading_rows: list[dict[str, Any]] | None
    try:
        from alpha.providers.structure_readings import reading_status_rows

        reading_rows, _errors = reading_status_rows(edges, today=today or date.today(), as_of=as_of)
    except Exception:  # noqa: BLE001 — 讀圖 ledger 讀不到只讓第 1、4 型降級，其餘照走
        reading_rows = None
    leads: Mapping[str, Mapping[str, Any]] | None
    try:
        from engine_b import leads as leads_mod

        leads = leads_mod.load().get("leads") or {}
    except Exception:  # noqa: BLE001
        leads = None
    return walk(edges=edges, graph_nodes=graph_nodes, reading_rows=reading_rows, leads=leads,
                registry=get_registry(), coverage_rows=coverage_rows,
                duplicate_buckets=duplicate_buckets, duplicate_node_total=len(duplicate_rows))


# ---------------------------------------------------------------------------
# 呈現
# ---------------------------------------------------------------------------

def fraction(question: Mapping[str, Any]) -> str:
    """「命中／母體」——0 也印；讀不到印缺席，不印 0（INV-3）。"""
    if question.get("absence"):
        return str(question["absence"]["kind"])
    return f"{question['hit_n']}／{question['scope_n']}"


def summary_line(result: Mapping[str, Any]) -> str:
    """一行九格（心跳段 3 用）：每型「中文短名 命中／母體」，順序固定、0 也印、**不加總**。"""
    return "｜".join(f"{q['short']} {fraction(q)}" for q in result["questions"])


def render_markdown(result: Mapping[str, Any]) -> str:
    out = [f"# {result['title']}", "",
           "> **零 LLM、零分數、不排序。** 九型各自「命中／母體」；型別順序是閱讀順序，不是價值判斷。", "",
           summary_line(result), ""]
    for q in result["questions"]:
        judged = ("（母體 <10，只印不判）" if not q["judged"] else
                  ("　⚠ **命中率 ≥50%：恆亮，要收窄母體**" if q["always_on"] else ""))
        out.append(f"## {q['order']}. {q['short']}（`{q['key']}`）　{fraction(q)}{judged if not q.get('absence') else ''}")
        out.append(f"母體：{q['scope_rule']}｜命中：{q['hit_rule']}｜下一步：{q['next_action']}")
        if q.get("absence"):
            out.append(f"⚠ {q['absence']['reason']}")
            out.append("")
            continue
        for hit in q["hits"]:
            out.append(f"- {hit['text']}")
        extra = q.get("extra") or {}
        if extra.get("unresolved_names"):
            names = extra["unresolved_names"]
            out.append(f"- 另有 {len(names)} 個名字 registry 解析不到（不算命中；ID 沒解析對 ≠ 圖中真無此公司）："
                       + "、".join(f"`{n}`" for n in names))
        if extra.get("no_first_seen"):
            out.append(f"- 其中 {len(extra['no_first_seen'])} 則沒有首見時間，排在最後（不補假日期）")
        if extra.get("product_noise"):
            out.append(f"- 抽取副產品（`prod:` 前綴、0 家）{len(extra['product_noise'])} 個，只計數、不是題目")
        if extra.get("withdrawn"):
            out.append(f"- 有紀錄但已全部撤回（不在母體）：{'、'.join(extra['withdrawn'])}")
        if extra.get("registry_mentioned"):
            out.append(f"- registry 的 note 提過的候選 {len(extra['registry_mentioned'])} 對（不算命中；先讀 note）")
        out.append("")
    out.append("---")
    out += [f"- {line}" for line in result["this_is_not"]]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="走圖：九型問句的命中／母體（零 LLM、零分數、不排序）")
    parser.add_argument("--json", action="store_true", help="機器可讀")
    args = parser.parse_args(argv)
    try:
        result = collect()
    except Exception as exc:  # noqa: BLE001 — 讀不到圖就說讀不到，不印 0
        print(f"✗ 走圖讀不到圖：{type(exc).__name__}: {exc}（upstream_unavailable）", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(render_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ACTIVE_LEAD_STATUSES", "ALWAYS_ON_RATE", "QUESTION_BY_KEY", "QUESTION_TYPES", "QUESTION_TYPE_KEYS",
    "QuestionType", "SCOPE_JUDGE_MIN", "THIS_IS_NOT", "TITLE", "collect", "coverage_questions",
    "duplicate_questions", "fraction", "lead_not_in_graph", "layer_questions", "reading_stale",
    "render_markdown", "summary_line", "supplier_no_anchor", "walk",
]