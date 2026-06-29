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

def build_context(driver, supply_limit: int = 50, claim_limit: int = 20) -> str:
    """Query Neo4j and return a structured Markdown context string for thesis generation."""
    sections = ["## CPO/矽光子供應鏈上下文\n"]

    with driver.session() as session:
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
        ctx = build_context(driver)
        print(ctx)
    finally:
        driver.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
