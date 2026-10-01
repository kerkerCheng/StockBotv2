"""層計數器（Phase 4 Step 4.4c）：ROADMAP Phase 4 驗收 ①②③ 的常駐計數器——**純函式**，不查圖、不寫任何東西。

唯一連圖的地方是 `query.graph_walk.collect()`（走圖與它共用一次連線）；結果跟著 `graph_walk` artifact 走
（`layer_stats` 一段），心跳段 3 與結構表頁首讀同一份 artifact，不重算（L16）。

三個數各自回答一個問題，**只印、不判、不排序、沒有門檻**（plan 不可越線 10）：

- ①（A1）凍結節點集合（Step 4.0 的 186 個 tech／mat／prod 節點）裡，供給側（`query.structure` 的 supply_side＝
  只算 supplies_to）恰 1 家、且那條供貨邊不是外部印證／雙方聯合的節點數。另印集合外的新節點數與已不在圖上的。
- ②（A2）有一份**非供應商 origin** 的來源、引文**逐字具名 ≥2 家**這一層供應商的層數（G4 的指紋：一份文件列舉
  一層的供應商集合）。另印母體（≥3 家的層數）、稽核（≥3 家且每家撐住：引文具名它或 origin 就是它）、
  origin 解析不到的來源數（解析不到不能算「非供應商」，不猜）。
- ③（A3）③a 存量：Step 4.0 凍結的 113 筆帶 sub assertion 裡，引文不含可替代性語言的筆數與 id（只印、當歷史）；
  ③b Phase 內新增或 supersede 的帶 sub assertion（不在 4.0 凍結的 assertion id 集合）中 supported 的比例。

附屬：「外部印證但引文不具名供應商」的邊數（plan §4 L11-6 ④；§14 #2 的量測）、字表版本。

⚠ 已知會失焦（AGENTS「這個指標會隨我們多讀一份文件而單調上升嗎？」）：②的母體「≥3 家」會隨多讀文件單調上升，
所以它**只印**；驗收數的是②本身（一份文件列舉多家），不是母體。
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
BASELINES_PATH = ROOT / "config" / "graph_baselines.json"
BASELINE_KEY = "phase4_2026_10_01"
#: 與 Step 4.0 凍結節點集合同一個口徑（`frozen_nodes.scope`）。
LAYER_TYPES: tuple[str, ...] = ("TechNode", "Product", "Material")
LAYER_NODES_CYPHER = "MATCH (t) WHERE t.type IN $types AND t.id IS NOT NULL RETURN t.id AS id"


def load_baseline(path: Path | None = None, *, key: str = BASELINE_KEY) -> dict[str, frozenset[str]]:
    """Step 4.0 凍結的三個 id 集合。讀不到就丟例外——呼叫端把它變成缺席（INV-3），不是 0。"""
    data = json.loads((path or BASELINES_PATH).read_text(encoding="utf-8"))
    baseline = (data.get("baselines") or {})[key]
    return {name: frozenset(str(i) for i in (baseline[name].get("ids") or ()))
            for name in ("frozen_nodes", "frozen_assertions", "sub_assertions")}


def _supply_side(node: str, edges: Sequence[Any]) -> list[Any]:
    from query.structure import build_structure

    return list(build_structure(node, edges).angles.get("supply_side") or ())


def compute_layer_stats(*, edges: Sequence[Any], rows: Iterable[Mapping[str, Any]],
                        quotes_by_assertion: Mapping[str, Sequence[str]], layer_nodes: Iterable[str],
                        baseline: Mapping[str, frozenset[str]], registry: Any,
                        language: Any = None, publishers: Any = None,
                        baseline_key: str = BASELINE_KEY) -> dict[str, Any]:
    """①②③＋附屬。`edges` 要已分過證據等級（`query.structure._classify_edges`）；`rows` 是 `fetch_assertions` 的列
    （帶 `assertion_id`、`source_doc_id`、`origin`）；`quotes_by_assertion` 是 `query.sub_language.fetch_all_quotes`。"""
    from query.bottleneck import quote_names_company, shared_name_forms
    from query.graph_walk import CORROBORATED_EVIDENCE
    from query.origin_resolution import resolve_origin
    from query.sub_language import get_language, sub_language_flags

    lang = language or get_language()
    rows = list(rows)
    shared = shared_name_forms(registry)
    current_layers = sorted(set(layer_nodes))
    rows_by_edge: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        rows_by_edge[(str(row.get("src")), str(row.get("relation")), str(row.get("dst")))].append(row)
    resolved_cache: dict[str, Any] = {}

    def resolve(origin: Any) -> Any:
        key = str(origin or "")
        if key not in resolved_cache:
            resolved_cache[key] = resolve_origin(origin, registry, publishers=publishers)
        return resolved_cache[key]

    def names(quotes: Iterable[str], company_id: str) -> bool:
        company = registry.company(company_id)
        return company is not None and any(quote_names_company(q, company, shared=shared) for q in quotes)

    # ① 凍結節點集合的供給側分布
    frozen = baseline["frozen_nodes"]
    on_graph = set(current_layers)
    buckets: Counter = Counter()
    sole_self: list[str] = []
    for node in sorted(frozen & on_graph):
        supply = _supply_side(node, edges)
        suppliers = {e.src for e in supply}
        buckets["3+" if len(suppliers) >= 3 else str(len(suppliers))] += 1
        if len(suppliers) == 1 and not ({e.evidence for e in supply} & CORROBORATED_EVIDENCE):
            sole_self.append(node)

    # ② 層列舉（對**現在**圖上的層節點；母體會隨多讀文件上升，只印）
    with_suppliers = 0
    at_least_3 = 0
    all_held: list[str] = []
    enumerated: list[dict[str, Any]] = []
    unresolved_docs: set[str] = set()
    for node in current_layers:
        supply = _supply_side(node, edges)
        suppliers = sorted({e.src for e in supply})
        if not suppliers:
            continue
        with_suppliers += 1
        held = {s: False for s in suppliers}
        doc_quotes: dict[str, list[str]] = defaultdict(list)
        doc_origin: dict[str, Any] = {}
        for edge in supply:
            for row in rows_by_edge.get((edge.src, edge.relation, edge.dst), ()):
                quotes = list(quotes_by_assertion.get(str(row.get("assertion_id") or "")) or ())
                doc = str(row.get("source_doc_id") or "")
                if doc:
                    doc_quotes[doc].extend(quotes)
                    doc_origin.setdefault(doc, row.get("origin"))
                if not held[edge.src]:
                    resolution = resolve(row.get("origin"))
                    held[edge.src] = names(quotes, edge.src) or (
                        resolution.kind == "company" and resolution.id == edge.src)
        if len(suppliers) >= 3:
            at_least_3 += 1
            if all(held.values()):
                all_held.append(node)
        for doc in sorted(doc_quotes):
            resolution = resolve(doc_origin.get(doc))
            if resolution.kind == "unresolved":
                unresolved_docs.add(doc)
                continue
            if resolution.kind == "company" and resolution.id in held:
                continue                       # 供應商自己的文件不算「非供應商來源」
            named = [s for s in suppliers if names(doc_quotes[doc], s)]
            if len(named) >= 2:
                enumerated.append({"node": node, "doc": doc, "origin": doc_origin.get(doc),
                                   "origin_kind": resolution.kind, "named": named})
    enumerated_layers = sorted({hit["node"] for hit in enumerated})

    # ③ sub 引文核對
    flags = sub_language_flags(rows, quotes_by_assertion, language=lang)
    stock = baseline["sub_assertions"]
    stock_unsupported = sorted(a for a in stock if flags.get(a) is False)
    stock_gone = sorted(a for a in stock if a not in flags)
    new = sorted(a for a in flags if a not in baseline["frozen_assertions"])
    new_unsupported = sorted(a for a in new if not flags[a])

    # 附屬：外部印證但引文不具名供應商（§14 #2 的量測；cw_dfb 讀圖指出的華星光案例）
    ec_unnamed: list[str] = []
    for edge in edges:
        if edge.evidence != "externally_corroborated" or not str(edge.src).startswith("co:"):
            continue
        if registry.company(edge.src) is None:
            continue
        quotes = [q for row in rows_by_edge.get((edge.src, edge.relation, edge.dst), ())
                  for q in quotes_by_assertion.get(str(row.get("assertion_id") or "")) or ()]
        if not names(quotes, edge.src):
            ec_unnamed.append(f"{edge.src} {edge.relation} {edge.dst}")

    return {
        "baseline": baseline_key,
        "language": lang.label,
        "supply": {
            "frozen_n": len(frozen),
            "frozen_on_graph": len(frozen & on_graph),
            "frozen_gone": sorted(frozen - on_graph),
            "ns": {key: buckets.get(key, 0) for key in ("0", "1", "2", "3+")},
            "sole_self_reported": len(sole_self),
            "sole_self_reported_nodes": sole_self,
            "new_nodes": sorted(on_graph - frozen),
        },
        "enumeration": {
            "layers": len(current_layers),
            "layers_with_suppliers": with_suppliers,
            "at_least_3": at_least_3,
            "named_by_non_supplier": len(enumerated_layers),
            "named_by_non_supplier_layers": enumerated_layers,
            "hits": enumerated,
            "at_least_3_all_held": len(all_held),
            "at_least_3_all_held_layers": all_held,
            "unresolved_origin_sources": len(unresolved_docs),
        },
        "sub_language": {
            "checked": len(flags),
            "stock_n": len(stock),
            "stock_unsupported": stock_unsupported,
            "stock_gone": stock_gone,
            "new_n": len(new),
            "new_supported": len(new) - len(new_unsupported),
            "new_unsupported": new_unsupported,
        },
        "ec_quote_does_not_name_supplier": sorted(ec_unnamed),
    }


def summary_line(stats: Mapping[str, Any] | None) -> str:
    """心跳段 3、結構表頁首、CLI 共用的一行（L16：呈現只有一份）。讀不到印缺席，不印 0（INV-3）。"""
    if not stats:
        return "層：layer_stats 讀不到（upstream_unavailable）——不是 0"
    if stats.get("absence"):
        absence = stats["absence"]
        return f"層：{absence.get('reason')}（{absence.get('kind')}）——不是 0"
    supply, enum, sub = stats["supply"], stats["enumeration"], stats["sub_language"]
    new_ratio = (f"{sub['new_supported']}／{sub['new_n']}" if sub["new_n"] else "0／0（Phase 內還沒有新增帶 sub 的）")
    return (f"層：①獨家且全自報 {supply['sole_self_reported']}（凍結 {supply['frozen_n']} 個節點；集合外新節點 "
            f"{len(supply['new_nodes'])}）｜②非供應商來源列舉 ≥2 家 {enum['named_by_non_supplier']} 層（≥3 家母體 "
            f"{enum['at_least_3']}；每家撐住 {enum['at_least_3_all_held']}；origin 解析不到的來源 "
            f"{enum['unresolved_origin_sources']}）｜③a sub 引文不含可替代性語言 {len(sub['stock_unsupported'])}／"
            f"{sub['stock_n']}（存量）｜③b 新增帶 sub supported {new_ratio}｜外部印證但引文不具名供應商 "
            f"{len(stats['ec_quote_does_not_name_supplier'])}｜字表 {stats['language']}")


__all__ = ["BASELINE_KEY", "LAYER_NODES_CYPHER", "LAYER_TYPES", "compute_layer_stats", "load_baseline",
           "summary_line"]
