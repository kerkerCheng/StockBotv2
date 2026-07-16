"""
graph_mcp.py — 把知識圖譜（Neo4j）包成 MCP server，供 claude.ai 各介面遠端讀寫。

為什麼存在：Pro 方案的 cloud routine sandbox 出站網路無法直連自訂網域（U7a 四次
實測確認），但 MCP connector 流量走 Anthropic 伺服器轉發、不受 sandbox 白名單
限制。本 server 跑在本機常開機器上，走 Cloudflare Tunnel 暴露，掛成 claude.ai
custom connector 後，cloud routine / 手機 App / 網頁對話都能讀寫圖。
見 docs/plans/2026-07-10-006-...-plan.md 的 U7d。

安全設計（三層）：
1. URL 路徑內嵌 token（GRAPH_MCP_TOKEN）——不知道完整 URL 連 MCP 端點都碰不到
2. Neo4j 連線一律用 cloud_routine 最小權限帳號（無 DELETE / schema / admin）
3. run_read_query 以 READ access mode 開 session——即使帳號有寫入權，這條工具
   本身也拒絕寫入交易

工具（窄面原則，不暴露原始寫入）：
- get_graph_context   — 公司子圖 / 產業全圖的 LLM-ready Markdown 摘要
- run_read_query      — 唯讀 Cypher（探索用）
- get_source_trace_manual — 收到未驗證線索時端出完整追源路由與分級處置手冊
- load_extraction     — 載入一份「先通過 schema 驗證」的抽取 JSON（L8 人工核准
                        之後才會被呼叫；驗證不過就拒載，錯誤原样回傳）
- finalize_research_action — 以 doc_ids manifest 精確建立報告、單一 commit 與 push；
                             預設由 server-side kill switch 關閉

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

from query.graph_context import build_context
from loader.validate import validate as validate_extraction
from loader.load_to_neo4j import edge_key, evidence_id, load as load_to_graph
from loader.edge_resolution import project_edge_keys
from mcp_server.intake import (
    ROOT as INTAKE_ROOT,
    commit_and_push,
    git_preflight,
    pending_intake_files,
    publish_provenance,
    resolve_action_paths,
    sanitize_source_url,
    validate_action_slug,
    validate_doc_id,
    write_report,
)

# ── 設定 ───────────────────────────────────────────────────────────────────────

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
USER = os.environ.get("NEO4J_ROUTINE_USER")
PASSWORD = os.environ.get("NEO4J_ROUTINE_PASSWORD")
TOKEN = os.environ.get("GRAPH_MCP_TOKEN")
PORT = int(os.environ.get("GRAPH_MCP_PORT", "8788"))

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


# ── MCP server ─────────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="stockbotv2-graph",
    host="127.0.0.1",           # 只綁本機；對外一律走 Cloudflare Tunnel
    port=PORT,
    streamable_http_path=f"/{TOKEN or 'unconfigured-token'}/mcp",  # 啟動前會驗 config
)


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
def get_extraction_rules() -> str:
    """取得撰寫抽取 JSON 前必讀的完整規則書。

    在呼叫 load_extraction 之前務必先讀這份——它包含 intermediate-format 的
    完整欄位規格、vocab 白名單（node type / abstraction_level / relation 等）、
    節點 ID 命名慣例、L4 屬性歸位三問、以及 L6 反幻覺鐵律（具體型號/公司名
    必須逐字出現在 quote 中），以及 remote intake 的 storage permission、
    filesystem-first、conflict 回報與 finalize 義務。不讀規則直接抽取，軟品質規則
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
        "\n\n---\n\n# 遠端 Intake／Finalize 協定（prompts/intake_protocol.md）\n\n" +
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


@mcp.tool()
def get_source_trace_manual() -> str:
    """取得未驗證線索進場前必讀的完整追源手冊。

    收到推文、轉述、截圖、搜尋摘要、新聞或任何尚未取得原文的 claim 時，
    必須先呼叫本工具，再依市場路由追回原始文件並套 tier 1–2 誠實降級／
    tier 3–4 未果隔離規則。手冊缺失時本工具回可讀錯誤，server 不會崩潰；
    呼叫端應停止抽取與 load_extraction。
    """
    return _read_source_trace_manual()


@mcp.tool()
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
    載入失敗，遠端不可自行選值。研究行動結束後，僅把 finalize_eligible=true 且
    status=loaded_or_already_complete 的 doc_id 傳給 finalize_research_action。
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
    try:
        doc = json.loads(extraction_json)
    except json.JSONDecodeError as e:
        return {"status": "rejected", "error": f"不是合法 JSON：{e}"}

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
        provenance = publish_provenance(
            doc_id,
            doc,
            raw_payload,
            root=root,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        return {
            "status": "rejected",
            "doc_id": doc_id,
            "error": f"provenance publish rejected: {exc}",
            "finalize_eligible": False,
        }

    driver = _driver()
    try:
        with driver.session() as session:
            load_to_graph(doc, session)
        _verify_loaded_doc(driver, doc)
        affected_edge_keys = {
            edge_key(edge["src_id"], edge["relation"], edge["dst_id"])
            for edge in doc.get("edges", [])
        }
        projection = project_edge_keys(driver, affected_edge_keys)
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
        "counts": {
            "nodes": len(doc.get("nodes", [])),
            "edges": len(doc.get("edges", [])),
            "claims": len(doc.get("claims", [])),
        },
        "warnings": warnings,
    }


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


def _remote_finalize_enabled() -> bool:
    return os.environ.get("ENABLE_REMOTE_FINALIZE", "").strip().casefold() in {
        "1",
        "true",
        "yes",
    }


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
    return {
        "git_status": git_result["status"],
        "commit": git_result.get("commit"),
        "push_error": git_result.get("push_error"),
        "error": git_result.get("error"),
        "report_path": report_relative,
        "manifest": manifest["documents"],
        "committed_paths": git_result.get("paths") or [],
        "pending_warning": pending_warning,
    }


@mcp.tool()
def finalize_research_action(
    report_markdown: str,
    action_slug: str,
    commit_headline: str,
    doc_ids: list[str],
) -> str:
    """完成一次遠端研究行動：報告、精確 pathspec commit、push。

    四個參數皆必填。只接受本次 load_extraction 成功回傳且
    finalize_eligible=true 的 doc_ids；server 會重新查落地 permission，不信任 client。
    任何 local_only、非 master、staged index、HEAD 與 origin/master 不同步或 fetch
    失敗都在寫報告前 fail closed。push 失敗保留 local commit。此工具預設由
    ENABLE_REMOTE_FINALIZE kill switch 關閉；啟用前必須在 connector 設 Needs approval。
    """
    return json.dumps(
        _finalize_research_action_impl(
            report_markdown,
            action_slug,
            commit_headline,
            doc_ids,
            enabled=_remote_finalize_enabled(),
        ),
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
