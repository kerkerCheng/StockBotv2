"""入圖副作用：一份抽取檔載入（`loader.load_to_neo4j.load`）時，會改到圖上**既有**節點與 SourceDoc 的哪些值——唯一 owner。

為什麼（Phase 6 Step 6.2，Phase 4 closeout #32）：`MERGE_NODE` 對 `type`／`abstraction_level`／`role` 是直接 `SET`、
`MERGE_SOURCE_DOC` 對大部分欄位也是直接 `SET`——**最後載入的那一份贏**（`loader/migrate_entity_dedup_20260904.py` 檔頭的
「順帶發現」）。重載一份文件（身分遷移、更正走廊、新的 RA）因此可能靜默改掉別份文件寫下的節點屬性或 SourceDoc 欄位，
而沒有任何東西會叫。這裡把「會改到什麼」在寫入**之前**算出來印給人看：遷移工具的 dry-run 與 RA packet 共用這一支（L16）。

- 只讀：`fetch_graph_state` 以呼叫端給的 session 查**這份文件會 MERGE 的節點與 SourceDoc 的現值**，不寫任何東西。
- 計算是純函式（`compute_side_effects`），合併規則照抄 loader：name／attributes／aliases 走 `preserve_existing_node_fields`
  （同一個函式，不重寫）、confidence 取大、`published_at`／`retrieved_at` 是 coalesce（抽取檔沒帶就保留圖上值）、其餘直接覆寫。
- 讀不到圖：`side_effects()` 回 `status=upstream_unavailable`——**不得印成「無副作用」**（成功與失敗同形，L13）。

**入圖後證據等級會變的邊**（Phase 6 Step 6.4）：`evidence_after_load` 把本包的抽取照 loader 的 MERGE 語意併進當下的
assertion 列與逐字（`rows_after_load`），用分類的唯一 owner（`query.bottleneck.classify_evidence`→`corroboration`）在記憶體裡
前後各算一次。MERGE 語意照抄：assertion 以 `evidence_id` 覆寫（舊版有、新版沒有的 assertion **留著**）、SourceDoc 欄位直接
SET（同一份文件的舊 assertion 也跟著換 origin／宣告——[666] 就是這樣升級的）、`published_at` coalesce、Source 的逐字 coalesce、
`QUOTES` 連結只增不減。
"""
from __future__ import annotations

import json
from typing import Any, Mapping

#: `MERGE_NODE` 直接 SET 的欄位（name／aliases／attributes 另有保留規則、confidence 取大、source_ids 聯集）。
NODE_OVERWRITE_FIELDS: tuple[str, ...] = ("type", "abstraction_level", "role")
#: `MERGE_SOURCE_DOC` 直接 SET 的欄位。
SOURCE_DOC_OVERWRITE_FIELDS: tuple[str, ...] = (
    "title", "source_type", "evidence_tier", "origin_entity", "url", "publisher",
    "storage_permission", "permission_basis", "section", "origin_linkage",
)
#: `MERGE_SOURCE_DOC` 用 coalesce 的欄位（抽取檔帶了值才蓋過去）。
SOURCE_DOC_COALESCE_FIELDS: tuple[str, ...] = ("published_at", "retrieved_at")

_NODES_CYPHER = (
    "MATCH (n:Entity) WHERE n.id IN $ids "
    "RETURN n.id AS id, n.type AS type, n.name AS name, n.abstraction_level AS abstraction_level, n.role AS role, "
    "n.aliases AS aliases, n.attributes AS attrs, n.confidence AS confidence"
)
_SOURCE_DOC_CYPHER = (
    "MATCH (sd:SourceDoc {id: $id}) RETURN "
    + ", ".join(f"sd.{f} AS {f}" for f in SOURCE_DOC_OVERWRITE_FIELDS + SOURCE_DOC_COALESCE_FIELDS)
)


def fetch_graph_state(session: Any, doc: Mapping[str, Any]) -> dict[str, Any]:
    """這份文件會 MERGE 的節點與 SourceDoc 在圖上的現值（唯讀；session 由呼叫端開、關）。"""
    ids = sorted({str(n["id"]) for n in doc.get("nodes") or () if n.get("id")})
    nodes = {str(r["id"]): dict(r) for r in session.run(_NODES_CYPHER, ids=ids)}
    doc_id = str((doc.get("source_doc") or {}).get("doc_id") or "")
    found = list(session.run(_SOURCE_DOC_CYPHER, id=doc_id)) if doc_id else []
    return {"nodes": nodes, "source_doc": dict(found[0]) if found else None}


def _norm(value: Any) -> Any:
    return None if value in ("", None) else value


def compute_side_effects(doc: Mapping[str, Any], graph: Mapping[str, Any]) -> dict[str, Any]:
    """`graph`：`fetch_graph_state` 的輸出。回會被改到的值（新節點、新 SourceDoc 不算副作用，另列）。"""
    from identity.registry import TICKER_MAP          # 與 loader 同一份（ticker 的家是 registry，不經 loader 轉手）
    from loader.load_to_neo4j import preserve_existing_node_fields

    nodes_now: Mapping[str, Mapping[str, Any]] = graph.get("nodes") or {}
    overwrites: list[dict[str, Any]] = []
    alias_unions: list[dict[str, Any]] = []
    attribute_additions: list[dict[str, Any]] = []
    new_nodes: list[str] = []
    for node in doc.get("nodes") or ():
        node_id = str(node.get("id") or "")
        existing = nodes_now.get(node_id)
        if existing is None:
            new_nodes.append(node_id)
            continue
        for field in NODE_OVERWRITE_FIELDS:
            before, after = _norm(existing.get(field)), _norm(node.get(field))
            if before != after:
                overwrites.append({"node": node_id, "field": field, "graph": before, "after": after})
        confidence = node.get("confidence")
        if isinstance(confidence, (int, float)) and isinstance(existing.get("confidence"), (int, float)) \
                and confidence > existing["confidence"]:
            overwrites.append({"node": node_id, "field": "confidence", "graph": existing["confidence"],
                               "after": confidence})
        declared_attrs = dict(node.get("attributes") or {})
        if node.get("type") == "Company" and node_id in TICKER_MAP:      # 與 loader 同一步：先注入 ticker
            declared_attrs["ticker"] = TICKER_MAP[node_id]
        _name, aliases, attrs, _notes = preserve_existing_node_fields(
            str(node.get("name") or ""), [str(a) for a in node.get("aliases") or ()], declared_attrs, existing)
        prior_aliases = [str(a) for a in existing.get("aliases") or ()]
        added = [a for a in aliases if a not in prior_aliases]
        if added:
            alias_unions.append({"node": node_id, "graph": prior_aliases, "added": added})
        prior_attrs = json.loads(existing.get("attrs") or "{}") if isinstance(existing.get("attrs"), str) \
            else dict(existing.get("attrs") or {})
        new_keys = sorted(k for k in attrs if k not in prior_attrs)
        if new_keys:
            attribute_additions.append({"node": node_id, "added": {k: attrs[k] for k in new_keys}})

    source_doc = dict(doc.get("source_doc") or {})
    sd_now = graph.get("source_doc")
    sd_conflicts: list[dict[str, Any]] = []
    if sd_now is not None:
        for field in SOURCE_DOC_OVERWRITE_FIELDS:
            before, after = _norm(sd_now.get(field)), _norm(source_doc.get(field))
            if before != after:
                sd_conflicts.append({"field": field, "graph": before, "after": after})
        for field in SOURCE_DOC_COALESCE_FIELDS:
            before, after = _norm(sd_now.get(field)), _norm(source_doc.get(field))
            if after is not None and before != after:
                entry = {"field": field, "graph": before, "after": after}
                if before is not None and str(after) < str(before):
                    entry["regression"] = True          # 日期倒退（例：retrieved_at 比圖上早）
                sd_conflicts.append(entry)
    return {
        "status": "checked",
        "node_overwrites": overwrites,
        "alias_unions": alias_unions,
        "attribute_additions": attribute_additions,
        "new_nodes": sorted(new_nodes),
        "source_doc_new": sd_now is None,
        "source_doc_conflicts": sd_conflicts,
    }


def as_loaded(doc: Mapping[str, Any]) -> dict[str, Any]:
    """loader 實際 MERGE 的那一份：深拷貝後照 `load()` 第一步把非公司實體 id 換成 canonical（`identity.entities`）。

    ⚠ 不換的話，抽取檔裡的別名 id（`tech:eml_laser`）會被當成「圖上沒有的新節點」，而真正會被覆寫的 canonical 節點
    反而沒被比對到（2026-10-03 試算撞到）。`resolve_document` 會原地改 doc，所以先拷貝。"""
    import copy

    from identity import entities as entity_registry

    resolved = copy.deepcopy(dict(doc))
    entity_registry.resolve_document(resolved)
    return resolved


def side_effects(doc: Mapping[str, Any], session: Any) -> dict[str, Any]:
    """`as_loaded` → `fetch_graph_state` → `compute_side_effects`；讀不到圖回 `upstream_unavailable`（不是「無副作用」）。"""
    loaded = as_loaded(doc)
    try:
        graph = fetch_graph_state(session, loaded)
    except AssertionError:
        raise                       # 測試的絆線不得被當成「讀不到圖」吞掉
    except Exception as exc:  # noqa: BLE001 — 讀不到就不能宣稱沒有副作用
        return {"status": "upstream_unavailable",
                "reason": f"讀不到圖上的現值（{type(exc).__name__}: {str(exc)[:160]}）——副作用無法核對"}
    return compute_side_effects(loaded, graph)


#: 證據等級預告要的另外兩樣現值：每筆 assertion 連到哪幾段 Source、每段 Source 的逐字（`fetch_all_quotes` 只給逐字，
#: 模擬「這份文件改了 s3 的逐字」要知道誰連著 s3）。
_LINKS_CYPHER = "MATCH (ea:EdgeAssertion)-[:QUOTES]->(s:Source) RETURN ea.id AS id, collect(DISTINCT s.id) AS sources"
_SOURCE_QUOTES_CYPHER = "MATCH (s:Source) WHERE s.quote IS NOT NULL RETURN s.id AS id, s.quote AS quote"


def fetch_evidence_state(tx: Any) -> dict[str, Any]:
    """證據等級預告的圖現值（唯讀；同一個 transaction 裡取三樣）：assertion 列、逐字連結、Source 逐字。"""
    from query.bottleneck import fetch_assertions

    return {"rows": fetch_assertions(tx),
            "links": {str(r["id"]): sorted(str(s) for s in r["sources"] or ()) for r in tx.run(_LINKS_CYPHER)},
            "source_quotes": {str(r["id"]): str(r["quote"]) for r in tx.run(_SOURCE_QUOTES_CYPHER)}}


def quotes_by_assertion(links: Mapping[str, Any], source_quotes: Mapping[str, str]) -> dict[str, list[str]]:
    """assertion id → 它連到的 Source 的逐字（與 `query.sub_language.fetch_all_quotes` 同一個口徑：去重、沒逐字的不算）。"""
    out: dict[str, list[str]] = {}
    for aid, sources in links.items():
        texts = sorted({source_quotes[s] for s in sources if source_quotes.get(s)})
        if texts:
            out[str(aid)] = texts
    return out


def rows_after_load(rows: list[Mapping[str, Any]], links: Mapping[str, Any], source_quotes: Mapping[str, str],
                    documents: list[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """`fetch_assertions` 的列＋逐字連結 → 依序載入 `documents`（已 `as_loaded`）之後會長的樣子（純函式）。"""
    from loader.load_to_neo4j import evidence_id

    after = {str(r.get("assertion_id") or f"#{i}"): dict(r) for i, r in enumerate(rows)}
    link_after = {str(k): set(v) for k, v in links.items()}
    quotes_after = dict(source_quotes)
    for doc in documents:
        source_doc = dict(doc.get("source_doc") or {})
        doc_id = str(source_doc.get("doc_id") or "")
        if not doc_id:
            continue
        for row in after.values():
            if str(row.get("source_doc_id") or "") == doc_id:
                row.update(origin=source_doc.get("origin_entity"), source_type=source_doc.get("source_type"),
                           origin_linkage=source_doc.get("origin_linkage"),
                           published_at=source_doc.get("published_at") or row.get("published_at"))
        template = next((r for r in after.values() if str(r.get("source_doc_id") or "") == doc_id), {})
        for source in doc.get("sources") or ():
            if source.get("id") and source.get("quote") is not None:
                quotes_after[str(source["id"])] = str(source["quote"])
        for edge in doc.get("edges") or ():
            aid = evidence_id(doc_id, str(edge["id"]))
            after[aid] = {
                "src": edge["src_id"], "relation": edge["relation"], "dst": edge["dst_id"],
                "attributes": json.dumps(edge.get("attributes") or {}, ensure_ascii=False),
                "confidence": edge.get("confidence"), "origin": source_doc.get("origin_entity"),
                "source_type": source_doc.get("source_type"), "origin_linkage": source_doc.get("origin_linkage"),
                "source_doc_id": doc_id,
                "published_at": source_doc.get("published_at") or template.get("published_at"),
                "assertion_id": aid,
            }
            link_after.setdefault(aid, set()).update(str(s) for s in edge.get("source_ids") or ())
    return list(after.values()), quotes_by_assertion(link_after, quotes_after)


def evidence_after_load(state: Mapping[str, Any], documents: list[Mapping[str, Any]], registry: Any, *,
                        publishers: Any = None, relay: Any = None) -> list[dict[str, Any]]:
    """入圖後證據等級會變的邊：`state`（`fetch_evidence_state`）前後各算一次；新邊 `before=None`。
    `after_withheld`：改後那一邊沒升外部印證的理由（`corroboration` 的 `withheld`，去重排序）——RA 補引文看得出補到了沒。"""
    from query.bottleneck import best_evidence, collapse_assertions, edge_corroborations, shared_name_forms

    shared = shared_name_forms(registry)

    def verdicts(rows, quotes):
        return {key: edge_corroborations(edge.src, edge.origins, registry, edge.filing_origins,
                                         quotes_by_assertion=quotes, origin_assertions=edge.origin_assertions,
                                         publishers=publishers, relay=relay, shared=shared)
                for key, edge in collapse_assertions(rows).items()}

    loaded = [as_loaded(doc) for doc in documents]
    before = verdicts(state["rows"], quotes_by_assertion(state["links"], state["source_quotes"]))
    after = verdicts(*rows_after_load(list(state["rows"]), state["links"], state["source_quotes"], loaded))
    changes: list[dict[str, Any]] = []
    for key in sorted(after):
        old = best_evidence(c.level for c in before[key]) if key in before else None
        new = best_evidence(c.level for c in after[key])
        if old != new:
            changes.append({"edge": list(key), "before": old, "after": new,
                            "after_withheld": sorted({c.withheld for c in after[key] if c.withheld})})
    return changes


def graph_increment(state: Mapping[str, Any], documents: list[Mapping[str, Any]], session: Any) -> dict[str, Any]:
    """本包入圖後圖上**真的多出來**的節點、canonical 邊、claims——與文件宣告數分開（2026-10-08，Phase 7 failure log #17）。

    事發：決策區塊的「圖影響」數的是凍結 payload 裡每份抽取**宣告**的節點／邊／claims。抽取檔會重新宣告它引用到的既有節點，
    更正走廊的新版更是整份重宣告——[699] 印 +19 節點、20 邊、12 claims，實際新增 3 節點、4 邊、4 claims（L12：一個數字兩種語意）。
    `state`＝`fetch_evidence_state` 的現值（呼叫端已在同一個唯讀 session 取過）；邊照 `rows_after_load`（loader 的 MERGE 語意）前後
    各收斂一次（`collapse_assertions` 的 canonical key）；節點與 claims 查 `:Entity` 的 id 在不在圖上（Claim 也是 `:Entity`）。
    """
    from query.bottleneck import collapse_assertions

    loaded = [as_loaded(doc) for doc in documents]
    node_ids = sorted({str(n["id"]) for d in loaded for n in d.get("nodes") or () if n.get("id")})
    claim_ids = sorted({str(c["id"]) for d in loaded for c in d.get("claims") or () if c.get("id")})
    on_graph = {str(r["id"]) for r in session.run("MATCH (n:Entity) WHERE n.id IN $ids RETURN n.id AS id",
                                                  ids=node_ids + claim_ids)}
    before = set(collapse_assertions(state["rows"]))
    after_rows, _quotes = rows_after_load(list(state["rows"]), state["links"], state["source_quotes"], loaded)
    declared_edges = set(collapse_assertions(
        [{"src": e.get("src_id"), "relation": e.get("relation"), "dst": e.get("dst_id")}
         for d in loaded for e in d.get("edges") or ()]))
    new_edges = sorted(set(collapse_assertions(after_rows)) - before)
    return {
        "status": "checked",
        "nodes": {"new": [n for n in node_ids if n not in on_graph], "declared": len(node_ids)},
        "edges": {"new": [list(key) for key in new_edges], "declared": len(declared_edges)},
        "claims": {"new": [c for c in claim_ids if c not in on_graph], "declared": len(claim_ids)},
    }


def increment_line(check: Mapping[str, Any] | None) -> str | None:
    """「圖影響」那一行的數字（決策區塊與 RA packet 共用；failure log #17）。沒有收據＝None（呼叫端退回宣告數並標明）。"""
    if not check:
        return None
    if check.get("status") != "checked":
        return f"增量無法核對（{check.get('reason') or 'upstream_unavailable'}）——下列是文件宣告數，不是增量"
    parts, kept = [], 0
    for key, label in (("nodes", "節點"), ("edges", "邊"), ("claims", "claims")):
        block = check.get(key) or {}
        new = len(block.get("new") or ())
        parts.append(f"{new} {label}")
        kept += max(0, int(block.get("declared") or 0) - new)
    return f"新增 {'、'.join(parts)}" + (f"（另 {kept} 筆已在圖上或逐字保留）" if kept else "")


def evidence_lines(check: Mapping[str, Any] | None) -> list[str]:
    """「入圖後證據等級會變的邊」那幾行（RA packet；遷移工具有自己的全圖比對）。沒有收據＝不印（舊紀錄 render 不變）。"""
    if not check:
        return []
    from query.bottleneck import EVIDENCE_LABEL
    from query.origin_resolution import WITHHELD_LABELS

    if check.get("status") != "checked":
        return [f"- 證據等級預告無法核對（{check.get('status') or 'upstream_unavailable'}）：{check.get('reason') or ''}"
                "——不是「不會變」"]
    changes = check.get("changes") or []
    if not changes:
        return ["- 入圖後沒有任何一條邊的證據等級會變"]
    lines = [f"- 入圖後證據等級會變的邊 {len(changes)} 條："]
    for change in changes:
        before = EVIDENCE_LABEL.get(str(change.get("before")), "新邊") if change.get("before") else "新邊"
        after = EVIDENCE_LABEL.get(str(change.get("after")), str(change.get("after")))
        withheld = [WITHHELD_LABELS.get(str(w), str(w)) for w in change.get("after_withheld") or ()]
        note = f"（沒升外部印證：{'、'.join(withheld)}）" if withheld else ""
        lines.append(f"  - `{' '.join(change['edge'])}`：{before} → {after}{note}")
    return lines


def has_side_effects(result: Mapping[str, Any]) -> bool | None:
    """有沒有會改到既有值的副作用（新節點、新 SourceDoc 不算）。讀不到圖＝None（不知道），不是 False。"""
    if result.get("status") != "checked":
        return None
    return bool(result.get("node_overwrites") or result.get("source_doc_conflicts"))


def render_lines(result: Mapping[str, Any], *, doc_id: str | None = None) -> list[str]:
    """給人看的幾行（遷移 dry-run 與 RA packet 共用）。"""
    head = f"`{doc_id}`：" if doc_id else ""
    if result.get("status") != "checked":
        return [f"- {head}副作用無法核對（{result.get('status') or 'upstream_unavailable'}）：{result.get('reason') or ''}"]
    lines: list[str] = []
    for item in result.get("node_overwrites") or ():
        lines.append(f"- {head}節點 `{item['node']}` 的 `{item['field']}` 會被覆寫：{item['graph']!r} → {item['after']!r}")
    for item in result.get("alias_unions") or ():
        lines.append(f"- {head}節點 `{item['node']}` 別名聯集：新增 {item['added']}（圖上 {item['graph']}）")
    for item in result.get("attribute_additions") or ():
        lines.append(f"- {head}節點 `{item['node']}` 新增屬性鍵：{item['added']}")
    for item in result.get("source_doc_conflicts") or ():
        flag = "（⚠ 日期倒退）" if item.get("regression") else ""
        lines.append(f"- {head}SourceDoc 的 `{item['field']}` 會被改：{item['graph']!r} → {item['after']!r}{flag}")
    if not lines:
        lines.append(f"- {head}不會改到圖上任何既有節點屬性或 SourceDoc 欄位"
                     + (f"（新節點 {len(result.get('new_nodes') or ())} 個）" if result.get("new_nodes") else ""))
    return lines


__all__ = ["NODE_OVERWRITE_FIELDS", "SOURCE_DOC_COALESCE_FIELDS", "SOURCE_DOC_OVERWRITE_FIELDS", "as_loaded",
           "compute_side_effects", "evidence_after_load", "evidence_lines", "fetch_evidence_state", "fetch_graph_state",
           "has_side_effects", "quotes_by_assertion", "render_lines", "rows_after_load", "side_effects"]
