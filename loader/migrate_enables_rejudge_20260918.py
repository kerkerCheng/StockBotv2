"""[608][609][610]：把 `enables` 重判的結果落進圖（使用者 2026-09-18 核准）。

## 事發

`schema/vocab.json` 與 `prompts/extract_system.md` 對 `enables` 的定義只有一個——
**A's adoption drives demand for B**。但圖裡有一批邊是照相反的讀法寫的，而
`query/bottleneck.py` 的走訪**也**實作了相反那一邊，於是兩個錯互相抵銷、長期沒人發現。

pq2 [607] 逐條對來源逐字重判了 84 對（覆蓋圖裡 82 對＝100%）：
`keep 47`／`retype_is_component_of 14`／`reverse 10`／`flag_evidence 8`／
`retype_depends_on 3`／`delete 2`。判決逐條在
`library/private/alpha/enables_rejudge/classification.json`。

另加 pq2 [606] 查出的兩件（packet 在同目錄 `packet_606.md`）：
1. `tech:external_laser_source is_component_of tech:isolator` **方向相反**——
   原逐字只是列舉 Coherent 做的兩樣東西，完全沒說哪個是哪個的元件（L6-③ 幻覺型態）；
   正確方向有 tier-1 逐字兩處（`coherent_q3fy26_cpo`）。
2. `tech:inp_eml` 與 `tech:eml` 是**重複節點**——走 `identity/entities.py` 的 alias，
   本腳本**不改抽取檔**來搬節點（沿用 `migrate_nand_merge_20260910.py` 的判準）。

## 為什麼要改抽取檔（與 nand 那次的差異）

nand 那次是**搬節點**，registry 在 loader 入圖前解析，所以抽取檔保持原樣——
它是逐字證據，不該為了搬節點被改寫。

**本次有一半是改 relation**，而 relation 不是逐字，是抽取當下 LLM 的判讀，
圖又可由抽取檔重建（L10）。所以判讀錯了就必須改在判讀所在的那一層，
否則下次重載會把錯的值放回來。⚠ **`sources[].quote` 一個字都不動。**

⚠ `library/resolutions/` 承載不了這件事：它是 per-edge-key／per-attribute 的**值**衝突解決，
表達不出「relation 判錯」或「這條邊不該存在」。

## 為什麼是重載而不是 Cypher 手術

`edge_key = sha256([src_id, relation, dst_id])`——改 relation 必須重算 key，
手工改會弄髒（沿用 2026-09-04／09-10 兩次的結論）。本腳本走 scoped 重載：
**改檔 → 重載受影響的 22 份 → 刪掉被移除的 assertion 與孤兒 canonical 邊 → 重投影**。

用法::

    python loader/migrate_enables_rejudge_20260918.py --dry-run
    python loader/migrate_enables_rejudge_20260918.py \
        --backup-dir backups/20260918-enables-rejudge
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loader.edge_resolution import project_edge_keys  # noqa: E402
from loader.load_to_neo4j import edge_key, evidence_id, load  # noqa: E402
from loader.migrate_entity_dedup_20260904 import _admin_driver  # noqa: E402

EXTRACTIONS = ROOT / "extractions"
SUPERSEDED = EXTRACTIONS / "superseded"
CLASSIFICATION = ROOT / "library/private/alpha/enables_rejudge/classification.json"

#: 抽取檔用的節點 id 與圖裡收斂後的 id 對映（重判時撞到的）。
ALIAS = {
    "tech:nand_flash": "tech:nand",
    "tech:nand_production": "tech:nand",
    "tech:nand_technology": "tech:nand",
    "tech:dram_production": "tech:dram_manufacturing",
}

#: [610] 的第一件：方向相反的既有邊。
ISOLATOR = ("tech:external_laser_source", "is_component_of", "tech:isolator")

#: [610] 的第二件走 registry，不在這裡列——`identity/entities.py` 是唯一登記處（L16）。
MERGED_AWAY_NODE = "tech:inp_eml"


def _verdicts() -> dict[tuple[str, str], str]:
    rows = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))
    out: dict[tuple[str, str], str] = {}
    for r in rows:
        if r["verdict"] in ("keep", "flag_evidence"):
            continue          # keep 不動；flag_evidence 退回研究，也不動
        out[(r["src"], r["dst"])] = r["verdict"]
    return out


def _rewrite_edges(doc: dict, verdicts: dict) -> tuple[list[dict], list[str]]:
    """回傳（新的 edges, 被移除的 edge local_id）。**只動 relation／端點，不動 quote。**"""
    kept: list[dict] = []
    removed: list[str] = []
    for e in doc.get("edges", []):
        src, rel, dst = e.get("src_id"), e.get("relation"), e.get("dst_id")
        if (src, rel, dst) == ISOLATOR:
            e = dict(e, src_id=dst, dst_id=src)          # 翻方向，relation 不變
            kept.append(e)
            continue
        if rel != "enables":
            kept.append(e)
            continue
        verdict = verdicts.get((src, dst)) or verdicts.get(
            (ALIAS.get(src, src), ALIAS.get(dst, dst)))
        if verdict is None:
            kept.append(e)
        elif verdict == "delete":
            removed.append(e["id"])
        elif verdict == "reverse":
            kept.append(dict(e, src_id=dst, dst_id=src))
        elif verdict == "retype_is_component_of":
            kept.append(dict(e, relation="is_component_of"))
        elif verdict == "retype_depends_on":
            # B depends_on A：端點與 relation 一起換
            kept.append(dict(e, src_id=dst, dst_id=src, relation="depends_on"))
        else:
            raise RuntimeError(f"未知判決 {verdict}")
    return kept, removed


def plan() -> dict:
    verdicts = _verdicts()
    files: dict[str, dict] = {}
    for path in sorted(EXTRACTIONS.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        new_edges, removed = _rewrite_edges(doc, verdicts)
        if new_edges == doc.get("edges", []) and not removed:
            continue
        doc_id = (doc.get("source_doc") or {}).get("doc_id") or path.stem
        before_by_id = {e["id"]: e for e in doc.get("edges", [])}
        old_keys = {edge_key(e["src_id"], e["relation"], e["dst_id"])
                    for e in doc.get("edges", [])}
        new_keys = {edge_key(e["src_id"], e["relation"], e["dst_id"]) for e in new_edges}
        files[path.name] = {
            "doc_id": doc_id,
            "new_edges": new_edges,
            "removed_local_ids": removed,
            "removed_assertion_ids": [evidence_id(doc_id, lid) for lid in removed],
            "old_edge_keys": sorted(old_keys),
            "new_edge_keys": sorted(new_keys),
            # ⚠ 按 **edge id** 比，不要 zip：刪掉一條之後整串位移，zip 會把後面每一條
            # 都算成「變了」（首版就是這樣報出 61 而不是 29）。
            "changed": sum(1 for e in new_edges if e != before_by_id.get(e["id"])),
        }
    return {"files": files, "verdicts": len(verdicts)}


def _supersede(path: Path) -> Path:
    """封存被取代的版本。

    ⚠ 檔名用**被封存內容自身**的 `sha256[:8]`，任何人可以重算驗證。
    既有 9 份的雜湊後綴沒有任何程式在產生、也對不上檔案內容——那是無法驗證的人工慣例，
    不沿用（`docs/` 另記）。
    """
    SUPERSEDED.mkdir(parents=True, exist_ok=True)
    raw = path.read_bytes()
    dest = SUPERSEDED / f"{path.stem}.{hashlib.sha256(raw).hexdigest()[:8]}.json"
    shutil.copy2(path, dest)
    return dest


def _cleanup(session, removed_assertion_ids: list[str]) -> dict:
    """刪掉：①被移除的 assertion ②沒有任何 assertion 撐著的 canonical 邊 ③併走的舊節點。

    ⚠ 順序重要（沿用 nand 那次的教訓）：先刪 assertion，再刪孤兒邊——
    反過來會讓 `edge_resolution` 的 reconciliation 認為有 assertion 沒有對應 relationship。
    """
    dropped_assertions = 0
    if removed_assertion_ids:
        dropped_assertions = session.run(
            "MATCH (e:EdgeAssertion) WHERE e.id IN $ids DETACH DELETE e RETURN count(e) AS c",
            ids=removed_assertion_ids,
        ).single()["c"]

    # 併走的節點：它的 assertion 已由重載改指 canonical，殘留的是舊 id 的節點本身
    dropped_merged_assertions = session.run(
        "MATCH (e:EdgeAssertion) WHERE e.src_id = $id OR e.dst_id = $id "
        "DETACH DELETE e RETURN count(e) AS c", id=MERGED_AWAY_NODE,
    ).single()["c"]
    dropped_nodes = session.run(
        "MATCH (n:Entity {id: $id}) DETACH DELETE n RETURN count(n) AS c",
        id=MERGED_AWAY_NODE,
    ).single()["c"]

    # 孤兒 canonical 邊：edge_key 底下一條 assertion 都不剩
    orphans = session.run(
        """
        MATCH (a:Entity)-[r]->(b:Entity) WHERE r.edge_key IS NOT NULL
        WITH r, r.edge_key AS k
        WHERE NOT EXISTS { MATCH (e:EdgeAssertion {edge_key: k}) }
        DELETE r RETURN count(r) AS c
        """
    ).single()["c"]
    return {
        "dropped_assertions": dropped_assertions,
        "dropped_merged_node_assertions": dropped_merged_assertions,
        "dropped_merged_nodes": dropped_nodes,
        "dropped_orphan_edges": orphans,
    }


def migrate(*, dry_run: bool, backup_dir: str | None) -> dict:
    if not dry_run and not backup_dir:
        raise RuntimeError("live migration 需要 --backup-dir（含非空 neo4j_export.json）")
    if not dry_run:
        export = Path(backup_dir).resolve() / "neo4j_export.json"
        if not export.is_file() or export.stat().st_size == 0:
            raise RuntimeError(f"找不到 Neo4j 匯出或為空：{export}")

    p = plan()
    result: dict = {
        "dry_run": dry_run,
        "backup_dir": backup_dir,
        "files": len(p["files"]),
        "edges_changed": sum(f["changed"] for f in p["files"].values()),
        "edges_removed": sum(len(f["removed_local_ids"]) for f in p["files"].values()),
    }
    if dry_run:
        result["detail"] = {k: {"doc_id": v["doc_id"], "changed": v["changed"],
                                "removed": v["removed_local_ids"]}
                            for k, v in p["files"].items()}
        return result

    # ── ① 改檔（封存舊版）──
    superseded: list[str] = []
    for name, spec in p["files"].items():
        path = EXTRACTIONS / name
        superseded.append(_supersede(path).name)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["edges"] = spec["new_edges"]
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    result["superseded"] = superseded

    # ── ② 重載 ＋ ③ 清理 ＋ ④ 重投影 ──
    removed_ids = [i for f in p["files"].values() for i in f["removed_assertion_ids"]]
    affected_keys: set[str] = set()
    for f in p["files"].values():
        affected_keys |= set(f["new_edge_keys"])

    driver = _admin_driver()
    try:
        with driver.session() as session:
            for name, spec in p["files"].items():
                doc = json.loads((EXTRACTIONS / name).read_text(encoding="utf-8"))
                load(doc, session, allow_dup_url=True)
            result["cleanup"] = _cleanup(session, removed_ids)
            live_keys = set(session.run(
                "MATCH (e:EdgeAssertion) WHERE e.edge_key IN $keys "
                "RETURN collect(DISTINCT e.edge_key) AS k", keys=sorted(affected_keys),
            ).single()["k"])
        # ⚠ 只重投影**還有 assertion 撐著**的 key：`project_edge_keys` 對沒有 assertion 的
        # key 會 raise，而那正是我們剛刪掉的那些。
        result["reprojected"] = project_edge_keys(driver, live_keys)["edges"]
    finally:
        driver.close()
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="[608][609][610] enables 重判落圖")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--backup-dir")
    args = ap.parse_args()
    print(json.dumps(migrate(dry_run=args.dry_run, backup_dir=args.backup_dir),
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
