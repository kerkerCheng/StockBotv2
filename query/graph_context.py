"""
graph_context.py — 把 Neo4j 圖轉成 LLM-ready 的結構化 Markdown context。

四個 Cypher query 依序執行，組合成一個 Markdown 字串傳給 thesis generator。
使用 APOC 解析 JSON attributes（避免字串 CONTAINS 靜默失效）。

Env vars（與 loader/load_to_neo4j.py 相同）:
    NEO4J_URI       — default bolt://localhost:7687
    NEO4J_USER      — default neo4j
    NEO4J_PASSWORD  — required
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


# ── Cypher queries ─────────────────────────────────────────────────────────────

_Q_DEMAND = """\
MATCH (n:Entity {abstraction_level: 'end_demand'})
RETURN n.name AS name, n.role AS role, n.confidence AS confidence,
       n.source_ids AS source_ids
ORDER BY n.confidence DESC LIMIT 10
"""

_Q_SUPPLY = """\
MATCH (a:Entity)-[r]->(b:Entity)
WHERE r.confidence >= 0.6
  AND NOT (a:Claim) AND NOT (b:Claim)
RETURN a.name AS src, type(r) AS rel, b.name AS dst,
       r.attributes AS attrs, r.confidence AS confidence,
       r.source_ids AS source_ids
ORDER BY r.confidence DESC LIMIT {limit}
"""

_Q_BOTTLENECK = """\
MATCH (a:Entity)-[r]->(b:Entity)
WHERE NOT (a:Claim) AND NOT (b:Claim)
  AND (
    apoc.convert.fromJsonMap(coalesce(r.attributes, '{}')).sole_source = true
    OR toInteger(apoc.convert.fromJsonMap(coalesce(r.attributes, '{}')).substitutability) <= 2
  )
RETURN a.name AS src, b.name AS dst, type(r) AS rel,
       r.attributes AS attrs, r.source_ids AS source_ids
LIMIT 30
"""

_Q_CLAIMS = """\
MATCH (c:Claim)-[:ABOUT]->(s:Entity)
WHERE c.confidence >= 0.5
RETURN c.statement AS statement, c.demand_proof_level AS proof_level,
       c.disproof_condition AS disproof, c.confidence AS confidence,
       s.name AS subject, c.source_ids AS source_ids
ORDER BY
  CASE c.demand_proof_level
    WHEN 'confirmed' THEN 1 WHEN 'guided' THEN 2
    WHEN 'inferred' THEN 3 ELSE 4 END,
  c.confidence DESC
LIMIT {limit}
"""

_INSUFFICIENT_MSG = (
    "⚠ 圖資料不足（尚未載入足夠文件）。"
    "請先執行 U2：手選 5-8 篇文件跑 extract → validate → load，再執行本腳本。"
)

# 公司不在圖中時的回傳格式
_NOT_FOUND_TEMPLATE = (
    "⚠ 公司 '{company_id}' 不在 Neo4j 圖中。\n"
    "請依照 docs/onboarding-sop.md 執行新公司 onboarding 流程：\n"
    "  1. python fetchers/edgar.py --ticker <TICKER> --forms 10-K,10-Q --n 2\n"
    "  2. python extract.py --input library/raw/<doc>.txt ...\n"
    "  3. python loader/validate.py extractions/<doc>.json\n"
    "  4. python loader/load_to_neo4j.py extractions/<doc>.json\n"
    "  5. 確認節點存在後重新執行本查詢"
)

# 以公司為中心的 2 跳子圖查詢（company_id 過濾模式）
_Q_COMPANY_SUPPLY = """\
MATCH (c:Entity {{id: $company_id}})-[r]-(n:Entity)
WHERE NOT (c:Claim) AND NOT (n:Claim)
  AND r.confidence >= 0.5
RETURN c.name AS src, type(r) AS rel, n.name AS dst,
       r.attributes AS attrs, r.confidence AS confidence,
       r.source_ids AS source_ids,
       c.id AS src_id, n.id AS dst_id
ORDER BY r.confidence DESC LIMIT {limit}
"""

_Q_COMPANY_CLAIMS = """\
MATCH (cl:Claim)-[:ABOUT]->(s:Entity)
WHERE (s.id = $company_id OR EXISTS {{
    MATCH (s2:Entity {{id: $company_id}})-[*1..2]-(s)
}})
  AND cl.confidence >= 0.5
WITH DISTINCT cl, s
ORDER BY
  CASE cl.demand_proof_level
    WHEN 'confirmed' THEN 1 WHEN 'guided' THEN 2
    WHEN 'inferred' THEN 3 ELSE 4 END,
  cl.confidence DESC
LIMIT {limit}
RETURN cl.statement AS statement, cl.demand_proof_level AS proof_level,
       cl.disproof_condition AS disproof, cl.confidence AS confidence,
       s.name AS subject, cl.source_ids AS source_ids
"""


# ── builders ───────────────────────────────────────────────────────────────────

def _fmt_sources(source_ids) -> str:
    if not source_ids:
        return "(no source)"
    ids = source_ids if isinstance(source_ids, list) else [source_ids]
    return ", ".join(ids[:3]) + ("…" if len(ids) > 3 else "")


def _parse_attrs(attrs_json: str | None) -> dict:
    if not attrs_json:
        return {}
    try:
        return json.loads(attrs_json)
    except Exception:
        return {}


def _build_demand_section(records) -> str:
    if not records:
        return "### 需求層 (end_demand)\n_(無資料)_\n"
    lines = ["### 需求層 (end_demand)"]
    for r in records:
        src = _fmt_sources(r["source_ids"])
        lines.append(
            f"- **{r['name']}** — role: {r['role'] or 'n/a'}, "
            f"confidence: {r['confidence']:.2f} (source: {src})"
        )
    return "\n".join(lines) + "\n"


def _build_supply_section(records) -> str:
    if not records:
        return "### 關鍵供應關係 (confidence ≥ 0.6)\n_(無資料)_\n"
    header = "### 關鍵供應關係 (confidence ≥ 0.6)"
    col = "| 供應商/來源 | 關係 | 目標 | sole_source | substitutability | confidence | source |"
    sep = "|---|---|---|---|---|---|---|"
    rows = [header, col, sep]
    for r in records:
        attrs = _parse_attrs(r["attrs"])
        ss = "✓" if attrs.get("sole_source") else "—"
        sub = str(attrs.get("substitutability", "—"))
        src = _fmt_sources(r["source_ids"])
        rows.append(
            f"| {r['src']} | {r['rel']} | {r['dst']} | {ss} | {sub} "
            f"| {r['confidence']:.2f} | {src} |"
        )
    return "\n".join(rows) + "\n"


def _build_bottleneck_section(records) -> str:
    if not records:
        return "### 瓶頸候選 (sole_source=true 或 substitutability ≤ 2)\n_(無資料)_\n"
    lines = ["### 瓶頸候選 (sole_source=true 或 substitutability ≤ 2)"]
    for r in records:
        attrs = _parse_attrs(r["attrs"])
        attr_summary = ", ".join(
            f"{k}={v}" for k, v in attrs.items()
            if k in ("sole_source", "substitutability", "lead_time_weeks", "qualification_status")
        )
        src = _fmt_sources(r["source_ids"])
        lines.append(
            f"- **{r['src']}** --[{r['rel']}]--> **{r['dst']}**: "
            f"{attr_summary or '(no chokepoint attrs)'} (source: {src})"
        )
    return "\n".join(lines) + "\n"


def _build_claims_section(records) -> str:
    if not records:
        return "### 需求主張 (Claims)\n_(無資料)_\n"
    lines = ["### 需求主張 (Claims，confirmed/guided 優先)"]
    for r in records:
        src = _fmt_sources(r["source_ids"])
        lines.append(
            f"- [{r['proof_level']}] **{r['statement']}**\n"
            f"  subject: {r['subject']}, confidence: {r['confidence']:.2f}\n"
            f"  disproof: {r['disproof'] or '(未設定)'}\n"
            f"  source: {src}"
        )
    return "\n".join(lines) + "\n"


# ── public API ─────────────────────────────────────────────────────────────────

def _company_exists(session, company_id: str) -> bool:
    """Neo4j 中是否存在此 company_id 節點。"""
    result = session.run(
        "MATCH (n:Entity {id: $id}) RETURN count(n) AS cnt", id=company_id
    )
    return (result.single() or {}).get("cnt", 0) > 0


def _build_company_context(session, company_id: str,
                            supply_limit: int, claim_limit: int) -> str:
    """以 company_id 為中心建構 context（公司過濾模式）。"""
    supply_recs = list(session.run(
        _Q_COMPANY_SUPPLY.format(limit=supply_limit),
        company_id=company_id
    ))

    try:
        claim_recs = list(session.run(
            _Q_COMPANY_CLAIMS.format(limit=claim_limit),
            company_id=company_id
        ))
    except Exception:
        claim_recs = []

    company_name = company_id
    if supply_recs:
        r = supply_recs[0]
        company_name = r["src"] if r["src_id"] == company_id else r["dst"]

    sections = [f"## {company_name} 供應鏈上下文（公司過濾模式）\n"]
    sections.append(_build_supply_section(supply_recs))
    sections.append(_build_claims_section(claim_recs))
    return "\n".join(sections)


def build_context(
    driver,
    supply_limit: int = 50,
    claim_limit: int = 20,
    company_id: str | None = None,
) -> str:
    """
    Query Neo4j and return a structured Markdown context string for thesis generation.

    company_id (optional):
        None  → 產業全圖模式（原有行為，向後相容）
        str   → 以此公司為中心的 2 跳子圖過濾模式
                若公司不在圖中，回傳 _NOT_FOUND_TEMPLATE（不崩潰）
    """
    with driver.session() as session:
        if company_id is not None:
            if not _company_exists(session, company_id):
                return _NOT_FOUND_TEMPLATE.format(company_id=company_id)
            context = _build_company_context(
                session, company_id, supply_limit, claim_limit
            )
            estimated_tokens = len(context) // 4
            print(f"[graph_context] company_id={company_id}, "
                  f"~{estimated_tokens} tokens", file=sys.stderr)
            return context

        # ── 產業全圖模式（原有邏輯）──
        demand_recs = list(session.run(_Q_DEMAND))
        supply_recs = list(session.run(_Q_SUPPLY.format(limit=supply_limit)))

        try:
            bottle_recs = list(session.run(_Q_BOTTLENECK))
        except Exception as e:
            bottle_recs = []
            print(f"[graph_context] WARN: bottleneck query failed (APOC 未啟用?): {e}",
                  file=sys.stderr)

        claim_recs = list(session.run(_Q_CLAIMS.format(limit=claim_limit)))

    total_records = len(demand_recs) + len(supply_recs) + len(claim_recs)
    if total_records == 0:
        return _INSUFFICIENT_MSG

    sections = ["## CPO/矽光子供應鏈上下文\n"]
    sections.append(_build_demand_section(demand_recs))
    sections.append(_build_supply_section(supply_recs))
    sections.append(_build_bottleneck_section(bottle_recs))
    sections.append(_build_claims_section(claim_recs))

    context = "\n".join(sections)

    # Token guard: rough estimate, shrink if over limit
    estimated_tokens = len(context) // 4
    if estimated_tokens > 7500:
        print(
            f"[graph_context] context too large (~{estimated_tokens} tokens), retrying with smaller limits",
            file=sys.stderr,
        )
        return build_context(driver, supply_limit=30, claim_limit=15)

    print(f"[graph_context] built context: ~{estimated_tokens} tokens "
          f"({len(demand_recs)} demand, {len(supply_recs)} supply, "
          f"{len(bottle_recs)} bottleneck, {len(claim_recs)} claims)",
          file=sys.stderr)
    return context


# ── CLI (smoke-test) ───────────────────────────────────────────────────────────

def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Build graph context for thesis generation")
    ap.add_argument("--company-id", default=None,
                    help="公司 node id（如 co:sive），不傳則產業全圖模式")
    args = ap.parse_args()

    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("需要 neo4j 套件: pip install neo4j", file=sys.stderr)
        return 1

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    pw = os.environ.get("NEO4J_PASSWORD")
    if not pw:
        print("請設 NEO4J_PASSWORD", file=sys.stderr)
        return 1

    driver = GraphDatabase.driver(uri, auth=(user, pw))
    try:
        ctx = build_context(driver, company_id=args.company_id)
        print(ctx)
    finally:
        driver.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
