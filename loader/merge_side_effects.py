"""入圖副作用：一份抽取檔載入（`loader.load_to_neo4j.load`）時，會改到圖上**既有**節點與 SourceDoc 的哪些值——唯一 owner。

為什麼（Phase 6 Step 6.2，Phase 4 closeout #32）：`MERGE_NODE` 對 `type`／`abstraction_level`／`role` 是直接 `SET`、
`MERGE_SOURCE_DOC` 對大部分欄位也是直接 `SET`——**最後載入的那一份贏**（`loader/migrate_entity_dedup_20260904.py` 檔頭的
「順帶發現」）。重載一份文件（身分遷移、更正走廊、新的 RA）因此可能靜默改掉別份文件寫下的節點屬性或 SourceDoc 欄位，
而沒有任何東西會叫。這裡把「會改到什麼」在寫入**之前**算出來印給人看：遷移工具的 dry-run 與 RA packet 共用這一支（L16）。

- 只讀：`fetch_graph_state` 以呼叫端給的 session 查**這份文件會 MERGE 的節點與 SourceDoc 的現值**，不寫任何東西。
- 計算是純函式（`compute_side_effects`），合併規則照抄 loader：name／attributes／aliases 走 `preserve_existing_node_fields`
  （同一個函式，不重寫）、confidence 取大、`published_at`／`retrieved_at` 是 coalesce（抽取檔沒帶就保留圖上值）、其餘直接覆寫。
- 讀不到圖：`side_effects()` 回 `status=upstream_unavailable`——**不得印成「無副作用」**（成功與失敗同形，L13）。
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
           "compute_side_effects", "fetch_graph_state", "has_side_effects", "render_lines", "side_effects"]
