"""MCP tool surface — **optional remote adapter**，不是核心架構。

本檔只剩 `@mcp.tool()` 包裝與 FastMCP 設定；application 邏輯全在
`intake/application.py`（2026-09-03，Phase 3b 抽出）。

⚠ **依賴方向只准 peripheral → core。** 新核心必須能在完全沒有 MCP 的情況下運作；
**本檔可整包刪除而不影響任何 core 功能**。

工具語意、權限邊界與安全分層見 `docs/remote-access-architecture.md`。
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass
import neo4j
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
from intake.provenance import (
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
from intake import actions as research_actions
from mcp_server.engine_c_tools import get_financial_checklist_core
from mcp_server.decision_tools import get_decision_brief_core
from mcp_server.leads_tools import get_pending_leads_core, record_lead_decision_core

# application 邏輯的 re-import：讓既有測試仍能對本模組 monkeypatch。
from intake.application import (
    PORT,
    TOKEN,
    _apply_research_action_impl,
    _check_server_config,
    _driver,
    _get_research_action_status_impl,
    _load_extraction_impl,
    _prepare_research_action_impl,
    _read_source_trace_manual,
)

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

if __name__ == "__main__":
    try:
        _check_server_config()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"[graph_mcp] starting on 127.0.0.1:{PORT}, path=/<token>/mcp", file=sys.stderr)
    mcp.run(transport="streamable-http")
