"""Golden fixtures：凍結 refactor **之前**的 expected semantic behavior。

## 為什麼必須現在做

`historical-failure-matrix.md` §8：dual run 要求「舊 pipeline 與新 pipeline 對**同一
frozen input** 並行執行，產生 semantic diff」。而 **B1 一動，「舊行為長什麼樣」就
補不回來了**——所以捕捉必須在任何搬遷之前。

## 隱私分層（硬規則）

Decision Store 與 Google Sheet 是 private authority，**永不進 Git**。所以輸出分兩層：

- `tests/fixtures/golden/`（tracked）——公開輸入 ＋ **語意摘要與 digest**。
  可以回答「行為變了沒」，但不含任何 NAV／持股／部位金額。
- `library/private/golden/`（gitignored）——完整輸出，供本機 dual run 逐欄比對。

**digest 就足以偵測漂移**；要看差在哪一欄時才需要 private 那份。

用法：
    python scripts/capture_golden_fixtures.py            # 擷取／更新
    python scripts/capture_golden_fixtures.py --verify   # 只比對，不寫檔（漂移即 exit 1）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TRACKED_DIR = ROOT / "tests" / "fixtures" / "golden"
PRIVATE_DIR = ROOT / "library" / "private" / "golden"


def _digest(payload: Any) -> str:
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      default=str, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


# ---------------------------------------------------------------------------
# 14 類 fixture 的登記表
# ---------------------------------------------------------------------------

class Capture:
    """一類 golden fixture。

    `private` 為 True 代表完整內容含 private authority，只有摘要與 digest 進 Git。
    `guards` 指回它守的歷史事故——**沒有指向的 fixture 是裝飾品**。
    """

    def __init__(self, key: str, guards: str, fn: Callable[[], dict],
                 *, private: bool = False) -> None:
        self.key = key
        self.guards = guards
        self.fn = fn
        self.private = private


def _registry_rows() -> list[dict]:
    return json.loads((ROOT / "config" / "company_identity.json")
                      .read_text(encoding="utf-8"))["companies"]


# ---- 1. 正常公司 ----------------------------------------------------------
def cap_normal_company() -> dict:
    rows = _registry_rows()
    entry = next(r for r in rows if r["company_id"] == "co:coherent")
    return {"registry_entry": entry,
            "note": "資料最完整的標的：有五軸、有 variant perception、有 live fill、有 outcome"}


# ---- 2. ticker alias / 三層 symbol（F-05）---------------------------------
def cap_symbol_layers() -> dict:
    rows = _registry_rows()
    entry = next(r for r in rows if r["company_id"] == "co:sivers_semiconductors")
    return {
        "registry_entry": entry,
        "expected": {
            "research_ticker": "SIVE.ST", "market_currency": "SEK",
            "execution_venue": "FRA", "execution_currency": "EUR",
        },
        "note": "研究／執行／provider 三層 symbol 不得互相冒充；"
                "瑞典主掛牌的 ADV 不得冒充 Frankfurt live liquidity",
    }


# ---- 3. minor unit 報價（F-02）-------------------------------------------
def cap_minor_unit_quotes() -> dict:
    from identity.currency import resolve_quote_unit  # type: ignore[attr-defined]

    registry = json.loads((ROOT / "config" / "currency_units.json")
                          .read_text(encoding="utf-8"))
    units = {k: v for k, v in registry.items() if not k.startswith("_")}
    resolved = {}
    for code in ("GBp", "GBP", "ILA", "ZAc", "USD"):
        try:
            resolved[code] = str(resolve_quote_unit(code))
        except Exception as exc:
            resolved[code] = f"<{type(exc).__name__}>"
    return {
        "registered_units": units,
        "resolution": resolved,
        "note": "⚠ 大小寫敏感：GBp（便士）與 GBP（英鎊）折疊會讓價格差 100 倍。"
                "「修正」成 ISO code 會通過所有驗證卻餵出錯價——比 quarantine 危險得多",
    }


# ---- 4. 缺財務資料的未上市公司（F-03）------------------------------------
def cap_unlisted_company() -> dict:
    rows = _registry_rows()
    unlisted = [r for r in rows if r.get("research_ticker") is None]
    return {
        "count": len(unlisted),
        "sample": next(r for r in unlisted if r["company_id"] == "co:agility_robotics"),
        "note": "research_ticker=null 是**明確標記**不是空缺（L9）。"
                "identity 的部分缺漏不得靜默關掉整條下游管線（F-03）",
    }


# ---- 5/6/13. 圖：瓶頸、多替代源、截斷邊界 --------------------------------
def _graph_rows() -> list[dict]:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from neo4j import GraphDatabase
    from identity.registry import get_registry
    from query.bottleneck import fetch_assertions, rank_bottlenecks

    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    try:
        with driver.session() as session:
            assertions = fetch_assertions(session)
            ranked = rank_bottlenecks(assertions, get_registry())
    finally:
        driver.close()
    rows = ranked["rows"] if isinstance(ranked, dict) else ranked
    return [dict(r) for r in rows]


def cap_structural_bottleneck() -> dict:
    rows = _graph_rows()
    top = rows[:3]
    return {
        "top3": [{k: v for k, v in r.items() if k in
                  ("company_id", "relation", "target_id", "substitutability",
                   "sole_source", "evidence_class", "qualification_status",
                   "demand_anchor")} for r in top],
        "total_rows": len(rows),
        "note": "sub>=4 的可行動排序。**唯一排序權威是 query/bottleneck.py**；"
                "alpha 排序必須消費它，不得重算結構分",
    }


def cap_multiple_substitutes() -> dict:
    rows = _graph_rows()
    by_target: dict[str, list[str]] = {}
    for row in rows:
        by_target.setdefault(str(row.get("target_id")), []).append(
            str(row.get("company_id")))
    crowded = sorted(by_target.items(), key=lambda kv: -len(kv[1]))[:3]
    return {
        "most_supplied_targets": [{"target": t, "suppliers": sorted(set(s))}
                                  for t, s in crowded],
        "note": "⚠ 同一 chokepoint 的供應商計數反映的是**我們研究了幾家**，"
                "不是世界上有幾家——不得單獨當瓶頸性證據",
    }


def cap_truncation_boundary() -> dict:
    rows = _graph_rows()
    limit = 10
    return {
        "limit": limit,
        "rows_within_limit": [str(r.get("company_id")) for r in rows[:limit]],
        "full_id_count": len(rows),
        "first_beyond_limit": (str(rows[limit].get("company_id"))
                               if len(rows) > limit else None),
        "note": "F-20：只帶前 N 名時，第 N+1 名會被誤判成「不在排序裡」。"
                "RankedList 型別強制同時帶截斷前的完整 id 集合",
    }


# ---- 7. watching item（F-15）---------------------------------------------
def cap_watch_states() -> dict:
    from engine_b import event_watch as ew

    data = ew.load_watches()
    watches = data.get("watches", []) if isinstance(data, dict) else list(data)
    stalled = [w for w in watches if ew.is_stalled(w)]
    return {
        "counters": ew.counters(data),
        "total": len(watches),
        "stalled_ids": sorted(str(w.get("watch_id")) for w in stalled)[:10],
        "note": "F-15：consumed-marker 沒有到期兜底時，標的用完即靜默沉底。"
                "「可觸發」與「還會醒」是兩個問題，不得共用一個布林",
    }


# ---- 8/9. cohort lifecycle 與 blocked state（F-06／F-24；結構 only）------
def cap_cohort_lifecycle() -> dict:
    from decision_lab.bootstrap import open_default_store

    store = open_default_store()
    try:
        cohorts = store.list_operational_cohorts(
            as_of=datetime.now().astimezone().isoformat())
        states: dict[str, int] = {}
        multi_epoch: list[str] = []
        for cohort in cohorts:
            status = str(cohort.get("lifecycle_status") or "unknown")
            states[status] = states.get(status, 0) + 1
            if int(cohort.get("lifecycle_epoch") or 1) > 1:
                multi_epoch.append(str(cohort.get("company_id")))
        return {
            "lifecycle_state_counts": states,
            "cohorts_with_reopened_epoch": sorted(multi_epoch),
            "note": "F-06：terminal 不等於死亡——已終結的 cohort 仍可能收到新事實，"
                    "必須有 append-only 的重開路徑（reopen_lifecycle_epoch）",
        }
    finally:
        store.close()


def cap_blocked_states() -> dict:
    from decision_lab.bootstrap import open_default_store

    store = open_default_store()
    try:
        cohorts = store.list_operational_cohorts(
            as_of=datetime.now().astimezone().isoformat())
        missing: dict[str, int] = {}
        for cohort in cohorts:
            decision_id = cohort.get("latest_decision_id")
            if not decision_id:
                continue
            payload = store.get_decision(str(decision_id)).get("payload", {})
            if isinstance(payload, str):
                payload = json.loads(payload)
            for axis in (payload.get("sizing", {}).get("axis_results") or {}).values():
                for item in (axis.get("missing_data") or []):
                    key = str(item)[:60]
                    missing[key] = missing.get(key, 0) + 1
        return {
            "missing_data_histogram": dict(sorted(missing.items(),
                                                  key=lambda kv: -kv[1])[:15]),
            "note": "F-24：research_assessment_missing 與「缺某一筆觀測」是兩層關卡。"
                    "順序是 assessment → 觀測才有機會被引用",
        }
    finally:
        store.close()


# ---- 10. stale data ------------------------------------------------------
def cap_stale_observations() -> dict:
    from engine_c.db import get_conn

    cur = get_conn().cursor()
    cur.execute("SELECT ticker, field_name, as_of FROM manual_observations "
                "ORDER BY as_of ASC LIMIT 5")
    oldest = [dict(zip(("ticker", "field_name", "as_of"), tuple(r)))
              for r in cur.fetchall()]
    cur.execute("SELECT COUNT(*) FROM manual_observations")
    total = cur.fetchone()[0]
    return {
        "total_manual_observations": total,
        "oldest": oldest,
        "note": "runway 觀測的 as_of 應填**資產負債表日**不是申報日；"
                "100 天鮮度窗是刻意對齊財報節奏的設計，**不要去改窗**",
    }


# ---- 11. conflicting evidence -------------------------------------------
def cap_edge_conflicts() -> dict:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from neo4j import GraphDatabase
    from query.edge_conflicts import build_edge_states, detect_conflicts, fetch_assertions

    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    try:
        with driver.session() as session:
            conflicts = detect_conflicts(build_edge_states(fetch_assertions(session)))
    finally:
        driver.close()
    return {
        "raw_conflict_count": len(conflicts),
        "sample_ids": sorted(str(c.get("conflict_id"))
                             for c in conflicts[:5]) if conflicts else [],
        "note": "衝突單位是 edge_key + attribute。⚠ 這是 RAW detector，"
                "不扣除已核准的 resolution——數字恆定不代表沒被處理",
    }


# ---- 12. point-in-time boundary（F-31）----------------------------------
def cap_point_in_time_boundary() -> dict:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from neo4j import GraphDatabase

    query = """
    MATCH (a:EdgeAssertion) OPTIONAL MATCH (a)-[:CITES]->(d:SourceDoc)
    RETURN count(a) AS assertions, count(d.published_at) AS dated
    """
    query2 = """
    MATCH (c:Claim) OPTIONAL MATCH (c)-[:CITES]->(d:SourceDoc)
    RETURN count(c) AS claims, count(d.published_at) AS dated
    """
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    try:
        with driver.session() as session:
            a = dict(session.run(query).single())
            c = dict(session.run(query2).single())
    finally:
        driver.close()
    return {
        "assertion_dated_coverage": a,
        "claim_dated_coverage": c,
        "note": "🔴 canonical edge **完全沒有時間欄位**；唯一時間線索是 "
                "CITES → SourceDoc.published_at。Phase 6 的驗收是把 dated 比例推到 ≥95%",
    }


# ---- 14. 多帳戶同一檔（F-21；PRIVATE）------------------------------------
def cap_multi_account_holding() -> dict:
    from engine_d_runtime.adapters import fetch_nav_exposure

    exposure = fetch_nav_exposure() or {}
    upstream = exposure.get("upstream") or {}
    status = str(upstream.get("status") or exposure.get("status") or "unknown")
    rows = [r for r in (exposure.get("positions") or exposure.get("rows") or [])
            if isinstance(r, dict)]
    if not rows:
        return {"status": status,
                "note": "Google Sheet 讀不到或無持股——**兩者是不同狀態**，"
                        "不得壓成同一個 unavailable（F-33）"}
    def _lot_count(row: dict) -> int:
        # ⚠ `lots` 是**筆數（int）**不是清單——第一版假設它是 list 而 TypeError。
        # 這正是 golden fixture 要抓的東西：對上游形狀的錯誤假設。
        lots = row.get("lots")
        return lots if isinstance(lots, int) else len(lots or [])

    multi = [r for r in rows if _lot_count(r) > 1]
    return {
        "status": status,
        "position_count": len(rows),
        "tickers_across_multiple_lots": sorted(
            str(r.get("ticker")) for r in multi),
        "note": "F-21：同一檔散在多帳戶時，按第一列 nav_base 計算會讓"
                "**沒有任何一列顯示真實曝險**。只記 ticker 與 lot 數，不記金額",
    }


CAPTURES: tuple[Capture, ...] = (
    Capture("normal_company", "baseline", cap_normal_company),
    Capture("symbol_layers", "F-05", cap_symbol_layers),
    Capture("minor_unit_quotes", "F-02", cap_minor_unit_quotes),
    Capture("unlisted_company", "F-03", cap_unlisted_company),
    Capture("structural_bottleneck", "—", cap_structural_bottleneck),
    Capture("multiple_substitutes", "—", cap_multiple_substitutes),
    Capture("watch_states", "F-15", cap_watch_states),
    Capture("cohort_lifecycle", "F-06", cap_cohort_lifecycle),
    Capture("blocked_states", "F-24", cap_blocked_states),
    Capture("stale_observations", "—", cap_stale_observations),
    Capture("edge_conflicts", "—", cap_edge_conflicts),
    Capture("point_in_time_boundary", "F-31", cap_point_in_time_boundary),
    Capture("truncation_boundary", "F-20", cap_truncation_boundary),
    Capture("multi_account_holding", "F-21", cap_multi_account_holding, private=True),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true",
                        help="只比對 digest，不寫檔；漂移即 exit 1")
    args = parser.parse_args()

    manifest_path = TRACKED_DIR / "manifest.json"
    previous = (json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest_path.exists() else {"fixtures": {}})

    manifest: dict[str, Any] = {
        "_comment": "Golden fixtures 的 digest 清單。private=true 的完整內容只在"
                    " library/private/golden/（gitignored）；這裡只有摘要與 digest。",
        "captured_at": date.today().isoformat(),
        "fixtures": {},
    }
    drift: list[str] = []
    failures: list[str] = []

    for capture in CAPTURES:
        try:
            payload = capture.fn()
        except Exception as exc:
            failures.append(f"{capture.key}: {type(exc).__name__}: {exc}")
            print(f"  ✗ {capture.key:<26} {type(exc).__name__}: {str(exc)[:70]}")
            continue
        digest = _digest(payload)
        old = (previous.get("fixtures", {}).get(capture.key) or {}).get("digest")
        status = "新增" if old is None else ("**漂移**" if old != digest else "不變")
        if old is not None and old != digest:
            drift.append(capture.key)
        manifest["fixtures"][capture.key] = {
            "guards": capture.guards, "private": capture.private, "digest": digest,
        }
        print(f"  ✓ {capture.key:<26} {capture.guards:<8} {status}")

        if args.verify:
            continue
        if capture.private:
            PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
            (PRIVATE_DIR / f"{capture.key}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8")
            manifest["fixtures"][capture.key]["summary"] = {
                k: v for k, v in payload.items()
                if k in ("status", "note", "position_count",
                         "tickers_across_multiple_lots")
            }
        else:
            TRACKED_DIR.mkdir(parents=True, exist_ok=True)
            (TRACKED_DIR / f"{capture.key}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8")

    print(f"\n擷取 {len(manifest['fixtures'])}/{len(CAPTURES)} 類"
          f"｜漂移 {len(drift)}｜失敗 {len(failures)}")
    for item in failures:
        print(f"  ✗ {item}")
    if drift:
        print(f"  ⚠ 漂移：{drift}")
        print("     漂移不必然是壞事（資料本來就會長），但**必須被解釋**："
              "是 EXPECTED_CHANGE 還是 REGRESSION？")

    if not args.verify:
        TRACKED_DIR.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n已寫入 {TRACKED_DIR}（tracked）與 {PRIVATE_DIR}（private）")

    if failures:
        return 1
    return 1 if (args.verify and drift) else 0


if __name__ == "__main__":
    raise SystemExit(main())
