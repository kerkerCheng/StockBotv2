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
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loader.edge_resolution import project_edge_keys  # noqa: E402
from loader.load_to_neo4j import edge_key, evidence_id, load  # noqa: E402
from loader.migrate_enables_rejudge_20260918 import _supersede  # noqa: E402
from loader.migrate_entity_dedup_20260904 import _admin_driver  # noqa: E402

EXTRACTIONS = ROOT / "extractions"

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


def plan(verdicts: dict[str, str]) -> dict:
    files: dict[str, dict] = {}
    seen: set[str] = set()
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
        if not removed and changed == 0:
            continue
        files[path.name] = {
            "doc_id": doc_id,
            "new_edges": kept,
            "removed_local_ids": removed,
            "removed_assertion_ids": [evidence_id(doc_id, lid) for lid in removed],
            "new_edge_keys": sorted({edge_key(e["src_id"], e["relation"], e["dst_id"])
                                     for e in kept}),
            "changed": changed,
        }
    missing = sorted(set(verdicts) - seen)
    return {"files": files, "verdicts": len(verdicts), "not_found": missing}


def migrate(*, classification: Path, only: set[str] | None,
            dry_run: bool, backup_dir: str | None) -> dict:
    if not dry_run and not backup_dir:
        raise RuntimeError("live migration 需要 --backup-dir（含非空 neo4j_export.json）")
    if not dry_run:
        export = Path(backup_dir).resolve() / "neo4j_export.json"
        if not export.is_file() or export.stat().st_size == 0:
            raise RuntimeError(f"找不到 Neo4j 匯出或為空：{export}")

    verdicts = load_verdicts(classification, only)
    p = plan(verdicts)
    result: dict = {
        "dry_run": dry_run,
        "classification": str(classification),
        "only": sorted(only) if only else None,
        "verdicts_in_scope": p["verdicts"],
        "files": len(p["files"]),
        "edges_changed": sum(f["changed"] for f in p["files"].values()),
        "edges_removed": sum(len(f["removed_local_ids"]) for f in p["files"].values()),
        # ⚠ 判決指到一個抽取檔裡找不到的 assertion＝**判決檔與抽取檔對不上**，
        # 那不是「沒事做」。空集合與成功在這裡必須分得開（L13-2）。
        "not_found": p["not_found"],
    }
    if dry_run:
        result["detail"] = {k: {"doc_id": v["doc_id"], "changed": v["changed"],
                                "removed": v["removed_local_ids"]}
                            for k, v in p["files"].items()}
        return result
    if p["not_found"]:
        raise RuntimeError(f"判決指到抽取檔裡不存在的 assertion：{p['not_found']}")

    superseded: list[str] = []
    for name, spec in p["files"].items():
        path = EXTRACTIONS / name
        superseded.append(_supersede(path).name)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["edges"] = spec["new_edges"]
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
    ap.add_argument("--classification", required=True, help="判決檔路徑（JSON list）")
    ap.add_argument("--only", nargs="*", help="只套這些 verdict（白名單）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--backup-dir")
    args = ap.parse_args()
    print(json.dumps(
        migrate(classification=Path(args.classification),
                only=set(args.only) if args.only else None,
                dry_run=args.dry_run, backup_dir=args.backup_dir),
        ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
