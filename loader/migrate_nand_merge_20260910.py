"""把五個 NAND 節點併進 canonical `tech:nand`（pq2 [505]，使用者 2026-09-10 核准選項 A）。

## 事發

圖裡 NAND 有六個 id。逐字讀完六份原文後，實際是 **5＋1**：

| id | name | 唯一／主要 quote |
|---|---|---|
| `tech:nand` ← canonical | NAND Flash Memory fabrication | AMAT 10-K |
| `tech:nand_technology` | NAND Flash Memory Fab | AMAT 10-Q「Revenue for Semiconductor Systems **by market**… Flash memory (NAND) 4%」 |
| `tech:nand_flash` | Flash Memory (NAND) | **同一段** by-market 營收拆分（兩份 10-Q） |
| `tech:nand_manufacturing` | NAND / Non-Volatile Memory Manufacturing | Lam 10-Q |
| `tech:nand_production` | NAND / non-volatile memory wafer fabrication | Lam 10-K「decreases in **non-volatile memory spending**… by our customers」 |

五份全部指向同一件事：**設備商賣給 NAND 製造市場的營收／客戶資本支出**。
⚠ `tech:nand_flash` 原被標成 `device_chip`（其餘 `foundry_packaging`），但它的兩份
source 就是 AMAT 的 by-market 營收拆分——那個分層沒有證據支持，故一併併入。

## 刻意不做的三件事

1. **不併 `tech:3d_nand_manufacturing`。** 它的唯一 quote 是「Lam Research Corporation
   is a global supplier of wafer fabrication equipment and services to the semiconductor
   industry.」——**完全沒提 3D NAND**。它不是重複節點，是 L6 Gap 4 型（LLM 從類別詞
   推斷出具體實體）的證據不足節點。合併會把一條沒有證據的邊洗進 canonical，之後就
   看不出它來歷可疑了。它連同它的 `co:lam_research SUPPLIES_TO` 邊留在原地，另案檢視。
2. **不改抽取檔。** 這是與 `migrate_entity_dedup_20260904.py` 的關鍵差異：那次沒有
   registry，只能改來源；現在 `identity/entities.py` 在 loader 入圖前解析，**抽取檔
   保持原樣**——它是逐字證據，本來就不該為了搬節點而被改寫。
3. **不新增任何知識主張。** 只重指邊、保留每條原始 provenance 與 SourceDoc。

## 為什麼是重載而不是 Cypher 手術

`edge_key = sha256([src_id, relation, dst_id])`——搬邊必須重算 key，手工改會弄髒
（沿用 09-04 的結論）。本支走 scoped 重載：**重載 5 份 → 刪掉舊 id 的 assertion 與
節點 → 重投影受影響的 edge_key**。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from identity import entities as entity_registry
from loader.edge_resolution import project_edge_keys
from loader.load_to_neo4j import load
from loader.migrate_entity_dedup_20260904 import _admin_driver

CANONICAL = "tech:nand"

#: 由 registry 讀，不在這裡再寫一份——重造一份清單的那天起，兩邊就會開始漂移（L16）。
def _aliases() -> list[str]:
    entry = entity_registry.load().get(CANONICAL)
    if not entry:
        raise RuntimeError(f"{CANONICAL} 不在 registry；先登記再遷移")
    if entry.get("basis") == "semantic_reviewed" and not entry.get("approval_receipt"):
        raise RuntimeError(f"{CANONICAL} 是語意登記但沒有核准 receipt")
    return list(entry.get("aliases") or ())


#: 要重載的抽取檔——**含 canonical 端**，否則新 id 的節點屬性不會被寫進去。
RELOAD_DOCS: tuple[str, ...] = (
    "amat_10_k_20251212",     # tech:nand（canonical）＋ tech:nand_production
    "amat_10_q_20260219",     # tech:nand_technology ＋ tech:nand_flash
    "amat_10_q_20260521",     # tech:nand_flash
    "lrcx_10_q_20260129",     # tech:nand_manufacturing
    "lrcx_10_k_20250811",     # tech:nand_production
)

#: 明確不動的節點——寫進程式碼而不是只寫在 docstring，這樣它是可執行的斷言。
KEEP_OUT: tuple[str, ...] = ("tech:3d_nand_manufacturing",)


def _preflight(session, aliases: list[str]) -> dict:
    """先驗來源，再動圖。

    這裡驗的不是「抽取檔有沒有改乾淨」（本支刻意不改抽取檔），而是
    **registry 會不會把它們解析到同一個 canonical**——那才是這次搬遷的依據。
    """

    unresolved = [a for a in aliases if entity_registry.resolve(a) != CANONICAL]
    if unresolved:
        raise RuntimeError(
            f"registry 沒有把這些 id 解析到 {CANONICAL}，重載後會原樣長回來：{unresolved}"
        )
    leaked = [k for k in KEEP_OUT if entity_registry.resolve(k) != k]
    if leaked:
        raise RuntimeError(
            f"KEEP_OUT 的節點被 registry 併掉了，與 [505] 選項 A 的核准範圍不符：{leaked}"
        )
    return {
        "canonical": CANONICAL,
        "aliases": aliases,
        "keep_out": list(KEEP_OUT),
        "nodes_before": session.run(
            "MATCH (n:Entity) WHERE n.id IN $ids RETURN collect(n.id) AS ids",
            ids=[CANONICAL, *aliases, *KEEP_OUT],
        ).single()["ids"],
        "legacy_edges_before": session.run(
            "MATCH ()-[r]->() WHERE NOT type(r) IN ['CITES','ABOUT'] "
            "AND r.edge_key IS NULL RETURN count(r) AS c"
        ).single()["c"],
    }


def _affected_edge_keys(session, aliases: list[str]) -> set[str]:
    rows = session.run(
        "MATCH (e:EdgeAssertion) WHERE e.src_id IN $ids OR e.dst_id IN $ids "
        "RETURN collect(DISTINCT e.edge_key) AS keys",
        ids=[CANONICAL, *aliases],
    ).single()["keys"]
    return {k for k in rows if k}


def _drop_duplicates(session, aliases: list[str]) -> dict:
    """刪掉舊 id 的節點與**只屬於它們**的 assertion。

    ⚠ 順序重要：先刪 assertion（它們帶著舊 `src_id`／`dst_id`，留著會讓
    `edge_resolution` 的 reconciliation 認為有 assertion 沒有對應 relationship）。
    """

    dropped_assertions = session.run(
        "MATCH (e:EdgeAssertion) WHERE e.src_id IN $ids OR e.dst_id IN $ids "
        "DETACH DELETE e RETURN count(e) AS c",
        ids=aliases,
    ).single()["c"]
    dropped_nodes = session.run(
        "MATCH (n:Entity) WHERE n.id IN $ids DETACH DELETE n RETURN count(n) AS c",
        ids=aliases,
    ).single()["c"]
    return {"dropped_assertions": dropped_assertions, "dropped_nodes": dropped_nodes}


def migrate(*, dry_run: bool, backup_dir: str | None) -> dict:
    if not dry_run and not backup_dir:
        raise RuntimeError("live migration 需要 --backup-dir（先跑 backup_private.py run）")
    if not dry_run:
        export = Path(backup_dir).resolve() / "neo4j_export.json"
        if not export.is_file() or export.stat().st_size == 0:
            raise RuntimeError(f"找不到 Neo4j 匯出或為空：{export}")

    aliases = _aliases()
    driver = _admin_driver()
    result: dict = {
        "dry_run": dry_run,
        "canonical": CANONICAL,
        "aliases": aliases,
        "keep_out": list(KEEP_OUT),
        "backup_dir": backup_dir,
    }
    try:
        with driver.session() as session:
            result["preflight"] = _preflight(session, aliases)
            if dry_run:
                result["would_reload"] = list(RELOAD_DOCS)
                result["would_drop_assertions"] = session.run(
                    "MATCH (e:EdgeAssertion) WHERE e.src_id IN $ids OR e.dst_id IN $ids "
                    "RETURN count(e) AS c", ids=aliases,
                ).single()["c"]
                result["would_drop_nodes"] = session.run(
                    "MATCH (n:Entity) WHERE n.id IN $ids RETURN count(n) AS c",
                    ids=aliases,
                ).single()["c"]
                result["edges_moving"] = [
                    dict(row) for row in session.run(
                        "MATCH (a)-[r]->(b) WHERE a.id IN $ids OR b.id IN $ids "
                        "RETURN a.id AS src, type(r) AS rel, b.id AS dst",
                        ids=aliases,
                    )
                ]
                return result

            for doc_id in RELOAD_DOCS:
                doc = json.loads(
                    (ROOT / "extractions" / f"{doc_id}.json").read_text(encoding="utf-8")
                )
                load(doc, session, allow_dup_url=True)
            result["reloaded"] = list(RELOAD_DOCS)
            result.update(_drop_duplicates(session, aliases))
            keys = _affected_edge_keys(session, aliases)

        result["reprojected"] = project_edge_keys(driver, keys)
        with driver.session() as session:
            result["nodes_after"] = session.run(
                "MATCH (n:Entity) WHERE n.id IN $ids RETURN collect(n.id) AS ids",
                ids=[CANONICAL, *aliases, *KEEP_OUT],
            ).single()["ids"]
            result["canonical_edges_after"] = [
                dict(row) for row in session.run(
                    "MATCH (a)-[r]->(b) WHERE a.id = $c OR b.id = $c "
                    "RETURN a.id AS src, type(r) AS rel, b.id AS dst", c=CANONICAL,
                )
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
