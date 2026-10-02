"""身分清理（Phase 6 Step 6.2）：OpenLight 兩個代號合併、`co:nava_thailand` 退役——吃一份宣告式 manifest。

## 為什麼是這一支

`loader/migrate_entity_dedup_20260904.py` 的四步是對的（**改抽取檔 → 只重載那幾份 → 刪舊 id 的 assertion 與節點 → 重投影**；
抽取檔是 ground truth，不做 Cypher 手術），但它把合併對象寫死在常數、而且先要人手改好抽取檔。這次多兩件事：
**公司**身分（名冊 `config/company_identity.json` 要同一次改）與**入圖副作用**（Phase 4 #32：重載會用抽取檔的節點宣告覆寫圖上
`type`／`abstraction_level`／`role`，最後載入者贏）。所以本支：

- **dry-run 預設、什麼都不寫**：抽取檔與名冊的改動在記憶體裡算（manifest 驅動），印逐欄 diff、入圖副作用
  （`loader.merge_side_effects`，與 RA packet 同一個 owner）、**證據等級會變的邊**（當下的 `classify_evidence`，改前改後各算一次）、
  活的引用（lead registry／event_watches／讀圖／敘事 ledger）。
- `--apply`：要 `--pq2 N`（存在、未結案、`manual`、`ref_id` 等於 manifest 的 `pq2_ref`）＋`--backup-dir`（裡面要先有非空、
  counts 自洽的 `neo4j_export.json`）＋ writer lock；先用記憶體裡改好的抽取檔重載、刪舊、重投影，**再**寫抽取檔（改前的版本歸檔到
  `extractions/superseded/<doc_id>.<舊指紋8碼>.json`）與名冊——中途失敗時重跑就是再 MERGE 一次；最後**對真的圖逐條重算證據等級，
  必須等於 dry-run 的預告**（L13：驗收是產出，不是指令沒報錯）。
- `_supersede` 式的局部刪除、`_admin_driver` 沿用既有實作（不複製）；遷移走管理員憑證（routine writer 沒有 DELETE 權限——
  見 `migrate_entity_dedup_20260904._admin_driver` 的說明）。⚠ Neo4j 回 Forbidden 一律停下問使用者，不換憑證重試。

用法::

    python loader/migrate_identity_cleanup.py                       # dry-run（唯讀；印計畫 JSON）
    python loader/migrate_identity_cleanup.py --apply --pq2 N --backup-dir library/private/backups/<name>
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_MANIFEST = ROOT / "loader" / "manifests" / "identity-cleanup-20261003.json"
REGISTRY_PATH = ROOT / "config" / "company_identity.json"
EXTRACTIONS = ROOT / "extractions"
#: 節點宣告要照抄圖上現值的欄位（`MERGE_NODE` 會 SET 的那幾個；`migrate_relation_rejudge._NODE_FIELDS` 同一組）。
_ALIGN_FIELDS = ("type", "name", "abstraction_level", "role")
#: 活的引用：這幾份 authority 若還指著舊 id，遷移之後就是懸空參照——列出來（歷史紀錄 todo_pool 不算）。
_LIVE_REFERENCE_FILES = ("library/leads/pending_leads.json", "library/leads/event_watches.json",
                         "library/leads/hypotheses.json")
_LIVE_REFERENCE_DIRS = ("library/private/alpha/structure_readings", "library/private/alpha/briefs")


class IdentityCleanupError(RuntimeError):
    """計畫或前置條件不成立——沒有任何寫入。"""


# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------

def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if manifest.get("kind") != "identity_cleanup":
        raise IdentityCleanupError(f"{path}：kind 必須是 identity_cleanup")
    decisions = manifest.get("decisions") or {}
    if not decisions:
        raise IdentityCleanupError(f"{path}：decisions 是空的")
    for old_id, decision in decisions.items():
        if not str(old_id).startswith("co:") or not str(decision.get("into") or "").startswith("co:"):
            raise IdentityCleanupError(f"{path}：{old_id} 的決定必須是 co:* → co:*")
        if decision.get("action") not in ("merge_into", "retire_into_owner"):
            raise IdentityCleanupError(f"{path}：{old_id} 的 action 不認得：{decision.get('action')!r}")
        if not str(decision.get("why") or "").strip():
            raise IdentityCleanupError(f"{path}：{old_id} 沒有寫理由")
    removed = set((manifest.get("registry") or {}).get("remove") or ())
    if removed != set(decisions):
        raise IdentityCleanupError(f"{path}：名冊要刪的 {sorted(removed)} 必須等於決定的舊 id {sorted(decisions)}")
    if not str(manifest.get("pq2_ref") or "").strip():
        raise IdentityCleanupError(f"{path}：沒有 pq2_ref（apply 要核對編號掛的是不是這一份）")
    return manifest


def old_ids(manifest: Mapping[str, Any]) -> list[str]:
    return sorted(manifest["decisions"])


# ---------------------------------------------------------------------------
# 抽取檔的改動（純函式）
# ---------------------------------------------------------------------------

def _rename(value: Any, renames: Mapping[str, str]) -> Any:
    return renames.get(value, value) if isinstance(value, str) else value


def plan_extraction_edit(doc: Mapping[str, Any], ops: Mapping[str, Any],
                         graph_nodes: Mapping[str, Mapping[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """一份抽取檔 × 一組操作 → (改後的 doc, 逐項改動紀錄)。不讀檔、不連圖（圖上節點現值由呼叫端給）。

    操作（manifest 的 `extractions[]`）：
    - `rename_ids`：node id、edge 端點、claim subject 一起換（漏任何一處，節點合併了邊還指著舊 id）。
    - `delete_edges`：依 local id 刪邊。
    - `merge_edges`：`{id, into}`——把 `id` 的 `source_ids` 聯集進 `into`（同檔已有同一條邊時），再刪 `id`；
      `id` 自己的屬性**不**併入（紀錄裡列出被丟掉的屬性——它們由同一段逐字支持時應已在 `into` 上）。
    - `delete_nodes`：刪節點宣告（之後不得還有邊或 claim 指著它——否則拒收）。
    - `align_nodes_to_graph`：每個在圖上已存在的節點，宣告的 `type`／`name`／`abstraction_level`／`role`、別名（圖上在前聯集）、
      屬性（圖上鍵優先）、confidence（不高於圖上）照抄圖上現值——重載就不會覆寫別份文件寫下的值（Phase 4 #32）。
    """
    new = copy.deepcopy(dict(doc))
    changes: list[dict[str, Any]] = []
    renames = dict(ops.get("rename_ids") or {})
    if renames:
        for node in new.get("nodes") or ():
            if node.get("id") in renames:
                changes.append({"op": "rename_node", "from": node["id"], "to": renames[node["id"]]})
                node["id"] = renames[node["id"]]
        for edge in new.get("edges") or ():
            for end in ("src_id", "dst_id"):
                if edge.get(end) in renames:
                    changes.append({"op": "rename_edge_end", "edge": edge.get("id"), "end": end,
                                    "from": edge[end], "to": renames[edge[end]]})
                    edge[end] = renames[edge[end]]
        for claim in new.get("claims") or ():
            if claim.get("subject_id") in renames:
                changes.append({"op": "rename_claim_subject", "claim": claim.get("id"),
                                "from": claim["subject_id"], "to": renames[claim["subject_id"]]})
                claim["subject_id"] = renames[claim["subject_id"]]
        # 改名後同一個 id 宣告兩次：留第一個（之後 align 會照抄圖上值），source_ids 聯集
        seen: dict[str, dict] = {}
        merged_nodes = []
        for node in new.get("nodes") or ():
            first = seen.get(node["id"])
            if first is None:
                seen[node["id"]] = node
                merged_nodes.append(node)
                continue
            first["source_ids"] = list(dict.fromkeys([*first.get("source_ids", []), *node.get("source_ids", [])]))
            changes.append({"op": "merge_node_declarations", "node": node["id"]})
        new["nodes"] = merged_nodes

    edges_by_id = {str(e.get("id")): e for e in new.get("edges") or ()}
    drop: set[str] = set()
    for spec in ops.get("merge_edges") or ():
        src, dst = edges_by_id.get(str(spec["id"])), edges_by_id.get(str(spec["into"]))
        if src is None or dst is None:
            raise IdentityCleanupError(f"merge_edges：{spec} 指的邊不在 {new['source_doc']['doc_id']}")
        added = [s for s in src.get("source_ids") or () if s not in (dst.get("source_ids") or [])]
        dst["source_ids"] = [*dst.get("source_ids", []), *added]
        changes.append({"op": "merge_edge", "edge": spec["id"], "into": spec["into"],
                        "edge_was": [src.get("src_id"), src.get("relation"), src.get("dst_id")],
                        "into_is": [dst.get("src_id"), dst.get("relation"), dst.get("dst_id")],
                        "source_ids_added": added, "attributes_dropped": dict(src.get("attributes") or {}),
                        "into_attributes": dict(dst.get("attributes") or {})})
        drop.add(str(spec["id"]))
    for local_id in ops.get("delete_edges") or ():
        edge = edges_by_id.get(str(local_id))
        if edge is None:
            raise IdentityCleanupError(f"delete_edges：{local_id} 不在 {new['source_doc']['doc_id']}")
        changes.append({"op": "delete_edge", "edge": local_id,
                        "was": [edge.get("src_id"), edge.get("relation"), edge.get("dst_id")],
                        "attributes": dict(edge.get("attributes") or {})})
        drop.add(str(local_id))
    if drop:
        new["edges"] = [e for e in new.get("edges") or () if str(e.get("id")) not in drop]

    doomed = set(ops.get("delete_nodes") or ())
    if doomed:
        dangling = sorted({f"{e.get('id')}（{e.get('src_id')}→{e.get('dst_id')}）" for e in new.get("edges") or ()
                           if e.get("src_id") in doomed or e.get("dst_id") in doomed}
                          | {f"claim {c.get('id')}" for c in new.get("claims") or () if c.get("subject_id") in doomed})
        if dangling:
            raise IdentityCleanupError(f"delete_nodes：{sorted(doomed)} 還有邊或 claim 指著它：{dangling}")
        for node in new.get("nodes") or ():
            if node.get("id") in doomed:
                changes.append({"op": "delete_node", "node": node["id"]})
        new["nodes"] = [n for n in new.get("nodes") or () if n.get("id") not in doomed]

    if ops.get("align_nodes_to_graph"):
        from identity import entities as entity_registry

        for node in new.get("nodes") or ():
            # 以 loader 會 MERGE 的 canonical id 查圖（抽取檔裡可能是別名 id，例：tech:eml_laser）
            graph = graph_nodes.get(entity_registry.resolve(str(node.get("id"))))
            if graph is None:
                continue
            before = {f: node.get(f) for f in (*_ALIGN_FIELDS, "aliases", "attributes", "confidence")}
            for field in _ALIGN_FIELDS:
                node[field] = graph.get(field)
            graph_aliases = [str(a) for a in graph.get("aliases") or ()]
            node["aliases"] = graph_aliases + [a for a in (node.get("aliases") or []) if a not in graph_aliases]
            graph_attrs = graph.get("attrs")
            graph_attrs = json.loads(graph_attrs) if isinstance(graph_attrs, str) else dict(graph_attrs or {})
            node["attributes"] = {**dict(node.get("attributes") or {}), **graph_attrs}
            if isinstance(graph.get("confidence"), (int, float)) and isinstance(node.get("confidence"), (int, float)):
                node["confidence"] = min(node["confidence"], graph["confidence"])
            after = {f: node.get(f) for f in before}
            diff = {f: {"before": before[f], "after": after[f]} for f in before if before[f] != after[f]}
            if diff:
                changes.append({"op": "align_node_to_graph", "node": node["id"], "fields": diff})
    return new, changes


def references(doc: Mapping[str, Any], ids: Iterable[str]) -> list[str]:
    """這份 doc 裡還指著 `ids` 的地方（node／edge 端點／claim subject）。"""
    wanted = set(ids)
    found = [f"node {n.get('id')}" for n in doc.get("nodes") or () if n.get("id") in wanted]
    found += [f"edge {e.get('id')}" for e in doc.get("edges") or ()
              if e.get("src_id") in wanted or e.get("dst_id") in wanted]
    found += [f"claim {c.get('id')}" for c in doc.get("claims") or () if c.get("subject_id") in wanted]
    return found


# ---------------------------------------------------------------------------
# 名冊的改動（純函式）
# ---------------------------------------------------------------------------

def plan_registry_edit(registry: Mapping[str, Any], spec: Mapping[str, Any], *,
                       pq2: int | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    new = copy.deepcopy(dict(registry))
    companies = list(new.get("companies") or ())
    by_id = {c["company_id"]: c for c in companies}
    changes: list[dict[str, Any]] = []
    for company_id in spec.get("remove") or ():
        if company_id not in by_id:
            raise IdentityCleanupError(f"名冊沒有 {company_id}——manifest 與名冊不一致（已經遷移過？）")
        changes.append({"op": "remove", "company": company_id, "entry": by_id[company_id]})
    keep = [c for c in companies if c["company_id"] not in set(spec.get("remove") or ())]
    for company_id, fields in (spec.get("set") or {}).items():
        target = next((c for c in keep if c["company_id"] == company_id), None)
        if target is None:
            raise IdentityCleanupError(f"名冊沒有 {company_id}（要寫 {sorted(fields)}）")
        for field, value in fields.items():
            text = str(value).replace("{pq2}", str(pq2) if pq2 is not None else "（鑄號後填）")
            changes.append({"op": "set", "company": company_id, "field": field, "before": target.get(field),
                            "after": text})
            target[field] = text
    new["companies"] = keep
    return new, changes


def registry_from_json(data: Mapping[str, Any]):
    """把名冊 JSON（記憶體裡的）做成 `IdentityRegistry`——與 `IdentityRegistry.from_path` 同一條解析路。"""
    import tempfile

    from identity.registry import IdentityRegistry

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "company_identity.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return IdentityRegistry.from_path(path)


# ---------------------------------------------------------------------------
# 證據等級：改前改後各算一次（純函式）
# ---------------------------------------------------------------------------

def rows_after_edit(rows: list[Mapping[str, Any]], quotes: Mapping[str, list[str]],
                    edited: Mapping[str, tuple[Mapping[str, Any], Mapping[str, Any]]], gone_ids: Iterable[str]
                    ) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """`fetch_assertions` 的列 → 遷移之後會長的樣子。`edited`：doc_id → (改前的抽取檔, 改後的抽取檔)。

    - 只換掉**那個抽取檔**原本那幾條邊的 assertion（`evidence_id(doc_id, local_id)`）——同一個 doc_id 的另一份抽取檔
      （addendum）不重載，它的 assertion 留著（2026-10-03 dry-run 撞到：`lumentum_q2fy26_coverage_addendum_2026_08_30`）。
    - 改後的邊照 loader 換成 canonical id（`merge_side_effects.as_loaded`）——圖上的列本來就是 canonical id。
    - 任何還指著舊 id 的列刪掉（`_drop` 那一步）。逐字跟著 assertion id 走。"""
    from loader.load_to_neo4j import evidence_id
    from loader.merge_side_effects import as_loaded

    gone = set(gone_ids)
    replaced = {evidence_id(doc_id, str(e["id"])) for doc_id, (before, _after) in edited.items()
                for e in before.get("edges") or ()}
    new_rows = [dict(r) for r in rows if str(r.get("assertion_id") or "") not in replaced
                and r.get("src") not in gone and r.get("dst") not in gone]
    new_quotes = {k: list(v) for k, v in quotes.items()}
    template_by_doc = {}
    for r in rows:
        template_by_doc.setdefault(r.get("source_doc_id"), r)
    for doc_id, (_before, after_doc) in edited.items():
        doc = as_loaded(after_doc)
        source_doc = doc.get("source_doc") or {}
        template = template_by_doc.get(doc_id) or {}
        quote_by_source = {s["id"]: s.get("quote") for s in doc.get("sources") or () if s.get("id")}
        for edge in doc.get("edges") or ():
            aid = evidence_id(doc_id, edge["id"])
            new_rows.append({
                "src": edge["src_id"], "relation": edge["relation"], "dst": edge["dst_id"],
                "attributes": json.dumps(edge.get("attributes") or {}, ensure_ascii=False),
                "confidence": edge.get("confidence"), "origin": source_doc.get("origin_entity"),
                "source_type": source_doc.get("source_type"), "origin_linkage": source_doc.get("origin_linkage"),
                "source_doc_id": doc_id,
                "published_at": source_doc.get("published_at") or template.get("published_at"),
                "assertion_id": aid,
            })
            texts = [quote_by_source[s] for s in edge.get("source_ids") or () if quote_by_source.get(s)]
            if texts:
                new_quotes[aid] = texts
            else:
                new_quotes.pop(aid, None)
    return new_rows, new_quotes


def evidence_by_edge(rows: Iterable[Mapping[str, Any]], registry: Any) -> dict[tuple[str, str, str], str]:
    from query.bottleneck import classify_evidence, collapse_assertions

    out: dict[tuple[str, str, str], str] = {}
    for key, edge in collapse_assertions(rows).items():
        out[key] = classify_evidence(edge.src, edge.origins, registry, filing_origins=edge.filing_origins,
                                     origin_linkages=edge.origin_linkages)
    return out


def evidence_changes(before: Mapping[tuple, str], after: Mapping[tuple, str]) -> list[dict[str, Any]]:
    out = []
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            out.append({"edge": list(key), "before": before.get(key), "after": after.get(key)})
    return out


# ---------------------------------------------------------------------------
# 讀（dry-run 與 apply 共用）
# ---------------------------------------------------------------------------

def _read_graph(driver, docs: Mapping[str, Mapping[str, Any]], gone: list[str],
                extra_ids: Iterable[str] = ()) -> dict[str, Any]:
    import neo4j

    from loader.merge_side_effects import as_loaded
    from query.bottleneck import fetch_assertions
    from query.sub_language import fetch_all_quotes

    # 改名的目標（例：co:openlight_photonics）不在原抽取檔的節點宣告裡，但照抄現值要讀得到它
    ids: set[str] = set(extra_ids)
    for doc in docs.values():
        ids |= {str(n["id"]) for n in as_loaded(doc).get("nodes") or ()}
    with driver.session(default_access_mode=neo4j.READ_ACCESS) as session:
        def work(tx):
            nodes = {str(r["id"]): dict(r) for r in tx.run(
                "MATCH (n:Entity) WHERE n.id IN $ids RETURN n.id AS id, n.type AS type, n.name AS name, "
                "n.abstraction_level AS abstraction_level, n.role AS role, n.aliases AS aliases, n.attributes AS attrs, "
                "n.confidence AS confidence", ids=sorted(ids))}
            old_refs = tx.run(
                "MATCH (e:EdgeAssertion) WHERE e.src_id IN $ids OR e.dst_id IN $ids "
                "RETURN e.id AS id, e.source_doc_id AS doc", ids=gone).data()
            claims = tx.run("MATCH (c:Claim) WHERE c.subject_node_id IN $ids RETURN c.id AS id", ids=gone).data()
            return {"rows": fetch_assertions(tx), "quotes": fetch_all_quotes(tx), "nodes": nodes,
                    "old_refs": old_refs, "old_claims": claims}
        return session.execute_read(work)


def live_references(gone: Iterable[str], *, root: Path = ROOT) -> dict[str, int]:
    """活的 authority 檔裡還指著舊 id 的次數（檔案 → 次數）。todo_pool 是歷史紀錄，不在這裡。"""
    import re

    pattern = re.compile("|".join(re.escape(i) + r"(?![a-z0-9_])" for i in gone))
    hits: dict[str, int] = {}
    paths = [root / p for p in _LIVE_REFERENCE_FILES]
    for directory in _LIVE_REFERENCE_DIRS:
        paths += sorted((root / directory).glob("*.jsonl"))
    for path in paths:
        try:
            n = len(pattern.findall(path.read_text(encoding="utf-8")))
        except OSError:
            continue
        if n:
            hits[path.relative_to(root).as_posix()] = n
    return hits


def plan(manifest: Mapping[str, Any], *, driver, root: Path = ROOT, pq2: int | None = None) -> dict[str, Any]:
    """dry-run 的全部內容（唯讀）。apply 也先跑這一支，拿它的預告比對結果。"""
    from loader.merge_side_effects import as_loaded, compute_side_effects, fetch_graph_state

    gone = old_ids(manifest)
    files = {spec["file"]: json.loads((root / "extractions" / spec["file"]).read_text(encoding="utf-8"))
             for spec in manifest["extractions"]}
    docs = {doc["source_doc"]["doc_id"]: doc for doc in files.values()}
    targets = {d["into"] for d in manifest["decisions"].values()}
    targets |= {to for spec in manifest["extractions"] for to in (spec.get("rename_ids") or {}).values()}
    graph = _read_graph(driver, docs, gone, extra_ids=targets)

    edited: dict[str, dict[str, Any]] = {}
    extraction_report = []
    for spec in manifest["extractions"]:
        doc = files[spec["file"]]
        new_doc, changes = plan_extraction_edit(doc, spec, graph["nodes"])
        left = references(new_doc, gone)
        if left:
            raise IdentityCleanupError(f"{spec['file']} 改完仍指著舊 id：{left}")
        edited[doc["source_doc"]["doc_id"]] = new_doc
        extraction_report.append({"file": f"extractions/{spec['file']}", "doc_id": doc["source_doc"]["doc_id"],
                                  "changes": changes})

    # 預檢：其他抽取檔（不在 manifest）不得還指著舊 id——重載不到它們，刪舊時會連它們的證據一起刪掉
    others = []
    for path in sorted((root / "extractions").glob("*.json")):
        if path.name in files:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if any(f'"{i}"' in text for i in gone):
            others.append(path.name)
    if others:
        raise IdentityCleanupError(f"manifest 以外的抽取檔還指著舊 id：{others}——先把它們加進 manifest")
    stray = [r for r in graph["old_refs"] if r["doc"] not in edited]
    if stray or graph["old_claims"]:
        raise IdentityCleanupError(f"圖上還有不在 manifest 文件裡、指著舊 id 的 assertion／claim：{stray}／{graph['old_claims']}")

    # 入圖副作用：改後的抽取檔，對**現在的圖**（照抄之後應為 0）
    import neo4j

    side = {}
    with driver.session(default_access_mode=neo4j.READ_ACCESS) as session:
        for doc_id, doc in edited.items():
            loaded = as_loaded(doc)
            side[doc_id] = compute_side_effects(loaded, session.execute_read(lambda tx: fetch_graph_state(tx, loaded)))

    registry_now = json.loads((root / "config" / "company_identity.json").read_text(encoding="utf-8"))
    registry_new, registry_changes = plan_registry_edit(registry_now, manifest["registry"], pq2=pq2)
    reg_before = registry_from_json(registry_now)
    reg_after = registry_from_json(registry_new)
    before = evidence_by_edge(graph["rows"], reg_before)
    rows_new, _quotes_new = rows_after_edit(graph["rows"], graph["quotes"],
                                            {doc_id: (docs[doc_id], edited[doc_id]) for doc_id in edited}, gone)
    after = evidence_by_edge(rows_new, reg_after)

    from query.bottleneck import company_id_for_origin

    origin_checks = {origin: company_id_for_origin(origin, reg_after)
                     for origin in ("OpenLight", "OpenLight Photonics", "OpenLight Photonics Inc.", "Lumentum")}
    return {
        "manifest": manifest.get("date"), "pq2_ref": manifest["pq2_ref"], "old_ids": gone,
        "extractions": extraction_report, "edited_docs": edited,
        "side_effects": side,
        "registry": {"changes": registry_changes, "companies_before": len(registry_now["companies"]),
                     "companies_after": len(registry_new["companies"])},
        "registry_new": registry_new,
        "graph_old_refs": graph["old_refs"],
        "evidence_changes": evidence_changes(before, after),
        # 改後全圖每條邊的預告等級（apply 之後對真的圖逐條比；dry-run 印出時拿掉）
        "evidence_after": {" ".join(k): v for k, v in sorted(after.items())},
        "origin_resolution_after": origin_checks,
        "live_references": live_references(gone, root=root),
    }


# ---------------------------------------------------------------------------
# apply（要 pq2 go）
# ---------------------------------------------------------------------------

def check_approval(n: int, manifest: Mapping[str, Any], *, pool_path: Path | None = None) -> dict:
    """[n] 存在且未結案、型別 manual、ref_id 等於 manifest 的 pq2_ref。授權載體仍是對話中的明確 go；這一道只擋打錯號。"""
    from engine_b import todo

    pool = todo.load(pool_path or todo.DEFAULT_POOL_PATH)
    try:
        item = todo.get(pool, n)
    except todo.TodoError as exc:
        raise IdentityCleanupError(f"[{n}] 不存在或已結案——--apply 只接受本 manifest 掛的、尚未結案的 pq2 編號") from exc
    if item.get("type") != "manual" or str(item.get("ref_id") or "") != manifest["pq2_ref"]:
        raise IdentityCleanupError(f"[{n}] 不是本 manifest 掛的項（type={item.get('type')}、ref_id={item.get('ref_id')}；"
                                   f"要 manual 且 ref_id＝{manifest['pq2_ref']}）——沒有任何寫入")
    return item


def check_backup(backup_dir: str | Path) -> tuple[int, int]:
    from scripts.backup_private import verify_neo4j_export

    export = Path(backup_dir) / "neo4j_export.json"
    if not export.is_file() or export.stat().st_size == 0:
        raise IdentityCleanupError(f"找不到 Neo4j 匯出或為空：{export}（先用 scripts/backup_private.py 的 export_neo4j_payload 匯出）")
    return verify_neo4j_export(export)


def _write_extraction(path: Path, doc: Mapping[str, Any], *, root: Path) -> dict[str, Any]:
    from intake.provenance import canonical_extraction_hash

    with path.open(encoding="utf-8", newline="") as handle:     # 原樣讀（保留 CRLF／LF），歸檔才是逐位的舊版
        raw = handle.read()
    before = json.loads(raw)
    old_hash = canonical_extraction_hash(before)
    archive = root / "extractions" / "superseded" / f"{before['source_doc']['doc_id']}.{old_hash[:8]}.json"
    if not archive.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_text(raw, encoding="utf-8", newline="")
    # 兩份檔都是 indent=2（2026-10-03 核對）；換行字元照原檔，git diff 只剩真正改的那幾行
    newline = "\r\n" if "\r\n" in raw else "\n"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline=newline)
    return {"file": path.relative_to(root).as_posix(), "superseded_archive": archive.relative_to(root).as_posix(),
            "extraction_sha256": {"before": old_hash, "after": canonical_extraction_hash(doc)},
            "file_sha256": {"before": hashlib.sha256(raw.encode("utf-8")).hexdigest()}}


def apply(manifest: Mapping[str, Any], *, pq2: int, backup_dir: str | Path, driver, root: Path = ROOT) -> dict[str, Any]:
    from loader.edge_resolution import project_edge_keys
    from loader.load_to_neo4j import edge_key, load
    from loader.merge_side_effects import as_loaded

    check_approval(pq2, manifest)
    nodes_n, rels_n = check_backup(backup_dir)
    planned = plan(manifest, driver=driver, root=root, pq2=pq2)
    if any(r.get("status") != "checked" or r.get("node_overwrites") or r.get("source_doc_conflicts")
           for r in planned["side_effects"].values()):
        raise IdentityCleanupError("改後的抽取檔重載仍有入圖副作用（或核對不了）——停下，沒有任何寫入："
                                   + json.dumps(planned["side_effects"], ensure_ascii=False)[:600])
    gone = planned["old_ids"]
    # ⚠ 順序：**先寫圖（用記憶體裡改好的抽取檔），再寫檔案與名冊**。反過來的話，寫圖中途失敗（例：Forbidden）時檔案已改、
    # 圖還沒改，重跑時 manifest 對不上已改的名冊（「已經遷移過？」）就續不了；這個順序下重跑只是再 MERGE 一次（冪等）。
    keys: set[str] = set()
    with driver.session() as session:
        for doc in planned["edited_docs"].values():
            load(copy.deepcopy(doc), session, allow_dup_url=True)
            keys |= {edge_key(e["src_id"], e["relation"], e["dst_id"]) for e in as_loaded(doc).get("edges") or ()}
        dropped_assertions = session.run(
            "MATCH (e:EdgeAssertion) WHERE e.src_id IN $ids OR e.dst_id IN $ids DETACH DELETE e RETURN count(e) AS c",
            ids=gone).single()["c"]
        dropped_nodes = session.run(
            "MATCH (n:Entity) WHERE n.id IN $ids DETACH DELETE n RETURN count(n) AS c", ids=gone).single()["c"]
    projection = project_edge_keys(driver, keys)

    with driver.session() as session:
        still = session.run("MATCH (n:Entity) WHERE n.id IN $ids RETURN collect(n.id) AS ids", ids=gone).single()["ids"]
        legacy = session.run("MATCH ()-[r]->() WHERE NOT type(r) IN ['CITES','ABOUT','QUOTES','FROM_DOC'] "
                             "AND r.edge_key IS NULL RETURN count(r) AS c").single()["c"]
    if still:
        raise IdentityCleanupError(f"舊 id 仍在圖上：{still}")
    if legacy:
        raise IdentityCleanupError(f"仍有未投影的邊：{legacy}")

    # 圖已經是新版——抽取檔（ground truth，L10）與名冊立刻跟上；之後驗收不過也照寫（否則重建會把合併倒回去）
    written = []
    for spec in manifest["extractions"]:
        doc_id = json.loads((root / "extractions" / spec["file"]).read_text(encoding="utf-8"))["source_doc"]["doc_id"]
        written.append(_write_extraction(root / "extractions" / spec["file"], planned["edited_docs"][doc_id], root=root))
    registry_path = root / "config" / "company_identity.json"
    with registry_path.open(encoding="utf-8", newline="") as handle:
        newline = "\r\n" if "\r\n" in handle.read() else "\n"
    registry_path.write_text(json.dumps(planned["registry_new"], ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8", newline=newline)

    # 驗收是產出（L13）：對真的圖重算證據等級（用寫進去的那份名冊），必須逐條等於 dry-run 的預告
    import neo4j

    from identity.registry import IdentityRegistry
    from query.bottleneck import fetch_assertions

    with driver.session(default_access_mode=neo4j.READ_ACCESS) as session:
        rows_real = session.execute_read(lambda tx: fetch_assertions(tx))
    real_after = {" ".join(k): v for k, v in evidence_by_edge(
        rows_real, IdentityRegistry.from_path(registry_path)).items()}
    # dry-run 的「改後」那一邊——**全圖逐條**比，不只比預告會變的那幾條（沒預告到的變動一樣是錯）
    predicted = planned["evidence_after"]
    mismatched = [{"edge": k, "predicted": predicted.get(k), "real": real_after.get(k)}
                  for k in sorted(set(predicted) | set(real_after)) if predicted.get(k) != real_after.get(k)]
    result = {
        "kind": "identity_cleanup_result", "at": datetime.now(timezone.utc).isoformat(), "pq2": int(pq2),
        "backup": {"dir": str(backup_dir), "nodes": nodes_n, "relationships": rels_n},
        "extractions_written": written, "registry_changes": planned["registry"]["changes"],
        "dropped_assertions": dropped_assertions, "dropped_nodes": dropped_nodes, "projection": projection,
        "evidence_changes": planned["evidence_changes"], "evidence_mismatch_vs_dry_run": mismatched,
        "origin_resolution_after": planned["origin_resolution_after"],
    }
    out = root / "loader" / "manifests" / f"identity-cleanup-{manifest['date'].replace('-', '')}.result.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    if mismatched:
        raise IdentityCleanupError(f"真的圖重算的證據等級與 dry-run 預告不同（{len(mismatched)} 條）——見 {out}")
    return result


def _summary(planned: Mapping[str, Any]) -> dict[str, Any]:
    """dry-run 印出來的版本：拿掉整份改後抽取檔與名冊（太長；逐項改動已在 extractions／registry.changes）。"""
    return {k: v for k, v in planned.items() if k not in ("edited_docs", "registry_new", "evidence_after")}


def main(argv: list[str] | None = None) -> int:
    from loader.migrate_entity_dedup_20260904 import _admin_driver

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--apply", action="store_true", help="寫抽取檔、名冊與圖（要 --pq2 與 --backup-dir）")
    parser.add_argument("--pq2", type=int, default=None, help="--apply 必填：使用者明確 go 的 pq2 編號")
    parser.add_argument("--backup-dir", default=None, help="--apply 必填：裡面要有非空的 neo4j_export.json")
    args = parser.parse_args(argv)
    if args.apply and (args.pq2 is None or not args.backup_dir):
        parser.error("--apply 必須帶 --pq2 與 --backup-dir（圖寫入要經使用者核准，且先有匯出）")
    try:
        manifest = load_manifest(Path(args.manifest))
    except (OSError, ValueError, IdentityCleanupError) as exc:
        print(f"✗ manifest 不合法：{exc}", file=sys.stderr)
        return 2
    driver = _admin_driver() if args.apply else _read_driver()
    try:
        if not args.apply:
            print(json.dumps(_summary(plan(manifest, driver=driver)), ensure_ascii=False, indent=2, default=str))
            return 0
        from engine_b.writer_lock import INTERACTIVE_OWNER, acquire, release

        acquire(INTERACTIVE_OWNER, ttl_minutes=30, purpose=f"身分清理遷移（pq2 [{args.pq2}]）")
        try:
            result = apply(manifest, pq2=args.pq2, backup_dir=args.backup_dir, driver=driver)
        finally:
            release(INTERACTIVE_OWNER)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except IdentityCleanupError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 2
    finally:
        driver.close()


def _read_driver():
    """dry-run 用的連線：與 query 層同一份（`NEO4J_*`），只開 READ session。"""
    from query.structure import _graph_driver

    return _graph_driver()


if __name__ == "__main__":
    raise SystemExit(main())
