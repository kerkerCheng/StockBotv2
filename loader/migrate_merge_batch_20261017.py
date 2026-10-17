"""三組同義節點合併（pq2 [776][777][778]，使用者 2026-10-17 go）——同 `migrate_npo_merge_20261008.py` 的作法，參數化成一支。

| 編號 | canonical ← 舊 id | 重載文件 |
|---|---|---|
| [776] | `tech:transceiver_1_6t` ← `tech:cloud_transceiver_1_6t` | lumentum_q2fy26_cpo |
| [777] | `tech:six_inch_inp_production` ← `tech:inp_6inch_fab` | coherent_q3fy26_cpo、nvidia_blog_coherent_texas_2026_06_16、semitoday_cohr_chips_2026_06_17 |
| [778] | `tech:external_laser_source` ← `prod:els_module`、`tech:els_pluggable_module` | lumentum_q2fy26_cpo、lumentum_q3fy26_cpo、lumentum_q4fy26_els_order、lite_transcript_q4fy2026、cignal_cpo_elsfp_1q26_2026_04_01 |

兩端逐字與 canonical 的選法寫在 `config/entity_aliases.json` 各筆的 note。

## 和 NPO 那支不同的一件事：重放舊宣告會覆寫屬性

2026-10-17 乾跑（唯讀，記憶體換 id 後用 `loader.merge_side_effects`）：[777] 重載會把 `co:nvidia`、`tech:multi_rail` 的
abstraction_level 與 `co:coherent` 的 role 改回舊宣告；[778] 會把 `tech:external_laser_source` 的 abstraction_level 從
device_chip 改成 module_subsystem、`co:nvidia` 改成 end_demand（failure log #67 的形狀：最後載入者贏）。
所以這支在重載**前**快照重載文件宣告的每個節點的 name／abstraction_level／role／confidence，重載**後**把被改掉的設回快照值，
並逐筆寫進 manifest。aliases 是聯集（只增不改），不還原——canonical 多出舊 id 的別名正是合併要的結果。

## 刻意不做的事

1. 不改抽取檔（registry 在 loader 入圖前解析；抽取檔是逐字證據，保持原樣）。
2. 不新增任何知識主張：只重指邊、保留每條原始 provenance。
3. 舊 id 上若有來自別份文件的 assertion 或 claim，preflight 直接拒絕——重載改不到它們，刪除會吃掉證據。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from identity import entities as entity_registry  # noqa: E402
from loader.edge_resolution import project_edge_keys  # noqa: E402
from loader.load_to_neo4j import load  # noqa: E402
from loader.migrate_entity_dedup_20260904 import _admin_driver  # noqa: E402

MANIFEST_DIR = ROOT / "library" / "private" / "graph_migrations"

MERGES: dict[str, dict] = {
    "776": {"canonical": "tech:transceiver_1_6t", "approval": "todo:776",
            "reload": ("lumentum_q2fy26_cpo",), "keep_out": ("tech:pluggable_transceiver", "tech:cloud_transceiver")},
    "777": {"canonical": "tech:six_inch_inp_production", "approval": "todo:777",
            "reload": ("coherent_q3fy26_cpo", "nvidia_blog_coherent_texas_2026_06_16", "semitoday_cohr_chips_2026_06_17"),
            "keep_out": ("mat:inp_substrate",)},
    "778": {"canonical": "tech:external_laser_source", "approval": "todo:778",
            "reload": ("lumentum_q2fy26_cpo", "lumentum_q3fy26_cpo", "lumentum_q4fy26_els_order", "lite_transcript_q4fy2026",
                       "cignal_cpo_elsfp_1q26_2026_04_01"),
            "keep_out": ("prod:els_8ch_module", "tech:module_integrated_laser_source")},
}
SCALAR_PROPS = ("name", "abstraction_level", "role", "confidence")


def _aliases(spec: dict) -> list[str]:
    entry = entity_registry.load().get(spec["canonical"])
    if not entry:
        raise RuntimeError(f"{spec['canonical']} 不在 registry；先登記再遷移")
    if entry.get("basis") != "semantic_reviewed" or entry.get("approval_receipt") != spec["approval"]:
        raise RuntimeError(f"{spec['canonical']} 的 basis／receipt 不是 semantic_reviewed／{spec['approval']}："
                           f"{entry.get('basis')!r}／{entry.get('approval_receipt')!r}")
    return list(entry.get("aliases") or ())


def _declared_nodes(spec: dict) -> list[str]:
    ids: set[str] = set()
    for doc_id in spec["reload"]:
        doc = json.loads((ROOT / "extractions" / f"{doc_id}.json").read_text(encoding="utf-8"))
        ids |= {entity_registry.resolve(n["id"]) for n in doc.get("nodes", [])}
    return sorted(ids)


def _snapshot(session, ids: list[str]) -> dict[str, dict]:
    rows = session.run("MATCH (n:Entity) WHERE n.id IN $ids RETURN n.id AS id, "
                       + ", ".join(f"n.{p} AS {p}" for p in SCALAR_PROPS), ids=ids)
    return {r["id"]: {p: r[p] for p in SCALAR_PROPS} for r in rows}


def _preflight(session, spec: dict, aliases: list[str]) -> dict:
    unresolved = [a for a in aliases if entity_registry.resolve(a) != spec["canonical"]]
    if unresolved:
        raise RuntimeError(f"registry 沒有把這些 id 解析到 {spec['canonical']}：{unresolved}")
    leaked = [k for k in spec["keep_out"] if entity_registry.resolve(k) != k]
    if leaked:
        raise RuntimeError(f"KEEP_OUT 的節點被 registry 併掉了，超出核准範圍：{leaked}")
    docs = list(spec["reload"])
    for doc_id in docs:
        if not (ROOT / "extractions" / f"{doc_id}.json").is_file():
            raise RuntimeError(f"重載文件的抽取檔不在 checkout：{doc_id}（failure log #73）")
    foreign = [dict(r) for r in session.run(
        "MATCH (e:EdgeAssertion) WHERE (e.src_id IN $ids OR e.dst_id IN $ids) AND NOT e.source_doc_id IN $docs "
        "RETURN e.id AS id, e.source_doc_id AS doc", ids=aliases, docs=docs)]
    foreign += [dict(r) for r in session.run(
        "MATCH (c)-[:ABOUT]->(n:Entity) WHERE n.id IN $ids AND NOT c.source_doc_id IN $docs "
        "RETURN c.id AS id, c.source_doc_id AS doc", ids=aliases, docs=docs)]
    if foreign:
        raise RuntimeError(f"舊 id 上有不在重載文件裡的證據，重載改不到、刪除會吃掉它們——停：{foreign}")
    return {"nodes_before": session.run("MATCH (n:Entity) WHERE n.id IN $ids RETURN collect(n.id) AS ids",
                                        ids=[spec["canonical"], *aliases, *spec["keep_out"]]).single()["ids"]}


def _edges_touching(session, ids: list[str]) -> list[dict]:
    return [dict(r) for r in session.run(
        "MATCH (a)-[r]->(b) WHERE (a.id IN $ids OR b.id IN $ids) AND NOT type(r) IN ['QUOTES'] "
        "RETURN a.id AS src, type(r) AS rel, b.id AS dst ORDER BY src, rel, dst", ids=ids)]


def migrate(number: str, *, dry_run: bool, backup_dir: str | None) -> dict:
    spec = MERGES[number]
    if not dry_run:
        if not backup_dir:
            raise RuntimeError("live migration 需要 --backup-dir（先跑 backup_private.py run）")
        export = Path(backup_dir).resolve() / "neo4j_export.json"
        if not export.is_file() or export.stat().st_size == 0:
            raise RuntimeError(f"找不到 Neo4j 匯出或為空：{export}")
    aliases = _aliases(spec)
    canonical = spec["canonical"]
    declared = _declared_nodes(spec)
    driver = _admin_driver()
    result: dict = {"migration": f"merge_batch_20261017[{number}]", "approval": spec["approval"], "dry_run": dry_run,
                    "canonical": canonical, "aliases": aliases, "reload": list(spec["reload"]), "backup_dir": backup_dir}
    try:
        with driver.session() as session:
            result["preflight"] = _preflight(session, spec, aliases)
            result["edges_before"] = _edges_touching(session, [canonical, *aliases])
            before = _snapshot(session, declared)
            if dry_run:
                result["assertions_on_alias"] = [dict(r) for r in session.run(
                    "MATCH (e:EdgeAssertion) WHERE e.src_id IN $ids OR e.dst_id IN $ids "
                    "RETURN e.id AS id, e.src_id AS src, e.relation AS rel, e.dst_id AS dst", ids=aliases)]
                result["declared_nodes_snapshot"] = len(before)
                return result
            for doc_id in spec["reload"]:
                doc = json.loads((ROOT / "extractions" / f"{doc_id}.json").read_text(encoding="utf-8"))
                load(doc, session, allow_dup_url=True)
            after_reload = _snapshot(session, declared)
            restored = []
            for nid, props in before.items():
                changed = {p: (props[p], after_reload.get(nid, {}).get(p)) for p in SCALAR_PROPS
                           if after_reload.get(nid, {}).get(p) != props[p]}
                if changed:
                    session.run("MATCH (n:Entity {id: $id}) SET " + ", ".join(f"n.{p} = ${p}" for p in changed),
                                id=nid, **{p: props[p] for p in changed})
                    restored.append({"node": nid, "restored": {p: {"pre": v[0], "reload_wrote": v[1]} for p, v in changed.items()}})
            result["restored_after_reload"] = restored
            result["dropped_assertions"] = session.run(
                "MATCH (e:EdgeAssertion) WHERE e.src_id IN $ids OR e.dst_id IN $ids DETACH DELETE e RETURN count(e) AS c",
                ids=aliases).single()["c"]
            result["dropped_nodes"] = session.run(
                "MATCH (n:Entity) WHERE n.id IN $ids DETACH DELETE n RETURN count(n) AS c", ids=aliases).single()["c"]
            keys = {k for k in session.run(
                "MATCH (e:EdgeAssertion) WHERE e.src_id = $c OR e.dst_id = $c RETURN collect(DISTINCT e.edge_key) AS keys",
                c=canonical).single()["keys"] if k}
        result["reprojected"] = project_edge_keys(driver, keys)
        with driver.session() as session:
            result["edges_after"] = _edges_touching(session, [canonical, *aliases])
            result["alias_leftovers"] = session.run(
                "MATCH (n) WHERE n.id IN $ids OR n.src_id IN $ids OR n.dst_id IN $ids RETURN count(n) AS c",
                ids=aliases).single()["c"]
            result["declared_nodes_still_changed"] = [
                nid for nid, props in _snapshot(session, declared).items()
                if nid in before and any(props[p] != before[nid][p] for p in SCALAR_PROPS)]
    finally:
        driver.close()
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest = MANIFEST_DIR / f"merge_{number}_{stamp}.json"
    result["manifest"] = str(manifest.relative_to(ROOT)).replace("\\", "/")
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--merge", required=True, choices=sorted(MERGES))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backup-dir", default=None)
    args = parser.parse_args()
    print(json.dumps(migrate(args.merge, dry_run=args.dry_run, backup_dir=args.backup_dir),
                     ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
