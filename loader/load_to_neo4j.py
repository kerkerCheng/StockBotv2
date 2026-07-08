"""
load_to_neo4j.py — 把 DB 無關的中介 JSON(intermediate_format)MERGE 進 Neo4j。

這是「JSON → DB」的可替換 loader(見 graph_schema.md §0)。
唯一綁 Neo4j 的地方就是這支;換 DB 只要換這層。

跨文件合併策略(v0,故意簡單):
- node/edge 以 id MERGE;重複出現就把 source_ids 聯集、confidence 取 max。
- 真正的信心累加/衝突解析等之後撞到再升級,不要現在過度設計(L2)。

用法:
    pip install neo4j
    export NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=...
    python loader/load_to_neo4j.py samples/cpo_external_laser_source.json

加 --dry-run 只印出要跑的操作、不連 DB(沒裝 neo4j 也能測邏輯)。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# ── Ticker Map (Plan B — source of truth for A→C join key) ────────────────────
# 人工維護；LLM 不生成 ticker（避免幻覺）。
# 私人公司明確設 None（區分「已知無 ticker」vs「尚未建檔」）。
# 新公司 onboarding 後在此補上對應 ticker。
TICKER_MAP: dict[str, str | None] = {
    "co:coherent":   "COHR",
    "co:lumentum":   "LITE",
    "co:broadcom":   "AVGO",
    "co:nvidia":     "NVDA",
    "co:tsmc":       "TSM",
    "co:intel":      "INTC",
    "co:samsung":    "005930.KS",
    "co:apple":      "AAPL",
    "co:corning":    "GLW",
    "co:arista":     "ANET",
    "co:meta":       "META",
    "co:google":     "GOOGL",
    "co:jabil":      "JBL",
    "co:anthropic":  None,   # 私人公司，明確 null
    "co:openai":     None,   # 私人公司，明確 null
    # Sivers Semiconductors AB — 瑞典上市 (Nasdaq First North Stockholm)
    # yfinance ticker: SIVE.ST；非美股，EDGAR 無資料，文件走 IR 人工下載路徑
    "co:sivers_semiconductors": "SIVE.ST",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rel_type(relation: str) -> str:
    """relation 字彙 → Neo4j 關係 type(大寫)。"""
    return relation.upper()


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
    n.source_ids = $source_ids_merged,
    n.updated_at = $updated_at
RETURN n.id
"""

MERGE_EDGE = """
MATCH (a:Entity {id: $src_id})
MATCH (b:Entity {id: $dst_id})
MERGE (a)-[r:%s {id: $id}]->(b)
SET r.relation = $relation,
    r.attributes = $attributes_json,
    r.confidence = CASE WHEN r.confidence IS NULL OR r.confidence < $confidence THEN $confidence ELSE r.confidence END,
    r.source_ids = $source_ids_merged,
    r.updated_at = $updated_at
RETURN r.id
"""


def load(doc: dict, session, use_apoc: bool = False) -> None:
    ts = _now()

    # ── nodes ──
    for n in doc.get("nodes", []):
        attrs = dict(n.get("attributes", {}))
        # Inject ticker for known Company nodes (Engine A→C join key)
        if n.get("type") == "Company" and n["id"] in TICKER_MAP:
            attrs["ticker"] = TICKER_MAP[n["id"]]
        params = {
            "id": n["id"],
            "type": n["type"],
            "name": n["name"],
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
            session.run(MERGE_NODE, **params)
        else:
            # 純 Cypher:source_ids 聯集在讀回後處理較麻煩,v0 先直接覆寫成本文件的 source_ids。
            # (跨文件 source_ids 聯集等接 APOC 或改用批次 reconcile;見 graph_schema.md §0)
            params["source_ids_merged"] = n["source_ids"]
            session.run(MERGE_NODE_NOAPOC, **params)
            # type label 後補(純 Cypher 動態 label 需字串拼接)
            session.run(
                f"MATCH (n:Entity {{id:$id}}) SET n:`{n['type']}`", id=n["id"]
            )

    # ── edges ──
    for e in doc.get("edges", []):
        cypher = MERGE_EDGE % _rel_type(e["relation"])
        session.run(
            cypher,
            id=e["id"],
            src_id=e["src_id"],
            dst_id=e["dst_id"],
            relation=e["relation"],
            attributes_json=json.dumps(e.get("attributes", {}), ensure_ascii=False),
            confidence=e["confidence"],
            source_ids_merged=e["source_ids"],
            updated_at=ts,
        )

    # ── claims(v0:存成節點掛在 subject 上,之後再細化) ──
    for c in doc.get("claims", []):
        name = c.get("name") or (c["statement"][:30] + "…")
        session.run(
            """
            MERGE (cl:Claim:Entity {id: $id})
            SET cl.name = $name,
                cl.statement = $statement,
                cl.demand_proof_level = $dpl,
                cl.disproof_condition = $disproof,
                cl.confidence = $confidence,
                cl.source_ids = $source_ids,
                cl.updated_at = $updated_at
            WITH cl
            MATCH (s:Entity {id: $subject_id})
            MERGE (cl)-[:ABOUT]->(s)
            """,
            id=c["id"],
            name=name,
            statement=c["statement"],
            dpl=c["demand_proof_level"],
            disproof=c["disproof_condition"],
            confidence=c["confidence"],
            source_ids=c["source_ids"],
            subject_id=c["subject_id"],
            updated_at=ts,
        )


def dry_run(doc: dict) -> None:
    print(f"[dry-run] doc={doc['source_doc']['doc_id']} "
          f"tier={doc['source_doc']['evidence_tier']}")
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
    with driver.session() as session:
        load(doc, session, use_apoc=args.apoc)
    driver.close()
    print(f"loaded {args.json_path} into {uri}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
