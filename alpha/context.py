"""`ResearchContext` 的組裝，以及 Q1（Structural Scarcity）的 deterministic 計算。

## 為什麼 Q1 是 deterministic 而 Q2–Q5 需要 session

**判斷已經在入圖時做過了。** `substitutability`／`sole_source`／`qualification_status`
是**已經通過 admission gate 的事實**——它們是研究者當時的判斷，經人工核准寫進圖，
帶著 provenance。再讓 session 對同一批事實重新「判斷一次」，等於在 gate 之後
又開一個沒有 gate 的判斷入口（L15：LLM 可以提議，不可以授權）。

所以 Q1 的分數是**已入圖事實的確定性函數**；Q2–Q5 才需要新的語意判斷
（pricing power、segment 曝險、市場隱含假設、催化劑），而那些圖裡沒有。

## Q1 的計分規則刻意極簡

`substitutability`（1–5）為主、`sole_source` 與 `qualification_status` 為佐證。
**不做加權總分**——三者相加會讓「替代難度低但已 designed_in」看起來像
「替代難度高」，正是 2026-08-21 pq1 補償性的形狀。改用**字典序降階**：
先看 substitutability 落在哪一階，再由另外兩項在該階內微調，且**微調幅度
不足以跨階**。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Sequence

from .contracts import (
    ComponentTrace, ConsensusSnapshot, EvidenceQuality, EvidenceRef, EvidenceSelection,
    FreshnessState, FundamentalsSnapshot, MarketSnapshot, ResearchContext, ScarcityInputs,
    Score, StructuralContext, ValuationSnapshot, select_point_in_time_evidence,
)
from .errors import ContractViolation
from .evidence_quality import assess_evidence_quality
from .identity import CompanyId, Ticker

SCARCITY_RULE_VERSION = "structural-scarcity/v1"

#: `substitutability` → 分數基階。**只有五階，對應圖上的 1–5**，不內插。
#:
#: ⚠ **階距必須等寬。** 第一版是 `{5:0.80, 4:0.60, 3:0.40, 2:0.20, 1:0.10}`——
#: 1→2 的階距只有 0.10，而佐證預算也是 0.10，於是
#: 「sub=1 ＋ sole_source ＋ designed_in」剛好追平「sub=2 裸值」。
#: **單一 case 測不到；掃過 5×3×6=90 組的 property test 當場抓到**
#: （`historical-failure-matrix.md` §5：多維 gate 不得只做 regression example）。
_SUBSTITUTABILITY_BAND: Mapping[int, float] = {
    5: 0.90, 4: 0.70, 3: 0.50, 2: 0.30, 1: 0.10,
}

#: 階內微調。⚠ **所有佐證項加總的上限（0.08）刻意小於半個階距（0.10）**，
#: 所以任何組合都不足以跨階——這是「不做加權總分」的**機械保證**，不是靠人記得。
#: `test_bonus_budget_is_structurally_smaller_than_half_a_band` 對常數本身斷言。
_SOLE_SOURCE_BONUS = 0.04
_QUALIFICATION_BONUS: Mapping[str, float] = {
    "designed_in": 0.04, "qualified": 0.02, "qualifying": 0.01,
    "sampling": 0.0, "none": 0.0,
}
_MAX_ADJUSTMENT = 0.08


def structural_score(
    inputs: ScarcityInputs, *, trace_id: str = "ct_structural"
) -> tuple[Score, ComponentTrace] | tuple[None, None]:
    """由已入圖的結構事實算出 Q1。缺 `substitutability` 一律回 `None`（不知道）。"""
    substitutability = inputs.substitutability
    if substitutability is None or substitutability not in _SUBSTITUTABILITY_BAND:
        return None, None
    if not inputs.evidence:
        return None, None          # 沒有 provenance 的分數不得存在（INV-6）

    base = _SUBSTITUTABILITY_BAND[int(substitutability)]
    adjustment = 0.0
    reasons: list[str] = [f"substitutability={substitutability}"]
    if inputs.sole_source:
        adjustment += _SOLE_SOURCE_BONUS
        reasons.append("sole_source")
    qualification = str(inputs.qualification_status or "").lower()
    if qualification in _QUALIFICATION_BONUS:
        adjustment += _QUALIFICATION_BONUS[qualification]
        if _QUALIFICATION_BONUS[qualification]:
            reasons.append(f"qualification={qualification}")
    adjustment = min(adjustment, _MAX_ADJUSTMENT)
    declared = round(min(base + adjustment, 1.0), 4)

    quality = assess_evidence_quality(inputs.evidence)
    effective, downgrade = quality.apply(declared)
    trace = ComponentTrace(
        trace_id=trace_id,
        rule_version=SCARCITY_RULE_VERSION,
        inputs={
            "substitutability": substitutability,
            "sole_source": inputs.sole_source,
            "qualification_status": inputs.qualification_status,
            "dependency_depth": inputs.dependency_depth,
            "band_base": base,
            "adjustment": round(adjustment, 4),
            "evidence_ceiling": quality.ceiling,
        },
        evidence_refs=inputs.evidence,
        note="；".join(reasons) + "｜階內微調上限 0.08 < 半階距 0.10，佐證項不得跨階",
    )
    return Score(declared=declared, effective=round(effective, 4),
                 trace_id=trace_id, downgrade_reason=downgrade), trace


@dataclass(frozen=True, slots=True)
class ContextBuild:
    """`ResearchContext` ＋ 組裝過程中的 deterministic 產物。"""

    context: ResearchContext
    structural: Score | None
    structural_trace: ComponentTrace | None
    evidence_quality: EvidenceQuality
    coverage: Mapping[str, Any]
    notes: tuple[str, ...]


def build_research_context(
    *,
    ticker: Ticker,
    company_id: CompanyId,
    graph_provider: Any,
    fundamentals_provider: Any,
    as_of: date | None = None,
    source_versions: Mapping[str, str] | None = None,
) -> ContextBuild:
    """把 provider 的輸出組成一份 `ResearchContext`。

    ⚠ **`as_of` 直接往下傳。** Engine A 目前會拋 `PointInTimeUnsupported`——
    那是刻意的：組裝層不得替 provider 決定「就用當前資料吧」。
    """
    notes: list[str] = []
    graph: StructuralContext = graph_provider.get_company_structural_context(
        company_id, as_of=as_of)
    rows = [r for r in graph_provider.get_bottlenecks(as_of=as_of)
            if str(r.company_id) == str(company_id)]

    if rows:
        # 取這家公司**最強的一條瓶頸邊**當 Q1 的輸入。
        # ⚠ 不平均、不加總——多條邊不會讓一條弱的邊變強（補償性）。
        best = max(rows, key=lambda r: (r.inputs.substitutability or 0,
                                        bool(r.inputs.sole_source)))
        scarcity = best.inputs
        notes.append(
            f"Q1 取最強的一條邊：{best.relation} → {best.target_id}"
            f"（sub={scarcity.substitutability}）；共 {len(rows)} 條邊，不做平均"
        )
    else:
        scarcity = ScarcityInputs(evidence=graph.evidence)
        notes.append(
            "圖中沒有這家公司的可行動瓶頸邊——可能是 substitutability 未填"
            "（全圖覆蓋僅 15%），不代表它不是瓶頸"
        )

    fundamentals, fund_fresh = fundamentals_provider.fundamentals(ticker, as_of=as_of)
    market, market_fresh = fundamentals_provider.market(ticker, as_of=as_of)
    consensus, consensus_fresh = fundamentals_provider.consensus(ticker, as_of=as_of)
    # 估計修正與股價變動分開的完整 payload（Phase 4）。provider 沒有這個能力時
    # 是 None——與「有序列但算不出修正」不同，兩者在 method 字串裡各有說法。
    revision_fn = getattr(fundamentals_provider, "estimate_revision", None)
    revision = revision_fn(ticker, as_of=as_of) if callable(revision_fn) else None

    valuation = _implied_valuation(market, consensus, notes, revision)

    all_refs: list[EvidenceRef] = []
    for block in (graph.evidence, scarcity.evidence, fundamentals.evidence,
                  market.evidence, consensus.evidence):
        all_refs.extend(block or ())
    selection = select_point_in_time_evidence(_dedupe(all_refs), as_of=as_of)
    if selection.filtered_count:
        notes.append(
            f"as-of 篩掉 {selection.filtered_count} 條證據"
            f"（{selection.reasons()}）——排除但計數，不靜默丟棄"
        )

    score, trace = structural_score(scarcity)
    if score is None:
        notes.append("Q1 無法計算：缺 substitutability 或缺 evidence → None（不是 0）")

    context = ResearchContext(
        ticker=ticker, company_id=company_id, as_of=as_of,
        graph=graph, structural=scarcity, fundamentals=fundamentals,
        market=market, consensus=consensus, valuation=valuation,
        evidence_selection=selection,
        freshness={
            "fundamentals": fund_fresh, "market": market_fresh,
            "consensus": consensus_fresh,
        },
        source_versions=dict(source_versions or {}) | {
            "scarcity_rule": SCARCITY_RULE_VERSION,
        },
    )
    return ContextBuild(
        context=context, structural=score, structural_trace=trace,
        evidence_quality=assess_evidence_quality(selection.kept),
        coverage=dict(getattr(graph_provider, "coverage", dict)() or {}),
        notes=tuple(notes),
    )


def _implied_valuation(
    market: MarketSnapshot,
    consensus: ConsensusSnapshot,
    notes: list[str],
    revision: Mapping[str, Any] | None = None,
) -> ValuationSnapshot:
    """由行情與共識反推市場隱含假設。

    ⚠ **這是 Q4 的原料，不是 Q4 的答案。** 目前只算得出「市場隱含」那一半；
    「本 thesis 認為」那一半是 session 的判斷（variant perception 的操作定義：
    市場隱含 X／本 thesis 認為 Y／催化劑 Z）。
    """
    method_parts: list[str] = []
    implied_growth = None
    if consensus.forward_pe and consensus.trailing_pe:
        if consensus.forward_pe > 0 and consensus.trailing_pe > 0:
            # forward 相對 trailing 的折價＝市場隱含的盈餘成長。
            # ⚠ 粗略 proxy：它假設本益比不變，而那正是要質疑的東西。
            implied_growth = (consensus.trailing_pe / consensus.forward_pe) - 1.0
            method_parts.append("implied_growth=trailing_pe/forward_pe-1（假設倍數不變）")
        else:
            # 負的 forward PE＝分析師預估下一年度仍虧損，比值無意義（POET 現值 −43）。
            # 不擋會算出 −2.4 並被讀成「−240%」——一個看起來像資訊、實際什麼都不是的數字。
            # 與 scripts/alpha_expectation_gap.py 的 `pe_forward_nonpositive` 同一條判準。
            method_parts.append("implied_growth=不可算（forward／trailing PE 非正，比值無意義）")
    if revision:
        # Phase 4 的核心：**估計修正與股價變動分開**。原版取 `pe_forward` 的 30 日
        # 變化，而倍數同時被兩者推動，下游無從分辨（L12）。分開之後才問得出 Q4 的
        # 問題——「分析師改了估計，而股價還沒反映」正是 expectation gap 的形狀。
        method_parts.append(
            f"estimate_revision=forward EPS {revision['eps_change']:+.1%}"
            f" vs 股價 {revision['price_change']:+.1%}"
            f"（{revision['observations']} 個觀測，{revision['from']}→{revision['to']}）"
        )
    elif consensus.forward_pe:
        method_parts.append("estimate_revision=不可得（序列太短、起點為 0 或跨越正負號）")
    if not method_parts:
        notes.append("Q4 原料不足：缺 forward/trailing 倍數，市場隱含假設算不出來")
    return ValuationSnapshot(
        market_implied_growth=implied_growth,
        market_implied_margin=None,      # 需要 segment/margin bridge（Phase 4）
        internal_implied_growth=None,    # ← session 的判斷，不由程式填
        internal_implied_margin=None,
        method="；".join(method_parts) or None,
        evidence=consensus.evidence,
    )


def _dedupe(refs: Sequence[EvidenceRef]) -> tuple[EvidenceRef, ...]:
    seen: dict[str, EvidenceRef] = {}
    for ref in refs:
        seen.setdefault(ref.ref, ref)
    return tuple(seen.values())
