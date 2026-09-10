"""把圖裡的存量節點對齊 `config/entity_aliases.json`（pq2 [506]）。

## 為什麼需要它

`identity/entities.py` 只作用於**未來**的抽取——loader 在入圖前把 alias id 解析成
canonical。**圖裡既有的節點不會自己合併**，那是 graph write，走 pq2。

## 與 `migrate_nand_merge_20260910.py` 的關係

那支是 [505] 的一次性 scoped 遷移（NAND，五個 id，語意判斷）。本支是它的泛化版：
**吃 registry 的每一組 canonical**，因此新增登記之後可以直接重跑，不必再寫一支
一次性腳本——重造第二支腳本的那天起，兩邊就會開始漂移（L16）。

冪等：已經合併完的組，`aliases_present` 會是空的，該組直接跳過。

## 要重載哪些抽取檔——用推導的，不是寫死的

節點的 `source_ids` 形如 `<doc_id>_s<N>`，正則就拿得到 doc_id。寫死清單會在下一次
新增登記時漏掉（那正是 [505] 手動列 RELOAD_DOCS 的代價）。
⚠ 必須**含 canonical 端自己的來源文件**，否則 canonical 節點的屬性不會被寫進去。

⚠ **doc_id 不等於檔名**，必須掃一次 `extractions/` 建索引：
`cpo_chip_package_paper.json` 的 doc_id 是
`Electronic_Chip_Package_and_CPO_Technology_for_Modern_AI_Era`。第一版用檔名拼路徑，
於是回報「抽取檔不存在」而中止——但那是查錯了，不是它不存在（L11-5）。

⚠ **而且 doc_id → 抽取檔是一對多。** 全庫 229 份檔案只有 206 個 doc_id，
**21 組共用、涉及 44 份**——那是刻意的 addendum 慣例（同一份來源文件分多次抽取，
共用 doc_id 讓 SourceDoc 不重複）。第二版用 `dict[str, Path]` 存索引，後掃到的覆蓋
先掃到的，於是 `tech:eml` 合併後少了 `Broadcom_q2fy26_cpo_s1`／`_s12`
（重載到 addendum、漏掉正本）。**漏掉不會有東西壞掉，只會安靜地少一段 provenance。**

## 刻意不做

- **不改抽取檔。** 解析在 loader 入圖前發生，抽取檔是逐字證據，不為搬節點而改寫。
- **不新增任何知識主張。** 只重指邊、保留每條原始 provenance 與 SourceDoc。
- **不碰 registry 沒登記的 id。** 登記門檻（機械 or 已核准的語意判斷）就是這支腳本的
  授權邊界；它不自己判斷「這兩個看起來很像」。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from identity import entities as entity_registry
from loader.extraction_index import build_index
from loader.edge_resolution import project_edge_keys
from loader.load_to_neo4j import load
from loader.migrate_entity_dedup_20260904 import _admin_driver

_SOURCE_ID = re.compile(r"^(?P<doc>.+)_s\d+$")


def _doc_ids(source_ids) -> set[str]:
    out: set[str] = set()
    for source_id in source_ids or ():
        match = _SOURCE_ID.match(str(source_id))
        if match:
            out.add(match.group("doc"))
    return out


def _plan(session, index: dict[str, tuple[Path, ...]]) -> list[dict]:
    """每一組登記 → 它在圖裡的現況與要重載的文件。"""

    plan: list[dict] = []
    for canonical_id, entry in sorted(entity_registry.load().items()):
        aliases = list(entry.get("aliases") or ())
        rows = {
            record["id"]: record["source_ids"]
            for record in session.run(
                "MATCH (n:Entity) WHERE n.id IN $ids "
                "RETURN n.id AS id, n.source_ids AS source_ids",
                ids=[canonical_id, *aliases],
            )
        }
        present = [a for a in aliases if a in rows]
        docs: set[str] = set()
        for source_ids in rows.values():
            docs |= _doc_ids(source_ids)
        missing_docs = sorted(d for d in docs if d not in index)
        plan.append({
            "canonical": canonical_id,
            "basis": entry.get("basis"),
            "approval_receipt": entry.get("approval_receipt"),
            "aliases_present": present,
            "canonical_present": canonical_id in rows,
            "reload_docs": sorted(docs - set(missing_docs)),
            "missing_extractions": missing_docs,
            "skip": not present,
        })
    return plan


def migrate(*, dry_run: bool, backup_dir: str | None) -> dict:
    if not dry_run and not backup_dir:
        raise RuntimeError("live migration 需要 --backup-dir（先跑 backup_private.py run）")
    if not dry_run:
        export = Path(backup_dir).resolve() / "neo4j_export.json"
        if not export.is_file() or export.stat().st_size == 0:
            raise RuntimeError(f"找不到 Neo4j 匯出或為空：{export}")

    index = build_index()
    driver = _admin_driver()
    result: dict = {
        "dry_run": dry_run,
        "backup_dir": backup_dir,
        "extractions_indexed": sum(len(v) for v in index.values()),
        "doc_ids_indexed": len(index),
    }
    try:
        with driver.session() as session:
            plan = _plan(session, index)
            result["plan"] = plan
            todo = [group for group in plan if not group["skip"]]
            result["groups_to_migrate"] = [g["canonical"] for g in todo]

            # 有 source_ids 指向不存在的抽取檔就停——重載會漏掉那份的節點屬性，
            # 而漏掉不會有任何東西壞掉，只會安靜地少一段 provenance。
            broken = {g["canonical"]: g["missing_extractions"]
                      for g in todo if g["missing_extractions"]}
            if broken:
                raise RuntimeError(f"下列組的 source 指向不存在的抽取檔：{broken}")

            if dry_run:
                for group in todo:
                    group["edges_moving"] = [
                        dict(row) for row in session.run(
                            "MATCH (a)-[r]->(b) WHERE a.id IN $ids OR b.id IN $ids "
                            "RETURN a.id AS src, type(r) AS rel, b.id AS dst",
                            ids=group["aliases_present"],
                        )
                    ]
                return result

            moved_keys: set[str] = set()
            for group in todo:
                aliases = group["aliases_present"]
                for doc_id in group["reload_docs"]:
                    # 一個 doc_id 可能有多份抽取檔——全部重載，不是只挑一份。
                    for path in index[doc_id]:
                        doc = json.loads(path.read_text(encoding="utf-8"))
                        load(doc, session, allow_dup_url=True)
                keys = session.run(
                    "MATCH (e:EdgeAssertion) WHERE e.src_id IN $ids OR e.dst_id IN $ids "
                    "RETURN collect(DISTINCT e.edge_key) AS keys",
                    ids=[group["canonical"], *aliases],
                ).single()["keys"]
                moved_keys |= {k for k in keys if k}
                group["dropped_assertions"] = session.run(
                    "MATCH (e:EdgeAssertion) WHERE e.src_id IN $ids OR e.dst_id IN $ids "
                    "DETACH DELETE e RETURN count(e) AS c", ids=aliases,
                ).single()["c"]
                group["dropped_nodes"] = session.run(
                    "MATCH (n:Entity) WHERE n.id IN $ids DETACH DELETE n RETURN count(n) AS c",
                    ids=aliases,
                ).single()["c"]

        result["reprojected"] = project_edge_keys(driver, moved_keys)
        with driver.session() as session:
            result["verify"] = [
                {
                    "canonical": group["canonical"],
                    "aliases_still_present": [
                        r["id"] for r in session.run(
                            "MATCH (n:Entity) WHERE n.id IN $ids RETURN n.id AS id",
                            ids=group["aliases_present"],
                        )
                    ],
                    "edges": [
                        dict(row) for row in session.run(
                            "MATCH (a)-[r]->(b) WHERE a.id = $c OR b.id = $c "
                            "RETURN a.id AS src, type(r) AS rel, b.id AS dst",
                            c=group["canonical"],
                        )
                    ],
                }
                for group in todo
            ]
    finally:
        driver.close()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backup-dir", default=None)
    args = parser.parse_args()
    print(json.dumps(
        migrate(dry_run=args.dry_run, backup_dir=args.backup_dir),
        ensure_ascii=False, indent=2, default=str,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
