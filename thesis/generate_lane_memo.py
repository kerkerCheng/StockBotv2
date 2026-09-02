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
import hashlib
import json
import os
import sys
import tempfile
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


def _check_env(*, require_anthropic: bool = True) -> bool:
    ok = True
    if require_anthropic and not os.environ.get("ANTHROPIC_API_KEY"):
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
            from identity.registry import TICKER_MAP
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


def _build_variant_perception_context(company_id: str | None) -> str:
    """從 Decision cohort 讀已寫定的 variant perception（2026-09-02 cohort 是終點）。

    memo 是渲染視圖：thesis 差異點的家在 cohort，這裡只帶出、不代寫。
    讀不到（無 private root、無 cohort、未寫）都如實現形，不擋 memo 生成。"""
    if not company_id:
        return ""
    try:
        from decision_lab.bootstrap import open_default_store

        store = open_default_store()
        try:
            vp = store.latest_variant_perception_for_company(company_id)
        finally:
            store.close()
    except Exception as e:
        return f"## Variant Perception（cohort thesis）\n⚠ 讀取失敗：{e}\n"
    if vp is None:
        return (
            "## Variant Perception（cohort thesis）\n"
            "⚠ 該公司所有 cohort 均未寫 variant perception——memo 的差異點段落"
            "只能由市場數據現推，寫定請用 "
            f"`decision_lab variant-perception <cohort> --text …`（company_id={company_id}）\n"
        )
    return (
        "## Variant Perception（cohort thesis——已寫定的權威版本，memo 必須以此為準）\n"
        f"- cohort：`{vp['cohort_id']}`（寫入 {vp['created_at']}）\n"
        f"- {vp['variant_perception']}\n"
    )


def _parse_envelope(raw_text: str) -> tuple[dict | None, str | None]:
    """Parse provider-independent JSON, tolerating only an outer code fence."""

    candidate = raw_text.strip()
    if candidate.startswith("```") and candidate.endswith("```"):
        lines = candidate.splitlines()
        candidate = "\n".join(lines[1:-1]).strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return None, f"Model response is not valid JSON: {exc}"
    if not isinstance(parsed, dict):
        return None, "Model response JSON must be an object"
    return parsed, None


def _atomic_write_pair(memo_path: Path, memo_text: str, sidecar: dict) -> Path:
    """Publish a memo and its evidence sidecar without exposing partial files."""

    memo_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path = memo_path.with_suffix(".evidence.json")
    temp_paths: list[Path] = []
    try:
        for target, content in (
            (memo_path, memo_text),
            (
                sidecar_path,
                json.dumps(sidecar, ensure_ascii=False, indent=2, default=str) + "\n",
            ),
        ):
            handle = tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            )
            temp_path = Path(handle.name)
            temp_paths.append(temp_path)
            with handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        # Sidecar first: a visible memo never points at a not-yet-published manifest.
        os.replace(temp_paths[1], sidecar_path)
        temp_paths.pop(1)
        os.replace(temp_paths[0], memo_path)
        temp_paths.clear()
    finally:
        for path in temp_paths:
            path.unlink(missing_ok=True)
    return sidecar_path


def generate(
    out_path: str | Path | None = None,
    model: str | None = None,
    ticker: str | None = None,
    company_id: str | None = None,
    override_gate: bool = False,
    override_reason: str | None = None,
    envelope_path: str | Path | None = None,
) -> int:
    if not _check_env(require_anthropic=envelope_path is None):
        return 1

    Anthropic = None
    if envelope_path is None:
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
    from thesis.evidence_manifest import (
        build_context_inventory,
        evaluate_evidence_gates,
        gate_notes_markdown,
        inventory_to_markdown,
        validate_envelope,
    )

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
        inventory = build_context_inventory(driver, company_id=company_id)
        source_diversity_ctx, source_diversity_pass = _check_source_diversity(
            company_id,
            driver=driver,
        )
    finally:
        driver.close()

    if graph_ctx.startswith("⚠"):
        print(f"ERROR: 圖資料問題。\n{graph_ctx}", file=sys.stderr)
        return 1

    # ── 3. Engine C gate + L9 pre-conditions + market data ───────────────────
    resolved_ticker = _resolve_ticker(ticker, company_id)
    gate_ctx, gate_pass = _build_gate_context(resolved_ticker, override_gate, override_reason)
    market_ctx = _build_market_context(resolved_ticker)
    vp_ctx = _build_variant_perception_context(company_id)

    # L9 pre-condition gate (CLAUDE.md L9): must pass before "investment" label
    l9_ctx = ""
    l9_pass = False
    if not override_gate:
        try:
            from thesis.preconditions import check_all, format_gate
            l9_result = check_all(resolved_ticker, company_id=company_id)
            l9_ctx = format_gate(l9_result) + "\n"
            l9_pass = l9_result.get("gate_pass", False)
        except Exception as e:
            l9_ctx = f"## L9 前置條件 Gate\n⚠ 無法執行：{e}\n"
    else:
        l9_pass = True
        l9_ctx = f"## L9 前置條件 Gate\n⚠ Gate 已手動覆蓋（override-gate）\n"

    # Company-wide L8 is context only.  Promotion is decided after the draft by
    # inspecting the exact Claim/edge evidence selected in the manifest.
    evidence_inventory_ctx = inventory_to_markdown(inventory)

    print(f"[generate_lane_memo] ticker={resolved_ticker}, checklist_pass={gate_pass}, "
          f"l9_pass={l9_pass}, company_l8_pass={source_diversity_pass}", file=sys.stderr)

    # ── 4. Claude API call ────────────────────────────────────────────────────
    model = model or os.environ.get("THESIS_MODEL", "claude-sonnet-4-6")
    user_message = f"""\
以下是供應鏈知識圖譜的結構化上下文與財務/市場數據，請依照 system prompt 的格式撰寫 Directional Lane Memo。

{graph_ctx}

{evidence_inventory_ctx}

{source_diversity_ctx}

{gate_ctx}

{l9_ctx}

{market_ctx}

{vp_ctx}

請只輸出 system prompt 指定的 JSON envelope，不要加 code fence、前言或解釋。
確保 Variant Perception 段落有具體的「市場現在信 X，本 thesis 認為 Y，催化劑 Z」，
並引用上方市場定價數據中的具體數字。若上方已提供 cohort thesis 的權威版本，
Variant Perception 段落必須以它為基礎渲染（可補市場數字，不得改寫方向）。每個重要論點必須用 `[E#]` 指向
evidence_items；所有 ID 必須逐字取自 Evidence Inventory。"""

    if envelope_path is not None:
        envelope_file = Path(envelope_path)
        try:
            raw_text = envelope_file.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"ERROR: 無法讀取 envelope file：{exc}", file=sys.stderr)
            return 1
        print(f"[generate_lane_memo] envelope_file={envelope_file}", file=sys.stderr)
    else:
        print(f"[generate_lane_memo] model={model}", file=sys.stderr)
        client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.create(
            model=model,
            max_tokens=16000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        raw_text = response.content[0].text
    envelope, parse_error = _parse_envelope(raw_text)
    if envelope is None:
        validation = {
            "ok": False,
            "errors": [parse_error or "Unknown envelope parse error"],
            "resolved_evidence": [],
        }
        envelope = {"memo_markdown": raw_text, "evidence_items": []}
    else:
        validation = validate_envelope(envelope, inventory)
    evidence_gate = evaluate_evidence_gates(validation, inventory)

    evidence_pass = validation["ok"] and evidence_gate["promotion_pass"]
    if evidence_pass and gate_pass and l9_pass:
        output_type = "Watchlist Candidate"
    elif evidence_pass and override_gate:
        output_type = "Watchlist Candidate (override)"
    else:
        output_type = "Research Note"

    # ── 5. Write output and auditable evidence sidecar ────────────────────────
    header = (
        f"<!-- output_type: [{output_type}] | ticker: {resolved_ticker or 'n/a'} "
        f"| checklist_pass: {gate_pass} | l9_pass: {l9_pass} "
        f"| evidence_manifest_pass: {validation['ok']} "
        f"| evidence_gate_pass: {evidence_gate['promotion_pass']} -->\n\n"
    )
    if override_gate:
        header += f"<!-- gate_override: {override_reason or '(no reason)'} -->\n\n"

    memo_text = str(envelope.get("memo_markdown") or "").strip()
    if not validation["ok"]:
        manifest_errors = "\n".join(f"- {error}" for error in validation["errors"])
        memo_text += (
            "\n\n## Evidence Manifest Errors\n"
            "本稿無法驗證引用鏈，因此只能保存為 Research Note。\n"
            f"{manifest_errors}"
        )
    notes = gate_notes_markdown(evidence_gate)
    if notes:
        memo_text += "\n\n" + notes.rstrip()

    full_output = header + memo_text.rstrip() + "\n"

    out = Path(out_path) if out_path else DEFAULT_OUT
    canonical_inventory = json.dumps(
        inventory,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    sidecar = {
        "schema_version": "1.0",
        "memo_path": out.name,
        "memo_sha256": hashlib.sha256(full_output.encode("utf-8")).hexdigest(),
        "output_type": output_type,
        "ticker": resolved_ticker,
        "company_id": company_id,
        "context_inventory_sha256": hashlib.sha256(
            canonical_inventory.encode("utf-8")
        ).hexdigest(),
        "context_inventory": inventory,
        "evidence_items": envelope.get("evidence_items") or [],
        "validation": validation,
        "evidence_gate": evidence_gate,
        "engine_c_context": {
            "financial_checklist_markdown": gate_ctx,
            "market_snapshot_markdown": market_ctx,
        },
        "other_gates": {
            "financial_checklist_pass": gate_pass,
            "l9_pass": l9_pass,
            "company_l8_context_pass": source_diversity_pass,
            "override": override_gate,
            "override_reason": override_reason,
        },
    }
    sidecar_path = _atomic_write_pair(out, full_output, sidecar)
    print(f"[generate_lane_memo] wrote {out} and {sidecar_path}", file=sys.stderr)
    promotion_label = "可升格 Watchlist" if output_type.startswith("Watchlist") else "仍為 Research Note（見 gate 狀態）"
    print(f"\n[{output_type}] — {promotion_label}", file=sys.stderr)
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
    ap.add_argument(
        "--envelope-file",
        default=None,
        help=(
            "讀取 provider-independent JSON envelope，不呼叫 Anthropic API；"
            "適合由其他 agent/model 先產生 draft，再走同一驗證與 gate。"
        ),
    )
    args = ap.parse_args()
    return generate(
        out_path=args.out,
        model=args.model,
        ticker=args.ticker,
        company_id=args.company_id,
        override_gate=args.override_gate,
        override_reason=args.override_reason,
        envelope_path=args.envelope_file,
    )


if __name__ == "__main__":
    raise SystemExit(main())
