"""
load_to_neo4j.py — 把 DB 無關的中介 JSON(intermediate_format)MERGE 進 Neo4j。

這是「JSON → DB」的可替換 loader(見 graph_schema.md §0)。
唯一綁 Neo4j 的地方就是這支;換 DB 只要換這層。

跨文件合併策略:
- domain edge 以(src_id, relation, dst_id)產生的穩定 edge_key MERGE。
- 每份文件的 edge 候選值另存為 EdgeAssertion，不讓後載入文件覆寫屬性。
- Claim 與 EdgeAssertion id 都加 doc_id 前綴，document-local id 不進全域圖。
- canonical edge 的 confidence 只代表關係存在；屬性由 projector 從 assertions 投影。

用法:
    pip install neo4j
    export NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=...
    python loader/load_to_neo4j.py samples/cpo_external_laser_source.json

加 --dry-run 只印出要跑的操作、不連 DB(沒裝 neo4j 也能測邏輯)。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from identity.registry import TICKER_MAP

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

#: 非公司實體的 canonical-id registry。**在任何 MERGE 之前解析**——節點合併了但邊
#: 還指著舊 id，會產生指不到的端點，比不合併更糟。
from identity import entities as entity_registry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rel_type(relation: str) -> str:
    """relation 字彙 → Neo4j 關係 type(大寫)。"""
    normalized = relation.lower()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", normalized):
        raise ValueError(f"unsafe relationship type: {relation!r}")
    return normalized.upper()


def edge_key(src_id: str, relation: str, dst_id: str) -> str:
    """Return the stable identity for a canonical domain relationship."""

    identity = json.dumps(
        [src_id, relation.lower(), dst_id],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return "edge:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()


def evidence_id(doc_id: str, local_id: str) -> str:
    """Namespace document-local evidence IDs without double-prefixing reloads."""

    prefix = f"{doc_id}_"
    return local_id if local_id.startswith(prefix) else prefix + local_id


def _execute(session, query: str, **params):
    """Execute a write eagerly so commit/permission failures surface in-call."""

    result = session.run(query, **params)
    consume = getattr(result, "consume", None)
    if callable(consume):
        consume()
    return result


# node.type → 額外 label(:Entity 之外)
def _node_labels(node_type: str) -> list[str]:
    return ["Entity", node_type]


MERGE_NODE = """
MERGE (n:Entity {id: $id})
SET n.type = $type,
    n.name = $name,
    n.abstraction_level = $abstraction_level,
    n.role = $role,
    n.aliases = $aliases,
    n.attributes = $attributes_json,
    n.confidence = CASE WHEN n.confidence IS NULL THEN $confidence
                        ELSE (CASE WHEN n.confidence > $confidence THEN n.confidence ELSE $confidence END) END,
    n.source_ids = CASE WHEN n.source_ids IS NULL THEN $source_ids
                        ELSE apoc.coll.toSet(n.source_ids + $source_ids) END,
    n.updated_at = $updated_at
WITH n
CALL apoc.create.addLabels(n, $extra_labels) YIELD node
RETURN node.id
"""

# 不依賴 APOC 的後備版(label 與 source_ids 聯集用 Python/Cypher 純表達式處理)
MERGE_NODE_NOAPOC = """
MERGE (n:Entity {id: $id})
SET n.type = $type,
    n.name = $name,
    n.abstraction_level = $abstraction_level,
    n.role = $role,
    n.aliases = $aliases,
    n.attributes = $attributes_json,
    n.confidence = CASE WHEN n.confidence IS NULL OR n.confidence < $confidence THEN $confidence ELSE n.confidence END,
    n.source_ids = reduce(acc = coalesce(n.source_ids, []), source_id IN $source_ids |
                          CASE WHEN source_id IN acc THEN acc ELSE acc + source_id END),
    n.updated_at = $updated_at
RETURN n.id
"""

MERGE_EDGE = """
MATCH (a:Entity {id: $src_id})
MATCH (b:Entity {id: $dst_id})
MERGE (a)-[r:%s {edge_key: $edge_key}]->(b)
SET r.id = $edge_key,
    r.relation = $relation,
    r.attributes = $attributes_json,
    r.confidence = CASE WHEN r.confidence IS NULL OR r.confidence < $confidence THEN $confidence ELSE r.confidence END,
    r.source_ids = reduce(acc = coalesce(r.source_ids, []), source_id IN $source_ids |
                          CASE WHEN source_id IN acc THEN acc ELSE acc + source_id END),
    r.source_doc_ids = reduce(acc = coalesce(r.source_doc_ids, []), source_doc_id IN $source_doc_ids |
                              CASE WHEN source_doc_id IN acc THEN acc ELSE acc + source_doc_id END),
    r.updated_at = $updated_at
RETURN r.edge_key
"""

# ⚠ `published_at`／`retrieved_at` 用 coalesce，**其餘欄位照舊直接覆寫**。
# 理由：抽取 JSON 沒帶日期時原本會 SET 成 null，把
# `scripts/backfill_source_dating.py` 補上的日期靜默洗掉——而那個日期正是
# as-of 投影的唯一時間線索，洗掉的後果是回測重新看到未來（F-31 的形狀）。
# 帶了值仍以抽取 JSON 為準（一手優先）；值若與回填當時不同，
# 節點上的 `published_at_backfilled` 會與現值分歧，由 audit 的 PointInTime 抓出來。
MERGE_SOURCE_DOC = """
MERGE (sd:SourceDoc {id: $id})
SET sd.title = $title,
    sd.source_type = $source_type,
    sd.evidence_tier = $evidence_tier,
    sd.origin_entity = $origin_entity,
    sd.url = $url,
    sd.publisher = $publisher,
    sd.published_at = coalesce($published_at, sd.published_at),
    sd.retrieved_at = coalesce($retrieved_at, sd.retrieved_at),
    sd.storage_permission = $storage_permission,
    sd.permission_basis = $permission_basis,
    sd.section = $section
RETURN sd.id
"""

MERGE_EDGE_ASSERTION = """
MERGE (ea:EdgeAssertion {id: $assertion_id})
SET ea.local_id = $local_id,
    ea.edge_key = $edge_key,
    ea.src_id = $src_id,
    ea.relation = $relation,
    ea.dst_id = $dst_id,
    ea.attributes = $attributes_json,
    ea.confidence = $confidence,
    ea.source_ids = $source_ids,
    ea.source_doc_id = $source_doc_id,
    ea.updated_at = $updated_at
WITH ea
MATCH (sd:SourceDoc {id: $source_doc_id})
MERGE (ea)-[:CITES]->(sd)
RETURN ea.id
"""

MERGE_NODE_CLAIM = """
MERGE (cl:Claim:Entity {id: $id})
SET cl.local_id = $local_id,
    cl.name = $name,
    cl.statement = $statement,
    cl.demand_proof_level = $dpl,
    cl.disproof_condition = $disproof,
    cl.confidence = $confidence,
    cl.source_ids = $source_ids,
    cl.source_doc_id = $source_doc_id,
    cl.subject_kind = $subject_kind,
    cl.subject_node_id = $subject_node_id,
    cl.subject_edge_key = null,
    cl.updated_at = $updated_at
WITH cl
MATCH (sd:SourceDoc {id: $source_doc_id})
MERGE (cl)-[:CITES]->(sd)
WITH cl
MATCH (s:Entity {id: $subject_node_id})
MERGE (cl)-[:ABOUT]->(s)
RETURN cl.id
"""

MERGE_EDGE_CLAIM = """
MERGE (cl:Claim:Entity {id: $id})
SET cl.local_id = $local_id,
    cl.name = $name,
    cl.statement = $statement,
    cl.demand_proof_level = $dpl,
    cl.disproof_condition = $disproof,
    cl.confidence = $confidence,
    cl.source_ids = $source_ids,
    cl.source_doc_id = $source_doc_id,
    cl.subject_kind = $subject_kind,
    cl.subject_node_id = null,
    cl.subject_edge_key = $subject_edge_key,
    cl.updated_at = $updated_at
WITH cl
MATCH (sd:SourceDoc {id: $source_doc_id})
MERGE (cl)-[:CITES]->(sd)
RETURN cl.id
"""


class DuplicateUrlError(RuntimeError):
    """Raised when a different doc_id already owns the same canonical source URL."""


def normalize_url(url) -> str | None:
    """Canonicalize a source URL for cross-doc_id dedup (host-lower, no fragment/trailing slash)."""
    if not isinstance(url, str) or not url.strip():
        return None
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    if parts.port:
        host = f"{host}:{parts.port}"
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), host, path, parts.query, ""))


def check_duplicate_url(source_doc: dict, session, allow_dup_url: bool = False) -> list[str]:
    """Fail closed if another SourceDoc already owns this URL under a different doc_id.

    Root-cause guard for silent duplicates: SourceDoc identity is the agent-assigned
    doc_id, so the same document under a new doc_id would otherwise create a second
    node with zero collision. Returns the clashing doc_ids (empty if none).

    正當例外——同文件多段抽取：同一 canonical URL 的多個 doc，只要**新 doc 與每個
    既有同 URL doc 都聲明了非空 `section` 且彼此不同**，就是刻意拆段（如年報財務段／
    光子段），放行且不算 clash。任一方缺 section 或 section 相同 → 仍當靜默重複擋下。
    """
    norm = normalize_url(source_doc.get("url"))
    if norm is None:
        return []
    doc_id = source_doc["doc_id"]
    new_section = (source_doc.get("section") or "").strip()
    rows = session.run(
        "MATCH (sd:SourceDoc) WHERE sd.url IS NOT NULL AND sd.id <> $doc_id "
        "RETURN sd.id AS id, sd.url AS url, sd.section AS section",
        doc_id=doc_id,
    )
    same_url = [
        (r["id"], (r["section"] or "").strip())
        for r in rows
        if normalize_url(r["url"]) == norm
    ]
    if not same_url:
        return []
    clashes = sorted({sid for sid, _ in same_url})
    legit_multi_section = bool(new_section) and all(
        sec and sec != new_section for _, sec in same_url
    )
    if legit_multi_section:
        print(
            f"[load] INFO: 同文件多段（section={new_section!r}），與 {clashes} 同 URL "
            f"但 section 互異，視為合法拆段放行",
            file=sys.stderr,
        )
        return []
    if not allow_dup_url:
        raise DuplicateUrlError(
            f"SourceDoc URL 已存在於 doc_id {clashes}（正規化 URL: {norm}）。"
            f"這很可能是同一份文件被以不同 doc_id 重複 onboard。"
            f"若為同一文件的不同段落，請為各段填不同的 source_doc.section 再載入；"
            f"若確為不同文件，重跑並加 --allow-dup-url。"
        )
    print(
        f"[load] WARN: URL 與既有 {clashes} 相同，--allow-dup-url 已放行",
        file=sys.stderr,
    )
    return clashes


def load_source_doc(doc: dict, session) -> None:
    """Materialize one extraction's immutable document-level provenance."""

    source_doc = doc["source_doc"]
    _execute(
        session,
        MERGE_SOURCE_DOC,
        id=source_doc["doc_id"],
        title=source_doc["title"],
        source_type=source_doc["source_type"],
        evidence_tier=source_doc["evidence_tier"],
        origin_entity=source_doc.get("origin_entity"),
        url=source_doc.get("url"),
        publisher=source_doc.get("publisher"),
        published_at=source_doc.get("published_at"),
        retrieved_at=source_doc.get("retrieved_at"),
        storage_permission=source_doc.get("storage_permission"),
        permission_basis=source_doc.get("permission_basis"),
        section=source_doc.get("section"),
    )


def load(doc: dict, session, use_apoc: bool = False, allow_dup_url: bool = False) -> None:
    ts = _now()
    doc_id = doc["source_doc"]["doc_id"]

    # ── canonical entity id ──
    # 抽取端每份文件由 LLM 自造 tech:／mat:／prod: id，於是同一層會被攤成多個節點
    # （2026-09-10 實測：NAND 6 個、DRAM 4 個）。在這裡解析一次，node／edge 端點／
    # claim subject 一起換，之後所有 MERGE 都吃 canonical id。
    # ⚠ 未登記的新 id **放行**（世界一直在長新的 tech 節點，擋下來等於停掉抽取），
    # 但一定要說出口——安靜放行就是下一個同義節點的來源。
    resolution = entity_registry.resolve_document(doc)
    # ⚠ 走 stderr：呼叫端（migrate_* 腳本）的 stdout 是要被 json.load() 解析的。
    # 診斷混進去會讓「已經成功」看起來像「解析失敗」（L12：一個 stream 兩種語意）。
    if resolution["remapped"]:
        for alias_id, canonical_id in sorted(resolution["remapped"].items()):
            print(f"  [entity-id] {alias_id} → {canonical_id}", file=sys.stderr)
    if resolution["unregistered"]:
        print(f"  [entity-id] 未登記的實體 id {len(resolution['unregistered'])} 個："
              f"{', '.join(resolution['unregistered'])}", file=sys.stderr)

    # Fail closed on the same source URL under a different doc_id (silent-duplicate guard).
    check_duplicate_url(doc["source_doc"], session, allow_dup_url)

    # SourceDoc must exist before Claim/EdgeAssertion CITES edges are created.
    load_source_doc(doc, session)

    # ── nodes ──
    for n in doc.get("nodes", []):
        attrs = dict(n.get("attributes", {}))
        # Inject ticker for known Company nodes (Engine A→C join key)
        if n.get("type") == "Company" and n["id"] in TICKER_MAP:
            attrs["ticker"] = TICKER_MAP[n["id"]]

        # ⚠ 既有節點的 name／attributes 不得被這次載入靜默覆蓋。
        # `MERGE_NODE` 只有 `source_ids` 會聯集；name 與 attributes 原本是直接 SET，
        # 於是**重載**一份既有文件就會改寫別的文件寫下的值（2026-09-10 實測改掉 7 個
        # name，其中 tech:vcsel 被改成產品規格）。要改 name 有明確路徑——migration 或
        # 人工 SET——不該是載入的副作用。
        name = n["name"]
        existing_rows = _execute(
            session,
            "MATCH (n:Entity {id: $id}) RETURN n.name AS name, n.attributes AS attrs",
            id=n["id"],
        )
        # ⚠ 不用 .single()：測試的 fake session 直接回 list，只有真實 driver 回 Result
        # ——假設回傳型別只有一種，正是本次要修的那個形狀（L17）。兩者都 iterable。
        existing = next(iter(existing_rows), None)
        if existing:
            prior_name = existing["name"]
            if prior_name and prior_name != name:
                print(f"  [node-merge] {n['id']} name 保留既有 {prior_name!r}"
                      f"（本次文件寫 {name!r}）", file=sys.stderr)
                name = prior_name
            prior_attrs = json.loads(existing["attrs"] or "{}")
            clashed = {k: (prior_attrs[k], attrs[k]) for k in attrs
                       if k in prior_attrs and prior_attrs[k] != attrs[k]}
            if clashed:
                print(f"  [node-merge] {n['id']} attributes 保留既有 {clashed}",
                      file=sys.stderr)
            # 既有 key 優先；本次文件只補上既有沒有的 key。
            attrs = {**attrs, **prior_attrs}

        params = {
            "id": n["id"],
            "type": n["type"],
            "name": name,
            "abstraction_level": n["abstraction_level"],
            "role": n.get("role"),
            "aliases": n.get("aliases", []),
            "attributes_json": json.dumps(attrs, ensure_ascii=False),
            "confidence": n["confidence"],
            "updated_at": ts,
        }
        if use_apoc:
            params["source_ids"] = n["source_ids"]
            params["extra_labels"] = [n["type"]]
            _execute(session, MERGE_NODE, **params)
        else:
            params["source_ids"] = n["source_ids"]
            _execute(session, MERGE_NODE_NOAPOC, **params)
            # type label 後補(純 Cypher 動態 label 需字串拼接)
            _execute(
                session,
                f"MATCH (n:Entity {{id:$id}}) SET n:`{n['type']}`", id=n["id"]
            )

    # ── edges ──
    edge_keys_by_local_id: dict[str, str] = {}
    for e in doc.get("edges", []):
        canonical_key = edge_key(e["src_id"], e["relation"], e["dst_id"])
        edge_keys_by_local_id[e["id"]] = canonical_key
        cypher = MERGE_EDGE % _rel_type(e["relation"])
        _execute(
            session,
            cypher,
            edge_key=canonical_key,
            src_id=e["src_id"],
            dst_id=e["dst_id"],
            relation=e["relation"],
            # U3b materializes attributes from assertions. Loading evidence must
            # never silently pick the last document's candidate value.
            attributes_json="{}",
            confidence=e["confidence"],
            source_ids=e["source_ids"],
            source_doc_ids=[doc_id],
            updated_at=ts,
        )
        _execute(
            session,
            MERGE_EDGE_ASSERTION,
            assertion_id=evidence_id(doc_id, e["id"]),
            local_id=e["id"],
            edge_key=canonical_key,
            src_id=e["src_id"],
            dst_id=e["dst_id"],
            relation=e["relation"],
            attributes_json=json.dumps(e.get("attributes", {}), ensure_ascii=False),
            confidence=e["confidence"],
            source_ids=e["source_ids"],
            source_doc_id=doc_id,
            updated_at=ts,
        )

    # ── claims ──
    for c in doc.get("claims", []):
        name = c.get("name") or (c["statement"][:30] + "…")
        local_id = c["id"]
        params = dict(
            id=evidence_id(doc_id, local_id),
            local_id=local_id,
            name=name,
            statement=c["statement"],
            dpl=c["demand_proof_level"],
            disproof=c["disproof_condition"],
            confidence=c["confidence"],
            source_ids=c["source_ids"],
            source_doc_id=doc_id,
            updated_at=ts,
        )
        if c["subject_id"] in edge_keys_by_local_id:
            params.update(
                subject_kind="edge",
                subject_edge_key=edge_keys_by_local_id[c["subject_id"]],
            )
            _execute(session, MERGE_EDGE_CLAIM, **params)
        else:
            params.update(
                subject_kind="node",
                subject_node_id=c["subject_id"],
            )
            _execute(session, MERGE_NODE_CLAIM, **params)


def dry_run(doc: dict) -> None:
    # dry-run 必須跑同一條解析，否則它預覽的是一份與實際載入不同的文件。
    resolution = entity_registry.resolve_document(doc)
    print(f"[dry-run] doc={doc['source_doc']['doc_id']} "
          f"tier={doc['source_doc']['evidence_tier']}")
    if resolution["remapped"]:
        print(f"  entity-id 改寫 : {resolution['remapped']}")
    if resolution["unregistered"]:
        print(f"  未登記實體 id  : {resolution['unregistered']}")
    print(f"  nodes : {len(doc.get('nodes', []))}")
    for n in doc.get("nodes", []):
        print(f"    MERGE (:{n['type']} {{id:{n['id']}}})  conf={n['confidence']}")
    print(f"  edges : {len(doc.get('edges', []))}")
    for e in doc.get("edges", []):
        print(f"    ({e['src_id']})-[:{_rel_type(e['relation'])}]->({e['dst_id']})")
    print(f"  claims: {len(doc.get('claims', []))}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apoc", action="store_true", help="用 APOC 做 label/source_ids 聯集")
    ap.add_argument("--allow-dup-url", action="store_true",
                    help="放行 URL 與既有 SourceDoc 相同的載入（預設 fail closed）")
    args = ap.parse_args()

    with open(args.json_path, encoding="utf-8") as f:
        doc = json.load(f)

    if args.dry_run:
        dry_run(doc)
        return 0

    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("需要 neo4j 套件: pip install neo4j(或用 --dry-run)", file=sys.stderr)
        return 1

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    pw = os.environ.get("NEO4J_PASSWORD")
    if not pw:
        print("請設 NEO4J_PASSWORD", file=sys.stderr)
        return 1

    driver = GraphDatabase.driver(uri, auth=(user, pw))
    try:
        with driver.session() as session:
            load(doc, session, use_apoc=args.apoc, allow_dup_url=args.allow_dup_url)
    except DuplicateUrlError as exc:
        print(f"FAIL CLOSED: {exc}", file=sys.stderr)
        return 1
    finally:
        driver.close()
    print(f"loaded {args.json_path} into {uri}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
