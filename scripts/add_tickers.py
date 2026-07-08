"""
add_tickers.py — 一次性 Cypher patch：把 ticker 欄位寫入現有 Company 節點。

這是 Engine C 的 P0 blocker 修補腳本（Plan A）。
Plan B（loader 層 TICKER_MAP）已合入 loader/load_to_neo4j.py，
確保未來新載入的公司自動帶 ticker。

用法:
    python scripts/add_tickers.py
    python scripts/add_tickers.py --dry-run   # 只印出要 patch 的節點，不寫入

設計根據:
    docs/solutions/architecture-patterns/knowledge-graph-data-quality-and-engine-c-join-key.md
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# loader 是 source of truth；這裡 import 確保兩邊同步
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from loader.load_to_neo4j import TICKER_MAP

PATCH_QUERY = """
MATCH (c:Entity {id: $node_id})
SET c.attributes = apoc.map.merge(
    coalesce(apoc.convert.fromJsonMap(coalesce(c.attributes, '{}')), {}),
    {ticker: $ticker}
)
RETURN c.id AS id, c.attributes AS attrs
"""

PATCH_QUERY_NOAPOC = """
MATCH (c:Entity {id: $node_id})
SET c.ticker = $ticker
RETURN c.id AS id
"""


def patch(driver, dry_run: bool = False) -> None:
    with driver.session() as session:
        for node_id, ticker in TICKER_MAP.items():
            label = ticker if ticker is not None else "(private/no ticker)"
            if dry_run:
                print(f"[dry-run] would patch {node_id} → {label}")
                continue

            try:
                result = session.run(PATCH_QUERY, node_id=node_id, ticker=ticker)
                record = result.single()
                if record:
                    print(f"patched  {node_id} → {label}")
                else:
                    print(f"skipped  {node_id} (node not in graph)")
            except Exception as e:
                if "apoc" in str(e).lower():
                    # APOC 不可用時退路：直接 SET 一個頂層 ticker 屬性
                    result = session.run(PATCH_QUERY_NOAPOC, node_id=node_id, ticker=ticker)
                    record = result.single()
                    if record:
                        print(f"patched  {node_id} → {label}  (no-APOC fallback)")
                    else:
                        print(f"skipped  {node_id} (node not in graph)")
                else:
                    print(f"ERROR    {node_id}: {e}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description="Patch ticker into existing Company nodes in Neo4j")
    ap.add_argument("--dry-run", action="store_true", help="只顯示要 patch 的節點，不寫入")
    args = ap.parse_args()

    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("需要 neo4j 套件: pip install neo4j", file=sys.stderr)
        return 1

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    pw = os.environ.get("NEO4J_PASSWORD")
    if not pw:
        print("請設 NEO4J_PASSWORD（或 .env）", file=sys.stderr)
        return 1

    driver = GraphDatabase.driver(uri, auth=(user, pw))
    try:
        print(f"{'[dry-run] ' if args.dry_run else ''}patching {len(TICKER_MAP)} entries...")
        patch(driver, dry_run=args.dry_run)
    finally:
        driver.close()

    if not args.dry_run:
        print("\n驗證查詢（可貼入 Neo4j Browser）:")
        print("  MATCH (c:Entity) WHERE c.type = 'Company' "
              "RETURN c.id, c.attributes, c.ticker ORDER BY c.id")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
