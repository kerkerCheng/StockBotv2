"""Weekly 系統健康審查的唯一權威：Cypher 常數（雲端經 MCP 跑）+ 本機 CLI。

雲端 weekly routine 讀本檔的具名 Cypher 常數，經 MCP `run_read_query` 執行
（同 query/single_origin_report.py 的 SINGLE_ORIGIN_CYPHER 模式，不在 prompt 裡
複製第二份 Cypher）。本機 CLI（`python query/health_audit.py --local`）跑同一組
Cypher，外加只有本機能做的檢查：Engine C 新鮮度、財務清單可跑性、深度 conflict
queue（query/edge_conflicts.py）、applied 未 commit 的 Research Action、skills 同步。

注意：邊與 assertion 的 attributes 以 JSON 字串儲存，APOC 不保證存在，所以雲端
Cypher 對 sole_source / 高風險屬性用字串匹配啟發式——over-inclusive 是刻意的，
準確推導由本機 query/edge_conflicts.py 負責。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from thesis.lifecycle_schedule import is_due as lifecycle_is_due  # noqa: E402

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if load_dotenv is not None:
    load_dotenv(ROOT / ".env")

LIFECYCLE_FILE = ROOT / "thesis" / "lifecycle.json"
THESIS_DIR = ROOT / "thesis"
ENGINE_C_STALE_DAYS = 7
MEMO_FRESHNESS_TITLE = "Memo 新鮮度（超過各自核查週期）"

# L7：active memo 必須同時寫出「核查頻率」與「觸發後 48 小時內動作」。
L7_REQUIRED_PATTERNS = {
    "核查頻率": re.compile(r"核查頻率"),
    "觸發後48h動作": re.compile(r"48\s*(?:小時|h)", re.IGNORECASE),
}

# 高風險屬性清單與 thesis/evidence_manifest.py 的 HIGH_RISK_ATTRIBUTES 一致；
# 這裡以字串形式嵌入 Cypher，改動時兩處要同步。
HIGH_RISK_ATTRIBUTE_NAMES = (
    "sole_source",
    "substitutability",
    "structural_lead_time_weeks",
)


# ── 雲端可跑的 Cypher 常數（routine 讀常數 → run_read_query）─────────────────

# L8 圖層巡檢：sole_source=true 的邊，其所有 assertion 的 origin_entity 只有一個
# （單一來源，多半是供應商自報）。attributes 是 JSON 字串，用 CONTAINS 啟發式匹配
# loader json.dumps 的兩種間隔寫法。
SOLE_SOURCE_WEAK_CYPHER = """
MATCH (src:Entity)-[r]->(dst:Entity)
WHERE r.edge_key IS NOT NULL
  AND (r.attributes CONTAINS '"sole_source": true'
       OR r.attributes CONTAINS '"sole_source":true')
OPTIONAL MATCH (assertion:EdgeAssertion {edge_key: r.edge_key})
OPTIONAL MATCH (assertion)-[:CITES]->(source_doc:SourceDoc)
WITH r, src, dst,
     collect(DISTINCT source_doc.origin_entity) AS origin_entities,
     collect(DISTINCT assertion.id) AS assertion_ids
WHERE size(origin_entities) <= 1
RETURN r.edge_key AS edge_key,
       src.id + ' -[' + r.relation + ']-> ' + dst.id AS summary,
       origin_entities,
       assertion_ids
ORDER BY edge_key
"""

# 衝突候選（輕量、over-inclusive）：同一 edge_key 有多份 assertion、attributes
# JSON 不完全相同、且至少一份提到高風險屬性。準確的衝突推導（值層級、排除已
# resolution 的）只在本機 query/edge_conflicts.py 做。
CONFLICT_CANDIDATES_CYPHER = """
MATCH (assertion:EdgeAssertion)
WHERE assertion.attributes CONTAINS 'sole_source'
   OR assertion.attributes CONTAINS 'substitutability'
   OR assertion.attributes CONTAINS 'structural_lead_time_weeks'
WITH assertion.edge_key AS edge_key,
     collect(DISTINCT assertion.attributes) AS attribute_variants,
     collect(DISTINCT assertion.id) AS assertion_ids
WHERE size(attribute_variants) > 1
RETURN edge_key, assertion_ids, size(attribute_variants) AS variant_count
ORDER BY variant_count DESC, edge_key
"""

CLAIMS_MISSING_CITES_CYPHER = """
CALL () {
  MATCH (claim:Claim)
  WHERE NOT (claim)-[:CITES]->(:SourceDoc)
  RETURN 'claim' AS kind, claim.id AS element_id,
         left(coalesce(claim.statement, ''), 80) AS summary
  UNION ALL
  MATCH (assertion:EdgeAssertion)
  WHERE NOT (assertion)-[:CITES]->(:SourceDoc)
  RETURN 'assertion' AS kind, assertion.id AS element_id,
         coalesce(assertion.edge_key, '') AS summary
}
RETURN kind, element_id, summary
ORDER BY kind, element_id
"""

SOURCE_DOC_URLS_CYPHER = """
MATCH (sd:SourceDoc) WHERE sd.url IS NOT NULL AND sd.url <> ''
RETURN sd.id AS id, sd.url AS url, sd.section AS section
ORDER BY sd.id
"""

SCHEMA_STATE_CYPHER = """
OPTIONAL MATCH (state:GraphSchemaState {id: 'stockbotv2'})
RETURN state.version AS version
"""

# TICKER_MAP 覆蓋率：圖中 Company 節點清單；比對端（TICKER_MAP）在 repo clone 裡，
# 雲端與本機都能做差集。
COMPANY_IDS_CYPHER = """
MATCH (company:Company)
RETURN company.id AS company_id, company.name AS name
ORDER BY company_id
"""


# ── 純函式（雲端/本機/測試共用，不碰 DB）────────────────────────────────────

def lifecycle_due(lifecycle: dict, today: date) -> list[dict]:
    """回傳到期的 thesis 條目，review_required 恆視為到期。

    到期判準委派給 `thesis.lifecycle_schedule`——固定週期與催化劑取較早者。先前這裡
    與 `crons/thesis_freshness_check.py` 各有一份只讀 `next_check` 的實作，是同一個
    判準跑兩次。`due_reason` 讓下游看得出是例行到期還是催化劑到了（後者帶著「去讀
    哪份文件」的資訊，例行複查沒有）。
    """

    due = []
    for thesis_id, entry in sorted(lifecycle.items()):
        due_now, reason = lifecycle_is_due(entry, today=today)
        if due_now:
            due.append({"thesis_id": thesis_id, "due_reason": reason, **entry})
    return due


def l7_field_gaps(memo_text: str) -> list[str]:
    """回傳 memo 缺少的 L7 必要欄位名稱（核查頻率 / 觸發後 48h 動作）。"""

    return [
        label
        for label, pattern in L7_REQUIRED_PATTERNS.items()
        if not pattern.search(memo_text)
    ]


def ticker_map_gaps(company_ids: list[str], ticker_map: dict) -> list[str]:
    """圖中 Company 節點沒有 TICKER_MAP 條目的 id 清單（None 是合法映射，不算缺）。"""

    return sorted(set(company_ids) - set(ticker_map))


def load_resolution_hashes(resolution_dir: Path) -> dict[str, str]:
    """讀 library/resolutions/，回傳 conflict_id -> candidate_set_hash。"""

    hashes: dict[str, str] = {}
    if not resolution_dir.is_dir():
        return hashes
    for path in sorted(resolution_dir.glob("conflict_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        conflict_id = payload.get("conflict_id")
        if conflict_id:
            hashes[conflict_id] = payload.get("candidate_set_hash", "")
    return hashes


def split_conflicts_by_resolution(
    conflicts: list[dict], resolution_hashes: dict[str, str]
) -> tuple[list[dict], list[dict]]:
    """把 open conflict 分成（未處置, 已核准但 hash 過期 = 新證據重開）。

    hash 相符的視為已解決、不回傳（deterministic resolver 已投影 canonical 值）。
    """

    unresolved, stale = [], []
    for conflict in conflicts:
        approved_hash = resolution_hashes.get(conflict["conflict_id"])
        if approved_hash is None:
            unresolved.append(conflict)
        elif approved_hash != conflict["candidate_set_hash"]:
            stale.append(conflict)
    return unresolved, stale


def active_edge_keys_from_manifests(thesis_dir: Path = THESIS_DIR) -> set[str]:
    """從 active memo 的 *.evidence.json 收集被引用的 edge_key（M1 規則比對用）。"""

    edge_keys: set[str] = set()
    for path in sorted(thesis_dir.glob("*.evidence.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        text = json.dumps(payload)
        edge_keys.update(re.findall(r"edge:[0-9a-f]{64}", text))
    return edge_keys


# ── 本機專屬檢查 ──────────────────────────────────────────────────────────────

def engine_c_freshness(conn, tickers: list[str], *, today: date, stale_days: int = ENGINE_C_STALE_DAYS) -> dict:
    """每個 ticker 的最後 snapshot 日期；超過 stale_days 或沒資料就列出來。

    ⚠ 這裡刻意用 `snapshot_date`（ETL 執行日）而**不是** `bar_date`（行情交易日）。
    本函式問的是「上次抓資料是什麼時候」，`snapshot_date` 正是那題的答案。
    2026-08-14 把兩者拆開後，容易有人順手把這裡也改成 bar_date——不要改：
    改了會把「provider 週末沒有新 bar」誤報成「我們的 ETL 停了」。
    需要「這個價格屬於哪一天」的消費者才讀 `bar_date`。
    """

    rows = conn.execute(
        "SELECT ticker, MAX(snapshot_date) AS latest FROM financial_snapshots GROUP BY ticker"
    ).fetchall()
    latest = {row["ticker"]: row["latest"] for row in rows}
    stale, missing = [], []
    for ticker in sorted(tickers):
        value = latest.get(ticker)
        if value is None:
            missing.append(ticker)
            continue
        try:
            snap_date = datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            missing.append(ticker)
            continue
        age = (today - snap_date).days
        if age > stale_days:
            stale.append((ticker, age))
    return {"stale": stale, "missing": missing, "tracked": len(tickers)}


def _load_lifecycle() -> dict:
    try:
        return json.loads(LIFECYCLE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _driver():
    from neo4j import GraphDatabase
    import os

    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("NEO4J_PASSWORD is required")
    return GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )


def _section(title: str, level: str, lines: list[str]) -> list[str]:
    icon = {"green": "🟢", "yellow": "🟡", "red": "🔴"}[level]
    return [f"## {icon} {title}", "", *(lines or ["_(none)_"]), ""]


def run_local_audit(*, today: date | None = None) -> str:  # pragma: no cover - 組裝層
    today = today or date.today()
    report: list[str] = [f"# 系統健康審查 — {today.isoformat()}", ""]

    # 1. 圖層巡檢（與雲端相同的 Cypher）
    graph_lines: dict[str, list[str]] = {}
    schema_version = None
    company_ids: list[str] = []
    try:
        driver = _driver()
        with driver.session() as session:
            weak = list(session.run(SOLE_SOURCE_WEAK_CYPHER))
            graph_lines["sole_source"] = [
                f"- `{row['edge_key']}` — {row['summary']}（origin={row['origin_entities']}）"
                for row in weak
            ]
            missing_cites = list(session.run(CLAIMS_MISSING_CITES_CYPHER))
            graph_lines["missing_cites"] = [
                f"- [{row['kind']}] `{row['element_id']}` {row['summary']}"
                for row in missing_cites
            ]
            # 重複 SourceDoc：同一份文件被以不同 doc_id 重複 onboard（URL 正規化後比對）。
            # 正當例外——同文件多段：同 URL 的 group 每個都有非空且互異的 section（見
            # loader.check_duplicate_url），視為刻意拆段，不報。
            from loader.load_to_neo4j import normalize_url

            by_norm_url: dict[str, list[tuple[str, str]]] = {}
            for row in session.run(SOURCE_DOC_URLS_CYPHER):
                norm = normalize_url(row["url"])
                if norm:
                    by_norm_url.setdefault(norm, []).append(
                        (row["id"], (row.get("section") or "").strip())
                    )

            def _is_legit_multi_section(members: list[tuple[str, str]]) -> bool:
                sections = [sec for _, sec in members]
                return all(sections) and len(set(sections)) == len(sections)

            graph_lines["dup_url"] = [
                f"- `{norm}` ← {sorted(sid for sid, _ in members)}"
                for norm, members in sorted(by_norm_url.items())
                if len(members) > 1 and not _is_legit_multi_section(members)
            ]
            schema_version = session.run(SCHEMA_STATE_CYPHER).single()["version"]
            company_ids = [row["company_id"] for row in session.run(COMPANY_IDS_CYPHER)]

            # 2. 深度 conflict queue（本機才準）
            from query.edge_conflicts import (
                build_edge_states,
                detect_conflicts,
                fetch_assertions,
                sort_conflicts,
            )

            states = build_edge_states(fetch_assertions(session))
            active_keys = active_edge_keys_from_manifests()
            from loader.edge_resolution import DEFAULT_RESOLUTION_DIR

            unresolved, stale_resolutions = split_conflicts_by_resolution(
                detect_conflicts(states),
                load_resolution_hashes(DEFAULT_RESOLUTION_DIR),
            )
            conflicts = sort_conflicts(unresolved, active_edge_keys=active_keys)
            stale_resolutions = sort_conflicts(
                stale_resolutions, active_edge_keys=active_keys
            )
        driver.close()
    except Exception as exc:
        report.extend(_section("圖層巡檢", "red", [f"- Neo4j 連線失敗：{exc}"]))
        conflicts, stale_resolutions, active_keys = [], [], set()
    else:
        report.extend(
            _section(
                "sole_source 單一來源（L8 weak）",
                "yellow" if graph_lines["sole_source"] else "green",
                graph_lines["sole_source"],
            )
        )
        report.extend(
            _section(
                "Claim/EdgeAssertion 缺 CITES",
                "red" if graph_lines["missing_cites"] else "green",
                graph_lines["missing_cites"],
            )
        )
        report.extend(
            _section(
                "重複 SourceDoc（同 URL 不同 doc_id）",
                "red" if graph_lines.get("dup_url") else "green",
                graph_lines.get("dup_url", []),
            )
        )
        from mcp_server.graph_mcp import GRAPH_SCHEMA_VERSION

        schema_ok = schema_version == GRAPH_SCHEMA_VERSION
        report.extend(
            _section(
                "Graph schema 版本",
                "green" if schema_ok else "red",
                [f"- 圖：`{schema_version}` / repo 期望：`{GRAPH_SCHEMA_VERSION}`"],
            )
        )

        active_conflicts = [c for c in conflicts if c["edge_key"] in active_keys]
        conflict_lines = [
            f"- `{c['conflict_id']}` `{c['edge_key']}`.{c['attribute']}"
            + ("（⛔ active thesis 引用）" if c["edge_key"] in active_keys else "")
            for c in conflicts
        ] + [
            f"- `{c['conflict_id']}` `{c['edge_key']}`.{c['attribute']}"
            "（🔁 resolution 已過期：candidate set 有新證據，需重審）"
            for c in stale_resolutions
        ]
        report.extend(
            _section(
                "未處置 edge conflict（M1：active 引用邊必須為零）",
                "red"
                if active_conflicts or stale_resolutions
                else ("yellow" if conflicts else "green"),
                conflict_lines,
            )
        )

    # 3. TICKER_MAP 覆蓋率
    from identity.registry import TICKER_MAP

    gaps = ticker_map_gaps(company_ids, TICKER_MAP)
    report.extend(
        _section(
            "TICKER_MAP 覆蓋率",
            "yellow" if gaps else "green",
            [f"- `{company_id}` 未登記" for company_id in gaps],
        )
    )

    # 4. Thesis lifecycle 到期 + memo 檔案檢查
    lifecycle = _load_lifecycle()
    due = lifecycle_due(lifecycle, today)
    due_lines = [
        f"- `{entry['thesis_id']}`（status={entry.get('status')}，next_check={entry.get('next_check')}）"
        for entry in due
    ]
    has_review = any(entry.get("status") == "review_required" for entry in due)
    report.extend(
        _section(
            "Thesis 到期核查",
            "red" if has_review else ("yellow" if due else "green"),
            due_lines if lifecycle else ["- ⚠ thesis/lifecycle.json 不存在或無法解析"],
        )
    )

    l7_lines = []
    for entry in lifecycle.values():
        memo_path = ROOT / entry.get("memo", "")
        if not memo_path.is_file():
            l7_lines.append(f"- `{entry.get('memo')}` 檔案不存在")
            continue
        gaps = l7_field_gaps(memo_path.read_text(encoding="utf-8", errors="ignore"))
        if gaps:
            l7_lines.append(f"- `{memo_path.name}` 缺 L7 欄位：{'、'.join(gaps)}")
    report.extend(
        _section("L7 欄位完整性（核查頻率 + 48h 動作）", "yellow" if l7_lines else "green", l7_lines)
    )

    from crons.thesis_freshness_check import check as stale_memos

    stale = stale_memos()
    report.extend(
        _section(
            MEMO_FRESHNESS_TITLE,
            "yellow" if stale else "green",
            [f"- {company}：{days} 天未核查" for company, days in stale],
        )
    )

    # 5. Engine C
    try:
        from engine_c.db import get_conn

        conn = get_conn()
        tickers = sorted({t for t in TICKER_MAP.values() if t})
        freshness = engine_c_freshness(conn, tickers, today=today)
        conn.close()
        engine_lines = [
            *(f"- `{ticker}` snapshot 已 {age} 天未更新" for ticker, age in freshness["stale"]),
            *(f"- `{ticker}` 完全沒有 snapshot" for ticker in freshness["missing"]),
        ]
        report.extend(
            _section(
                f"Engine C 新鮮度（{freshness['tracked']} 檔，閾值 {ENGINE_C_STALE_DAYS} 天）",
                "yellow" if engine_lines else "green",
                engine_lines,
            )
        )

        from engine_c.checklist import get_checklist

        checklist_lines = []
        for entry in lifecycle.values():
            ticker = entry.get("ticker")
            if not ticker:
                continue
            result = get_checklist(ticker)
            if not result.get("engine_c_available"):
                checklist_lines.append(f"- `{ticker}` Engine C 不可用")
                continue
            missing = [
                key
                for key, item in result.get("items", {}).items()
                if item.get("status") in {"missing", "manual_required"}
            ]
            if missing:
                checklist_lines.append(f"- `{ticker}` 待補：{'、'.join(missing)}")
        report.extend(
            _section("財務核驗清單可跑性", "yellow" if checklist_lines else "green", checklist_lines)
        )
    except Exception as exc:
        report.extend(_section("Engine C", "red", [f"- 檢查失敗：{exc}"]))

    # 6. 管道 / Provenance
    try:
        from mcp_server.action_publisher import publication_status

        status = publication_status(root=ROOT)
        pending = status.get("actions") or []
        stuck_graph = status.get("counts", {}).get("pending_graph", 0)
        lines = [
            f"- `{row['action_id']}`（state={row['state']}，git={row['git_status']}）"
            for row in pending
        ]
        if stuck_graph:
            lines.append(f"- ⛔ {stuck_graph} 個 action 卡在 pending_graph（圖寫入未完成，可重試 apply）")
        if pending:
            lines.append("- 執行：`python scripts/commit_pending_intake.py`")
        report.extend(
            _section(
                "Research Action 待 publish",
                "red" if stuck_graph else ("yellow" if pending else "green"),
                lines,
            )
        )
    except Exception as exc:
        report.extend(_section("Research Action 待 publish", "red", [f"- 檢查失敗：{exc}"]))

    sync = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "sync_agent_skills.py"), "--check"],
        capture_output=True,
        text=True,
    )
    report.extend(
        _section(
            "Skills 同步（Claude Code / Codex）",
            "green" if sync.returncode == 0 else "red",
            [] if sync.returncode == 0 else [f"- 漂移：{(sync.stdout or sync.stderr).strip()}"],
        )
    )

    return "\n".join(report).rstrip() + "\n"


def main() -> int:  # pragma: no cover - CLI 入口
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--local",
        action="store_true",
        help="跑完整本機審查（預設行為；旗標保留給 weekly 報告的指令一致性）",
    )
    parser.parse_args()
    print(run_local_audit(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
