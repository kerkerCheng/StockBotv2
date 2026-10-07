"""把同義節點 `tech:cpo_fiber_attach` 併進 canonical `tech:fiber_attach_unit`（pq2 [730]，使用者 2026-10-07 go）。

## 事發

Phase 7 failure log #36：NVIDIA 矽光子部落格的夥伴條目（客戶端點名 Browave、Corning、Senko、TFC、Coherent
五家做光纖組件）最初整份掛在 `tech:cpo_fiber_attach`，FAU 讀圖只看 `tech:fiber_attach_unit`，
於是寫錯「沒有客戶端點名」。[727] 已把五家補成 `tech:fiber_attach_unit` 的供貨邊，但舊節點還在：

| id | name | 掛在上面的 |
|---|---|---|
| `tech:fiber_attach_unit` ← canonical | Fiber Attach Unit | 6 家供貨邊、FAU 讀圖、層說明 ledger、兩份敘事的押注 |
| `tech:cpo_fiber_attach` | CPO 光纖耦合／連接器層（fiber attach） | Coherent 供貨（e2）、is_component_of `tech:scale_out_cpo`（e4）、claim cl1 |

兩端的唯一／主要逐字講的是同一層（把光纖接進矽光子引擎、接到面板與外部雷射光源的光纖組件），
逐字與例外理由寫在 `config/entity_aliases.json` 該筆的 note。

## 刻意不做的四件事

1. **canonical 不照「同組取最短 id」**：那會選 `tech:cpo_fiber_attach`，把上表右欄全部搬家；例外只在這一筆。
2. **不併 `tech:cpo`／`tech:scale_out_cpo`**（疑似同義，另案）——寫進 `KEEP_OUT`，是可執行的斷言。
3. **不改抽取檔**：registry 在 loader 入圖前解析，抽取檔是逐字證據，保持原樣（同 09-10 NAND）。
4. **不新增任何知識主張**：只重指邊、保留每條原始 provenance 與 SourceDoc。

## 作法（同 `migrate_nand_merge_20260910.py`）

`edge_key = sha256([src_id, relation, dst_id])`——搬邊必須重算 key，所以走 scoped 重載：
**重載 1 份 → 刪掉舊 id 的節點與殘留 assertion → 重投影受影響的 edge_key**。
重載會讓 e2、e4 兩筆 assertion（id 帶 doc 前綴）原地改指 canonical，所以刪除那一步預期刪到 0 筆 assertion；
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

CANONICAL = "tech:fiber_attach_unit"
MANIFEST_DIR = ROOT / "library" / "private" / "graph_migrations"


#: 由 registry 讀，不在這裡再寫一份（L16）。
def _aliases() -> list[str]:
    entry = entity_registry.load().get(CANONICAL)
    if not entry:
        raise RuntimeError(f"{CANONICAL} 不在 registry；先登記再遷移")
    if entry.get("basis") == "semantic_reviewed" and entry.get("approval_receipt") != "todo:730":
        raise RuntimeError(f"{CANONICAL} 的核准 receipt 不是 todo:730：{entry.get('approval_receipt')!r}")
    return list(entry.get("aliases") or ())


#: 要重載的抽取檔——舊 id 只出現在這一份（preflight 驗），它同時宣告 canonical 節點。
RELOAD_DOCS: tuple[str, ...] = ("nvidia_sipho_blog_partner_roles",)

#: 明確不動的節點。
KEEP_OUT: tuple[str, ...] = ("tech:cpo", "tech:scale_out_cpo")


def _preflight(session, aliases: list[str]) -> dict:
    """先驗來源與範圍，再動圖。"""

    unresolved = [a for a in aliases if entity_registry.resolve(a) != CANONICAL]
    if unresolved:
        raise RuntimeError(f"registry 沒有把這些 id 解析到 {CANONICAL}，重載後會原樣長回來：{unresolved}")
    leaked = [k for k in KEEP_OUT if entity_registry.resolve(k) != k]
    if leaked:
        raise RuntimeError(f"KEEP_OUT 的節點被 registry 併掉了，超出 [730] 的核准範圍：{leaked}")
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
        "migration": "fau_merge_20261007",
        "approval": "todo:730",
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
    manifest = MANIFEST_DIR / f"fau_merge_{stamp}.json"
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
