"""回填既有 SourceDoc 的 `published_at`／`retrieved_at`——**不需 pq2 核准**。

判準與四道補償控制寫在 `loader/source_dating.py` 的模組 docstring，那裡是權威；
這支只是它的 CLI。與 `scripts/record_mechanical_observation.py` 是同一個形狀：
**mechanical 的東西要有自己的走廊，否則判準改了而走廊沒改，等於改了個寂寞。**

⚠ 這支**不是** graph admission。它寫不進任何 claim、邊或判讀屬性；
讓新的知識主張進圖仍然是 pq2，一個字都不放寬。

用法：
    # 看還有誰沒定日，以及 URL 裡導不導得出日期
    python scripts/backfill_source_dating.py --list

    # 單筆
    python scripts/backfill_source_dating.py \\
        --doc-id lumentum_q2fy26_cpo --value 2026-02-03 --method url_path \\
        --basis "URL 路徑 fool.com/earnings/call-transcripts/2026/02/03/"

    # 批次（JSON list，每項 doc_id/value/method/basis，可選 property）
    python scripts/backfill_source_dating.py --batch library/private/dating.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loader.source_dating import (  # noqa: E402
    DATING_METHODS,
    DatingRejected,
    apply_proposal,
    dates_in_url,
    fetch_document,
    undated_documents,
    validate_proposal,
)


def _driver():
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    load_dotenv(ROOT / ".env")
    return GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )


def _render_list(session) -> int:
    rows = undated_documents(session)
    print(f"未定日 SourceDoc {len(rows)} 份（右欄＝它擋住幾條 EdgeAssertion）\n")
    for row in rows:
        candidates = dates_in_url(row.get("url"))
        hint = (", ".join(d.isoformat() for d in candidates)
                if candidates else "url 導不出完整日期 → 需實際讀文件")
        print(f"  {row['assertions']:>3}  {row['id'][:64]:<64} {hint}")
    print(f"\n合計擋住 {sum(r['assertions'] for r in rows)} 條 EdgeAssertion")
    return 0


def _apply_one(session, item: dict, *, dry_run: bool, supersede: bool) -> bool:
    doc_id = str(item.get("doc_id") or "")
    prop = str(item.get("property") or "published_at")
    node = fetch_document(session, doc_id)
    try:
        proposal = validate_proposal(
            doc_id=doc_id, prop=prop, value=str(item.get("value") or ""),
            method=str(item.get("method") or ""), basis=str(item.get("basis") or ""),
            node=node, supersede=bool(item.get("supersede", supersede)),
        )
    except DatingRejected as exc:
        print(f"  ✗ {doc_id[:56]:<56} {exc}", file=sys.stderr)
        return False
    if dry_run:
        print(f"  · {doc_id[:56]:<56} {prop}={proposal.value}（dry-run，未寫入）")
        return True
    apply_proposal(session, proposal)
    print(f"  ✓ {doc_id[:56]:<56} {prop}={proposal.value}｜{proposal.method}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="列出尚未定日的 SourceDoc")
    parser.add_argument("--doc-id")
    parser.add_argument("--property", default="published_at")
    parser.add_argument("--value", help="ISO 日期")
    parser.add_argument("--method", help=" / ".join(DATING_METHODS))
    parser.add_argument("--basis", help="一手出處與定位，必填")
    parser.add_argument("--batch", help="JSON 檔，內容是回填項目的 list")
    parser.add_argument("--supersede", action="store_true",
                        help="允許覆蓋既有值（舊值會留在 basis 裡）")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    driver = _driver()
    try:
        with driver.session() as session:
            if args.list:
                return _render_list(session)

            if args.batch:
                items = json.loads(Path(args.batch).read_text(encoding="utf-8"))
                if not isinstance(items, list):
                    print("✗ --batch 的內容必須是 list", file=sys.stderr)
                    return 2
            elif args.doc_id:
                items = [{"doc_id": args.doc_id, "property": args.property,
                          "value": args.value, "method": args.method,
                          "basis": args.basis}]
            else:
                parser.print_help()
                return 2

            done = sum(_apply_one(session, item, dry_run=args.dry_run,
                                  supersede=args.supersede) for item in items)
            print(f"\n{done}/{len(items)} 筆通過"
                  f"{'（dry-run）' if args.dry_run else ''}")
            return 0 if done == len(items) else 1
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
