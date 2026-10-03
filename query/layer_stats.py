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
  ③b 新增或重寫的帶 sub assertion 中 supported 的比例——**兩種分開計**（Phase 5 Step 5.1，#29）：「新增」＝id 不在
  4.0 凍結的 assertion id 集合；「重寫」＝id 在集合、但內容指紋（`assertion_content_digest`）與內容基準不同。
  ⚠ 只看 id 會漏掉更正走廊：重套一份文件沿用原 id，被重寫的斷言在 id 集合裡「看起來沒動」——成功與失敗同形（L13）。

附屬（Phase 6 Step 6.4 起；ROADMAP Phase 6 ①「外部印證名副其實」的常駐計數器）：
- `corroboration_withheld`：沒升外部印證的邊，依理由分三格（`unnamed`／`no_name_forms`／`relay`——
  `query.origin_resolution.WITHHELD_REASONS`；三種補救不同，不得壓成一格，L12）。每條帶邊、origin、文件——這就是
  研究 Step 補具名引文的清單。判定只問 `corroboration`（唯一 owner），這裡只收集。
- `ec_without_naming_quote`：外部印證、主詞是公司，但**沒有任何一個非主詞、解析得到的 origin 自己的引文**具名主詞的邊——
  逐來源口徑的違反數，**應恆為 0；非 0＝bug**（用名字比對與 origin 解析直接重算，不經 owner，所以它驗得到 owner）。
- `evidence_vs_baseline`：每條邊的證據等級對 6.0 凍結鍵（`config/graph_baselines.json` 的 `evidence_classes_2026_10_03`）
  的升、降、同級互換逐條——每一條變動都要歸得到一個事件（規則、資料更正、身分合併、補引文；plan 檔頭）。
- 字表版本（sub 字表與轉述字表各印一個）。
⚠ 2026-10-03 退役 `ec_quote_does_not_name_supplier`（「外部印證但引文不具名供應商」）：它的口徑是「這條邊**任何一段**引文
具名」——供應商自己的引文也算，所以漏掉 Sivers→CW DFB（撐它的是華星光年報，那段沒提 Sivers）；新規則下它結構上恆 0，
由上面三個取代。

⚠ 已知會失焦（AGENTS「這個指標會隨我們多讀一份文件而單調上升嗎？」）：②的母體「≥3 家」會隨多讀文件單調上升，
所以它**只印**；驗收數的是②本身（一份文件列舉多家），不是母體。
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
BASELINES_PATH = ROOT / "config" / "graph_baselines.json"
BASELINE_KEY = "phase4_2026_10_01"
#: ③b 判「重寫」的內容基準（Phase 5 Step 5.1，#29）。4.0 凍結只存 id；這一份由 5.1 當下的圖算
#: （Phase 4 結案後、[666] 重試前），append-only 的另一個鍵——4.0 的鍵一個字都不改。
CONTENT_BASELINE_KEY = "assertion_content_2026_10_02"
#: 證據等級的比較基準（Phase 6 Step 6.0 凍結；append-only 的另一個鍵）。
EVIDENCE_BASELINE_KEY = "evidence_classes_2026_10_03"
#: 與 Step 4.0 凍結節點集合同一個口徑（`frozen_nodes.scope`）。
LAYER_TYPES: tuple[str, ...] = ("TechNode", "Product", "Material")
LAYER_NODES_CYPHER = "MATCH (t) WHERE t.type IN $types AND t.id IS NOT NULL RETURN t.id AS id"


def load_baseline(path: Path | None = None, *, key: str = BASELINE_KEY) -> dict[str, frozenset[str]]:
    """Step 4.0 凍結的三個 id 集合。讀不到就丟例外——呼叫端把它變成缺席（INV-3），不是 0。"""
    data = json.loads((path or BASELINES_PATH).read_text(encoding="utf-8"))
    baseline = (data.get("baselines") or {})[key]
    return {name: frozenset(str(i) for i in (baseline[name].get("ids") or ()))
            for name in ("frozen_nodes", "frozen_assertions", "sub_assertions")}


def load_content_baseline(path: Path | None = None, *, key: str = CONTENT_BASELINE_KEY) -> dict[str, str] | None:
    """內容基準（assertion id → 內容指紋）。檔案裡沒有這個鍵回 `None`——呼叫端印「重寫量不到」，不是 0（INV-3）；
    檔案本身讀不到照樣丟例外（與 `load_baseline` 同一條缺席路）。"""
    data = json.loads((path or BASELINES_PATH).read_text(encoding="utf-8"))
    entry = (data.get("baselines") or {}).get(key)
    if not entry:
        return None
    return {str(k): str(v) for k, v in ((entry.get("assertion_digests") or {}).get("digests") or {}).items()}


def load_evidence_baseline(path: Path | None = None, *, key: str = EVIDENCE_BASELINE_KEY) -> dict[str, str] | None:
    """6.0 凍結的證據等級（邊 `"src relation dst"` → 等級）。檔案裡沒有這個鍵回 `None`——呼叫端印「基準讀不到」，
    不是 0（INV-3）；檔案本身讀不到照樣丟例外（與 `load_baseline` 同一條缺席路）。"""
    data = json.loads((path or BASELINES_PATH).read_text(encoding="utf-8"))
    entry = (data.get("baselines") or {}).get(key)
    if not entry:
        return None
    return {str(k): str(v) for k, v in (entry.get("classes") or {}).items()}


def evidence_vs_baseline(edges: Sequence[Any], baseline: Mapping[str, str]) -> dict[str, Any]:
    """每條邊的證據等級對基準：升、降、同級互換（`needs_review`↔`media_relay`）、新邊、不在了——逐條，不只總數。"""
    from query.bottleneck import EVIDENCE_RANK

    now = {f"{e.src} {e.relation} {e.dst}": str(e.evidence) for e in edges}
    up: list[dict[str, str]] = []
    down: list[dict[str, str]] = []
    same_rank: list[dict[str, str]] = []
    for edge in sorted(set(now) & set(baseline)):
        before, after = baseline[edge], now[edge]
        if before == after:
            continue
        entry = {"edge": edge, "from": before, "to": after}
        rank_before, rank_after = EVIDENCE_RANK.get(before, -1), EVIDENCE_RANK.get(after, -1)
        (up if rank_after > rank_before else down if rank_after < rank_before else same_rank).append(entry)
    return {"up": up, "down": down, "same_rank": same_rank,
            "new": [{"edge": e, "to": now[e]} for e in sorted(set(now) - set(baseline))],
            "gone": [{"edge": e, "from": baseline[e]} for e in sorted(set(baseline) - set(now))]}


def assertion_content_digest(row: Mapping[str, Any], quotes: Iterable[str] | None) -> str:
    """一筆 EdgeAssertion 的內容指紋：**邊（src／relation／dst）＋來源文件 id＋逐字＋sub＋決定證據等級的三個欄位**
    （`origin`、`source_type`、`origin_linkage`——`query.bottleneck.classify_evidence` 讀的就是它們）。

    ⚠ 刻意不含 `published_at`、`confidence`、`documents`：補日期或多讀一份文件不是「重寫了這筆主張」，算進來的話
    ③b 的分母會隨研究量上升（AGENTS「已知會失焦的指標」）。[666] 這種只宣告 `origin_linkage` 的重套也要算重寫——
    它改的是這筆斷言的證據等級。"""
    from query.sub_language import sub_value

    body = {"edge": [str(row.get("src")), str(row.get("relation")), str(row.get("dst"))],
            "source_doc_id": row.get("source_doc_id"),
            "quotes": sorted({str(q) for q in (quotes or ()) if q}),
            "sub": sub_value(row),
            "origin": row.get("origin"), "source_type": row.get("source_type"),
            "origin_linkage": row.get("origin_linkage")}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def content_digests(rows: Iterable[Mapping[str, Any]], quotes_by_assertion: Mapping[str, Sequence[str]], *,
                    ids: Iterable[str] | None = None) -> dict[str, str]:
    """`rows`（`fetch_assertions`）＋逐字 → `{assertion id: 內容指紋}`；給 `ids` 就只算那些。內容基準與每日比對共用這一支。"""
    wanted = None if ids is None else {str(i) for i in ids}
    out: dict[str, str] = {}
    for row in rows:
        aid = str(row.get("assertion_id") or "")
        if not aid or (wanted is not None and aid not in wanted):
            continue
        out[aid] = assertion_content_digest(row, quotes_by_assertion.get(aid))
    return out


def _supply_side(node: str, edges: Sequence[Any]) -> list[Any]:
    from query.structure import build_structure

    return list(build_structure(node, edges).angles.get("supply_side") or ())


def compute_layer_stats(*, edges: Sequence[Any], rows: Iterable[Mapping[str, Any]],
                        quotes_by_assertion: Mapping[str, Sequence[str]], layer_nodes: Iterable[str],
                        baseline: Mapping[str, frozenset[str]], registry: Any,
                        language: Any = None, publishers: Any = None, relay: Any = None,
                        baseline_key: str = BASELINE_KEY,
                        content_baseline: Mapping[str, str] | None = None,
                        content_baseline_key: str = CONTENT_BASELINE_KEY,
                        evidence_baseline: Mapping[str, str] | None = None,
                        evidence_baseline_key: str = EVIDENCE_BASELINE_KEY) -> dict[str, Any]:
    """①②③＋附屬。`edges` 要已分過證據等級（`query.structure._classify_edges`）；`rows` 是 `fetch_assertions` 的列
    （帶 `assertion_id`、`source_doc_id`、`origin`）；`quotes_by_assertion` 是 `query.sub_language.fetch_all_quotes`。
    `content_baseline`（`load_content_baseline`）是 ③b「重寫」的基準；`None`＝沒有基準，重寫那一格印缺席、不印 0。
    `evidence_baseline`（`load_evidence_baseline`）是證據等級升降的基準；`None`＝讀不到，那一格印缺席、不印 0。"""
    from query.bottleneck import edge_corroborations, quote_names_company, shared_name_forms
    from query.graph_walk import CORROBORATED_EVIDENCE
    from query.origin_resolution import WITHHELD_REASONS, get_relay_language, resolve_origin
    from query.sub_language import get_language, sub_language_flags

    lang = language or get_language()
    relay_language = relay if relay is not None else get_relay_language()
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
    frozen_assertions = baseline["frozen_assertions"]
    new = sorted(a for a in flags if a not in frozen_assertions)
    new_unsupported = sorted(a for a in new if not flags[a])
    # 重寫（#29）：id 在 4.0 凍結集合裡、內容指紋與內容基準不同。基準裡沒有這個 id（5.1 當下不在圖上、後來又出現）
    # 也算重寫——它不是新 id，但內容沒有可比的舊版。沒有內容基準＝量不到（None），不是 0。
    superseded: list[str] | None = None
    if content_baseline is not None:
        now = content_digests(rows, quotes_by_assertion, ids=[a for a in flags if a in frozen_assertions])
        superseded = sorted(a for a in now if content_baseline.get(a) != now[a])
    superseded_unsupported = None if superseded is None else sorted(a for a in superseded if not flags[a])

    # 附屬（Phase 6 Step 6.4）：沒升外部印證的邊與理由——判定只問 owner（`edge_corroborations`→`corroboration`）。
    withheld: dict[str, list[dict[str, Any]]] = {reason: [] for reason in WITHHELD_REASONS}
    for edge in edges:
        if edge.evidence == "externally_corroborated":
            continue
        for verdict in edge_corroborations(edge.src, edge.origins, registry, edge.filing_origins,
                                           quotes_by_assertion=quotes_by_assertion,
                                           origin_assertions=edge.origin_assertions,
                                           publishers=publishers, relay=relay_language, shared=shared):
            if verdict.withheld:
                entry = {"edge": f"{edge.src} {edge.relation} {edge.dst}", "evidence": edge.evidence,
                         "origin": verdict.origin, "docs": list(verdict.docs)}
                if verdict.relay_terms:
                    entry["relay_terms"] = list(verdict.relay_terms)
                withheld[verdict.withheld].append(entry)

    # 附屬：逐來源口徑的違反數（應恆為 0）——**不經 owner**，用 origin 解析與名字比對直接重算：外部印證、主詞是公司，
    # 但沒有任何一個「不是主詞、解析得到」的 origin 自己的引文具名主詞。
    violations: list[str] = []
    for edge in edges:
        if edge.evidence != "externally_corroborated" or not str(edge.src).startswith("co:"):
            continue
        held = False
        for row in rows_by_edge.get((edge.src, edge.relation, edge.dst), ()):
            resolution = resolve(row.get("origin"))
            if resolution.kind == "unresolved" or (resolution.kind == "company" and resolution.id == edge.src):
                continue
            if names(quotes_by_assertion.get(str(row.get("assertion_id") or "")) or (), edge.src):
                held = True
                break
        if not held:
            violations.append(f"{edge.src} {edge.relation} {edge.dst}")

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
            "content_baseline": content_baseline_key if content_baseline is not None else None,
            "superseded": superseded,
            "superseded_n": None if superseded is None else len(superseded),
            "superseded_supported": (None if superseded is None
                                     else len(superseded) - len(superseded_unsupported or ())),
            "superseded_unsupported": superseded_unsupported,
        },
        "relay_language": relay_language.label,
        "corroboration_withheld": {reason: sorted(items, key=lambda i: (i["edge"], i["origin"]))
                                   for reason, items in withheld.items()},
        "ec_without_naming_quote": sorted(violations),
        "evidence_baseline": evidence_baseline_key if evidence_baseline is not None else None,
        "evidence_vs_baseline": (None if evidence_baseline is None
                                 else evidence_vs_baseline(edges, evidence_baseline)),
    }


def summary_line(stats: Mapping[str, Any] | None) -> str:
    """心跳段 3、結構表頁首、CLI 共用的一行（L16：呈現只有一份）。讀不到印缺席，不印 0（INV-3）。"""
    if not stats:
        return "層：layer_stats 讀不到（upstream_unavailable）——不是 0"
    if stats.get("absence"):
        absence = stats["absence"]
        return f"層：{absence.get('reason')}（{absence.get('kind')}）——不是 0"
    supply, enum, sub = stats["supply"], stats["enumeration"], stats["sub_language"]
    withheld = stats["corroboration_withheld"]
    return (f"層：①獨家且全自報 {supply['sole_self_reported']}（凍結 {supply['frozen_n']} 個節點；集合外新節點 "
            f"{len(supply['new_nodes'])}）｜②非供應商來源列舉 ≥2 家 {enum['named_by_non_supplier']} 層（≥3 家母體 "
            f"{enum['at_least_3']}；每家撐住 {enum['at_least_3_all_held']}；origin 解析不到的來源 "
            f"{enum['unresolved_origin_sources']}）｜③a sub 引文不含可替代性語言 {len(sub['stock_unsupported'])}／"
            f"{sub['stock_n']}（存量）｜{_sub_b_fragment(sub)}｜外部印證違反 {len(stats['ec_without_naming_quote'])}"
            f"｜沒升外部印證：未具名 {len(withheld['unnamed'])}／名冊無名 {len(withheld['no_name_forms'])}／轉述 "
            f"{len(withheld['relay'])}（轉述字表 {stats['relay_language']}）｜{_evidence_fragment(stats)}"
            f"｜字表 {stats['language']}")


def _evidence_fragment(stats: Mapping[str, Any]) -> str:
    """證據等級對 6.0 基準那一格。基準讀不到印缺席（不是 0）；新邊、不在了的只在有的時候印。"""
    vs = stats.get("evidence_vs_baseline")
    if vs is None:
        return "證據等級較 6.0：基準讀不到（不是 0）"
    extra = "、".join(part for part in (f"新邊 {len(vs['new'])}" if vs["new"] else "",
                                       f"不在了 {len(vs['gone'])}" if vs["gone"] else "") if part)
    return (f"證據等級較 6.0：升 {len(vs['up'])}／降 {len(vs['down'])}／同級互換 {len(vs['same_rank'])}"
            + (f"（{extra}）" if extra else ""))


def _sub_b_fragment(sub: Mapping[str, Any]) -> str:
    """③b 那一格。新增與重寫各印一個數、分母是兩者之和；沒有內容基準時重寫印缺席（不是 0）。"""
    new_n, new_ok = int(sub["new_n"]), int(sub["new_supported"])
    if sub.get("superseded_n") is None:
        ratio = f"{new_ok}／{new_n}" if new_n else "0／0（還沒有新增帶 sub 的）"
        return f"③b 新增帶 sub supported {ratio}；重寫量不到（沒有內容基準，不是 0）"
    sup_n, sup_ok = int(sub["superseded_n"]), int(sub["superseded_supported"])
    total = new_n + sup_n
    if not total:
        return "③b 新增或重寫的帶 sub supported 0／0（還沒有新增或重寫帶 sub 的）"
    return f"③b 新增或重寫的帶 sub supported {new_ok + sup_ok}／{total}（新增 {new_n}、重寫 {sup_n}）"


__all__ = ["BASELINE_KEY", "CONTENT_BASELINE_KEY", "EVIDENCE_BASELINE_KEY", "LAYER_NODES_CYPHER", "LAYER_TYPES",
           "assertion_content_digest", "compute_layer_stats", "content_digests", "evidence_vs_baseline",
           "load_baseline", "load_content_baseline", "load_evidence_baseline", "summary_line"]
