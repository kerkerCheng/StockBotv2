"""
graph_mcp.py — 把知識圖譜（Neo4j）包成 MCP server，供支援 remote MCP 的介面讀寫。

為什麼存在：Pro 方案的 cloud routine sandbox 出站網路無法直連自訂網域（U7a 四次
實測確認），但 MCP connector 流量走 Anthropic 伺服器轉發、不受 sandbox 白名單
限制。本 server 跑在本機常開機器上，走 Cloudflare Tunnel 暴露，掛成 claude.ai
custom connector 後，Claude 手機／網頁與具 full-MCP 權限的 ChatGPT web 都能讀寫圖。
見 docs/plans/2026-07-10-006-...-plan.md 的 U7d。

安全設計（三層）：
1. URL 路徑內嵌 token（GRAPH_MCP_TOKEN）——不知道完整 URL 連 MCP 端點都碰不到
2. Neo4j 連線一律用 cloud_routine 最小權限帳號（無 DELETE / schema / admin）
3. run_read_query 以 READ access mode 開 session——即使帳號有寫入權，這條工具
   本身也拒絕寫入交易

工具（窄面原則，不暴露原始寫入）：
- get_graph_context   — 公司子圖 / 產業全圖的 LLM-ready Markdown 摘要
- run_read_query      — 唯讀 Cypher（探索用）
- get_financial_checklist — Engine C 五項清單、原始覆蓋數與即時 policy view
- get_decision_brief  — 今日 Engine D 決策摘要（redacted DTO；Decision Store
                        永不進 git，這是遠端看決策佇列的唯一唯讀視窗）
- get_pending_leads   — 今日 pending leads 佇列（priority 排序，唯讀）
- record_lead_decision — triage/advance 一則 lead；寫後窄 pathset commit+push
                        leads.json（只動注意力 metadata，永不入圖）
- get_extraction_rules — 遠端抽取與 Research Action 規則書
- get_source_trace_manual — 收到未驗證線索時端出完整追源路由與分級處置手冊
- load_extraction     — 載入一份「先通過 schema 驗證」的抽取 JSON（L8 人工核准
                        之後才會被 legacy weekly/local flow 呼叫）
- prepare_research_action — 驗證並凍結完整多文件 action，不寫圖
- get_research_action_status — 跨 session 安全 review／恢復狀態
- apply_research_action — 一次核准後冪等套用完整 action；永不執行 Git

用法:
    python mcp_server/graph_mcp.py          # 讀 .env 的 GRAPH_MCP_TOKEN / PORT

Env vars:
    NEO4J_URI               — default bolt://localhost:7687
    NEO4J_ROUTINE_USER      — 最小權限帳號（必填）
    NEO4J_ROUTINE_PASSWORD  — 必填
    GRAPH_MCP_TOKEN         — URL 路徑 token（必填，強隨機）
    GRAPH_MCP_PORT          — default 8788
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

import neo4j
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from query.graph_context import build_context
from loader.validate import validate as validate_extraction
from loader.load_to_neo4j import (
    DuplicateUrlError,
    check_duplicate_url,
    edge_key,
    evidence_id,
    load as load_to_graph,
)
from loader.edge_resolution import project_edge_keys
from mcp_server.intake import (
    MAX_EXTRACTION_CHARS,
    ROOT as INTAKE_ROOT,
    canonical_extraction_hash,
    commit_and_push,
    git_preflight,
    inspect_provenance,
    mark_graph_complete,
    pending_intake_files,
    publish_provenance,
    resolve_action_paths,
    sanitize_source_url,
    validate_action_slug,
    validate_doc_id,
    verify_graph_complete,
    write_report,
)
from mcp_server import research_actions
from mcp_server.engine_c_tools import get_financial_checklist_core
from mcp_server.decision_tools import get_decision_brief_core
from mcp_server.leads_tools import get_pending_leads_core, record_lead_decision_core

# ── 設定 ───────────────────────────────────────────────────────────────────────

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
USER = os.environ.get("NEO4J_ROUTINE_USER")
PASSWORD = os.environ.get("NEO4J_ROUTINE_PASSWORD")
TOKEN = os.environ.get("GRAPH_MCP_TOKEN")
PORT = int(os.environ.get("GRAPH_MCP_PORT", "8788"))
GRAPH_SCHEMA_VERSION = "2026-07-16-u3b"

SOURCE_TRACE_MANUAL = ROOT / "skills" / "source-trace" / "SKILL.md"


def _check_server_config() -> None:
    """Fail at server start, while keeping read-only helpers import-testable."""

    if not (USER and PASSWORD):
        raise RuntimeError(
            "需要 .env 設定 NEO4J_ROUTINE_USER / NEO4J_ROUTINE_PASSWORD（最小權限帳號）"
        )
    if not TOKEN or len(TOKEN) < 16:
        raise RuntimeError(
            "需要 .env 設定 GRAPH_MCP_TOKEN（≥16 字元強隨機字串，將內嵌於 URL 路徑）"
        )


def _driver() -> neo4j.Driver:
    return neo4j.GraphDatabase.driver(URI, auth=(USER, PASSWORD))


def _check_graph_write_readiness(driver) -> None:
    """Fail closed before graph writes when migration/materialization is incomplete."""

    with driver.session(default_access_mode=neo4j.READ_ACCESS) as session:
        state = session.run(
            """
            OPTIONAL MATCH (state:GraphSchemaState {id: 'stockbotv2'})
            RETURN state.version AS version
            """
        ).single()
        unprojected = session.run(
            """
            MATCH ()-[r]->()
            WHERE r.edge_key IS NOT NULL AND r.projected_at IS NULL
            RETURN count(r) AS count
            """
        ).single()["count"]
        legacy = session.run(
            """
            MATCH ()-[r]->()
            WHERE NOT type(r) IN ['CITES', 'ABOUT'] AND r.edge_key IS NULL
            RETURN count(r) AS count
            """
        ).single()["count"]
        orphaned = session.run(
            """
            MATCH (e)
            WHERE (e:EdgeAssertion OR e:Claim) AND NOT (e)-[:CITES]->(:SourceDoc)
            RETURN count(e) AS count
            """
        ).single()["count"]
    version = state["version"] if state else None
    if version != GRAPH_SCHEMA_VERSION:
        raise RuntimeError(
            f"graph schema is not ready: expected {GRAPH_SCHEMA_VERSION}, got {version!r}"
        )
    if unprojected or legacy or orphaned:
        raise RuntimeError(
            "graph reconciliation is incomplete: "
            f"unprojected={unprojected}, legacy={legacy}, orphaned_evidence={orphaned}"
        )


# ── MCP server ─────────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="stockbotv2-graph",
    host="127.0.0.1",           # 只綁本機；對外一律走 Cloudflare Tunnel
    port=PORT,
    streamable_http_path=f"/{TOKEN or 'unconfigured-token'}/mcp",  # 啟動前會驗 config
)

READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
ADDITIVE_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
PREPARE_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)


@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
def get_graph_context(company_id: str = "") -> str:
    """取得知識圖譜的 LLM-ready Markdown 摘要。

    company_id 給空字串時回傳產業全圖模式；給公司 ID（如 "co:sivers_semiconductors"）
    時回傳以該公司為中心的 2 跳子圖（供應關係、瓶頸屬性、claims、來源標註）。
    公司不在圖中時會明講，不會編造。
    """
    driver = _driver()
    try:
        return build_context(driver, company_id=company_id or None)
    finally:
        driver.close()


@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
def run_read_query(cypher: str) -> str:
    """對知識圖譜執行唯讀 Cypher 查詢，回傳 JSON 格式的結果（最多 50 筆）。

    僅限讀取——session 以 READ access mode 開啟，任何寫入操作都會被 Neo4j 拒絕。
    常用模式：
      MATCH (n:Entity {id: 'co:xxx'}) RETURN n
      MATCH (a)-[r:SUPPLIES_TO]->(b) RETURN a.name, b.name, r.confidence
    """
    driver = _driver()
    try:
        with driver.session(default_access_mode=neo4j.READ_ACCESS) as session:
            records = session.run(cypher)
            rows = [dict(r) for r in records.fetch(50)]
        return json.dumps(rows, ensure_ascii=False, default=str, indent=1)
    except Exception as e:
        return f"查詢失敗: {type(e).__name__}: {e}"
    finally:
        driver.close()


@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
def get_financial_checklist(ticker: str) -> str:
    """查一個 ticker 的 Engine C 五項財務核驗清單（唯讀）。

    回傳 checklist 原始狀態、最新 analyst coverage 客觀觀測，以及依當前
    policy_version 即時計算的 coverage view。工具不接受 SQL，也不把 crowding
    或任何政策分類寫回 Engine C；資料不足時明列缺項，不推測補值。
    """

    return json.dumps(
        get_financial_checklist_core(ticker),
        ensure_ascii=False,
        default=str,
        indent=2,
    )


@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
def get_decision_brief() -> str:
    """今日 Engine D 決策摘要（純讀，遠端唯一的決策佇列視窗）。

    回傳 `decision_lab today` 的 redacted public DTO：每筆 cohort／decision 附
    `attention`（`MONITOR`／`REVIEW`）、最弱軸、reason、blockers 與 next review。
    **系統不輸出任何部位尺寸**——買多少由使用者自行決定。純讀——不 freeze context、
    不建 decision、不寫任何 authority、不下單。

    Decision Store 是本機 private runtime，永不進 git；本工具是手機／雲端
    看今日決策的唯一管道。runtime 未就緒時回明確 `unavailable`，不洩私有
    路徑、也不假裝有資料。record-choice／record-fill 等寫入永遠只在本機
    以明確輸入執行，不經此遠端面。
    """

    return json.dumps(
        get_decision_brief_core(),
        ensure_ascii=False,
        default=str,
        indent=2,
    )


@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
def get_pending_leads(tracked_tickers: str = "", limit: int = 50) -> str:
    """今日 pending leads 佇列（priority 排序，唯讀）。

    回 priority 分數排序的 leads 摘要、狀態計數與最近 harvest_log。tracked_tickers
    （逗號分隔）用來算 thesis 影響度（是否關聯已追蹤/已入 probe 的公司）。
    leads 狀態只是注意力 metadata，永不影響 evidence tier、decision 或圖。
    """

    return json.dumps(
        get_pending_leads_core(tracked_tickers=tracked_tickers, limit=limit),
        ensure_ascii=False, default=str, indent=2,
    )


@mcp.tool(annotations=ADDITIVE_ANNOTATIONS)
def record_lead_decision(
    lead_id: str,
    op: str,
    go: bool = True,
    tier: int = 4,
    reason: str = "",
    contradiction: bool = False,
    novelty: bool = False,
    independent_source: bool = False,
    content_type: str = "",
    decision_impact: str = "",
    payment_direction: str = "",
    classification_reason: str = "",
    to_status: str = "",
    ref: str = "",
) -> str:
    """記錄一則 lead 的 triage／advance 決定，寫後由本機窄 pathset commit+push。

    op="triage"（PASS 用 go／tier／reason／三個 priority flag，並必填
    content_type／decision_impact；capital_commitment 另填 payment_direction）｜op="advance"（用
    to_status／ref，如 park、researching、applied）。寫入後本機 MCP server 把
    **只有** `library/leads/pending_leads.json` commit+push，cloud 每天讀到最新。

    **邊界：** 只動注意力 metadata——不入圖、不改 evidence tier、不建 decision。
    圖 admission 走 apply_research_action；此工具永不 commit 圖／碼／extraction。
    """

    flags = {
        "contradiction": contradiction,
        "novelty": novelty,
        "independent_source": independent_source,
    }
    return json.dumps(
        record_lead_decision_core(
            lead_id=lead_id, op=op, go=go, tier=tier, reason=reason,
            priority_flags=flags,
            content_type=content_type,
            decision_impact=decision_impact,
            payment_direction=payment_direction,
            classification_reason=classification_reason,
            to_status=to_status,
            ref=ref,
        ),
        ensure_ascii=False, default=str, indent=2,
    )


@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
def get_extraction_rules() -> str:
    """取得撰寫抽取 JSON 前必讀的完整規則書。

    在呼叫 load_extraction 之前務必先讀這份——它包含 intermediate-format 的
    完整欄位規格、vocab 白名單（node type / abstraction_level / relation 等）、
    節點 ID 命名慣例、L4 屬性歸位三問、以及 L6 反幻覺鐵律（具體型號/公司名
    必須逐字出現在 quote 中），以及 remote intake 的 storage permission、
    filesystem-first、conflict 回報與 prepare/review/apply 義務。不讀規則直接抽取，軟品質規則
    無法靠 schema 驗證補救。
    """
    rules = (ROOT / "prompts" / "extract_system.md").read_text(encoding="utf-8")
    vocab = (ROOT / "schema" / "vocab.json").read_text(encoding="utf-8")
    intake_protocol = (ROOT / "prompts" / "intake_protocol.md").read_text(
        encoding="utf-8"
    )
    return (
        "# 抽取規則書（prompts/extract_system.md）\n\n" + rules +
        "\n\n---\n\n# Vocab 白名單（schema/vocab.json）\n\n```json\n" + vocab + "\n```\n" +
        "\n\n---\n\n# 遠端 Research Action 協定（prompts/intake_protocol.md）\n\n" +
        intake_protocol
    )


def _read_source_trace_manual(path: Path = SOURCE_TRACE_MANUAL) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        return (
            "追源手冊目前不可用；不要在缺少規則時繼續抽取或入圖。"
            f"請檢查 skills/source-trace/SKILL.md（{type(exc).__name__}: {exc}）。"
        )


@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
def get_source_trace_manual() -> str:
    """取得未驗證線索進場前必讀的完整追源手冊。

    收到推文、轉述、截圖、搜尋摘要、新聞或任何尚未取得原文的 claim 時，
    必須先呼叫本工具，再依市場路由追回原始文件並套 tier 1–2 誠實降級／
    tier 3–4 未果隔離規則。手冊缺失時本工具回可讀錯誤，server 不會崩潰；
    呼叫端應停止抽取與 load_extraction。
    """
    return _read_source_trace_manual()


@mcp.tool(annotations=ADDITIVE_ANNOTATIONS)
def load_extraction(
    extraction_json: str,
    storage_permission: str,
    permission_basis: str,
    raw_text: str | None = None,
    raw_url: str | None = None,
    raw_excerpt: str | None = None,
) -> str:
    """把一份 intermediate-format 抽取 JSON 載入知識圖譜。

    一份文件呼叫一次；storage_permission 與 permission_basis 必填。先依授權把
    extraction/raw no-clobber 落地，再冪等寫圖並重投影受影響的 edge conflicts。
    同 doc_id 不同內容嚴格拒絕；圖失敗時檔案保留為 pending_graph，可用完全相同
    payload 重試。回傳 open conflict 只代表某些 edge attributes 待決，不代表文件
    載入失敗，遠端不可自行選值。此 primitive 暫留給已有外部人工核准閘門的
    weekly/local 流程；手機 ad hoc intake 必須使用 prepare/status/apply Research Action。
    """
    return json.dumps(
        _load_extraction_impl(
            extraction_json,
            storage_permission,
            permission_basis,
            raw_text=raw_text,
            raw_url=raw_url,
            raw_excerpt=raw_excerpt,
        ),
        ensure_ascii=False,
        default=str,
        indent=2,
    )


def _prepare_extraction_impl(
    extraction_json: str,
    storage_permission: str,
    permission_basis: str,
    *,
    raw_text: str | None = None,
    raw_url: str | None = None,
    raw_excerpt: str | None = None,
    root: Path = INTAKE_ROOT,
) -> dict:
    """Run the complete deterministic intake gate without publishing or writing graph."""

    if not isinstance(extraction_json, str):
        return {"status": "rejected", "error": "extraction_json 必須是 JSON 字串"}
    if len(extraction_json) > MAX_EXTRACTION_CHARS:
        return {"status": "rejected", "error": "extraction 超過 1,000,000 字元限制"}
    try:
        doc = json.loads(extraction_json)
    except json.JSONDecodeError as e:
        return {"status": "rejected", "error": f"不是合法 JSON：{e}"}

    if not isinstance(doc, dict):
        return {"status": "rejected", "error": "extraction JSON 必須是 object"}

    source_doc = doc.get("source_doc")
    if not isinstance(source_doc, dict):
        return {"status": "rejected", "error": "source_doc 是必填 object"}
    doc_id = source_doc.get("doc_id")
    try:
        validate_doc_id(doc_id)
    except ValueError as exc:
        return {"status": "rejected", "error": str(exc)}
    source_doc["storage_permission"] = storage_permission
    source_doc["permission_basis"] = permission_basis
    try:
        if raw_url:
            source_doc["url"] = sanitize_source_url(raw_url)
        elif source_doc.get("url"):
            source_doc["url"] = sanitize_source_url(source_doc["url"])
    except ValueError as exc:
        return {"status": "rejected", "doc_id": doc_id, "error": str(exc)}

    # 驗證（validate() 吃檔案路徑，寫入 temp 檔重用其完整邏輯）
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    try:
        json.dump(doc, tmp, ensure_ascii=False)
        tmp.close()
        try:
            problems = validate_extraction(tmp.name)
        except Exception as e:
            # 驗證器自身異常也必須回成清楚的拒載訊息，不能炸穿成框架錯誤
            return {
                "status": "rejected",
                "doc_id": doc_id,
                "error": (
                    f"驗證器異常（{type(e).__name__}: {e}）；"
                    "請先呼叫 get_extraction_rules 核對格式後重試"
                ),
            }
    finally:
        os.unlink(tmp.name)

    hard_errors = [p for p in problems if not p.startswith("WARN")]
    warnings = [p for p in problems if p.startswith("WARN")]
    if hard_errors:
        return {
            "status": "rejected",
            "doc_id": doc_id,
            "error": "驗證未通過",
            "problems": hard_errors,
        }

    # 公司 registry fail-closed（2026-09-02 對齊 enforcement ①）：validate 對未登記
    # co:* 刻意只 WARN（typo vs 未 onboard 由人分流）——但 openlight 實測證明 WARN
    # 沒人讀。prepare 是核准前最後一站：onboard 契約本來就要求 registry 條目隨包
    # staged（co:proterial／co:jl_mag 先例），這裡把慣例變 enforcement。
    _reg_path = Path(__file__).resolve().parent.parent / "config" / "company_identity.json"
    _registry_ids = {
        str(c.get("company_id"))
        for c in json.loads(_reg_path.read_text(encoding="utf-8")).get("companies") or []
    }
    _unregistered = sorted(
        {
            str(n.get("id"))
            for n in doc.get("nodes") or []
            if str(n.get("id") or "").startswith("co:")
            and str(n.get("id")) not in _registry_ids
        }
    )
    if _unregistered:
        return {
            "status": "rejected",
            "doc_id": doc_id,
            "error": (
                f"公司未登記 registry：{_unregistered}——join-key 契約要求先補 "
                "`config/company_identity.json` 條目（private 公司用 research_ticker null，"
                "見 co:proterial 先例）再 prepare；onboard 包的 registry 條目隨包 staged"
            ),
        }

    # 同 URL 多段驗證提前到 prepare（2026-09-02 ROADMAP 交付）：loader 的
    # DuplicateUrlError 原本在 apply 才炸，而 payload 已凍結、只能重 prepare＋
    # 重新請求核准（2026-09-01～02 實測連踩三次：原 [360][361]、[376]、[394]）。
    # 這裡用 loader 同一套判準先擋；Neo4j 不可用時降級放行——apply 端仍是最終防線，
    # prepare 不因需要圖連線而阻斷離線流程。
    try:
        dup_driver = _driver()
        try:
            with dup_driver.session() as dup_session:
                check_duplicate_url(doc.get("source_doc") or {}, dup_session)
        finally:
            dup_driver.close()
    except DuplicateUrlError as exc:
        return {
            "status": "rejected",
            "doc_id": doc_id,
            "error": (
                "同 URL 多段驗證未通過（prepare 端先擋，免得核准後 apply 才發現）："
                f"{exc}"
            ),
        }
    except Exception:  # noqa: BLE001 — 圖連線不可用時降級，apply 端仍會擋
        pass

    raw_payload = {
        key: value
        for key, value in {
            "raw_text": raw_text,
            "raw_url": raw_url,
            "raw_excerpt": raw_excerpt,
        }.items()
        if value is not None
    }
    try:
        provenance = inspect_provenance(
            doc_id,
            doc,
            raw_payload,
            root=root,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "status": "rejected",
            "doc_id": doc_id,
            "error": f"provenance validation rejected: {exc}",
            "finalize_eligible": False,
        }
    if provenance["status"] == "conflict":
        return {
            "status": "rejected",
            "doc_id": doc_id,
            "error": f"provenance validation rejected: conflicts={provenance['conflicts']}",
            "finalize_eligible": False,
        }
    return {
        "status": "prepared",
        "doc_id": doc_id,
        "document": doc,
        "raw_payload": provenance["normalised_raw"],
        "provenance_status": provenance["status"],
        "warnings": warnings,
    }


def _load_extraction_impl(
    extraction_json: str,
    storage_permission: str,
    permission_basis: str,
    *,
    raw_text: str | None = None,
    raw_url: str | None = None,
    raw_excerpt: str | None = None,
    root: Path = INTAKE_ROOT,
) -> dict:
    prepared = _prepare_extraction_impl(
        extraction_json,
        storage_permission,
        permission_basis,
        raw_text=raw_text,
        raw_url=raw_url,
        raw_excerpt=raw_excerpt,
        root=root,
    )
    if prepared["status"] != "prepared":
        return prepared
    doc_id = prepared["doc_id"]
    doc = prepared["document"]
    raw_payload = prepared["raw_payload"]
    warnings = prepared["warnings"]
    try:
        provenance = publish_provenance(doc_id, doc, raw_payload, root=root)
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "status": "rejected",
            "doc_id": doc_id,
            "error": f"provenance publish rejected: {exc}",
            "finalize_eligible": False,
        }

    driver = _driver()
    try:
        _check_graph_write_readiness(driver)
        with driver.session() as session:
            session.execute_write(lambda tx: load_to_graph(doc, tx))
        _verify_loaded_doc(driver, doc)
        affected_edge_keys = {
            edge_key(edge["src_id"], edge["relation"], edge["dst_id"])
            for edge in doc.get("edges", [])
        }
        projection = project_edge_keys(driver, affected_edge_keys)
        mark_graph_complete(doc_id, doc, root=root)
    except Exception as e:
        return {
            "status": "pending_graph",
            "doc_id": doc_id,
            "error": f"{type(e).__name__}: {e}",
            "resolved_paths": provenance["paths"],
            "finalize_eligible": False,
            "warnings": warnings,
        }
    finally:
        driver.close()

    return {
        "status": "loaded_or_already_complete",
        "doc_id": doc_id,
        "resolved_paths": provenance["paths"],
        "open_conflict_ids": projection["open_conflict_ids"],
        "stale_resolution_ids": projection["stale_resolution_ids"],
        "finalize_eligible": provenance["finalize_eligible"],
        "extraction_sha256": canonical_extraction_hash(doc),
        "counts": {
            "nodes": len(doc.get("nodes", [])),
            "edges": len(doc.get("edges", [])),
            "claims": len(doc.get("claims", [])),
        },
        "warnings": warnings,
    }


def _safe_error_message(value: object) -> str:
    message = str(value)
    if TOKEN:
        message = message.replace(TOKEN, "[redacted]")
    message = message.replace("\r", " ").replace("\n", " ")
    return message[:2_000]


def _safe_load_result(result: dict) -> dict:
    """Persist only bounded operational fields, never caller payloads."""

    safe = {
        key: result[key]
        for key in (
            "status",
            "doc_id",
            "resolved_paths",
            "open_conflict_ids",
            "stale_resolution_ids",
            "finalize_eligible",
            "extraction_sha256",
            "counts",
            "warnings",
        )
        if key in result
    }
    if result.get("error"):
        safe["error"] = _safe_error_message(result["error"])
    if result.get("problems"):
        safe["problems"] = [
            _safe_error_message(item) for item in (result.get("problems") or [])[:50]
        ]
    return safe


def _prepare_research_action_impl(
    action_json: str, *, root: Path = INTAKE_ROOT
) -> dict:
    try:
        request = research_actions.parse_action_request(action_json)
    except (ValueError, TypeError) as exc:
        return {"status": "rejected", "error": _safe_error_message(exc)}

    normalized_documents = []
    for index, document in enumerate(request["documents"]):
        prepared = _prepare_extraction_impl(
            document["extraction_json"],
            document["storage_permission"],
            document["permission_basis"],
            raw_text=document.get("raw_text"),
            raw_url=document.get("raw_url"),
            raw_excerpt=document.get("raw_excerpt"),
            root=root,
        )
        if prepared["status"] != "prepared":
            return {
                "status": "rejected",
                "document_index": index,
                "doc_id": prepared.get("doc_id"),
                "error": _safe_error_message(
                    prepared.get("error") or "document validation failed"
                ),
                "problems": [
                    _safe_error_message(item)
                    for item in (prepared.get("problems") or [])[:50]
                ],
            }
        normalized_documents.append(
            {
                "doc_id": prepared["doc_id"],
                "extraction": prepared["document"],
                "raw_payload": prepared["raw_payload"],
                "storage_permission": document["storage_permission"],
                "permission_basis": document["permission_basis"],
                "validation_warnings": prepared["warnings"],
            }
        )

    payload = {
        "schema_version": research_actions.ACTION_PAYLOAD_SCHEMA,
        "action_slug": request["action_slug"],
        "report": request["report"],
        "documents": normalized_documents,
    }
    if request.get("focus_company_id") is not None:
        payload["focus_company_id"] = request["focus_company_id"]
    try:
        record = research_actions.create_action(payload, root=root)
    except (OSError, RuntimeError, ValueError) as exc:
        return {"status": "rejected", "error": _safe_error_message(exc)}
    return {
        "status": "ready",
        "action_id": record["action_id"],
        "action_digest": record["action_digest"],
        "created_at": record["created_at"],
        "expires_at": record["expires_at"],
        "document_count": len(record["document_manifest"]),
        "review_packet": research_actions.render_review_packet(record),
        "next_action": (
            "Show this exact server-rendered packet to the user. Do not call apply "
            "until the user explicitly approves this action ID."
        ),
    }


@mcp.tool(annotations=PREPARE_ANNOTATIONS)
def prepare_research_action(action_json: str) -> str:
    """驗證並凍結一個多文件 Research Action，但不寫圖、不寫 Git 帳本。

    action_json 必須符合 research-action/v1。server 會重跑每份 extraction、permission、
    raw policy、URL 與 no-clobber gate，再簽發 action_id + 完整 digest + review packet。
    呼叫端必須把 packet 顯示給使用者並等待明確核准，不能在同一輪自動 apply。
    """

    return json.dumps(
        _prepare_research_action_impl(action_json),
        ensure_ascii=False,
        default=str,
        indent=2,
    )


def _get_research_action_status_impl(
    action_id: str = "", *, root: Path = INTAKE_ROOT
) -> dict:
    try:
        if not action_id:
            return research_actions.list_action_statuses(root=root)
        return research_actions.action_status(action_id, root=root)
    except FileNotFoundError:
        return {"status": "not_found", "action_id": action_id}
    except (OSError, ValueError) as exc:
        return {
            "status": "rejected",
            "action_id": action_id,
            "error": _safe_error_message(exc),
        }


@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
def get_research_action_status(action_id: str = "") -> str:
    """跨 session 查 Research Action；空 ID 只列安全摘要，完整 ID 回 review packet。

    永不回傳 raw body 或 extraction JSON。list mode 也不回 client-authored report prose；
    status 本身不 compact、不 apply，保持真正 read-only。
    """

    return json.dumps(
        _get_research_action_status_impl(action_id),
        ensure_ascii=False,
        default=str,
        indent=2,
    )


def _stored_extraction_for_action(document: dict, *, root: Path) -> dict:
    doc_id = validate_doc_id(document["doc_id"])
    if document["storage_permission"] == "local_only":
        path = root / "library" / "private" / "extractions" / f"{doc_id}.json"
    else:
        path = root / "extractions" / f"{doc_id}.json"
    if not path.exists():
        raise ValueError(f"stored extraction missing for completed doc_id: {doc_id}")
    try:
        extraction = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"stored extraction invalid for completed doc_id: {doc_id}") from exc
    if extraction.get("source_doc", {}).get("doc_id") != doc_id:
        raise ValueError(f"stored extraction doc_id mismatch: {doc_id}")
    return extraction


def _verify_action_document_receipt(
    document: dict, execution: dict, *, root: Path
) -> None:
    if execution.get("status") != "complete":
        raise ValueError(f"document checkpoint is incomplete: {document['doc_id']}")
    result = execution.get("result") or {}
    extraction = _stored_extraction_for_action(document, root=root)
    expected_hash = result.get("extraction_sha256")
    if expected_hash != canonical_extraction_hash(extraction):
        raise ValueError(f"document checkpoint hash mismatch: {document['doc_id']}")
    verify_graph_complete(document["doc_id"], extraction, root=root)


def _verify_completed_action(record: dict, *, root: Path) -> None:
    for document, execution in zip(
        record["document_manifest"], record["execution"]["documents"], strict=True
    ):
        _verify_action_document_receipt(document, execution, root=root)
    research_actions.verify_action_reports(record, root=root)


def _apply_response(record: dict, *, replayed: bool = False) -> dict:
    result = dict(record.get("final_result") or {})
    if not result:
        result = {
            "status": record["state"],
            "action_id": record["action_id"],
            "action_digest": record["action_digest"],
        }
    result["state"] = record["state"]
    result["git_status"] = record.get("git", {}).get("status")
    if replayed:
        result["replayed"] = True
    return result


def _sync_source_leads_after_apply(record: Mapping[str, Any]) -> None:
    """apply 成功後把 digest／focus 回寫到綁定的 leads 並推進 applied。

    L16 交付（2026-09-02）：complete-ra 要求 applied lead 帶 `action_digest` 與
    `focus_company_id`，但這兩個值一直只在 apply 端手上——每次都要人手動
    annotate＋advance，漏一次就撞「applied lead 的 action_digest 缺失」。
    分類（digest/focus）從此跟著資料走到消費端。best-effort：leads 檔異常不
    回滾 apply（graph 寫入已 durable），失敗留給既有的手動路徑。
    """
    try:
        from engine_b import leads as leads_mod

        action_id = str(record.get("action_id") or "")
        digest = str(record.get("action_digest") or "")
        payload = record.get("payload") or {}
        focus = str(
            payload.get("focus_company_id") or record.get("focus_company_id") or ""
        )
        if not action_id or not digest:
            return
        store = leads_mod.load()
        touched = False
        for lead in store["leads"].values():
            refs = lead.get("refs") or {}
            if str(refs.get("research_action_id") or "") != action_id:
                continue
            if lead.get("status") != "action_prepared":
                continue
            leads_mod.annotate_refs(
                store,
                lead["lead_id"],
                refs={
                    "action_digest": digest,
                    **({"focus_company_id": focus} if focus else {}),
                },
            )
            leads_mod.advance(store, lead["lead_id"], "applied")
            touched = True
        if touched:
            leads_mod.save(store)
    except Exception as exc:  # noqa: BLE001 — 回寫失敗不動搖 durable apply
        _write_log = logging.getLogger(__name__)
        _write_log.warning("lead sync after apply failed: %s", exc, exc_info=True)


def _apply_research_action_impl(
    action_id: str,
    action_digest: str,
    *,
    root: Path = INTAKE_ROOT,
    load_document=None,
) -> dict:
    try:
        research_actions.validate_action_id(action_id)
        research_actions.validate_action_digest(action_digest)
    except ValueError as exc:
        return {"status": "rejected", "error": _safe_error_message(exc)}
    loader = load_document or _load_extraction_impl

    try:
        lock = research_actions.action_lock(action_id, root=root)
        with lock:
            try:
                record = research_actions.read_action(action_id, root=root)
            except FileNotFoundError:
                return {"status": "not_found", "action_id": action_id}
            except (OSError, ValueError):
                return {
                    "status": "rejected",
                    "action_id": action_id,
                    "error": "Research Action record failed integrity validation",
                }

            if record["action_digest"] != action_digest:
                return {
                    "status": "rejected",
                    "action_id": action_id,
                    "error": "action_digest mismatch; no graph mutation occurred",
                }

            if record["state"] in {"applied", "committed_not_pushed", "pushed"}:
                try:
                    _verify_completed_action(record, root=root)
                except (OSError, ValueError) as exc:
                    return {
                        "status": "rejected",
                        "action_id": action_id,
                        "error": _safe_error_message(exc),
                    }
                return _apply_response(record, replayed=True)

            if record["state"] == "expired":
                return {
                    "status": "expired",
                    "action_id": action_id,
                    "error": "prepare a fresh Research Action before approval",
                }
            if record["state"] == "ready" and _parse_action_time(
                record["expires_at"]
            ) <= datetime.now(timezone.utc):
                return {
                    "status": "expired",
                    "action_id": action_id,
                    "error": "prepare a fresh Research Action before approval",
                }
            if record.get("payload") is None:
                return {
                    "status": "rejected",
                    "action_id": action_id,
                    "error": "Research Action payload is unavailable",
                }

            if record["state"] == "applying":
                record["state"] = (
                    "partial"
                    if any(
                        item.get("status") == "complete"
                        for item in record["execution"]["documents"]
                    )
                    else "ready"
                )
            record["state"] = "applying"
            record["execution"]["last_error"] = None
            record = research_actions.save_action(record, root=root)

            for index, document in enumerate(record["payload"]["documents"]):
                execution = record["execution"]["documents"][index]
                if execution.get("status") == "complete":
                    try:
                        _verify_action_document_receipt(
                            record["document_manifest"][index], execution, root=root
                        )
                    except (OSError, ValueError):
                        execution["status"] = "pending"
                        execution["result"] = None
                    else:
                        continue
                try:
                    result = loader(
                        json.dumps(document["extraction"], ensure_ascii=False),
                        document["storage_permission"],
                        document["permission_basis"],
                        root=root,
                        **document["raw_payload"],
                    )
                except Exception as exc:
                    result = {
                        "status": "internal_error",
                        "doc_id": document["doc_id"],
                        "error": type(exc).__name__,
                    }
                safe_result = _safe_load_result(result)
                execution["result"] = safe_result
                if result.get("status") == "loaded_or_already_complete":
                    execution["status"] = "complete"
                    execution["completed_at"] = datetime.now(timezone.utc).isoformat()
                    record = research_actions.save_action(record, root=root)
                    continue
                execution["status"] = "failed"
                record["state"] = "partial"
                record["execution"]["last_error"] = {
                    "code": "document_not_complete",
                    "doc_id": document["doc_id"],
                    "message": safe_result.get("error") or result.get("status"),
                }
                record = research_actions.save_action(record, root=root)
                return {
                    "status": "partial",
                    "action_id": action_id,
                    "action_digest": action_digest,
                    "completed_document_count": sum(
                        item.get("status") == "complete"
                        for item in record["execution"]["documents"]
                    ),
                    "document_count": len(record["execution"]["documents"]),
                    "failed_doc_id": document["doc_id"],
                    "error": record["execution"]["last_error"],
                    "next_action": "Retry the same action ID and digest after recovery.",
                }

            try:
                for manifest_document, execution in zip(
                    record["document_manifest"],
                    record["execution"]["documents"],
                    strict=True,
                ):
                    _verify_action_document_receipt(
                        manifest_document, execution, root=root
                    )
            except (OSError, ValueError) as exc:
                record["state"] = "partial"
                record["execution"]["last_error"] = {
                    "code": "document_receipt_invalid",
                    "message": _safe_error_message(exc),
                }
                research_actions.save_action(record, root=root)
                return {
                    "status": "partial",
                    "action_id": action_id,
                    "action_digest": action_digest,
                    "completed_document_count": sum(
                        item.get("status") == "complete"
                        for item in record["execution"]["documents"]
                    ),
                    "document_count": len(record["execution"]["documents"]),
                    "error": record["execution"]["last_error"],
                    "next_action": "Repair the durable document receipt, then retry exactly.",
                }

            try:
                report = research_actions.publish_action_reports(record, root=root)
            except (OSError, RuntimeError, ValueError) as exc:
                record["state"] = "partial"
                record["execution"]["report"] = {"status": "failed"}
                record["execution"]["last_error"] = {
                    "code": "report_publish_failed",
                    "message": _safe_error_message(exc),
                }
                research_actions.save_action(record, root=root)
                return {
                    "status": "partial",
                    "action_id": action_id,
                    "action_digest": action_digest,
                    "completed_document_count": len(record["execution"]["documents"]),
                    "document_count": len(record["execution"]["documents"]),
                    "error": record["execution"]["last_error"],
                    "next_action": "Retry the same action; completed documents will not reload.",
                }

            record["execution"]["report"] = report
            research_actions.verify_action_reports(record, root=root)
            eligible_paths = research_actions.eligible_action_paths(record)
            record["git"]["eligible_paths"] = eligible_paths
            record["git"]["status"] = "pending" if eligible_paths else "not_required"
            record["state"] = "applied"
            record["applied_at"] = datetime.now(timezone.utc).isoformat()
            conflict_ids = sorted(
                {
                    conflict_id
                    for item in record["execution"]["documents"]
                    for conflict_id in (
                        (item.get("result") or {}).get("open_conflict_ids") or []
                    )
                }
            )
            record["final_result"] = {
                "status": "applied",
                "action_id": action_id,
                "action_digest": action_digest,
                "document_count": len(record["execution"]["documents"]),
                "open_conflict_ids": conflict_ids,
                "report": report,
                "git_status": record["git"]["status"],
                "next_action": (
                    "Open a local session and publish pending intake."
                    if eligible_paths
                    else "No Git publication is required for this local-only action."
                ),
            }
            record = research_actions.compact_applied_payload(record)
            record = research_actions.save_action(record, root=root)
            _sync_source_leads_after_apply(record)
            return _apply_response(record)
    except research_actions.ActionBusyError:
        return {
            "status": "busy",
            "action_id": action_id,
            "error": "another apply is in progress; query status before retrying",
        }
    except Exception as exc:
        message = (
            _safe_error_message(exc)
            if isinstance(exc, (OSError, RuntimeError, ValueError, KeyError, TypeError))
            else type(exc).__name__
        )
        return {
            "status": "partial",
            "action_id": action_id,
            "action_digest": action_digest,
            "error": {"code": "action_apply_internal", "message": message},
            "next_action": "Query status, then retry the same action ID and digest.",
        }


def _parse_action_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Research Action timestamp has no timezone")
    return parsed.astimezone(timezone.utc)


@mcp.tool(annotations=ADDITIVE_ANNOTATIONS)
def apply_research_action(action_id: str, action_digest: str) -> str:
    """在一次 native approval 後套用使用者核准的完整 Research Action。

    必須傳 prepare/status 顯示的 server action_id 與完整 digest。server 會鎖定、重新驗
    digest、逐文件 checkpoint、冪等續跑並依 permission 寫報告；本工具永遠不執行 Git。
    digest 不符、過期、被竄改或 live concurrent apply 都在任何新 graph mutation 前拒絕。
    """

    return json.dumps(
        _apply_research_action_impl(action_id, action_digest),
        ensure_ascii=False,
        default=str,
        indent=2,
    )


def _verify_loaded_doc(driver, doc: dict) -> None:
    """Fail closed unless this document's graph identity is observable."""

    doc_id = doc["source_doc"]["doc_id"]
    expected_assertions = {
        evidence_id(doc_id, edge["id"]) for edge in doc.get("edges", [])
    }
    expected_claims = {
        evidence_id(doc_id, claim["id"]) for claim in doc.get("claims", [])
    }
    expected_edges = {
        edge_key(edge["src_id"], edge["relation"], edge["dst_id"])
        for edge in doc.get("edges", [])
    }
    with driver.session() as session:
        source_doc_count = session.run(
            "MATCH (sd:SourceDoc {id: $id}) RETURN count(sd) AS count",
            id=doc_id,
        ).single()["count"]
        assertions = {
            row["id"]
            for row in session.run(
                "MATCH (a:EdgeAssertion) WHERE a.id IN $ids RETURN a.id AS id",
                ids=sorted(expected_assertions),
            )
        }
        claims = {
            row["id"]
            for row in session.run(
                "MATCH (c:Claim) WHERE c.id IN $ids RETURN c.id AS id",
                ids=sorted(expected_claims),
            )
        }
        edges = {
            row["edge_key"]
            for row in session.run(
                """
                MATCH ()-[r]->()
                WHERE r.edge_key IN $edge_keys
                RETURN r.edge_key AS edge_key
                """,
                edge_keys=sorted(expected_edges),
            )
        }
    problems = []
    if source_doc_count != 1:
        problems.append(f"SourceDoc count={source_doc_count}")
    if assertions != expected_assertions:
        problems.append(f"missing EdgeAssertions={sorted(expected_assertions - assertions)}")
    if claims != expected_claims:
        problems.append(f"missing Claims={sorted(expected_claims - claims)}")
    if edges != expected_edges:
        problems.append(f"missing canonical edges={sorted(expected_edges - edges)}")
    if problems:
        raise RuntimeError("graph reconciliation failed: " + "; ".join(problems))


_REQUIRED_REPORT_SECTIONS = (
    "為何此時入圖",
    "文件清單",
    "搜尋過程摘要",
    "L8 確認備註",
)


def _finalize_research_action_impl(
    report_markdown: str,
    action_slug: str,
    commit_headline: str,
    doc_ids: list[str],
    *,
    root: Path = INTAKE_ROOT,
    enabled: bool,
) -> dict:
    if not enabled:
        return {
            "git_status": "not_committed",
            "reason": "remote_finalize_disabled",
            "action": (
                "Set ENABLE_REMOTE_FINALIZE=true only after accepting the remote-push "
                "security boundary and configuring this MCP tool as Needs approval."
            ),
        }
    try:
        validate_action_slug(action_slug)
    except ValueError as exc:
        return {"git_status": "not_committed", "reason": str(exc)}
    if not isinstance(commit_headline, str) or not commit_headline.strip():
        return {"git_status": "not_committed", "reason": "commit_headline is required"}
    if "\n" in commit_headline or "\r" in commit_headline:
        return {
            "git_status": "not_committed",
            "reason": "commit_headline must be one line",
        }
    if not isinstance(doc_ids, list):
        return {"git_status": "not_committed", "reason": "doc_ids must be a list"}
    try:
        manifest = resolve_action_paths(doc_ids, root=root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"git_status": "not_committed", "reason": str(exc)}
    if not manifest["paths"]:
        return {
            "git_status": "not_committed",
            "reason": "no_pending_files",
            "manifest": [],
        }
    missing_sections = [
        section for section in _REQUIRED_REPORT_SECTIONS if section not in report_markdown
    ]
    if missing_sections:
        return {
            "git_status": "not_committed",
            "reason": f"report missing required sections: {missing_sections}",
        }

    preflight = git_preflight(root=root)
    if not preflight["ok"]:
        return {
            "git_status": "not_committed",
            "reason": preflight["reason"],
            "detail": preflight.get("detail"),
        }
    pending = pending_intake_files(root=root)
    manifest_paths = set(manifest["paths"])
    modified_manifest = sorted(manifest_paths & set(pending.get("modified") or []))
    if modified_manifest:
        return {
            "git_status": "not_committed",
            "reason": f"manifest contains modified tracked files: {modified_manifest}",
        }
    pending_warning = {
        "untracked": sorted(set(pending.get("untracked") or []) - manifest_paths),
        "modified": sorted(set(pending.get("modified") or []) - manifest_paths),
        "error": pending.get("error"),
    }

    verified_lines = ["## Server-verified provenance manifest", ""]
    for document in manifest["documents"]:
        verified_lines.append(
            f"- `{document['doc_id']}` — storage_permission=`{document['storage_permission']}`; "
            f"URL={document.get('url') or 'n/a'}; permission_basis: "
            f"{document['permission_basis']}"
        )
    final_report = report_markdown.rstrip() + "\n\n" + "\n".join(verified_lines) + "\n"
    try:
        report_path = write_report(action_slug, final_report, root=root)
        report_relative = report_path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, RuntimeError, ValueError) as exc:
        return {"git_status": "not_committed", "reason": f"report write failed: {exc}"}

    git_result = commit_and_push(
        [*manifest["paths"], report_relative],
        commit_headline,
        root=root,
    )
    secondary_preflight = git_result.get("preflight") or {}
    return {
        "git_status": git_result["status"],
        "commit": git_result.get("commit"),
        "push_error": git_result.get("push_error"),
        "error": git_result.get("error") or secondary_preflight.get("reason"),
        "detail": git_result.get("detail") or secondary_preflight.get("detail"),
        "report_path": report_relative,
        "manifest": manifest["documents"],
        "committed_paths": git_result.get("paths") or [],
        "pending_warning": pending_warning,
    }

if __name__ == "__main__":
    try:
        _check_server_config()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"[graph_mcp] starting on 127.0.0.1:{PORT}, path=/<token>/mcp", file=sys.stderr)
    mcp.run(transport="streamable-http")
