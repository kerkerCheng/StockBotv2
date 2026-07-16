"""
generate_lane_memo.py — 用 Claude API 生成 Directional Lane Memo。

流程:
  1. 建立 Neo4j driver，呼叫 query.graph_context.build_context() 取得結構化 Markdown
  2. 若有 --ticker，跑 Engine C 財務核驗清單 gate + 市場數據快照
  3. 讀 prompts/lane_memo_system.md 作為 system prompt
  4. 呼叫 anthropic.messages.create
  5. 輸出加 output_type header（[Watchlist Candidate] 或 [Research Note]）寫入 --out

用法:
    python thesis/generate_lane_memo.py
    python thesis/generate_lane_memo.py --ticker COHR --company-id co:coherent
    python thesis/generate_lane_memo.py --out thesis/cpo_v1_lane_memo.md
    python thesis/generate_lane_memo.py --override-gate --override-reason "第一次 dry run"

Env vars:
    ANTHROPIC_API_KEY  — required
    NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD — Neo4j 連線
    THESIS_MODEL       — optional; defaults to claude-sonnet-4-6
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SYSTEM_PROMPT_FILE = ROOT / "prompts" / "lane_memo_system.md"
DEFAULT_OUT = ROOT / "thesis" / "cpo_v1_lane_memo.md"


def _check_env() -> bool:
    ok = True
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY 未設定", file=sys.stderr)
        ok = False
    if not os.environ.get("NEO4J_PASSWORD"):
        print("ERROR: NEO4J_PASSWORD 未設定", file=sys.stderr)
        ok = False
    return ok


def _resolve_ticker(ticker: str | None, company_id: str | None) -> str | None:
    """從 ticker 或 company_id 反查 TICKER_MAP 取得 ticker。"""
    if ticker:
        return ticker.upper()
    if company_id:
        try:
            from loader.load_to_neo4j import TICKER_MAP
            return TICKER_MAP.get(company_id)
        except ImportError:
            pass
    return None


_Q_SOURCE_DIVERSITY = """
MATCH (company:Entity {id: $company_id})
CALL (company) {
  MATCH (claim:Claim)-[:CITES]->(sd:SourceDoc)
  WHERE claim.subject_kind = 'node'
    AND claim.subject_node_id = company.id
  RETURN sd
  UNION
  MATCH (company)-[relationship]-()
  WHERE relationship.edge_key IS NOT NULL
  MATCH (assertion:EdgeAssertion {edge_key: relationship.edge_key})-[:CITES]->(sd:SourceDoc)
  RETURN sd
}
WITH collect(DISTINCT sd) AS evidence_docs
MATCH (all_sd:SourceDoc)
RETURN count(all_sd) AS total_source_docs,
       size(evidence_docs) AS evidence_documents,
       [sd IN evidence_docs WHERE sd.origin_entity IS NOT NULL | sd.origin_entity]
         AS origin_entities
"""


def _source_diversity_from_session(session, company_id: str) -> dict:
    """Return company evidence diversity derived exclusively from graph CITES."""

    record = session.run(_Q_SOURCE_DIVERSITY, company_id=company_id).single()
    if not record:
        return {
            "total_source_docs": 0,
            "evidence_documents": 0,
            "origin_entities": [],
        }
    return {
        "total_source_docs": record["total_source_docs"],
        "evidence_documents": record["evidence_documents"],
        "origin_entities": sorted(set(record["origin_entities"] or [])),
    }


def _check_source_diversity(
    company_id: str | None,
    *,
    driver=None,
) -> tuple[str, bool]:
    """
    L8 來源獨立性 gate：從 Claim／EdgeAssertion 的 CITES 路徑查 SourceDoc，
    統計與 company_id 證據直接相連的不重複 origin_entity。

    回傳 (context_md, passes)。
    """
    if not company_id:
        return (
            "## L8 來源獨立性 Gate\n"
            "⚠ 未指定 --company-id，跳過來源獨立性檢查（產業全圖模式）。\n",
            True,
        )

    owns_driver = driver is None
    if owns_driver:
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            return (f"## L8 來源獨立性 Gate\n⚠ neo4j 套件不可用：{exc}\n", False)
        password = os.environ.get("NEO4J_PASSWORD")
        if not password:
            return ("## L8 來源獨立性 Gate\n⚠ NEO4J_PASSWORD 未設定。\n", False)
        driver = GraphDatabase.driver(
            os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
        )
    try:
        with driver.session() as session:
            result = _source_diversity_from_session(session, company_id)
    finally:
        if owns_driver:
            driver.close()

    distinct_entities = result["origin_entities"]
    count = len(distinct_entities)
    passes = count >= 3

    lines = [f"## L8 來源獨立性 Gate"]
    lines.append(
        f"圖中 SourceDoc 共 {result['total_source_docs']} 份；"
        f"與 `{company_id}` 的 Claim／EdgeAssertion 證據直接相連："
        f"{result['evidence_documents']} 份"
    )
    lines.append(f"不重複 origin_entity 數：**{count}**/3（需 ≥ 3 才通過）")
    for e in distinct_entities:
        lines.append(f"- {e}")
    if not passes:
        lines.append(
            "\n⛔ 來源獨立性不足（L8）：需要至少 3 個不同 origin_entity 的文件才能生成 Lane Memo。\n"
            "請先補充獨立第三方或客戶端文件（見 AGENTS.md L8 判準），或用 --override-gate 強制覆蓋。"
        )
    else:
        lines.append("\n✓ 來源獨立性通過")
    return "\n".join(lines) + "\n", passes


def _build_gate_context(ticker: str | None, override_gate: bool,
                         override_reason: str | None) -> tuple[str, bool]:
    """
    回傳 (gate_context_md, gate_pass)。
    gate_context_md 注入 user message；gate_pass 決定 output_type header。
    """
    if override_gate:
        reason = override_reason or "(未填理由)"
        return (
            f"## Watchlist Gate 狀態\n⚠ Gate 已手動覆蓋（override-gate）\n理由：{reason}\n",
            True,
        )

    if not ticker:
        return (
            "## Watchlist Gate 狀態\n"
            "⚠ 未指定 ticker，跳過財務核驗清單（產業全圖模式）。\n"
            "若需 Watchlist 升格，請用 --ticker <TICKER> 重新生成。\n",
            False,
        )

    try:
        from engine_c.checklist import get_checklist, format_checklist
        result = get_checklist(ticker)
        return format_checklist(result) + "\n", result.get("gate_pass", False)
    except Exception as e:
        return (
            f"## Watchlist Gate 狀態\n⚠ 財務清單查詢失敗：{e}\n",
            False,
        )


def _build_market_context(ticker: str | None) -> str:
    """回傳市場數據 Markdown 片段（Variant Perception 錨點）。"""
    if not ticker:
        return (
            "## 市場定價數據\n"
            "⚠ 未指定 ticker，無法取得市場數據。\n"
            "[請手動填寫 Variant Perception — 市場信 X，本 thesis 信 Y，催化劑 Z]\n"
        )
    try:
        from engine_c.market_data import get_snapshot, format_snapshot
        snap = get_snapshot(ticker)
        return format_snapshot(snap) + "\n"
    except Exception as e:
        return f"## 市場定價數據\n⚠ 取得失敗：{e}\n"


def generate(
    out_path: str | Path | None = None,
    model: str | None = None,
    ticker: str | None = None,
    company_id: str | None = None,
    override_gate: bool = False,
    override_reason: str | None = None,
) -> int:
    if not _check_env():
        return 1

    try:
        from anthropic import Anthropic
    except ImportError:
        print("需要 anthropic 套件: pip install anthropic", file=sys.stderr)
        return 1
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("需要 neo4j 套件: pip install neo4j", file=sys.stderr)
        return 1

    from query.graph_context import build_context

    # ── 1. System prompt ──────────────────────────────────────────────────────
    if not SYSTEM_PROMPT_FILE.exists():
        print(f"ERROR: System prompt not found: {SYSTEM_PROMPT_FILE}", file=sys.stderr)
        return 1
    system_prompt = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")

    # ── 2. Graph context ──────────────────────────────────────────────────────
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    pw = os.environ.get("NEO4J_PASSWORD")
    driver = GraphDatabase.driver(uri, auth=(user, pw))
    try:
        graph_ctx = build_context(driver, company_id=company_id)
    finally:
        driver.close()

    if graph_ctx.startswith("⚠"):
        print(f"ERROR: 圖資料問題。\n{graph_ctx}", file=sys.stderr)
        return 1

    # ── 3. Engine C gate + L9 pre-conditions + market data ───────────────────
    resolved_ticker = _resolve_ticker(ticker, company_id)
    gate_ctx, gate_pass = _build_gate_context(resolved_ticker, override_gate, override_reason)
    market_ctx = _build_market_context(resolved_ticker)

    # L9 pre-condition gate (CLAUDE.md L9): must pass before "investment" label
    l9_ctx = ""
    l9_pass = False
    if not override_gate:
        try:
            from thesis.preconditions import check_all, format_gate
            l9_result = check_all(resolved_ticker)
            l9_ctx = format_gate(l9_result) + "\n"
            l9_pass = l9_result.get("gate_pass", False)
        except Exception as e:
            l9_ctx = f"## L9 前置條件 Gate\n⚠ 無法執行：{e}\n"
    else:
        l9_pass = True
        l9_ctx = f"## L9 前置條件 Gate\n⚠ Gate 已手動覆蓋（override-gate）\n"

    # ── L8 Source diversity gate ─────────────────────────────────────────────
    source_diversity_ctx, source_diversity_pass = _check_source_diversity(company_id)
    if not override_gate and not source_diversity_pass:
        print(source_diversity_ctx, file=sys.stderr)
        print("ERROR: L8 來源獨立性不足，拒絕生成 Lane Memo。"
              " 使用 --override-gate 可強制覆蓋（需說明理由）。", file=sys.stderr)
        return 1

    # output_type hierarchy: both gates must pass for Watchlist Candidate
    if gate_pass and l9_pass:
        output_type = "Watchlist Candidate"
    elif override_gate:
        output_type = "Watchlist Candidate (override)"
    else:
        output_type = "Research Note"

    print(f"[generate_lane_memo] ticker={resolved_ticker}, checklist_pass={gate_pass}, "
          f"l9_pass={l9_pass}, output_type=[{output_type}]", file=sys.stderr)

    # ── 4. Claude API call ────────────────────────────────────────────────────
    model = model or os.environ.get("THESIS_MODEL", "claude-sonnet-4-6")
    user_message = f"""\
以下是供應鏈知識圖譜的結構化上下文與財務/市場數據，請依照 system prompt 的格式撰寫 Directional Lane Memo。

{graph_ctx}

{source_diversity_ctx}

{gate_ctx}

{l9_ctx}

{market_ctx}

請輸出 Markdown 格式的 Lane Memo，直接開始寫，不要加前言或解釋。
確保 Variant Perception 段落有具體的「市場現在信 X，本 thesis 認為 Y，催化劑 Z」，
並引用上方市場定價數據中的具體數字。"""

    print(f"[generate_lane_memo] model={model}", file=sys.stderr)
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    memo_text = response.content[0].text

    # ── 5. Write output with output_type header ────────────────────────────────
    header = (
        f"<!-- output_type: [{output_type}] | ticker: {resolved_ticker or 'n/a'} "
        f"| checklist_pass: {gate_pass} | l9_pass: {l9_pass} -->\n\n"
    )
    if override_gate:
        header += f"<!-- gate_override: {override_reason or '(no reason)'} -->\n\n"

    full_output = header + memo_text

    out = Path(out_path) if out_path else DEFAULT_OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(full_output, encoding="utf-8")
    print(f"[generate_lane_memo] wrote {out}", file=sys.stderr)
    print(f"\n[{output_type}] — {'可升格 Watchlist' if gate_pass else '仍為 Research Note（見 gate 狀態）'}",
          file=sys.stderr)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate Directional Lane Memo using Claude API."
    )
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help="Output path for the Lane Memo markdown file.")
    ap.add_argument("--model",
                    help="Claude model override (env: THESIS_MODEL; default: claude-sonnet-4-6).")
    ap.add_argument("--ticker",
                    help="股票代號（如 COHR）。用於財務核驗清單 gate 與市場數據取得。")
    ap.add_argument("--company-id",
                    help="Neo4j 公司 node id（如 co:coherent）。用於 graph context 過濾。")
    ap.add_argument("--override-gate", action="store_true",
                    help="強制跳過 Watchlist gate（輸出仍標記覆蓋記錄）。")
    ap.add_argument("--override-reason", default=None,
                    help="override-gate 時說明跳過理由。")
    args = ap.parse_args()
    return generate(
        out_path=args.out,
        model=args.model,
        ticker=args.ticker,
        company_id=args.company_id,
        override_gate=args.override_gate,
        override_reason=args.override_reason,
    )


if __name__ == "__main__":
    raise SystemExit(main())
