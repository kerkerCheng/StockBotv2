"""從真實 authority 擷取 `alpha/` 契約的驗證 fixture（Phase 1 的 T2／T5）。

## 為什麼這支腳本存在

Phase 1 的驗收條件之一是「**契約能承載真實資料**」。用手寫的假資料驗契約只會證明
契約與自己一致；真正會撞出設計缺口的是圖裡那些長得很醜的 `evidence_refs`
（有 doc id、有 URI、有 entity id、有 edge key，也有整段帶逐字引文的散文）。

## 隱私邊界（硬規則）

輸出進 tracked 的 `tests/fixtures/alpha/`，所以**只擷取公開事實與結構**：
- ✅ 圖的 assertion／SourceDoc metadata（公開文件）
- ✅ Engine C 的欄位名與 as-of（公開財報事實）
- ✅ 五軸的 level／reason／evidence_refs（研究判斷，內容是公開財務）
- ❌ **不擷取** NAV、持股、部位、`live_current_position`、`paper_capacity_snapshot`、
  cash floor、貸款額度——那些是 private authority，永不進 Git。

用法：
    python scripts/capture_alpha_fixtures.py            # 寫入 fixture
    python scripts/capture_alpha_fixtures.py --report   # 只印報告，不寫檔
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alpha.contracts import EvidenceRef  # noqa: E402
from alpha.errors import ContractViolation  # noqa: E402

OUT_DIR = ROOT / "tests" / "fixtures" / "alpha"

#: 絕不寫進 tracked fixture 的欄位（private authority）。
FORBIDDEN_KEYS = frozenset({
    "live_current_position", "paper_capacity_snapshot", "nav_base", "nav",
    "holdings", "cash_floor", "credit_facility", "selected_weight",
    "single_position_nav_cap", "shares", "fill", "position",
})


def _scrub(payload):
    """遞迴移除 private authority 欄位。fail loudly：留下移除紀錄。"""
    removed: list[str] = []

    def walk(node, path=""):
        if isinstance(node, dict):
            out = {}
            for key, value in node.items():
                if key in FORBIDDEN_KEYS:
                    removed.append(f"{path}.{key}".lstrip("."))
                    continue
                out[key] = walk(value, f"{path}.{key}".lstrip("."))
            return out
        if isinstance(node, list):
            return [walk(v, f"{path}[]") for v in node]
        return node

    return walk(payload), removed


# ---------------------------------------------------------------------------
# evidence ref 分類：真實引用長什麼樣
# ---------------------------------------------------------------------------

_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^edge:[0-9a-f]{16,}$"), "graph_edge"),
    (re.compile(r"^(co|tech|mat|prod|std|person):[a-z0-9_]+$"), "graph_claim"),
    (re.compile(r"^yfinance://"), "market_series"),
    (re.compile(r"^[a-z0-9_]+_(10_[kq]|8k|q\d[a-z]{2}\d+)[a-z0-9_]*$"), "source_doc"),
    (re.compile(r"^engine_c://"), "engine_c_observation"),
    (re.compile(r"^[a-z0-9][a-z0-9_.\-]{3,}$"), "source_doc"),
)


def classify_ref(raw: str) -> tuple[str, str]:
    """把真實 evidence_ref 字串分類。回傳 (kind, 判準)。

    ⚠ **這是 Phase 2 的核心難題的預覽。** F-22 實測：`yfinance://history` 對不上
    `yfinance://history/AAOI`，一個少了後綴的字串讓整筆決策資本歸零 22 次。
    分類器在這裡只是描述現況，不是 gate——它告訴我們有多少引用**無法機器分類**。
    """
    text = raw.strip()
    for pattern, kind in _PATTERNS:
        if pattern.match(text):
            return kind, pattern.pattern
    return "external_document", "fallback:散文型引用（含逐字 quote，無結構化 id）"


# ---------------------------------------------------------------------------
# 來源 1：Engine A（圖）
# ---------------------------------------------------------------------------

_GRAPH_QUERY = """
MATCH (a:EdgeAssertion)-[:CITES]->(d:SourceDoc)
WHERE d.published_at IS NOT NULL
RETURN a.id AS assertion_id, a.edge_key AS edge_key,
       a.source_ids AS source_ids, a.confidence AS confidence,
       d.id AS doc_id, d.origin_entity AS origin_entity,
       d.evidence_tier AS evidence_tier, d.published_at AS published_at,
       d.retrieved_at AS retrieved_at, d.url AS url, d.source_type AS source_type
ORDER BY d.published_at DESC
LIMIT $limit
""".strip()


def capture_graph_refs(limit: int = 5) -> list[EvidenceRef]:
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        from neo4j import GraphDatabase
    except Exception as exc:  # pragma: no cover
        print(f"[graph] 略過（driver 或 .env 不可用）：{exc}", file=sys.stderr)
        return []
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    refs: list[EvidenceRef] = []
    with driver.session() as session:
        for row in session.run(_GRAPH_QUERY, limit=limit):
            data = dict(row)
            refs.append(EvidenceRef(
                ref=f"graph://assertion/{data['assertion_id']}",
                kind="graph_assertion",
                source_doc_id=data.get("doc_id"),
                origin_entity=data.get("origin_entity"),
                url=data.get("url"),
                published_at=_as_date(data.get("published_at")),
                retrieved_at=_as_date(data.get("retrieved_at")),
                evidence_tier=_as_tier(data.get("evidence_tier")),
                confidence=_as_float(data.get("confidence")),
            ))
    driver.close()
    return refs


def _as_date(value) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _as_tier(value) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed in (1, 2, 3, 4) else None


def _as_float(value) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if 0.0 <= parsed <= 1.0 else None


# ---------------------------------------------------------------------------
# 來源 2：Engine C（人工觀測 ledger）
# ---------------------------------------------------------------------------

def capture_engine_c_refs(limit: int = 3) -> list[EvidenceRef]:
    try:
        from engine_c.db import get_conn
    except Exception as exc:  # pragma: no cover
        print(f"[engine_c] 略過：{exc}", file=sys.stderr)
        return []
    cur = get_conn().cursor()
    cur.execute(
        "SELECT observation_id, ticker, field_name, source_ref, as_of, recorded_at "
        "FROM manual_observations ORDER BY as_of DESC LIMIT ?", (limit,)
    )
    refs: list[EvidenceRef] = []
    for row in cur.fetchall():
        obs = dict(row) if not isinstance(row, tuple) else dict(
            zip(("observation_id", "ticker", "field_name", "source_ref",
                 "as_of", "recorded_at"), row))
        refs.append(EvidenceRef(
            ref=f"engine_c://manual_observation/{obs['observation_id']}",
            kind="engine_c_observation",
            origin_entity=str(obs.get("ticker") or "") or None,
            # ⚠ `as_of` 是**事實生效日**（資產負債表日），`recorded_at` 是寫入日。
            # 兩者永遠不得共用一個欄位（F-27）。
            published_at=_as_date(obs.get("as_of")),
            recorded_at=_as_datetime(obs.get("recorded_at")),
            quote=str(obs.get("source_ref") or "")[:200] or None,
        ))
    return refs


def _as_datetime(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# 來源 3：Engine D（COHR 的五軸 assessment）
# ---------------------------------------------------------------------------

def capture_axis_assessment(company_id: str = "co:coherent") -> dict:
    from decision_lab.bootstrap import open_default_store

    store = open_default_store()
    try:
        cohorts = store.list_operational_cohorts(as_of=datetime.now().astimezone().isoformat())
        match = [c for c in cohorts if str(c.get("company_id")) == company_id]
        if not match:
            return {}
        decision_id = str(match[0]["latest_decision_id"])
        decision = store.get_decision(decision_id)
        payload = decision.get("payload", decision)
        if isinstance(payload, str):
            payload = json.loads(payload)
        sizing = payload.get("sizing", {})
        axes = sizing.get("axis_results", {})
        scrubbed, removed = _scrub({
            "cohort_id": match[0]["cohort_id"],
            "company_id": company_id,
            "weakest_axis": sizing.get("weakest_axis"),
            "research_status": sizing.get("research_status"),
            "rubric_version": sizing.get("rubric_version"),
            "axis_results": axes,
        })
        scrubbed["_scrubbed_private_keys"] = removed
        return scrubbed
    finally:
        store.close()


# ---------------------------------------------------------------------------
# 來源 3b：把既有五軸映射成新的五個 score（T5）
# ---------------------------------------------------------------------------

#: ⚠ **既有五軸與新的五個 score 不是同一組東西**（2026-09-03 實測發現）。
#: 舊五軸問的是「證據多強」（evidence-quality gate）；新五 score 問的是
#: prompt §6 的五個投資問題。對應關係是**輸入**不是改名：
AXIS_TO_SCORE: dict[str, str | None] = {
    "technical_causal_link": "structural",        # Q1：因果鏈強度 → 結構稀缺性
    "commercial_maturity": "value_capture",       # Q2：客戶端商業承諾 → 能否收租
    "financial_resilience": "earnings_exposure",  # Q3：⚠ 只是部分——真正要的是
                                                  #     segment revenue，Engine C 沒有欄位
    "valuation_payoff": "expectation_gap",        # Q4：估值錨點 → 市場隱含 vs 本 thesis
    "source_reliability": None,                   # ⚠ 無對應——它是**meta 軸**，
                                                  #     限定所有 EvidenceRef 的品質
}

#: Q5 catalyst 在舊系統**沒有任何軸**——它住在 `coverage_assessments.catalyst`
#: 的自由文字裡。因此真實 fixture 的 `catalyst_score` 是 `None`，
#: 而那正好讓 fixture 順帶驗到 `None ≠ 0` 與 `is_incomplete` 的路徑。
LEVEL_TO_SCORE: dict[str, float | None] = {
    "unknown": None,
    "bounded_hypothesis": 0.5,
    "corroborated": 0.85,
}


def build_alpha_signal_fixture(assessment: dict) -> dict:
    """把 COHR 的真實五軸組成一份 `AlphaSignal` payload，並記錄裝不下的東西。"""
    from alpha.contracts import (
        AXES, AlphaSignal, ComponentTrace, DisproofCondition, Score, _canonical,
    )
    from alpha.identity import CompanyId, Ticker

    axes = assessment.get("axis_results") or {}
    scores: dict[str, object] = {f"{name}_score": None for name in AXES}
    traces: dict[str, ComponentTrace] = {}
    gaps: list[str] = []

    for axis_name, payload in axes.items():
        target = AXIS_TO_SCORE.get(axis_name)
        if target is None:
            gaps.append(f"{axis_name}：meta 軸，不對應任何 score（限定 EvidenceRef 品質）")
            continue
        declared = LEVEL_TO_SCORE.get(str(payload.get("level")))
        effective = LEVEL_TO_SCORE.get(str(payload.get("effective_level")))
        if declared is None or effective is None:
            gaps.append(f"{axis_name}：level={payload.get('level')} 對應不到分數")
            continue
        trace_id = f"ct_{target}"
        refs = tuple(
            EvidenceRef(ref=str(raw), kind=classify_ref(str(raw))[0])
            for raw in (payload.get("evidence_refs") or [])
        )
        if not refs:
            gaps.append(f"{axis_name}：沒有 evidence_refs，score 依契約不得存在")
            continue
        traces[trace_id] = ComponentTrace(
            trace_id=trace_id,
            rule_version=str(assessment.get("rubric_version") or "unknown"),
            inputs={"source_axis": axis_name, "level": payload.get("level"),
                    "effective_level": payload.get("effective_level")},
            evidence_refs=refs,
            note=str(payload.get("reason") or "")[:400] or None,
        )
        scores[f"{target}_score"] = Score(
            declared=declared,
            effective=effective,
            trace_id=trace_id,
            downgrade_reason=(
                None if effective >= declared
                else ",".join(str(m) for m in (payload.get("missing_data") or [])) or "unspecified"
            ),
        )

    if scores.get("catalyst_score") is None:
        gaps.append(
            "catalyst（Q5）：舊系統無對應軸——它住在 coverage_assessments.catalyst 的"
            "自由文字裡，沒有結構化欄位。這是 Phase 4/5 要補的缺口"
        )

    signal = AlphaSignal(
        ticker=Ticker("COHR"),
        company_id=CompanyId(str(assessment.get("company_id") or "co:coherent")),
        as_of=date.today(),
        direction="long",
        confidence=0.6,
        expected_horizon="2-4 quarters",
        thesis="NVIDIA 多年期產能協議＋20 億美元投資使 COHR 在 CPO 外部光源具結構位置",
        variant_view=(
            "市場隱含：forward P/E 23.4x／EV-Revenue 9.9x 已給 Networking／CPO 成長"
            "相當高的兌現機率；本 thesis 認為毛利與現金流的轉換速度是未被充分定價的分歧點"
        ),
        bull_case="產能協議如期轉為營收，毛利率隨 CPO 組合上行",
        base_case="營收兌現但毛利改善落後",
        bear_case="CPO 時程遞延，供給側擴張壓縮定價權",
        disproof_conditions=(
            DisproofCondition(
                condition="non-GAAP 毛利率連續兩季低於 40.2%",
                check_frequency="quarterly",
                action_within_48h="強制 review → retire 或 revise thesis",
            ),
        ),
        model_components=traces,
        **scores,
    )
    return {
        "_comment": "由 scripts/capture_alpha_fixtures.py 從 COHR 真實五軸映射而成。"
                    "⚠ 舊五軸與新五 score 不是同一組東西，映射關係見 AXIS_TO_SCORE。",
        "signal": _canonical(signal),
        "is_incomplete": signal.is_incomplete,
        "weakest": signal.weakest,
        "known_axes": list(signal.known_axes),
        "ordering_key": [str(k) for k in signal.ordering_key()],
        "contract_gaps": gaps,
    }


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def build(report_only: bool = False) -> int:
    graph_refs = capture_graph_refs()
    engine_c_refs = capture_engine_c_refs()
    assessment = capture_axis_assessment()

    all_refs = graph_refs + engine_c_refs
    print(f"EvidenceRef：圖 {len(graph_refs)} 筆｜Engine C {len(engine_c_refs)} 筆")
    dated = sum(1 for r in all_refs if r.is_dated)
    print(f"  有 published_at：{dated}/{len(all_refs)}")

    # 真實 evidence_refs 字串的分類分佈——Phase 2 的難度預覽
    raw_refs: list[str] = []
    for axis in (assessment.get("axis_results") or {}).values():
        raw_refs.extend(str(r) for r in (axis.get("evidence_refs") or []))
    buckets: dict[str, int] = {}
    unclassifiable: list[str] = []
    for raw in raw_refs:
        kind, rule = classify_ref(raw)
        buckets[kind] = buckets.get(kind, 0) + 1
        if rule.startswith("fallback"):
            unclassifiable.append(raw[:80])
    print(f"\n五軸 evidence_refs 共 {len(raw_refs)} 條，機器分類分佈：")
    for kind, count in sorted(buckets.items(), key=lambda kv: -kv[1]):
        print(f"  {kind:24s} {count}")
    if unclassifiable:
        print(f"  ⚠ 無法結構化分類（散文型引用）{len(unclassifiable)} 條，例：")
        for sample in unclassifiable[:3]:
            print(f"      {sample}…")

    violations: list[str] = []
    for raw in raw_refs:
        kind, _ = classify_ref(raw)
        try:
            EvidenceRef(ref=raw, kind=kind)
        except ContractViolation as exc:
            violations.append(f"{raw[:60]} → {exc}")
    print(f"\n契約承載檢查：{len(raw_refs) - len(violations)}/{len(raw_refs)} 條可建成 EvidenceRef")
    for violation in violations[:5]:
        print(f"  ✗ {violation}")

    signal_fixture = build_alpha_signal_fixture(assessment) if assessment else {}
    if signal_fixture:
        print("")
        print(f"AlphaSignal 組裝：incomplete={signal_fixture['is_incomplete']}"
              f"｜weakest={signal_fixture['weakest']}"
              f"｜已知維度 {len(signal_fixture['known_axes'])}/5")
        print("契約裝不下／缺口：")
        for gap in signal_fixture["contract_gaps"]:
            print(f"  ⚠ {gap}")

    if report_only:
        return 1 if violations else 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    from alpha.contracts import _canonical

    (OUT_DIR / "evidence_refs_real.json").write_text(
        json.dumps({
            "_comment": "由 scripts/capture_alpha_fixtures.py 從真實 authority 擷取。"
                        "只含公開事實與結構；NAV／持股／部位已 scrub。",
            "captured_at": date.today().isoformat(),
            "graph": [_canonical(r) for r in graph_refs],
            "engine_c": [_canonical(r) for r in engine_c_refs],
            "raw_axis_refs": raw_refs,
            "classification": buckets,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    (OUT_DIR / "cohr_axis_assessment.json").write_text(
        json.dumps(assessment, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if signal_fixture:
        (OUT_DIR / "cohr_alpha_signal.json").write_text(
            json.dumps(signal_fixture, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(f"\n已寫入 {OUT_DIR}")
    return 1 if violations else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true", help="只印報告，不寫檔")
    args = parser.parse_args()
    return build(report_only=args.report)


if __name__ == "__main__":
    raise SystemExit(main())
