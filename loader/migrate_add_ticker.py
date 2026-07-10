"""
migrate_add_ticker.py — 把 TICKER_MAP 的 ticker 值補寫進已在 Neo4j 的 Company 節點。

新載入的文件已由 load_to_neo4j.py 自動注入 ticker；
此腳本只針對在 TICKER_MAP 加入前就已入圖的節點補齊。

用法:
    python loader/migrate_add_ticker.py
    python loader/migrate_add_ticker.py --dry-run   # 只列印要更新的節點，不寫 DB
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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loader.load_to_neo4j import TICKER_MAP


def migrate(dry_run: bool = False) -> int:
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("需要 neo4j 套件: pip install neo4j", file=sys.stderr)
        return 1

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    pw = os.environ.get("NEO4J_PASSWORD")
    if not pw:
        print("請設 NEO4J_PASSWORD", file=sys.stderr)
        return 1

    driver = GraphDatabase.driver(uri, auth=(user, pw))
    updated = 0
    skipped = 0

    with driver.session() as session:
        for company_id, ticker in TICKER_MAP.items():
            # 查現有節點
            result = session.run(
                "MATCH (n:Entity {id: $id}) RETURN n.attributes AS attrs",
                id=company_id,
            )
            record = result.single()
            if record is None:
                continue  # 節點不在圖中

            import json
            attrs = {}
            raw = record["attrs"]
            if raw:
                try:
                    attrs = json.loads(raw)
                except Exception:
                    attrs = {}

            current_ticker = attrs.get("ticker")
            if current_ticker == ticker:
                skipped += 1
                continue  # 已是最新值，跳過

            if dry_run:
                print(f"  [dry-run] {company_id}: ticker {current_ticker!r} → {ticker!r}")
                updated += 1
                continue

            # 寫入更新
            attrs["ticker"] = ticker
            session.run(
                "MATCH (n:Entity {id: $id}) SET n.attributes = $attrs",
                id=company_id,
                attrs=json.dumps(attrs, ensure_ascii=False),
            )
            print(f"  UPDATED {company_id}: ticker = {ticker!r}")
            updated += 1

    driver.close()

    action = "would update" if dry_run else "updated"
    print(f"\n{action} {updated} node(s), skipped {skipped} (already current)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill ticker into existing Neo4j Company nodes.")
    ap.add_argument("--dry-run", action="store_true", help="列印要更新的節點，不寫 DB")
    args = ap.parse_args()
    return migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
