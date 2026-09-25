"""吃一份判決檔，把 relation 重判的結果落進圖。**通用版，不綁特定 relation。**

## 為什麼是這一支

`migrate_enables_rejudge_20260918.py` 是 `enables` 那次的一次性腳本，它把方向修正
硬編碼成 `ISOLATOR` 常數；[612] 來的時候擴成 `DIRECTION_FIXES` tuple，並在檔頭寫下
「**第三次撞到同型就要把方向修正抽成資料檔**」。[613]／[614] 就是第三次，所以有了這一支。

判準（L17-2）：那時的擴充是「十行內、不動判決檔格式」所以當下修；現在要處理的是
**25 條分屬 4 種 verdict 的改動**，再擴常數就是把資料塞進程式碼。

## 與那一支的差別

| | `migrate_enables_rejudge_20260918` | 本支 |
|---|---|---|
| 判決 key | `(src, dst)` | **`assertion_id`** ——同一條 canonical edge 的多份斷言可以有不同判決 |
| relation | 只認 `enables` ＋ 硬編碼的方向修正 | 判決檔說了算 |
| verdict | `reverse`／`delete`／`retype_is_component_of`（只換 relation）／`retype_depends_on`（端點＋relation 一起換） | `reverse`／`delete`／`retype:<rel>`／`reverse_retype:<rel>` ——**對調與換型是兩個正交的動作，字彙明說，不靠記憶** |

⚠ 舊字彙裡 `retype_is_component_of` 與 `retype_depends_on` 一個換型、一個換型又對調，
**看名字分不出來**。那是 L12 在字彙層的小型版本；本支不沿用。

## 四步與那一支相同（不重造）

改抽取檔 → scoped 重載 → 刪掉被移除的 assertion 與孤兒 canonical 邊 → 重投影。
`_supersede`／`_cleanup`／`_admin_driver` 直接沿用既有實作，**不複製**。

用法::

    python loader/migrate_relation_rejudge.py --classification <path> --dry-run
    python loader/migrate_relation_rejudge.py --classification <path> \\
        --only reverse delete reverse_retype:develops \\
        --backup-dir library/private/backups/<name>

⚠ `--only` 是**白名單**：判決檔裡其餘 verdict（`keep`／`flag_*`）一律不動。
分批跑時用它把不同 pq2 編號的改動分開，驗收才分得出是誰造成的。

## 新增（`--additions`，2026-09-25，pq2 [651]／[652]）

判決檔以 assertion_id 為鍵，只表達得出「既有斷言怎麼改」；**「同一份文件的同一段逐字其實還支持另一條邊」**
（例：Sivers ECOC 2024 新聞稿逐字寫 Sivers 陣列整合進 Ayar 的 SuperNova，卻只掛在 `tech:wdm_laser_16ch`）
表達不出來。manifest 的每一列＝在**指定抽取檔**加一條邊：

- 只能引用該檔**既有的** `sources`——quote 一字不動，不新增逐字（新逐字走 Research Action）。
- local id 由 (src, relation, dst) 決定（`add_<edge_key 前 10 碼>`），同一份 manifest 重跑冪等；已存在就跳過並報出。
- 端點若沒在該檔宣告，照抄**圖上現值**宣告——loader 對節點是 `SET n.name／aliases／attributes`（最後載入者覆寫），
  自己編一份會悄悄改掉節點屬性。圖上沒有這個節點＝拒收（新增只接既有節點）。
- 改完的每份檔都過 `loader/validate.py`；有硬錯誤就整批不寫。

    python loader/migrate_relation_rejudge.py --additions loader/manifests/<name>.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loader.edge_resolution import project_edge_keys  # noqa: E402
from loader.load_to_neo4j import edge_key, evidence_id, load  # noqa: E402
from loader.migrate_enables_rejudge_20260918 import _supersede  # noqa: E402
from loader.migrate_entity_dedup_20260904 import _admin_driver  # noqa: E402
from loader.validate import validate  # noqa: E402

EXTRACTIONS = ROOT / "extractions"

#: 節點宣告要照抄的欄位（`load_to_neo4j.MERGE_NODE` 會 SET 的那幾個）。
_NODE_FIELDS = ("type", "name", "abstraction_level", "role", "aliases", "attributes", "confidence")

#: 會改動圖的 verdict 前綴。其餘（keep／flag_*）一律不動。
_ACTIONS = ("reverse", "delete", "retype:", "reverse_retype:")


def load_verdicts(path: Path, only: set[str] | None) -> dict[str, str]:
    """判決檔 → {assertion_id: verdict}，只留會改動圖的、且在白名單內的。"""
    rows = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for row in rows:
        verdict = str(row["verdict"])
        if not verdict.startswith(_ACTIONS):
            continue
        if only is not None and verdict not in only:
            continue
        key = str(row["assertion_id"])
        if key in out:
            raise RuntimeError(f"判決檔裡 {key} 出現兩次——assertion_id 必須唯一")
        out[key] = verdict
    return out


def load_additions(path: Path | None) -> list[dict]:
    """新增 manifest → 列。每列必須有 `file` 與 `edge`（src_id／relation／dst_id／非空 source_ids）。"""
    if path is None:
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))["additions"]
    for i, row in enumerate(rows):
        edge = row.get("edge") or {}
        if not row.get("file") or not all(edge.get(k) for k in ("src_id", "relation", "dst_id", "source_ids")):
            raise RuntimeError(f"additions[{i}] 缺 file 或 edge 的 src_id／relation／dst_id／source_ids")
    return rows


def addition_local_id(edge: dict) -> str:
    return "add_" + edge_key(edge["src_id"], edge["relation"], edge["dst_id"])[:10]


def graph_node_props(ids: Iterable[str]) -> dict[str, dict]:
    """圖上節點的現值（唯讀）——新增時補宣告端點用，避免覆寫節點屬性。"""
    driver = _admin_driver()
    try:
        with driver.session() as session:
            rows = session.run(
                "MATCH (n:Entity) WHERE n.id IN $ids RETURN n.id AS id, "
                + ", ".join(f"n.{f} AS {f}" for f in _NODE_FIELDS), ids=sorted(set(ids))).data()
    finally:
        driver.close()
    out: dict[str, dict] = {}
    for row in rows:
        node = {f: row[f] for f in _NODE_FIELDS}
        if isinstance(node["attributes"], str):
            node["attributes"] = json.loads(node["attributes"] or "{}")
        node["attributes"] = node["attributes"] or {}
        node["aliases"] = list(node["aliases"] or [])
        out[row["id"]] = node
    return out


def _add_edges(doc: dict, rows: list[dict], node_props: Callable[[Iterable[str]], dict[str, dict]],
               edges: list[dict]) -> tuple[list[dict], list[dict], int, list[str], list[str]]:
    """把 manifest 的列加進 `edges`；回（edges, nodes, 新增數, 已存在而跳過的 local id, 補宣告的節點）。"""
    source_ids = {s["id"] for s in doc.get("sources", []) or ()}
    nodes = list(doc.get("nodes", []) or ())
    declared = {n["id"] for n in nodes}
    added, skipped, newly_declared = 0, [], []
    for row in rows:
        edge = dict(row["edge"])
        missing = [s for s in edge["source_ids"] if s not in source_ids]
        if missing:
            raise RuntimeError(f"{row['file']}：新增的邊引用了該檔沒有的 source {missing}——新逐字走 Research Action")
        edge.setdefault("attributes", {})
        edge.setdefault("confidence", 0.7)
        edge["id"] = addition_local_id(edge)
        if any(e["id"] == edge["id"] for e in edges):
            skipped.append(edge["id"])
            continue
        need = [n for n in (edge["src_id"], edge["dst_id"]) if n not in declared]
        if need:
            props = node_props(need)
            absent = [n for n in need if n not in props]
            if absent:
                raise RuntimeError(f"{row['file']}：端點 {absent} 不在圖上——新增只接既有節點")
            for nid in need:
                nodes.append(dict(props[nid], id=nid, source_ids=list(edge["source_ids"])))
                declared.add(nid)
                newly_declared.append(nid)
        edges.append(edge)
        added += 1
    return edges, nodes, added, skipped, newly_declared


def _apply(edge: dict, verdict: str) -> dict | None:
    """一條 edge ＋ 一個 verdict → 新的 edge（`None` 代表移除）。"""
    src, dst = edge.get("src_id"), edge.get("dst_id")
    if verdict == "delete":
        return None
    if verdict == "reverse":
        return dict(edge, src_id=dst, dst_id=src)
    if verdict.startswith("reverse_retype:"):
        return dict(edge, src_id=dst, dst_id=src, relation=verdict.split(":", 1)[1])
    if verdict.startswith("retype:"):
        return dict(edge, relation=verdict.split(":", 1)[1])
    raise RuntimeError(f"未知判決 {verdict}")


def _validation_errors(doc: dict) -> list[str]:
    """改完的抽取檔照 `loader/validate.py` 驗一次（它吃路徑，寫暫存檔）；只回硬錯誤。"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "doc.json"
        path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        return [p for p in validate(str(path)) if not p.startswith("WARN")]


def plan(verdicts: dict[str, str], additions: list[dict] | None = None,
         node_props: Callable[[Iterable[str]], dict[str, dict]] = graph_node_props) -> dict:
    files: dict[str, dict] = {}
    seen: set[str] = set()
    by_file: dict[str, list[dict]] = {}
    for row in additions or ():
        by_file.setdefault(row["file"], []).append(row)
    unknown_files = sorted(f for f in by_file if not (EXTRACTIONS / f).is_file())
    skipped_additions: list[str] = []
    for path in sorted(EXTRACTIONS.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc_id = (doc.get("source_doc") or {}).get("doc_id") or path.stem
        kept: list[dict] = []
        removed: list[str] = []
        changed = 0
        for edge in doc.get("edges", []) or ():
            aid = evidence_id(doc_id, edge["id"])
            verdict = verdicts.get(aid)
            if verdict is None:
                kept.append(edge)
                continue
            seen.add(aid)
            new_edge = _apply(edge, verdict)
            if new_edge is None:
                removed.append(edge["id"])
            else:
                kept.append(new_edge)
                changed += 1
        nodes = doc.get("nodes", []) or []
        added, declared = 0, []
        if path.name in by_file:
            kept, nodes, added, skipped, declared = _add_edges(doc, by_file[path.name], node_props, kept)
            skipped_additions += [f"{path.name}:{s}" for s in skipped]
        if not removed and changed == 0 and added == 0:
            continue
        errors = _validation_errors(dict(doc, edges=kept, nodes=nodes))
        if errors:
            raise RuntimeError(f"{path.name} 改完後驗證不過：{errors}")
        files[path.name] = {
            "doc_id": doc_id,
            "new_edges": kept,
            "new_nodes": nodes,
            "removed_local_ids": removed,
            "removed_assertion_ids": [evidence_id(doc_id, lid) for lid in removed],
            "new_edge_keys": sorted({edge_key(e["src_id"], e["relation"], e["dst_id"])
                                     for e in kept}),
            "changed": changed,
            "added": added,
            "declared_nodes": declared,
        }
    missing = sorted(set(verdicts) - seen)
    return {"files": files, "verdicts": len(verdicts), "not_found": missing + unknown_files,
            "additions_skipped": skipped_additions}


def migrate(*, classification: Path | None, only: set[str] | None,
            dry_run: bool, backup_dir: str | None, additions: Path | None = None) -> dict:
    if classification is None and additions is None:
        raise RuntimeError("至少要給 --classification 或 --additions 其中一個")
    if not dry_run and not backup_dir:
        raise RuntimeError("live migration 需要 --backup-dir（含非空 neo4j_export.json）")
    if not dry_run:
        export = Path(backup_dir).resolve() / "neo4j_export.json"
        if not export.is_file() or export.stat().st_size == 0:
            raise RuntimeError(f"找不到 Neo4j 匯出或為空：{export}")

    verdicts = load_verdicts(classification, only) if classification is not None else {}
    p = plan(verdicts, load_additions(additions))
    result: dict = {
        "dry_run": dry_run,
        "classification": str(classification) if classification is not None else None,
        "additions": str(additions) if additions is not None else None,
        "only": sorted(only) if only else None,
        "verdicts_in_scope": p["verdicts"],
        "files": len(p["files"]),
        "edges_changed": sum(f["changed"] for f in p["files"].values()),
        "edges_removed": sum(len(f["removed_local_ids"]) for f in p["files"].values()),
        "edges_added": sum(f["added"] for f in p["files"].values()),
        "additions_skipped": p["additions_skipped"],
        # ⚠ 判決指到一個抽取檔裡找不到的 assertion＝**判決檔與抽取檔對不上**，
        # 那不是「沒事做」。空集合與成功在這裡必須分得開（L13-2）。
        "not_found": p["not_found"],
    }
    if dry_run:
        result["detail"] = {k: {"doc_id": v["doc_id"], "changed": v["changed"],
                                "removed": v["removed_local_ids"], "added": v["added"],
                                "declared_nodes": v["declared_nodes"]}
                            for k, v in p["files"].items()}
        return result
    if p["not_found"]:
        raise RuntimeError(f"判決指到抽取檔裡不存在的 assertion 或檔案：{p['not_found']}")

    superseded: list[str] = []
    for name, spec in p["files"].items():
        path = EXTRACTIONS / name
        superseded.append(_supersede(path).name)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["edges"] = spec["new_edges"]
        doc["nodes"] = spec["new_nodes"]
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["superseded"] = superseded

    removed_ids = [i for f in p["files"].values() for i in f["removed_assertion_ids"]]
    affected_keys: set[str] = set()
    for f in p["files"].values():
        affected_keys |= set(f["new_edge_keys"])

    driver = _admin_driver()
    try:
        with driver.session() as session:
            for name in p["files"]:
                doc = json.loads((EXTRACTIONS / name).read_text(encoding="utf-8"))
                load(doc, session, allow_dup_url=True)
            dropped = 0
            if removed_ids:
                dropped = session.run(
                    "MATCH (e:EdgeAssertion) WHERE e.id IN $ids DETACH DELETE e "
                    "RETURN count(e) AS c", ids=removed_ids).single()["c"]
            orphans = session.run(
                """
                MATCH (a:Entity)-[r]->(b:Entity) WHERE r.edge_key IS NOT NULL
                WITH r, r.edge_key AS k
                WHERE NOT EXISTS { MATCH (e:EdgeAssertion {edge_key: k}) }
                DELETE r RETURN count(r) AS c
                """).single()["c"]
            result["cleanup"] = {"dropped_assertions": dropped, "dropped_orphan_edges": orphans}
            live_keys = set(session.run(
                "MATCH (e:EdgeAssertion) WHERE e.edge_key IN $keys "
                "RETURN collect(DISTINCT e.edge_key) AS k", keys=sorted(affected_keys),
            ).single()["k"])
        result["reprojected"] = project_edge_keys(driver, live_keys)["edges"]
    finally:
        driver.close()
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--classification", help="判決檔路徑（JSON list）")
    ap.add_argument("--additions", help="新增 manifest（{additions: [...]}；見檔頭）")
    ap.add_argument("--only", nargs="*", help="只套這些 verdict（白名單）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--backup-dir")
    args = ap.parse_args()
    print(json.dumps(
        migrate(classification=Path(args.classification) if args.classification else None,
                only=set(args.only) if args.only else None,
                dry_run=args.dry_run, backup_dir=args.backup_dir,
                additions=Path(args.additions) if args.additions else None),
        ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
