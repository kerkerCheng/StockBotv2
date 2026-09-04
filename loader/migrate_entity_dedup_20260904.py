"""合併同一實體的重複 TechNode id，並補投影未投影的關係。

## 事發（2026-09-04）

`apply_research_action` 對兩份已核准的 RA 一律回 `partial`：

    graph reconciliation is incomplete: unprojected=0, legacy=1, orphaned_evidence=0

**一條屬性全空的 `ENABLES` 邊把整個入圖閘門卡死了**（對所有 RA 都一樣，不只那兩份）。
追下去發現的不是那條邊的問題，是**同一個實體有三個 id**：

| id | 來源抽取檔 | 邊 |
|---|---|---|
| `tech:semicon_manuf_equipment` | `gfs_20_f_20260227` | 2（有 key） |
| `tech:semiconductor_equipment` | `amat_10_q_20260219` | 4（**卡死的那條在這**） |
| `tech:semiconductor_manufacturing_equipment` | `amat_10_k_20251212` | 0（孤立） |

三者 `name` 完全相同、`abstraction_level` 都是 `equipment_epitaxy`。**其中兩個還來自
同一家公司（Applied Materials）的 10-K 與 10-Q**——這是 L6 那個坑（局部 ID 跨文件不收斂）
長在非公司實體上：公司有 `config/company_identity.json` 當 registry，TechNode 什麼都沒有，
所以每份抽取各猜各的。

⚠ **它安靜地造成了兩個下游錯誤：** ① 孤立的那個被 `query/coverage_gaps.py` 判成
「🔴 研究缺口」，差點派研究去挖一個已經有供應商的東西；② 入圖閘門全面卡死。

## 為什麼是改抽取檔再重載，不是 Cypher 手術

`edge_key = sha256([src_id, relation, dst_id])`——搬邊必須重算 key，手工改會弄髒。
`migrate_replay_identity.py` 的原則是對的（**抽取檔是 ground truth**），但它會全量 replay
225 份文件、清掉整個 identity 層；為了 3 個節點動那個規模，爆炸半徑不成比例。
本支走同一個原則的 scoped 版本：**改抽取檔 → 只重載那 6 份 → 刪掉孤立的舊節點 → 重投影**。

## 刻意不做的四件事

1. **不把 group B 併進 group A。** dep/etch/clean ⊊ WFE ⊊ semiconductor manufacturing
   equipment；併掉會抹平「ASML 的微影在 WFE 裡、但不在 dep/etch/clean 裡」這個對瓶頸
   分析真正重要的區別。
2. **不新增兩者之間的階層邊。** 那是新的知識主張，仍走 graph admission 人工 gate。
3. **不動 `tech:200mm_equipment`。** 它是 AMAT 的 200mm 舊製程機台，真的是別的東西。
4. **不解 `ramp_difficulty_intrinsic` 的值衝突。** Lam 的 10-K 寫 4、10-Q 寫 3，
   兩份都在講 dep/etch/clean。邊有 `edge_resolution.py` 處理衝突，**節點屬性沒有對應機制**
   ——這是另一個缺口，本支只記錄不裁決（見 ROADMAP）。

⚠ 另一個順帶發現、本支不修的隱患：`MERGE_NODE` 對 `n.attributes` 是直接 `SET`，
**後載入的文件會整包蓋掉前一份的節點屬性**（只有 `source_ids` 會聯集）。本次已把三份
抽取檔的 attributes 改成一致的聯集，讓載入順序不再決定結果——但那是繞過，不是修好。

用法::

    python loader/migrate_entity_dedup_20260904.py --dry-run
    python loader/migrate_entity_dedup_20260904.py --backup-dir library/private/backups/<ts>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:  # pragma: no cover
    pass

from loader.edge_resolution import project_edge_keys  # noqa: E402
from loader.load_to_neo4j import load  # noqa: E402

MANIFEST = ROOT / "loader" / "manifests" / "entity-dedup-20260904.json"

#: 重複 id → canonical id。**canonical 一律選「與 `name` 一致的全名式」**——
#: 縮寫式（`semicon_manuf`）正是會被下一份抽取重新猜錯的那種。
MERGES: dict[str, str] = {
    "tech:semiconductor_equipment": "tech:semiconductor_manufacturing_equipment",
    "tech:semicon_manuf_equipment": "tech:semiconductor_manufacturing_equipment",
    "tech:wafer_fab_equipment": "tech:deposition_etch_clean",
}

#: 要重載的抽取檔——含 canonical 端，否則新 id 的節點屬性不會被寫進去。
RELOAD_DOCS: tuple[str, ...] = (
    "amat_10_q_20260219", "gfs_20_f_20260227", "amat_10_k_20251212",
    "lrcx_10_q_20260129", "lrcx_10_k_20250811", "lrcx_10_q_20260423",
)


def _preflight(session) -> dict:
    """確認抽取檔已改乾淨——**先驗來源，再動圖**。"""
    stale: list[str] = []
    for path in (ROOT / "extractions").glob("*.json"):
        text = path.read_text(encoding="utf-8")
        for old in MERGES:
            if f'"{old}"' in text:
                stale.append(f"{path.name} → {old}")
    if stale:
        raise RuntimeError(
            "抽取檔仍引用舊 id，重載後會原樣長回來（L16：修來源不是修投影）：\n  "
            + "\n  ".join(stale)
        )
    return {
        "graph_before": session.run(
            "MATCH (n:Entity) WHERE n.id IN $ids RETURN collect(n.id) AS ids",
            ids=list(MERGES),
        ).single()["ids"],
        "legacy_edges_before": session.run(
            "MATCH ()-[r]->() WHERE NOT type(r) IN ['CITES','ABOUT'] "
            "AND r.edge_key IS NULL RETURN count(r) AS c"
        ).single()["c"],
    }


def _affected_edge_keys(session) -> set[str]:
    rows = session.run(
        """
        MATCH (e:EdgeAssertion)
        WHERE e.src_id IN $ids OR e.dst_id IN $ids
        RETURN collect(DISTINCT e.edge_key) AS keys
        """,
        ids=list(MERGES) + sorted(set(MERGES.values())),
    ).single()["keys"]
    return {k for k in rows if k}


def _drop_duplicates(session) -> dict:
    """刪掉舊 id 的節點與**只屬於它們**的 assertion／關係。

    ⚠ 順序重要：先刪 assertion（它們帶著舊 `src_id`／`dst_id`，留著會讓
    `edge_resolution` 的 reconciliation 認為有 assertion 沒有對應 relationship）。
    """
    dropped_assertions = session.run(
        """
        MATCH (e:EdgeAssertion) WHERE e.src_id IN $ids OR e.dst_id IN $ids
        DETACH DELETE e RETURN count(e) AS c
        """,
        ids=list(MERGES),
    ).single()["c"]
    dropped_nodes = session.run(
        "MATCH (n:Entity) WHERE n.id IN $ids DETACH DELETE n RETURN count(n) AS c",
        ids=list(MERGES),
    ).single()["c"]
    return {"dropped_assertions": dropped_assertions, "dropped_nodes": dropped_nodes}


def _admin_driver():
    """遷移走**管理員**憑證，不走 `intake.application` 的 routine driver。

    ⚠ 這不是繞過權限，是用對身分：日常排程的 `cloud_routine` 只有 `routine_writer`
    角色、**沒有 DELETE 權限**，那正是最小權限該有的樣子（第一次實跑就被它擋下來，
    這是它在做它的工作）。結構性遷移是明確經人授權的一次性動作，
    `migrate_replay_identity.py` 等既有 `migrate_*.py` 也都用 `NEO4J_USER`／`NEO4J_PASSWORD`。
    """
    import os

    import neo4j

    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("NEO4J_PASSWORD is required（遷移需要管理員憑證）")
    return neo4j.GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )


def migrate(*, dry_run: bool, backup_dir: str | None) -> dict:
    if not dry_run and not backup_dir:
        raise RuntimeError("live migration 需要 --backup-dir（先跑 backup_private.py run）")
    if not dry_run:
        path = Path(backup_dir).resolve()
        export = path / "neo4j_export.json"
        if not export.is_file() or export.stat().st_size == 0:
            raise RuntimeError(f"找不到 Neo4j 匯出或為空：{export}")

    driver = _admin_driver()
    result: dict = {"dry_run": dry_run, "merges": MERGES, "backup_dir": backup_dir}
    try:
        with driver.session() as session:
            result["preflight"] = _preflight(session)
            if dry_run:
                result["would_reload"] = list(RELOAD_DOCS)
                result["would_drop_assertions"] = session.run(
                    "MATCH (e:EdgeAssertion) WHERE e.src_id IN $ids OR e.dst_id IN $ids "
                    "RETURN count(e) AS c", ids=list(MERGES),
                ).single()["c"]
                return result

            for doc_id in RELOAD_DOCS:
                doc = json.loads(
                    (ROOT / "extractions" / f"{doc_id}.json").read_text(encoding="utf-8")
                )
                load(doc, session, allow_dup_url=True)
            result["reloaded"] = list(RELOAD_DOCS)
            result.update(_drop_duplicates(session))
            keys = _affected_edge_keys(session)

        result["reprojected"] = project_edge_keys(driver, keys)
        with driver.session() as session:
            result["graph_after"] = session.run(
                "MATCH (n:Entity) WHERE n.id IN $ids RETURN collect(n.id) AS ids",
                ids=list(MERGES),
            ).single()["ids"]
            result["legacy_edges_after"] = session.run(
                "MATCH ()-[r]->() WHERE NOT type(r) IN ['CITES','ABOUT'] "
                "AND r.edge_key IS NULL RETURN count(r) AS c"
            ).single()["c"]
    finally:
        driver.close()

    # 驗收是「舊 id 一個都不剩、legacy 邊歸零」，不是「指令沒報錯」（L13）。
    if result["graph_after"]:
        raise RuntimeError(f"舊 id 仍在圖上：{result['graph_after']}")
    if result["legacy_edges_after"]:
        raise RuntimeError(f"仍有未投影的邊：{result['legacy_edges_after']}")

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backup-dir", help="backup_private.py run 產出的目錄")
    args = parser.parse_args()
    print(json.dumps(migrate(dry_run=args.dry_run, backup_dir=args.backup_dir),
                     ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
