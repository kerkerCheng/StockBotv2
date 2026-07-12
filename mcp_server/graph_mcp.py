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
- load_extraction     — 載入一份「先通過 schema 驗證」的抽取 JSON（L8 人工核准
                        之後才會被呼叫；驗證不過就拒載，錯誤原样回傳）

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
from loader.load_to_neo4j import load as load_to_graph

# ── 設定 ───────────────────────────────────────────────────────────────────────

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
USER = os.environ.get("NEO4J_ROUTINE_USER")
PASSWORD = os.environ.get("NEO4J_ROUTINE_PASSWORD")
TOKEN = os.environ.get("GRAPH_MCP_TOKEN")
PORT = int(os.environ.get("GRAPH_MCP_PORT", "8788"))

if not (USER and PASSWORD):
    sys.exit("需要 .env 設定 NEO4J_ROUTINE_USER / NEO4J_ROUTINE_PASSWORD（最小權限帳號）")
if not TOKEN or len(TOKEN) < 16:
    sys.exit("需要 .env 設定 GRAPH_MCP_TOKEN（≥16 字元強隨機字串，將內嵌於 URL 路徑）")


def _driver() -> neo4j.Driver:
    return neo4j.GraphDatabase.driver(URI, auth=(USER, PASSWORD))


# ── MCP server ─────────────────────────────────────────────────────────────────

mcp = FastMCP(
    name="stockbotv2-graph",
    host="127.0.0.1",           # 只綁本機；對外一律走 Cloudflare Tunnel
    port=PORT,
    streamable_http_path=f"/{TOKEN}/mcp",   # URL 路徑內嵌 token
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
    必須逐字出現在 quote 中）。不讀規則直接抽取，軟品質規則無法靠 schema
    驗證補救。
    """
    rules = (ROOT / "prompts" / "extract_system.md").read_text(encoding="utf-8")
    vocab = (ROOT / "schema" / "vocab.json").read_text(encoding="utf-8")
    return (
        "# 抽取規則書（prompts/extract_system.md）\n\n" + rules +
        "\n\n---\n\n# Vocab 白名單（schema/vocab.json）\n\n```json\n" + vocab + "\n```\n"
    )


@mcp.tool()
def load_extraction(extraction_json: str) -> str:
    """把一份 intermediate-format 抽取 JSON 載入知識圖譜。

    只在使用者已人工核准（L8 來源獨立性確認）後呼叫。內建 schema/vocab 驗證：
    不合格的 JSON 會被拒載並回傳具體錯誤清單，不會寫進圖。
    輸入為完整的抽取 JSON 字串（schema_version / source_doc / sources / nodes / edges）。
    """
    try:
        doc = json.loads(extraction_json)
    except json.JSONDecodeError as e:
        return f"拒載：不是合法 JSON — {e}"

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
            return (f"拒載：驗證器異常（{type(e).__name__}: {e}）— "
                    f"通常代表 JSON 缺少必填欄位（如 claim 的 id）。"
                    f"請先呼叫 get_extraction_rules 核對格式後重試。")
    finally:
        os.unlink(tmp.name)

    hard_errors = [p for p in problems if not p.startswith("WARN")]
    warnings = [p for p in problems if p.startswith("WARN")]
    if hard_errors:
        return "拒載：驗證未通過\n" + "\n".join(hard_errors)

    driver = _driver()
    try:
        with driver.session() as session:
            load_to_graph(doc, session)
    except Exception as e:
        return f"載入失敗: {type(e).__name__}: {e}"
    finally:
        driver.close()

    doc_id = doc.get("source_doc", {}).get("doc_id", "?")
    summary = (
        f"已載入 doc_id={doc_id}: "
        f"{len(doc.get('nodes', []))} nodes, "
        f"{len(doc.get('edges', []))} edges, "
        f"{len(doc.get('claims', []))} claims"
    )
    if warnings:
        summary += "\n注意（不阻擋，但請回報給使用者）：\n" + "\n".join(warnings)
    return summary


if __name__ == "__main__":
    print(f"[graph_mcp] starting on 127.0.0.1:{PORT}, path=/<token>/mcp", file=sys.stderr)
    mcp.run(transport="streamable-http")
