"""同義節點合併＋同包退役逐字不支持的邊（pq2 [840][841][842]）與別名污染清理（[843]）——使用者 2026-10-23 go。

| 編號 | canonical ← 舊 id | 重載文件 | 同包抽取檔修改 |
|---|---|---|---|
| [840] | `tech:uhp_laser` ← `prod:uhp_laser` | lite_transcript_q4fy2026 | 退役 e17（is_component_of NPO，s4 沒提雷射）、e10（InP is_component_of，s6 沒寫 UHP） |
| [841] | `tech:micro_ring_modulator` ← `tech:mrm_200g` | trendforce_tsmc_pic_capacity_2026_07_08 | 退役 e3（NVIDIA depends_on，s5 講 COUPE 客戶）；e2 拿掉 s3（PIC 產能句） |
| [842] | `tech:dram_manufacturing` ← `tech:dram`；`tech:foundry_logic` ← `tech:leading_edge_logic_foundry` | amat_10_k_20251212、amat_10_q_20260521 | 退役 e10（HBM is_variant_of DRAM，s15 沒有 DRAM）；leading_edge 宣告拿掉「leading-edge」「7nm and smaller」與 s2 |
| [843] | （不合併） | 不重載 | 四個節點的污染別名：抽取檔宣告拿掉＋圖上 aliases 設成現值減去清單 |

兩端逐字與 canonical 的選法寫在 `config/entity_aliases.json` 各筆的 note、pq2 [840]–[843] 的 hint 與
`docs/reports/phase7/graph-walk-terminals-2026-10-22.md`。

## 和 2026-10-17 那支（`migrate_merge_batch_20261017.py`）不同的三件事

1. **會改抽取檔**：那支「不改抽取檔」，因為它只重指邊；這次要退役逐字不支持的邊——不從抽取檔拿掉，重載就會在 canonical 上
   長出一條沒有證據的新邊（L6 Gap 4；[752] note 已記 e17 的疑點）。改檔前照 [613]／[614] 的先例以 `_supersede` 封存舊版
   （檔名＝被封存內容的 sha256 前 8 碼，任何人可重算）。
2. **快照多帶 type**：2026-10-22 乾跑看到 [840] 重載會把 `tech:uhp_laser` 的 type 由 TechNode 改成 Product
   （舊宣告 prod:uhp_laser 是 Product）；10-17 那支只設回 name／abstraction_level／role／confidence。
3. **退役 assertion 與孤兒邊**：被拿掉的邊的 assertion 若掛在 canonical（不是舊 id）也要刪；之後清孤兒 canonical 邊再重投影
   （同 `migrate_relation_rejudge` 的順序：先刪 assertion，再刪孤兒邊）。

## 刻意不做的事

1. 不新增任何知識主張；不動 quote（只拿掉整條邊、邊上的一段引用、節點宣告的別名與一段節點 source）。
2. 舊 id 上若有來自別份文件的 assertion 或 claim，preflight 直接拒絕（failure log #73）。
3. 有 claim 以被退役的邊為主詞，preflight 拒絕（不替 claim 換主詞）。
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from identity import entities as entity_registry  # noqa: E402
from loader.edge_resolution import project_edge_keys  # noqa: E402
from loader.load_to_neo4j import evidence_id, load  # noqa: E402
from loader.migrate_enables_rejudge_20260918 import _supersede  # noqa: E402
from loader.migrate_entity_dedup_20260904 import _admin_driver  # noqa: E402

EXTRACTIONS = ROOT / "extractions"
MANIFEST_DIR = ROOT / "library" / "private" / "graph_migrations"
SCALAR_PROPS = ("name", "abstraction_level", "role", "confidence", "type")

MERGES: dict[str, dict] = {
    "840": {"approval": "todo:840", "groups": {"tech:uhp_laser": ["prod:uhp_laser"]},
            "edits": {"lite_transcript_q4fy2026": {"drop_edges": ["e17", "e10"]}}},
    "841": {"approval": "todo:841", "groups": {"tech:micro_ring_modulator": ["tech:mrm_200g"]},
            "edits": {"trendforce_tsmc_pic_capacity_2026_07_08": {
                "drop_edges": ["e3"],
                "edge_drop_sources": {"e2": ["trendforce_tsmc_pic_capacity_2026_07_08_s3"]}}}},
    "842": {"approval": "todo:842",
            "groups": {"tech:dram_manufacturing": ["tech:dram"],
                       "tech:foundry_logic": ["tech:leading_edge_logic_foundry"]},
            "edits": {"amat_10_k_20251212": {
                "drop_edges": ["amat_10_k_20251212_e10"],
                "node_alias_remove": {"tech:leading_edge_logic_foundry": ["leading-edge", "7nm and smaller"]},
                "node_source_remove": {"tech:leading_edge_logic_foundry": ["amat_10_k_20251212_s2"]}},
                "amat_10_q_20260521": {}}},
}
ALIAS_CLEANUP: dict[str, list[str]] = {  # [843]
    "tech:cpo": ["NPO", "near packaged optics"],
    "tech:ai_switch": ["scale-up network", "scale-out network", "scale-up networking", "scale-out networking"],
    "prod:aaoi_400mw_narrow_linewidth_pump_laser": ["ELS", "ELSFP", "external light source"],
    "tech:non_leading_edge_fab": ["mature node"],
}


def _norm(s: str) -> str:
    return " ".join(str(s).lower().replace("-", " ").split())


def _edit_doc(doc: dict, edit: dict) -> tuple[dict, list[str]]:
    """回（改好的抽取、被退役的 local edge id）。找不到要改的東西一律 raise——沒改到不是「沒事做」（L13）。"""
    doc = copy.deepcopy(doc)
    edges = {e["id"]: e for e in doc.get("edges", [])}
    drop = list(edit.get("drop_edges", []))
    for lid in drop:
        if lid not in edges:
            raise RuntimeError(f"{doc['source_doc']['doc_id']}：要退役的邊 {lid} 不在抽取檔")
    claims_on = [c["id"] for c in doc.get("claims", []) if c.get("subject_id") in drop]
    if claims_on:
        raise RuntimeError(f"{doc['source_doc']['doc_id']}：claim {claims_on} 以要退役的邊為主詞——不替 claim 換主詞，停")
    doc["edges"] = [e for e in doc["edges"] if e["id"] not in drop]
    for lid, sids in (edit.get("edge_drop_sources") or {}).items():
        e = next(x for x in doc["edges"] if x["id"] == lid)
        missing = [s for s in sids if s not in e["source_ids"]]
        if missing:
            raise RuntimeError(f"{lid} 沒有 source {missing}")
        e["source_ids"] = [s for s in e["source_ids"] if s not in sids]
        if not e["source_ids"]:
            raise RuntimeError(f"{lid} 拿掉後沒有任何 source")
    nodes = {n["id"]: n for n in doc.get("nodes", [])}
    for nid, rm in (edit.get("node_alias_remove") or {}).items():
        n = nodes[nid]
        before = list(n.get("aliases") or [])
        miss = [a for a in rm if a not in before]
        if miss:
            raise RuntimeError(f"{nid} 宣告沒有別名 {miss}")
        n["aliases"] = [a for a in before if a not in rm]
    for nid, rm in (edit.get("node_source_remove") or {}).items():
        n = nodes[nid]
        miss = [s for s in rm if s not in (n.get("source_ids") or [])]
        if miss:
            raise RuntimeError(f"{nid} 宣告沒有 source {miss}")
        n["source_ids"] = [s for s in n["source_ids"] if s not in rm]
    return doc, drop


def _registry_check(spec: dict) -> None:
    for canonical, olds in spec["groups"].items():
        for old in olds:
            if entity_registry.resolve(old) != canonical:
                raise RuntimeError(f"registry 沒有把 {old} 解析到 {canonical}——先登記（receipt {spec['approval']}）再遷移")


def _declared(docs: dict[str, dict]) -> list[str]:
    return sorted({entity_registry.resolve(n["id"]) for d in docs.values() for n in d.get("nodes", [])})


def _snapshot(session, ids: list[str]) -> dict[str, dict]:
    rows = session.run("MATCH (n:Entity) WHERE n.id IN $ids RETURN n.id AS id, labels(n) AS labels, "
                       + ", ".join(f"n.{p} AS {p}" for p in SCALAR_PROPS), ids=ids)
    return {r["id"]: {p: r[p] for p in SCALAR_PROPS} for r in rows}


def _preflight(session, spec: dict, docs: list[str]) -> dict:
    olds = [o for v in spec["groups"].values() for o in v]
    for doc_id in docs:
        if not (EXTRACTIONS / f"{doc_id}.json").is_file():
            raise RuntimeError(f"重載文件的抽取檔不在 checkout：{doc_id}（failure log #73）")
    foreign = [dict(r) for r in session.run(
        "MATCH (e:EdgeAssertion) WHERE (e.src_id IN $ids OR e.dst_id IN $ids) AND NOT e.source_doc_id IN $docs "
        "RETURN e.id AS id, e.source_doc_id AS doc", ids=olds, docs=docs)]
    foreign += [dict(r) for r in session.run(
        "MATCH (c)-[:ABOUT]->(n:Entity) WHERE n.id IN $ids AND NOT c.source_doc_id IN $docs "
        "RETURN c.id AS id, c.source_doc_id AS doc", ids=olds, docs=docs)]
    if foreign:
        raise RuntimeError(f"舊 id 上有不在重載文件裡的證據——停：{foreign}")
    return {"assertions_on_old": [dict(r) for r in session.run(
        "MATCH (e:EdgeAssertion) WHERE e.src_id IN $ids OR e.dst_id IN $ids "
        "RETURN e.id AS id, e.src_id AS src, e.relation AS rel, e.dst_id AS dst", ids=olds)]}


def migrate_merge(number: str, *, dry_run: bool) -> dict:
    spec = MERGES[number]
    _registry_check(spec)
    docs = list(spec["edits"])
    edited: dict[str, dict] = {}
    retired: list[str] = []
    for doc_id, edit in spec["edits"].items():
        doc = json.loads((EXTRACTIONS / f"{doc_id}.json").read_text(encoding="utf-8"))
        new_doc, drop = _edit_doc(doc, edit)
        edited[doc_id] = new_doc
        retired += [evidence_id(doc_id, lid) for lid in drop]
    declared = _declared(edited)
    canonicals = list(spec["groups"])
    olds = [o for v in spec["groups"].values() for o in v]
    result: dict = {"migration": f"merge_batch_20261023[{number}]", "approval": spec["approval"], "dry_run": dry_run,
                    "groups": spec["groups"], "reload": docs, "retired_assertions": retired}
    driver = _admin_driver()
    try:
        with driver.session() as session:
            result["preflight"] = _preflight(session, spec, docs)
            before = _snapshot(session, declared)
            result["declared_nodes_snapshot"] = len(before)
            if dry_run:
                return result
            result["superseded"] = []
            for doc_id, new_doc in edited.items():
                path = EXTRACTIONS / f"{doc_id}.json"
                result["superseded"].append(_supersede(path).name)
                path.write_text(json.dumps(new_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            for doc_id in docs:
                load(json.loads((EXTRACTIONS / f"{doc_id}.json").read_text(encoding="utf-8")), session, allow_dup_url=True)
            after = _snapshot(session, declared)
            restored = []
            for nid, props in before.items():
                changed = {p: (props[p], after.get(nid, {}).get(p)) for p in SCALAR_PROPS
                           if after.get(nid, {}).get(p) != props[p]}
                if changed:
                    session.run("MATCH (n:Entity {id: $id}) SET " + ", ".join(f"n.{p} = ${p}" for p in changed),
                                id=nid, **{p: props[p] for p in changed})
                    restored.append({"node": nid, "restored": {p: {"pre": v[0], "reload_wrote": v[1]} for p, v in changed.items()}})
            result["restored_after_reload"] = restored
            result["dropped_retired_assertions"] = session.run(
                "MATCH (e:EdgeAssertion) WHERE e.id IN $ids DETACH DELETE e RETURN count(e) AS c", ids=retired).single()["c"]
            result["dropped_old_id_assertions"] = session.run(
                "MATCH (e:EdgeAssertion) WHERE e.src_id IN $ids OR e.dst_id IN $ids DETACH DELETE e RETURN count(e) AS c",
                ids=olds).single()["c"]
            result["dropped_nodes"] = session.run(
                "MATCH (n:Entity) WHERE n.id IN $ids DETACH DELETE n RETURN count(n) AS c", ids=olds).single()["c"]
            result["dropped_orphan_edges"] = session.run(
                """
                MATCH (a:Entity)-[r]->(b:Entity) WHERE r.edge_key IS NOT NULL
                WITH r, r.edge_key AS k
                WHERE NOT EXISTS { MATCH (e:EdgeAssertion {edge_key: k}) }
                DELETE r RETURN count(r) AS c
                """).single()["c"]
            keys = {k for k in session.run(
                "MATCH (e:EdgeAssertion) WHERE e.src_id IN $c OR e.dst_id IN $c RETURN collect(DISTINCT e.edge_key) AS keys",
                c=canonicals).single()["keys"] if k}
        result["reprojected"] = project_edge_keys(driver, keys)["edges"]
        with driver.session() as session:
            result["alias_leftovers"] = session.run(
                "MATCH (n) WHERE n.id IN $ids OR n.src_id IN $ids OR n.dst_id IN $ids RETURN count(n) AS c",
                ids=olds).single()["c"]
            result["retired_leftovers"] = session.run(
                "MATCH (e:EdgeAssertion) WHERE e.id IN $ids RETURN count(e) AS c", ids=retired).single()["c"]
            result["declared_nodes_still_changed"] = [
                nid for nid, props in _snapshot(session, declared).items()
                if nid in before and any(props[p] != before[nid][p] for p in SCALAR_PROPS)]
    finally:
        driver.close()
    return _write_manifest(number, result)


def _alias_decls() -> dict[str, list[tuple[str, list[str]]]]:
    """[843]：哪些抽取檔的節點宣告帶著要拿掉的別名（掃全部抽取檔，不只 hint 點名的那幾份——對稱面，L17）。"""
    hits: dict[str, list[tuple[str, list[str]]]] = {}
    for path in sorted(EXTRACTIONS.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for n in doc.get("nodes", []) or []:
            nid = entity_registry.resolve(n["id"])
            if nid not in ALIAS_CLEANUP:
                continue
            bad = {_norm(a) for a in ALIAS_CLEANUP[nid]}
            found = [a for a in (n.get("aliases") or []) if _norm(a) in bad]
            if found:
                hits.setdefault(path.name, []).append((n["id"], found))
    return hits


def migrate_aliases(*, dry_run: bool) -> dict:
    hits = _alias_decls()
    result: dict = {"migration": "merge_batch_20261023[843]", "approval": "todo:843", "dry_run": dry_run,
                    "extraction_decls": {k: [[i, f] for i, f in v] for k, v in hits.items()}}
    driver = _admin_driver()
    try:
        with driver.session() as session:
            rows = {r["id"]: list(r["aliases"] or []) for r in session.run(
                "MATCH (n:Entity) WHERE n.id IN $ids RETURN n.id AS id, n.aliases AS aliases", ids=list(ALIAS_CLEANUP))}
            plan = {}
            for nid, rm in ALIAS_CLEANUP.items():
                if nid not in rows:
                    raise RuntimeError(f"{nid} 不在圖上")
                bad = {_norm(a) for a in rm}
                cur = rows[nid]
                plan[nid] = {"before": cur, "after": [a for a in cur if _norm(a) not in bad],
                             "removed": [a for a in cur if _norm(a) in bad]}
                if not plan[nid]["removed"]:
                    raise RuntimeError(f"{nid} 圖上沒有要拿掉的別名 {rm}——hint 與圖對不上，停")
            result["graph"] = plan
            if dry_run:
                return result
            result["superseded"] = []
            for name, items in hits.items():
                path = EXTRACTIONS / name
                result["superseded"].append(_supersede(path).name)
                doc = json.loads(path.read_text(encoding="utf-8"))
                for n in doc["nodes"]:
                    nid = entity_registry.resolve(n["id"])
                    if nid in ALIAS_CLEANUP:
                        bad = {_norm(a) for a in ALIAS_CLEANUP[nid]}
                        n["aliases"] = [a for a in (n.get("aliases") or []) if _norm(a) not in bad]
                path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            for nid, p in plan.items():
                session.run("MATCH (n:Entity {id: $id}) SET n.aliases = $aliases", id=nid, aliases=p["after"])
            result["graph_after"] = {r["id"]: list(r["aliases"] or []) for r in session.run(
                "MATCH (n:Entity) WHERE n.id IN $ids RETURN n.id AS id, n.aliases AS aliases", ids=list(ALIAS_CLEANUP))}
    finally:
        driver.close()
    return _write_manifest("843", result)


def _write_manifest(number: str, result: dict) -> dict:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest = MANIFEST_DIR / f"merge_{number}_{stamp}.json"
    result["manifest"] = str(manifest.relative_to(ROOT)).replace("\\", "/")
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--merge", required=True, choices=[*sorted(MERGES), "843"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backup-dir", default=None)
    args = parser.parse_args()
    if not args.dry_run:
        if not args.backup_dir:
            raise SystemExit("live migration 需要 --backup-dir（先跑 backup_private.py run）")
        export = Path(args.backup_dir).resolve() / "neo4j_export.json"
        if not export.is_file() or export.stat().st_size == 0:
            raise SystemExit(f"找不到 Neo4j 匯出或為空：{export}")
    out = migrate_aliases(dry_run=args.dry_run) if args.merge == "843" else migrate_merge(args.merge, dry_run=args.dry_run)
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
