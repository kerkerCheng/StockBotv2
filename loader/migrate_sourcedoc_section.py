"""替既有 SourceDoc 補上 `section`，讓同一份文件可以合法拆成多段抽取。

為什麼需要這支：`check_duplicate_url` 的合法拆段條件是「新 doc 與每個既有同 URL
doc **都**聲明了非空且互異的 section」。2026-08-01 之前入圖的文件沒有分段概念，
`section` 一律是 null，因此任何「同一份文件因為不同研究目的被抽第二次」的需求都會
撞上 DuplicateUrlError——而那個守門本身是對的，錯的是舊資料缺一個 provenance 標籤。

這支只改 SourceDoc 的 `section` 一個欄位，不動任何 claim、edge 或既有 source_ids。
依 AGENTS.md L10：改既有資料前先寫 manifest（含改動前完整節點狀態）、支援 dry-run、
事後回查對帳。

用法:
    python loader/migrate_sourcedoc_section.py meta_vistara_isca_2026 \
        --section asic_and_deployment --reason "..." --dry-run
    python loader/migrate_sourcedoc_section.py meta_vistara_isca_2026 \
        --section asic_and_deployment --reason "..." --apply
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
except ImportError:  # pragma: no cover
    load_dotenv = None

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MANIFEST_DIR = ROOT / "loader" / "manifests"

READ_CYPHER = "MATCH (sd:SourceDoc {id: $doc_id}) RETURN properties(sd) AS props"
SAME_URL_CYPHER = (
    "MATCH (sd:SourceDoc) WHERE sd.url IS NOT NULL AND sd.id <> $doc_id "
    "RETURN sd.id AS id, sd.url AS url, sd.section AS section"
)
WRITE_CYPHER = "MATCH (sd:SourceDoc {id: $doc_id}) SET sd.section = $section RETURN sd.section AS section"


def _driver():
    if load_dotenv is not None:
        load_dotenv(ROOT / ".env")
    from neo4j import GraphDatabase

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise SystemExit("請設 NEO4J_PASSWORD")
    return GraphDatabase.driver(uri, auth=(user, password))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("doc_id")
    parser.add_argument("--section", required=True, help="非空的段落標籤")
    parser.add_argument("--reason", required=True, help="寫入 manifest 的變更理由")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    section = args.section.strip()
    if not section:
        raise SystemExit("--section 不可為空（空值等同沒有分段，守門仍會擋）")

    from loader.load_to_neo4j import normalize_url

    driver = _driver()
    try:
        with driver.session() as session:
            row = session.run(READ_CYPHER, doc_id=args.doc_id).single()
            if row is None:
                raise SystemExit(f"找不到 SourceDoc {args.doc_id}")
            before = dict(row["props"])
            current = (before.get("section") or "").strip()
            if current and current != section:
                raise SystemExit(
                    f"{args.doc_id} 已有 section={current!r}；本工具不覆寫既有分段標籤"
                )

            norm = normalize_url(before.get("url"))
            siblings = [
                (r["id"], (r["section"] or "").strip())
                for r in session.run(SAME_URL_CYPHER, doc_id=args.doc_id)
                if normalize_url(r["url"]) == norm
            ]
            clash = [sid for sid, sec in siblings if sec == section]
            if clash:
                raise SystemExit(f"section={section!r} 與同 URL 的 {clash} 重複")

            print(f"doc_id      : {args.doc_id}")
            print(f"url         : {before.get('url')}")
            print(f"section     : {before.get('section')!r} -> {section!r}")
            print(f"同 URL 的其他 doc: {siblings or '（無）'}")
            if args.dry_run:
                print("\n[dry-run] 未寫入。")
                return 0

            manifest = {
                "backed_up_at": datetime.now(timezone.utc).isoformat(),
                "reason": args.reason,
                "change": {
                    "doc_id": args.doc_id,
                    "field": "section",
                    "from": before.get("section"),
                    "to": section,
                },
                "objects": {"source_doc": before},
                "same_url_docs": [
                    {"id": sid, "section": sec or None} for sid, sec in siblings
                ],
            }
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
            path = MANIFEST_DIR / f"sourcedoc-section-{args.doc_id}-{stamp}.json"
            path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"\nmanifest -> {path.relative_to(ROOT).as_posix()}")

            written = session.run(
                WRITE_CYPHER, doc_id=args.doc_id, section=section
            ).single()
            after = dict(
                session.run(READ_CYPHER, doc_id=args.doc_id).single()["props"]
            )
            # 對帳：只有 section 該變，其餘欄位必須逐一相同。
            changed = {
                key
                for key in set(before) | set(after)
                if before.get(key) != after.get(key)
            }
            if changed != {"section"} or after.get("section") != section:
                raise SystemExit(f"對帳失敗：實際變動欄位={sorted(changed)}")
            print(f"✓ 已寫入 section={written['section']!r}；對帳通過（只有 section 變動）")
            return 0
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
