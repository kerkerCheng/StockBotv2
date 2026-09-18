"""把 `extractions/*.json` 裡的逐字回填進圖（V1 / L18）。

**為什麼需要一支獨立腳本，而不是重跑 `loader.load()`：**
`load()` 會把整份文件重走一遍（節點、邊、claim、URL 重複檢查、entity id 解析），
那些步驟各自有保留與覆寫規則，對「只是要把漏掉的逐字補上」來說 blast radius 太大。
V1 宣稱**純新增、既有輸出逐位不變**，所以這裡只做兩件事：

1. `MERGE (:Source)` — 逐字本身
2. `MERGE (n)-[:QUOTES]->(:Source)` — 把 `source_ids` 從懸空字串變成走得到的邊

⚠ **一個既有欄位都不寫。** `source_ids` 原樣不動（既有消費端照舊讀它），
節點的 `name`／`attributes`／邊的屬性完全不碰。

⚠ **Cypher 一律消費 `loader.load_to_neo4j` 的常數，不在這裡另寫一份**——
同一個寫入語意有兩份實作，第二份會立刻開始偏離（L16）。

用法：
    python scripts/backfill_source_quotes.py --dry-run
    python scripts/backfill_source_quotes.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loader.load_to_neo4j import (  # noqa: E402
    LINK_QUOTES,
    MERGE_SOURCE,
    evidence_id,
)


def _docs(extraction_dir: Path):
    for path in sorted(extraction_dir.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"  ⚠ 跳過 {path.name}：{exc}", file=sys.stderr)
            continue
        if not (doc.get("source_doc") or {}).get("doc_id"):
            continue
        yield path, doc


def plan(extraction_dir: Path) -> dict:
    """要寫什麼——dry-run 與實跑共用同一份計畫，避免預覽與實際不同。"""
    sources: list[dict] = []
    links: list[tuple[str, list[str]]] = []
    docs = 0
    for _path, doc in _docs(extraction_dir):
        docs += 1
        doc_id = doc["source_doc"]["doc_id"]
        for src in doc.get("sources", []):
            if not src.get("id"):
                continue
            sources.append({
                "id": src["id"],
                "locator": src.get("locator"),
                "quote": src.get("quote"),
                "source_doc_id": doc_id,
            })
        # ⚠ 三種載體都帶 source_ids，三種都要接——漏掉一種就是又一個只對一半的機制（L17-3）。
        for node in doc.get("nodes", []):
            if node.get("source_ids"):
                links.append((node["id"], list(node["source_ids"])))
        for edge in doc.get("edges", []):
            if edge.get("source_ids"):
                links.append((evidence_id(doc_id, edge["id"]), list(edge["source_ids"])))
        for claim in doc.get("claims", []):
            if claim.get("source_ids"):
                links.append((evidence_id(doc_id, claim["id"]), list(claim["source_ids"])))
    return {"docs": docs, "sources": sources, "links": links}


def main() -> int:
    ap = argparse.ArgumentParser(description="把抽取檔的逐字回填進圖（純新增）")
    ap.add_argument("--extractions", default=str(ROOT / "extractions"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    p = plan(Path(args.extractions))
    quoted = sum(1 for s in p["sources"] if s["quote"])
    chars = sum(len(s["quote"] or "") for s in p["sources"])
    print(f"抽取檔 {p['docs']} 份｜Source {len(p['sources'])} 筆"
          f"（其中帶逐字 {quoted} 筆、{chars:,} 字元）｜QUOTES 連結 {len(p['links'])} 組")

    if args.dry_run:
        print("[dry-run] 不連 DB。")
        return 0

    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    load_dotenv(ROOT / ".env")
    pw = os.environ.get("NEO4J_PASSWORD")
    if not pw:
        print("請設 NEO4J_PASSWORD", file=sys.stderr)
        return 1

    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), pw),
    )
    linked = 0
    try:
        with driver.session() as session:
            for i, src in enumerate(p["sources"], 1):
                session.run(MERGE_SOURCE, **src).consume()
                if i % 250 == 0:
                    print(f"  …Source {i}/{len(p['sources'])}")
            for node_id, source_ids in p["links"]:
                rec = session.run(LINK_QUOTES, id=node_id, source_ids=source_ids).single()
                linked += (rec or {}).get("linked", 0) or 0
    finally:
        driver.close()

    print(f"✓ Source {len(p['sources'])} 筆已 MERGE｜QUOTES 邊命中 {linked} 條")
    print("下一步查證：MATCH (s:Source) RETURN count(s)；"
          "MATCH ()-[q:QUOTES]->() RETURN count(q)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
