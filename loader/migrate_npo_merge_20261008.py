"""把同義節點 `tech:npo` 併進 canonical `tech:near_package_optics`（pq2 [752]，使用者 2026-10-08 go）。

## 事發

Phase 7 failure log #59（#36 的第二例）：NPO（近封裝光學）這一層被拆成兩個節點——

| id | name | 掛在上面的 |
|---|---|---|
| `tech:near_package_optics` ← canonical | Near-Packaged Optics (NPO) | Coherent、Aeva 供貨，NewPhotonics 光引擎、VCSEL 元件，Credo 的 NPO vs CPO 定義；NPO 層讀圖、Aeva 敘事的押注 |
| `tech:npo` | Near-Packaged Optics | Lumentum Q4 FY2026 法說一句話抽出的三筆：AI 算力 enables、enables `tech:cpo`、UHP 雷射 is_component_of |

需求句（Lumentum：客戶優先採用 near-packaged 架構）掛在 `tech:npo`、供貨掛在 canonical，兩邊各缺一半，
走圖第 6 型把 Aeva 報成「供貨走不到錨」、第 8 型把 `tech:npo` 報成「建模待補」。兩端逐字與例外理由寫在
`config/entity_aliases.json` 該筆的 note。兩者共用別名 NPO，第 9 型（id token 子集、名稱逐字相同）兩條都不中。

## 刻意不做的四件事

1. **canonical 不照「同組取最短 id」**：那會選 `tech:npo`，把讀圖、敘事押注與四份來源全部搬家；例外只在這一筆（比照 [730]）。
2. **不併 `tech:cpo`／`tech:scale_up_cpo`／`tech:scale_out_cpo`**（CPO 同義群另案）——寫進 `KEEP_OUT`，是可執行的斷言。
3. **不改抽取檔**：registry 在 loader 入圖前解析，抽取檔是逐字證據，保持原樣（同 09-10 NAND、10-07 FAU）。
4. **不新增任何知識主張**：只重指邊、保留每條原始 provenance 與 SourceDoc；UHP 雷射那條的 L6 Gap 4 疑點照搬、另案。

## 作法（同 `migrate_fau_merge_20261007.py`）

`edge_key = sha256([src_id, relation, dst_id])`——搬邊必須重算 key，所以走 scoped 重載：
**重載 1 份 → 刪掉舊 id 的節點與殘留 assertion → 重投影受影響的 edge_key**。
2026-10-08 乾跑（唯讀，記憶體換 id 後用 `loader.merge_side_effects`）：重載不覆寫任何既有節點屬性；canonical 多別名
「near-packaged optics」與屬性 ramp_difficulty_intrinsic=3，co:axt 多別名「AXT」（都是只增不改）。
**舊 id 上若有來自別份文件的 assertion 或 claim，preflight 直接拒絕**——重載改不到它們，刪除會吃掉證據。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from identity import entities as entity_registry
from loader.edge_resolution import project_edge_keys
from loader.load_to_neo4j import load
from loader.migrate_entity_dedup_20260904 import _admin_driver

CANONICAL = "tech:near_package_optics"
MANIFEST_DIR = ROOT / "library" / "private" / "graph_migrations"


#: 由 registry 讀，不在這裡再寫一份（L16）。
def _aliases() -> list[str]:
    entry = entity_registry.load().get(CANONICAL)
    if not entry:
        raise RuntimeError(f"{CANONICAL} 不在 registry；先登記再遷移")
    if entry.get("basis") == "semantic_reviewed" and entry.get("approval_receipt") != "todo:752":
        raise RuntimeError(f"{CANONICAL} 的核准 receipt 不是 todo:752：{entry.get('approval_receipt')!r}")
    return list(entry.get("aliases") or ())


#: 要重載的抽取檔——舊 id 只出現在這一份（preflight 驗），它同時宣告 canonical 節點。
RELOAD_DOCS: tuple[str, ...] = ("lite_transcript_q4fy2026",)

#: 明確不動的節點。
KEEP_OUT: tuple[str, ...] = ("tech:cpo", "tech:scale_up_cpo", "tech:scale_out_cpo")


def _preflight(session, aliases: list[str]) -> dict:
    """先驗來源與範圍，再動圖。"""

    unresolved = [a for a in aliases if entity_registry.resolve(a) != CANONICAL]
    if unresolved:
        raise RuntimeError(f"registry 沒有把這些 id 解析到 {CANONICAL}，重載後會原樣長回來：{unresolved}")
    leaked = [k for k in KEEP_OUT if entity_registry.resolve(k) != k]
    if leaked:
        raise RuntimeError(f"KEEP_OUT 的節點被 registry 併掉了，超出 [752] 的核准範圍：{leaked}")
    foreign_assertions = [
        dict(row) for row in session.run(
            "MATCH (e:EdgeAssertion) WHERE (e.src_id IN $ids OR e.dst_id IN $ids) "
            "AND NOT e.source_doc_id IN $docs "
            "RETURN e.id AS id, e.source_doc_id AS doc",
            ids=aliases, docs=list(RELOAD_DOCS),
        )
    ]
    foreign_claims = [
        dict(row) for row in session.run(
            "MATCH (c:Claim)-[:ABOUT]->(n:Entity) WHERE n.id IN $ids AND NOT c.source_doc_id IN $docs "
            "RETURN c.id AS id, c.source_doc_id AS doc",
            ids=aliases, docs=list(RELOAD_DOCS),
        )
    ]
    if foreign_assertions or foreign_claims:
        raise RuntimeError(
            "舊 id 上有不在 RELOAD_DOCS 的證據，重載改不到、刪除會吃掉它們——停："
            f"{foreign_assertions + foreign_claims}"
        )
    return {
        "canonical": CANONICAL,
        "aliases": aliases,
        "keep_out": list(KEEP_OUT),
        "nodes_before": session.run(
            "MATCH (n:Entity) WHERE n.id IN $ids RETURN collect(n.id) AS ids",
            ids=[CANONICAL, *aliases, *KEEP_OUT],
        ).single()["ids"],
        "canonical_node_before": session.run(
            "MATCH (n:Entity {id: $c}) RETURN n.name AS name, n.aliases AS aliases, "
            "n.abstraction_level AS level, n.confidence AS confidence", c=CANONICAL,
        ).single().data(),
        "legacy_edges_before": session.run(
            "MATCH ()-[r]->() WHERE NOT type(r) IN ['CITES','ABOUT'] "
            "AND r.edge_key IS NULL RETURN count(r) AS c"
        ).single()["c"],
    }


def _edges_touching(session, ids: list[str]) -> list[dict]:
    return [
        dict(row) for row in session.run(
            "MATCH (a)-[r]->(b) WHERE (a.id IN $ids OR b.id IN $ids) AND NOT type(r) IN ['QUOTES'] "
            "RETURN a.id AS src, type(r) AS rel, b.id AS dst ORDER BY src, rel, dst",
            ids=ids,
        )
    ]


def _affected_edge_keys(session, aliases: list[str]) -> set[str]:
    rows = session.run(
        "MATCH (e:EdgeAssertion) WHERE e.src_id IN $ids OR e.dst_id IN $ids "
        "RETURN collect(DISTINCT e.edge_key) AS keys",
        ids=[CANONICAL, *aliases],
    ).single()["keys"]
    return {k for k in rows if k}


def _drop_duplicates(session, aliases: list[str]) -> dict:
    """刪掉舊 id 的節點與仍帶舊 id 的 assertion（重載後預期 0 筆；先刪 assertion 再刪節點）。"""

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
        "migration": "npo_merge_20261008",
        "approval": "todo:752",
        "dry_run": dry_run,
        "canonical": CANONICAL,
        "aliases": aliases,
        "keep_out": list(KEEP_OUT),
        "backup_dir": backup_dir,
    }
    try:
        with driver.session() as session:
            result["preflight"] = _preflight(session, aliases)
            result["edges_before"] = _edges_touching(session, [CANONICAL, *aliases])
            if dry_run:
                result["would_reload"] = list(RELOAD_DOCS)
                result["assertions_on_alias_before_reload"] = [
                    dict(row) for row in session.run(
                        "MATCH (e:EdgeAssertion) WHERE e.src_id IN $ids OR e.dst_id IN $ids "
                        "RETURN e.id AS id, e.src_id AS src, e.relation AS rel, e.dst_id AS dst",
                        ids=aliases,
                    )
                ]
                result["would_drop_nodes"] = session.run(
                    "MATCH (n:Entity) WHERE n.id IN $ids RETURN count(n) AS c", ids=aliases,
                ).single()["c"]
                return result

            for doc_id in RELOAD_DOCS:
                doc = json.loads((ROOT / "extractions" / f"{doc_id}.json").read_text(encoding="utf-8"))
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
            result["canonical_node_after"] = session.run(
                "MATCH (n:Entity {id: $c}) RETURN n.name AS name, n.aliases AS aliases, "
                "n.abstraction_level AS level, n.confidence AS confidence", c=CANONICAL,
            ).single().data()
            result["edges_after"] = _edges_touching(session, [CANONICAL, *aliases])
            result["alias_leftovers"] = {
                "assertions": session.run(
                    "MATCH (e:EdgeAssertion) WHERE e.src_id IN $ids OR e.dst_id IN $ids RETURN count(e) AS c",
                    ids=aliases).single()["c"],
                "claims_subject": session.run(
                    "MATCH (c:Claim) WHERE c.subject_node_id IN $ids RETURN count(c) AS c",
                    ids=aliases).single()["c"],
                "relationships": session.run(
                    "MATCH (a)-[r]->(b) WHERE a.id IN $ids OR b.id IN $ids RETURN count(r) AS c",
                    ids=aliases).single()["c"],
            }
    finally:
        driver.close()
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest = MANIFEST_DIR / f"npo_merge_{stamp}.json"
    result["manifest"] = str(manifest.relative_to(ROOT)).replace("\\", "/")
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
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
