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
import re
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
    OR toInteger(apoc.convert.fromJsonMap(coalesce(r.attributes, '{}')).substitutability) >= 4
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


#: Cypher 尾端的 `LIMIT {limit}` 或 `LIMIT 30`。
_LIMIT_RE = re.compile(r"\bLIMIT\s+(?:\{limit\}|\d+)\s*", re.IGNORECASE)


def _fetch(session, query: str, limit: int, **params) -> tuple[list, int]:
    """跑掉 `LIMIT` 的查詢、在 Python 端截，回傳 `(要用的列, 真實總數)`。

    ⚠ **`LIMIT` 留在 Cypher 裡時，回來的結果無法分辨「只有這麼多」與「被切掉了」**
    ——那正是 L13-2 說的「成功與失敗在同一個訊號上同形」。實測代價（2026-09-17／18）：
    `co:axt` 的 context 在 `claim_limit=20` 時字串 `jx` 出現 **1 次**、`claim_limit=200`
    時出現 **21 次**——JX Advanced Metals 宣布 InP 產能拉到 7–10 倍的那批證據**一直在圖裡**，
    只是被這個不說話的 `LIMIT` 切掉了。而 2026-09-17 的結構讀圖因此把病因誤診成「圖裡缺一條邊」，
    補了邊（pq2 [602]）也沒解決。

    ⚠ **`ORDER BY` 仍留在 server 端**，所以截出來的前 N 列與原本**逐列相同**；
    這一點由 `tests/test_graph_context_truncation.py` 鎖住——本修法宣稱「只多一行字，
    不動任何一列資料」，那個宣稱必須可否證。

    列數是量過才這樣做的（2026-09-18 實測最大 515 列）：全取比再跑一次 COUNT 便宜，
    而且總數是免費的。
    """
    # ⚠ 兩類查詢不能一視同仁：帶 `{limit}` 的那些用 `{{ }}` escape 過大括號，必須走
    # `.format()` 才會還原；`_Q_BOTTLENECK` 卻含裸的 `coalesce(r.attributes, '{}')`，
    # 對它呼叫 `.format()` 會把 `{}` 當成位置參數而炸掉。所以判斷條件是模板裡有沒有 `{limit}`。
    sql = query.format(limit=limit) if "{limit}" in query else query

    # ⚠⚠ **要用的那幾列一律走「原封不動的查詢」，第二趟只拿來數。**
    # 首版把 `LIMIT` 拿掉、改在 Python 端截——看起來等價，實測**不是**：帶 `LIMIT` 時
    # Neo4j 走 Top-N 運算子，平手（本圖大量 confidence=0.90）的 tie-break 與全排序不同，
    # 於是 `co:axt` 的 20 條 claim **換了一批**。舊版連跑兩次完全相同，所以那是我改出來的，
    # 不是它本來就不穩。多一趟往返換「這一行字不會動到任何一列資料」，值得。
    rows = list(session.run(sql, **params))
    total = len(list(session.run(_LIMIT_RE.sub("", sql), **params)))
    return rows, max(total, len(rows))


def _truncation_note(shown: int, total: int) -> str:
    """⚠ **沒被截斷時也要說。** 否則「全部列出」與「這一段壞了」在輸出上同形。

    只給數字；為什麼要在意寫在文件層級的 `_TRUNCATION_CAVEAT`，不在每段重複四次。
    """
    if shown >= total:
        return f"_（{total} 條全部列出，沒有截斷）_"
    return f"⚠ **只列出 {shown}／{total} 條——另外 {total - shown} 條不在這份 context 裡。**"


_TRUNCATION_CAVEAT = (
    "> ⚠ **這份 context 有段落被截斷了（見各段標題下的 N／M）。**"
    "截斷順序是查詢的 `ORDER BY`，**不是重要性排序**——沒出現不代表不存在、更不代表不重要。\n"
    "> **不得把它讀成完整證據。** 事發 2026-09-17：`co:axt` 的 context 在預設 `claim_limit=20` 下"
    "字串 `jx` 出現 **1 次**、放到 200 出現 **21 次**，於是 JX Advanced Metals 宣布 InP 產能拉到"
    " 7–10 倍的那批證據看起來「不在圖裡」，病因被誤診成「缺一條邊」，補了邊（pq2 [602]）也沒解決。\n"
)


def _any_truncated(*pairs: tuple[int, int]) -> bool:
    return any(shown < total for shown, total in pairs)


def _build_demand_section(records, total: int | None = None) -> str:
    if not records:
        return "### 需求層 (end_demand)\n_(無資料)_\n"
    lines = ["### 需求層 (end_demand)",
             _truncation_note(len(records), len(records) if total is None else total)]
    for r in records:
        src = _fmt_sources(r["source_ids"])
        lines.append(
            f"- **{r['name']}** — role: {r['role'] or 'n/a'}, "
            f"confidence: {r['confidence']:.2f} (source: {src})"
        )
    return "\n".join(lines) + "\n"


def _build_supply_section(records, total: int | None = None) -> str:
    if not records:
        return "### 關鍵供應關係 (confidence ≥ 0.6)\n_(無資料)_\n"
    header = ("### 關鍵供應關係 (confidence ≥ 0.6)\n"
              + _truncation_note(len(records), len(records) if total is None else total))
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


def _build_bottleneck_section(records, total: int | None = None) -> str:
    if not records:
        return "### 瓶頸候選 (sole_source=true 或 substitutability ≥ 4)\n_(無資料)_\n"
    lines = ["### 瓶頸候選 (sole_source=true 或 substitutability ≥ 4)",
             _truncation_note(len(records), len(records) if total is None else total)]
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


def _build_claims_section(records, total: int | None = None) -> str:
    if not records:
        return "### 需求主張 (Claims)\n_(無資料)_\n"
    lines = ["### 需求主張 (Claims，confirmed/guided 優先)",
             _truncation_note(len(records), len(records) if total is None else total)]
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
    supply_recs, supply_total = _fetch(
        session, _Q_COMPANY_SUPPLY, supply_limit, company_id=company_id)

    try:
        claim_recs, claim_total = _fetch(
            session, _Q_COMPANY_CLAIMS, claim_limit, company_id=company_id)
    except Exception:
        claim_recs, claim_total = [], 0

    company_name = company_id
    if supply_recs:
        r = supply_recs[0]
        company_name = r["src"] if r["src_id"] == company_id else r["dst"]

    sections = [f"## {company_name} 供應鏈上下文（公司過濾模式）\n"]
    if _any_truncated((len(supply_recs), supply_total), (len(claim_recs), claim_total)):
        sections.append(_TRUNCATION_CAVEAT)
    sections.append(_build_supply_section(supply_recs, supply_total))
    sections.append(_build_claims_section(claim_recs, claim_total))
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
        # ⚠ `_Q_DEMAND` 與 `_Q_BOTTLENECK` 的 LIMIT 是硬編在 Cypher 裡的（10／30），
        # 一樣不說話。實測 2026-09-18：demand 真實 23 條被切到 10、全圖 supply 515 條
        # 被切到 50、全圖 claims 325 條被切到 20——三段都沉默。
        demand_recs, demand_total = _fetch(session, _Q_DEMAND, 10)
        supply_recs, supply_total = _fetch(session, _Q_SUPPLY, supply_limit)

        try:
            bottle_recs, bottle_total = _fetch(session, _Q_BOTTLENECK, 30)
        except Exception as e:
            bottle_recs, bottle_total = [], 0
            print(f"[graph_context] WARN: bottleneck query failed (APOC 未啟用?): {e}",
                  file=sys.stderr)

        claim_recs, claim_total = _fetch(session, _Q_CLAIMS, claim_limit)

    total_records = len(demand_recs) + len(supply_recs) + len(claim_recs)
    if total_records == 0:
        return _INSUFFICIENT_MSG

    sections = ["## CPO/矽光子供應鏈上下文\n"]
    if _any_truncated((len(demand_recs), demand_total), (len(supply_recs), supply_total),
                      (len(bottle_recs), bottle_total), (len(claim_recs), claim_total)):
        sections.append(_TRUNCATION_CAVEAT)
    sections.append(_build_demand_section(demand_recs, demand_total))
    sections.append(_build_supply_section(supply_recs, supply_total))
    sections.append(_build_bottleneck_section(bottle_recs, bottle_total))
    sections.append(_build_claims_section(claim_recs, claim_total))

    context = "\n".join(sections)

    # Token guard: rough estimate, shrink if over limit
    estimated_tokens = len(context) // 4
    if estimated_tokens > 7500:
        print(
            f"[graph_context] context too large (~{estimated_tokens} tokens), retrying with smaller limits",
            file=sys.stderr,
        )
        # ⚠ **這一次收縮也要寫進 context 本身，不能只印到 stderr。**
        # 讀 context 的是下游的 LLM／使用者，他們看不到 stderr——「這份 context 被二次
        # 收縮過」如果只存在於 stderr，對消費端而言它就沒有發生過（L13-2）。
        return (
            f"⚠ **這份 context 被二次收縮過**：第一次組出來約 {estimated_tokens} tokens，"
            f"超過 7,500 的上限，於是以更小的 limit（supply 30／claims 15）重跑。"
            f"**下面每一段的「只列出 N／M」會比未收縮時更少。**\n\n"
            + build_context(driver, supply_limit=30, claim_limit=15)
        )

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
