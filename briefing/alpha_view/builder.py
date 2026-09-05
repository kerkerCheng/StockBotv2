"""`build_alpha_investment_view()`——把既有 authority 的輸出**組裝**成 canonical read model。

## 這裡只做五件事：選取、正規化、語意標註、組裝、序列化

- **不重算**：Q1 來自 `alpha.context.structural_score`、Q2–Q5 來自 `session_assessor`、
  瓶頸排序來自 `rank_bottlenecks()`（經 provider）、估值 proxy 來自 `alpha.context`、
  催化劑狀態來自 `shared.catalyst_state.assess_entry`、thesis 到期來自
  `thesis.lifecycle_schedule`。本檔沒有任何一條業務公式。
- **語意標註不是判斷**：`basis` 由**來源路徑**決定（Q1 走 deterministic 規則、Q2–Q5 走
  session、`market_implied_growth` 在 `alpha/context.py` 自己註明是 proxy），不是本檔對
  內容的評價。
- **純函式**：所有輸入由 `sources.py` 取好注入，本檔不開 Neo4j／SQLite／檔案。

## 缺口一律標 `not_modeled`，不用預設值補

internal fundamentals／earnings bridge／numeric expectation gap／expected return／
downside／entry logic 今天 runtime 上**沒有任何程式路徑產生**（`ValuationSnapshot.internal_*`
恆為 `None`、`AlphaSignal` 沒有這些欄位）。這些 section 仍然存在於 view 裡，
好讓下一階段的 Causal Fundamental Model 有明確的插座，但值一律 `None`、status 一律
`not_modeled`——**不得**拿 Q3 分數、分析師目標價或 bull/base 散文冒充。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Sequence

from alpha.causal import CausalPath, CompanyImpact, StructuralEvent
from alpha.context import ContextBuild
from alpha.contracts import AXES, AlphaSignal, EvidenceRef, Score
from alpha.provider import SupplyExposure
from shared.catalyst_state import STATE_LABEL, assess_entry
from thesis.lifecycle_schedule import CATALYST, effective_next_check

from .contracts import (
    CAP_AUTOMATIC_INVALIDATION, CAP_CATALYST_UNLINKED, CAP_FINANCIAL_CAUSAL,
    CAP_NARRATIVE_SCENARIOS, CAP_QUANTITATIVE_SCENARIOS, CAP_STRUCTURAL_CAUSAL,
    CAP_STRUCTURED_DISPROOF, SCHEMA_VERSION, AlphaInvestmentView, CatalystItem,
    CatalystSection, CausalPathSection, CheckpointItem, ConsensusSection, Datum,
    DisproofItem, EarningsBridgeSection, EventItem, EvidenceItem, EvidenceSection,
    EvidenceSelectionCounts, ExpectationGapSection, ExposureItem, FalsificationSection,
    FreshnessItem, FundamentalsSection, IdentitySection, ImpactItem,
    InternalFundamentalsSection, LifecycleFacts, NotModeledSection, PathItem,
    PriceImpliedSection, ScenarioSection, SectionMeta, SignalCompleteness,
    StructuralEdgeItem, StructuralThesisSection, VariantViewSection, missing, not_modeled,
)

# ---------------------------------------------------------------------------
# authority 的邏輯 URI（不是路徑）。改名要連 docs/ARCHITECTURE.md 的 authority map 一起改。
# ---------------------------------------------------------------------------
A_RANK = "engine_a://rank_bottlenecks"
A_GRAPH = "engine_a://graph_research_provider"
A_Q1 = "alpha://context/structural_score"
A_SESSION = "alpha://session_assessor"
A_EVQ = "alpha://evidence_quality"
A_IMPLIED = "alpha://context/implied_valuation"
A_SNAP = "engine_c://financial_snapshots"
A_LEDGER = "engine_c://manual_observations"
A_CHECKLIST = "engine_c://checklist"
A_ESTIMATES = "engine_c://estimates"
A_COVERAGE = "decision_lab://coverage_assessments"
A_THESIS_VP = "decision_lab://cohort_thesis"
A_DECISION = "decision_lab://system_decisions"
A_LIFECYCLE = "decision_lab://probe_lifecycle"
A_THESIS_FILE = "thesis://lifecycle.json"
A_CATALYST_STATE = "shared://catalyst_state.assess_entry"

#: 本圖標的高度集中的固定提醒（`AGENTS.md` Alpha 呈現契約：每次都講，不因一樣而省略）。
CORRELATION_WARNING = (
    "本圖標的高度集中於 AI 光互連：列出 N 檔不等於 N 個獨立機會，全買是同一賭注下 N 次。"
)
JUDGMENT_WARNING = "本 view 內的排序與分數是研究判斷，不是回測或統計勝率；系統不給部位尺寸。"
NEXT_PHASE_NOTE = (
    "下一階段 Causal Fundamental Model 的插座：Graph Evidence → Structural Driver → "
    "Explicit Operating Assumptions → Revenue／Margin Bridge → EPS → Internal Fundamental View "
    "→ Compare with Consensus。落地後這些格由 not_modeled 變成 available，schema 不必重寫。"
)

_SESSION_LEVEL_LABEL = {
    "unknown": "不知道", "weak": "弱", "moderate": "中等", "strong": "強", "very_strong": "很強",
}


@dataclass(frozen=True, slots=True)
class DecisionFacts:
    """Engine D 對這家公司的**公開** cohort 事實切片（由 `sources.py` 取，這裡只讀）。

    ⚠ 刻意沒有任何部位／NAV／尺寸欄位。`AlphaSignal != Position`，read model 也一樣。
    """

    cohort_id: str | None = None
    cohort_count: int | None = None
    selection_rule: str | None = None
    #: Engine D 唯讀查詢回報的時點：`current` 或 `as_of`＋日期。builder 在 as-of 模式下
    #: **只接受標記與 context.as_of 相符的事實**，其餘一律拒收（INV-6）。
    point_in_time_mode: str | None = None
    point_in_time_as_of: str | None = None
    research_status: str | None = None
    rubric_version: str | None = None
    lifecycle_status: str | None = None
    review_due_at: str | None = None
    decision_effective_at: str | None = None
    legacy_weakest_axis: str | None = None
    legacy_axis_levels: Mapping[str, str] | None = None
    catalyst: str | None = None
    disproof: str | None = None
    expiry: str | None = None
    coverage_created_at: str | None = None
    variant_perception: str | None = None
    variant_perception_created_at: str | None = None


# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------

def _refs(refs: Sequence[EvidenceRef]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(r.ref for r in refs))


def _absent(key: str, label: str, reason: str, *, status: str = "missing",
            authority: str | None = None) -> Datum:
    """缺席格。`status` 區分 `missing`（有能力沒資料）與 `not_applicable`
    （這個視角下不該回答，例如 as-of 模式對沒有時點投影的來源）。"""
    return Datum(key=key, label=label, value=None, status=status, basis="none",
                 authority=authority, reason=reason)


AXIS_LABEL: Mapping[str, str] = {
    "structural": "Q1 結構稀缺（確定性規則）",
    "value_capture": "Q2 價值攫取（session 判斷）",
    "earnings_exposure": "Q3 盈餘曝險（session 判斷）",
    "expectation_gap": "Q4 預期落差（session 判斷，ordinal）",
    "catalyst": "Q5 催化劑（session 判斷）",
}


def _q1_datum(build: ContextBuild) -> Datum:
    """Q1 由已入圖事實確定性算出，**不依賴 session**；權威是 `alpha.context.structural_score`。"""
    score = build.structural
    trace = build.structural_trace
    if score is None:
        return missing("structural_score", AXIS_LABEL["structural"],
                       "Q1 無法計算：缺 substitutability 或缺 evidence → None（不是 0）",
                       authority=A_Q1)
    return Datum(
        key="structural_score", label=AXIS_LABEL["structural"],
        value={"declared": score.declared, "effective": score.effective,
               "downgrade_reason": score.downgrade_reason},
        status="available", basis="deterministic", authority=A_Q1,
        method=trace.rule_version if trace else None, unit="ordinal_0_1",
        as_of=build.context.as_of,
        evidence_refs=_refs(trace.evidence_refs) if trace else (),
        reason=trace.note if trace else None,
    )


def _session_score_datum(
    signal: AlphaSignal | None, axis: str, *, signal_reason: str | None, stale: bool,
    judged_on: date | None = None, absent_status: str = "missing",
) -> Datum:
    """Q2–Q5 的一格：session 判斷，`None` 分數＝不知道，不是 0。"""
    label = AXIS_LABEL[axis]
    if signal is None:
        return _absent(f"{axis}_score", label,
                       signal_reason or "尚無 session 判斷（AlphaSignal 未組成）",
                       status=absent_status, authority=A_SESSION)
    score: Score | None = signal.score_for(axis)
    if score is None:
        return missing(f"{axis}_score", label, "session 回答 unknown——不知道，不是 0",
                       authority=A_SESSION)
    trace = signal.model_components.get(score.trace_id)
    inputs = dict(trace.inputs) if trace else {}
    level = str(inputs.get("session_level") or "")
    value: dict[str, Any] = {
        "declared": score.declared, "effective": score.effective,
        "downgrade_reason": score.downgrade_reason,
        "session_level": level or None,
        "session_level_label": _SESSION_LEVEL_LABEL.get(level),
    }
    return Datum(
        key=f"{axis}_score", label=label, value=value,
        status="stale" if stale else "available", basis="session_judgment", authority=A_SESSION,
        method=(trace.rule_version if trace else None), unit="ordinal_0_1",
        as_of=judged_on or signal.as_of, evidence_refs=_refs(trace.evidence_refs) if trace else (),
        reason=(trace.note if trace else None),
    )


def _text_datum(
    key: str, label: str, text: str | None, *, basis: str, authority: str,
    stale: bool, as_of: date | None, missing_reason: str, absent_status: str = "missing",
) -> Datum:
    if not text or not str(text).strip():
        return _absent(key, label, missing_reason, status=absent_status, authority=authority)
    return Datum(key=key, label=label, value=str(text), status="stale" if stale else "available",
                 basis=basis, authority=authority, as_of=as_of)


def _observation(
    key: str, label: str, value: Any, *, authority: str, unit: str | None,
    as_of: date | None, freshness: str | None, evidence_refs: tuple[str, ...],
    method: str | None = None, missing_reason: str = "authority 無此值",
    reason: str | None = None,
) -> Datum:
    if value is None:
        return missing(key, label, missing_reason, authority=authority)
    status = "stale" if freshness == "stale" else "available"
    return Datum(key=key, label=label, value=value, status=status, basis="observation",
                 authority=authority, method=method, unit=unit, as_of=as_of,
                 evidence_refs=evidence_refs, reason=reason)


def _path_item(path: CausalPath) -> PathItem:
    return PathItem(
        nodes=tuple(path.nodes), relations=tuple(path.relations), hops=path.hops,
        confidence=path.confidence.name.lower(), weakest_link=path.weakest_link,
        evidence_refs=_refs(path.evidence),
    )


def _freshness_status(build: ContextBuild, key: str) -> str | None:
    state = build.context.freshness.get(key)
    return state.status if state else None


def _freshness_as_of(build: ContextBuild, key: str) -> date | None:
    state = build.context.freshness.get(key)
    return state.as_of if state else None


# ---------------------------------------------------------------------------
# 主函式
# ---------------------------------------------------------------------------

def build_alpha_investment_view(
    *,
    build: ContextBuild,
    signal: AlphaSignal | None = None,
    signal_reason: str | None = None,
    dependency_paths: Sequence[CausalPath] = (),
    substitution_paths: Sequence[CausalPath] = (),
    supply_exposure: Sequence[SupplyExposure] = (),
    impacts: Sequence[CompanyImpact] = (),
    structural_events: Sequence[StructuralEvent] = (),
    causal_reason: str | None = None,
    ranking_position: Mapping[str, Any] | None = None,
    estimate_revision: Mapping[str, Any] | None = None,
    decision_facts: DecisionFacts | None = None,
    decision_facts_reason: str | None = None,
    catalyst_checkpoints: Sequence[Mapping[str, Any]] = (),
    checkpoint_source: str | None = None,
    thesis_lifecycle: Mapping[str, Any] | None = None,
    checklist: Mapping[str, Any] | None = None,
    identity: Mapping[str, Any] | None = None,
    today: date | None = None,
) -> AlphaInvestmentView:
    """組裝一家公司的 `AlphaInvestmentView`。所有參數都是已取好的既有 authority 輸出。"""
    today = today or date.today()
    context = build.context
    ticker = str(context.ticker)
    company_id = str(context.company_id) if context.company_id else None
    identity = dict(identity or {})

    # as-of 模式：Engine A／C 有時點投影，Decision Store 與 thesis 檔沒有。沒有投影的來源
    # 一律 `not_applicable` 並說明，不拿當前值冒充 T 時刻（INV-6）。builder 自己強制，
    # 不靠 sources 記得不要傳。
    as_of_mode = context.as_of is not None
    as_of_iso = context.as_of.isoformat() if context.as_of else None
    reference_day = context.as_of or today
    pit_reason = (
        f"as-of {as_of_iso} 模式：這個來源沒有時點投影，不以當前值冒充 T 時刻的知識（INV-6）"
        if as_of_mode else None
    )
    decision_refused = False
    if as_of_mode:
        # Decision Store 是 append-only 且帶時間戳，`company_decision_facts(as_of=…)` 能做真正的
        # 歷史過濾——所以允許**帶著相符 as-of 標記**的事實進來；沒有標記或標記不符的一律拒收，
        # 否則呼叫端傳錯就會把當前值混進歷史卡。
        if decision_facts is not None and decision_facts.point_in_time_as_of != as_of_iso:
            decision_refused = True
            decision_facts_reason = (
                f"as-of {as_of_iso} 模式：傳入的 Engine D 事實沒有相符的 as-of 過濾標記"
                f"（point_in_time_as_of={decision_facts.point_in_time_as_of!r}），拒收以免把當前值混進歷史卡（INV-6）"
            )
            decision_facts = None
        elif decision_facts is None and not decision_facts_reason:
            decision_refused = True
            decision_facts_reason = pit_reason
        # thesis/lifecycle.json 與 catalyst_calendar.json 是當前狀態檔，沒有歷史。
        thesis_lifecycle = None
        catalyst_checkpoints = ()
    #: 沒有時點語意的來源在 as-of 下是 not_applicable；authority 回答「T 時刻沒有」則是 missing。
    thesis_absent_status = "not_applicable" if as_of_mode else "missing"
    decision_absent_status = "not_applicable" if (as_of_mode and decision_refused) else "missing"

    # ---- 判斷新鮮度：判斷是對哪一份 context 做的 ---------------------------
    mismatch = None
    if signal is not None:
        mismatch = (signal.metadata or {}).get("context_mismatch")
    signal_stale = bool(mismatch)
    judged_digest = (
        str(mismatch.get("judged_context_digest")) if isinstance(mismatch, Mapping)
        else (signal.research_context_digest if signal else None)
    )
    stale_reason = (
        "判斷是對舊的 ResearchContext 做的（行情／證據已更新，判斷尚未重做）"
        if signal_stale else None
    )
    # 判斷的日期：判斷檔自報的 `_produced_at`（經 compose_signal 進 metadata），沒有才退回
    # `signal.as_of`。⚠ 後者在當前視角下是「今天」——那是 context 的日期，不是判斷的日期。
    judged_on: date | None = None
    if signal is not None:
        judged_on = _as_date((signal.metadata or {}).get("judged_at")) or signal.as_of
    # as-of 模式的 lookahead 防線：判斷寫於 T 之後就是 T 之後的知識，就算標 stale 也不得
    # 出現在歷史卡上（INV-6）。拒用後 Q2–Q5／thesis／情境全部 not_applicable 並說明。
    signal_absent_status = "missing"
    if as_of_mode and signal is not None and judged_on is not None and judged_on > context.as_of:
        signal_reason = (
            f"as-of {as_of_iso} 模式：session 判斷寫於 {judged_on.isoformat()}，晚於 as_of，"
            "屬 lookahead；歷史卡拒用（INV-6）"
        )
        signal = None
        signal_stale = False
        mismatch = None
        judged_digest = None
        stale_reason = None
        judged_on = None
        signal_absent_status = "not_applicable"

    # ---- Evidence index：context ＋ 路徑／事件的引用，去重 -------------------
    evidence_pool: dict[str, EvidenceRef] = {}
    for ref in context.evidence_refs:
        evidence_pool.setdefault(ref.ref, ref)
    for path in (*dependency_paths, *substitution_paths):
        for ref in path.evidence:
            evidence_pool.setdefault(ref.ref, ref)
    for exposure in supply_exposure:
        for ref in exposure.evidence:
            evidence_pool.setdefault(ref.ref, ref)
    for impact in impacts:
        for ref in impact.path.evidence:
            evidence_pool.setdefault(ref.ref, ref)
        if impact.event is not None:
            for ref in impact.event.evidence:
                evidence_pool.setdefault(ref.ref, ref)
    for event in structural_events:
        for ref in event.evidence:
            evidence_pool.setdefault(ref.ref, ref)
    if signal is not None:
        for ref in signal.evidence_refs:
            evidence_pool.setdefault(ref.ref, ref)

    fund_fresh = _freshness_status(build, "fundamentals")
    market_fresh = _freshness_status(build, "market")
    cons_fresh = _freshness_status(build, "consensus")
    snapshot_refs = _refs(context.fundamentals.evidence)
    market_refs = _refs(context.market.evidence)
    consensus_refs = _refs(context.consensus.evidence)

    # =======================================================================
    # A. Identity / State
    # =======================================================================
    data_completeness = tuple(
        Datum(
            key=f"freshness_{name}", label=f"{label} 新鮮度",
            value={"status": state.status, "as_of": state.as_of, "age_days": state.age_days,
                   "reason": state.reason},
            status="available", basis="observation", authority=A_SNAP, as_of=state.as_of,
        )
        for name, label in (("fundamentals", "財務"), ("market", "行情"), ("consensus", "共識"))
        for state in (context.freshness.get(name),)
        if state is not None
    )
    thesis_status = str(thesis_lifecycle.get("status")) if thesis_lifecycle else None
    next_check, next_source, _cp = (
        effective_next_check(thesis_lifecycle, today=today) if thesis_lifecycle
        else (None, None, None)
    )
    lifecycle = LifecycleFacts(
        research_status=decision_facts.research_status if decision_facts else None,
        lifecycle_status=decision_facts.lifecycle_status if decision_facts else None,
        review_due_at=decision_facts.review_due_at if decision_facts else None,
        decision_effective_at=decision_facts.decision_effective_at if decision_facts else None,
        legacy_weakest_axis=decision_facts.legacy_weakest_axis if decision_facts else None,
        legacy_axis_levels=(dict(decision_facts.legacy_axis_levels)
                            if decision_facts and decision_facts.legacy_axis_levels else None),
        cohort_count=decision_facts.cohort_count if decision_facts else None,
        cohort_selection_rule=decision_facts.selection_rule if decision_facts else None,
        decision_facts_as_of=decision_facts.point_in_time_as_of if decision_facts else None,
        thesis_lifecycle_status=thesis_status,
        thesis_next_check=next_check,
        thesis_next_check_source=next_source,
        authority=(A_LIFECYCLE if decision_facts else None),
        reason=(
            (decision_facts_reason or "Engine D 無此公司的 cohort，或本次未讀 Decision Store")
            if decision_facts is None else
            (f"同公司 {decision_facts.cohort_count} 個 cohort，只呈現規則 "
             f"{decision_facts.selection_rule} 選出的那個"
             if (decision_facts.cohort_count or 0) > 1 else None)
        ),
    )
    completeness = SignalCompleteness(
        has_signal=signal is not None,
        is_incomplete=signal.is_incomplete if signal else None,
        known_axes=tuple(signal.known_axes) if signal else (),
        weakest_axis=signal.weakest if signal else None,
        judged_at=judged_on.isoformat() if judged_on else None,
        judged_context_digest=judged_digest,
        current_context_digest=context.digest,
        context_matches=(None if signal is None else not signal_stale),
        reason=(signal_reason if signal is None else stale_reason),
    )
    identity_warnings: list[str] = []
    quote_unit = identity.get("market_quote_unit")
    market_currency = identity.get("market_currency")
    if quote_unit and market_currency and quote_unit != market_currency:
        identity_warnings.append(
            f"報價單位 {quote_unit} ≠ 結算幣別 {market_currency}：以報價單位計的欄位"
            "（price／forward_eps／market_cap）與結算幣別差 100 倍，跨標的比較前必須正規化"
        )
    identity_section = IdentitySection(
        ticker=ticker, company_id=company_id,
        company_label=f"{company_id}（{ticker}）" if company_id else ticker,
        market_currency=market_currency, market_quote_unit=quote_unit,
        execution_venue=identity.get("execution_venue"),
        as_of=context.as_of,
        point_in_time_mode="as_of" if context.as_of else "current",
        generated_on=today,
        research_context_digest=context.digest,
        signal=completeness, data_completeness=data_completeness, lifecycle=lifecycle,
        warnings=tuple(identity_warnings),
    )

    # =======================================================================
    # B. Variant View（thesis／variant view／方向／信心／期間：全部 session 判斷）
    # =======================================================================
    no_signal = signal_reason or "尚無 session 判斷（AlphaSignal 未組成）"
    q1 = _q1_datum(build)
    session_scores = {
        axis: _session_score_datum(signal, axis, signal_reason=signal_reason, stale=signal_stale,
                                   judged_on=judged_on, absent_status=signal_absent_status)
        for axis in AXES if axis != "structural"
    }
    all_scores = tuple(q1 if axis == "structural" else session_scores[axis] for axis in AXES)
    vp_as_of = None
    if decision_facts and decision_facts.variant_perception_created_at:
        vp_as_of = _as_date(decision_facts.variant_perception_created_at)
    variant_section = VariantViewSection(
        meta=SectionMeta(
            status=("stale" if signal_stale else "available") if signal else signal_absent_status,
            basis="session_judgment" if signal else "none",
            authority=A_SESSION if signal else None,
            reason=(stale_reason if signal else no_signal),
            as_of=judged_on,
            freshness=("stale" if signal_stale else "available") if signal else "missing",
            warnings=("thesis／variant view／bull-base-bear 是 session（LLM）判斷，"
                      "不是 deterministic model output；引用皆已解析到 ResearchContext 內的證據",),
        ),
        thesis=_text_datum("thesis", "Thesis", signal.thesis if signal else None,
                           basis="session_judgment", authority=A_SESSION, stale=signal_stale,
                           as_of=judged_on, missing_reason=no_signal,
                           absent_status=signal_absent_status),
        variant_view=_text_datum("variant_view", "Variant perception（市場隱含 X／本 thesis 認為 Y／催化劑 Z）",
                                 signal.variant_view if signal else None,
                                 basis="session_judgment", authority=A_SESSION, stale=signal_stale,
                                 as_of=judged_on, missing_reason=no_signal,
                                 absent_status=signal_absent_status),
        direction=(Datum(key="direction", label="方向", value=signal.direction,
                         status="stale" if signal_stale else "available",
                         basis="session_judgment", authority=A_SESSION, as_of=judged_on)
                   if signal else _absent("direction", "方向", no_signal,
                                          status=signal_absent_status, authority=A_SESSION)),
        confidence=(Datum(key="confidence", label="信心（session 自評）", value=signal.confidence,
                          status="stale" if signal_stale else "available",
                          basis="session_judgment", authority=A_SESSION, unit="confidence_0_1",
                          as_of=judged_on,
                          reason="session 自評的信心（0..1），不是量測的勝率")
                    if signal else _absent("confidence", "信心（session 自評）", no_signal,
                                           status=signal_absent_status, authority=A_SESSION)),
        expected_horizon=_text_datum("expected_horizon", "預期期間",
                                     signal.expected_horizon if signal else None,
                                     basis="session_judgment", authority=A_SESSION,
                                     stale=signal_stale, as_of=judged_on,
                                     missing_reason=no_signal, absent_status=signal_absent_status),
        scores=all_scores,
        risks=tuple(signal.risks) if signal else (),
        decision_store_variant_perception=_text_datum(
            "decision_store_variant_perception", "Decision Store 的 variant perception",
            decision_facts.variant_perception if decision_facts else None,
            basis="session_judgment", authority=A_THESIS_VP, stale=False, as_of=vp_as_of,
            missing_reason=("cohort 從未寫過 variant perception（None＝未寫，現形不隱藏）"
                            if decision_facts else
                            decision_facts_reason or "本次未讀 Decision Store"),
            absent_status=decision_absent_status,
        ),
    )

    # =======================================================================
    # C. Structural Thesis（Q1 ＋ 已入圖事實 ＋ 排序位置）
    # =======================================================================
    scarcity = context.structural
    scarcity_refs = _refs(scarcity.evidence)
    graph_as_of = context.as_of
    scarcity_inputs = tuple(
        _observation(key, label, value, authority=A_RANK, unit=unit, as_of=graph_as_of,
                     freshness=None, evidence_refs=scarcity_refs,
                     method="已經 graph admission gate 核准的邊屬性；provider 取最強的一條邊，不平均",
                     missing_reason="圖上這條邊沒有這個屬性（未填≠否；rank_bottlenecks 自 2026-09-05 起保留三態）")
        for key, label, value, unit in (
            ("substitutability", "替代難度", scarcity.substitutability, "ordinal_1_5"),
            ("sole_source", "獨家供應", scarcity.sole_source, "bool"),
            ("qualification_status", "認證狀態", scarcity.qualification_status, "vocab"),
            ("qualification_lead_time_weeks", "認證前置時間（週）",
             scarcity.qualification_lead_time_weeks, "weeks"),
            ("dependency_depth", "距需求端跳數", scarcity.dependency_depth, "hops"),
            ("demand_anchor", "需求錨點",
             str(scarcity.demand_anchor) if scarcity.demand_anchor else None, "entity_id"),
        )
    )
    ranking_items: list[Datum] = []
    if ranking_position:
        for key, label in (("actionable_rank", "可行動排序名次（rank_bottlenecks rows）"),
                           ("actionable_total", "可行動候選總數")):
            value = ranking_position.get(key)
            ranking_items.append(
                Datum(key=key, label=label, value=value, status="available",
                      basis="deterministic", authority=A_RANK,
                      method="讀 rank_bottlenecks() 的既有順序，本 view 不重排", unit="rank")
                if value is not None else
                missing(key, label, "這家公司不在 rows（可行動排序）內", authority=A_RANK)
            )
    else:
        ranking_items.append(missing("actionable_rank", "可行動排序名次",
                                     "本次未注入排序位置", authority=A_RANK))
    edges = tuple(
        StructuralEdgeItem(
            relation=str(e.get("relation") or ""), target=str(e.get("target") or ""),
            substitutability=e.get("substitutability"), sole_source=e.get("sole_source"),
            qualification_status=e.get("qualification_status"),
            demand_anchor=e.get("demand_anchor"), demand_hops=e.get("demand_hops"),
            evidence_class=e.get("evidence_class"), purpose="actionable",
        ) for e in context.graph.edges
    ) + tuple(
        StructuralEdgeItem(
            relation=str(e.get("relation") or ""), target=str(e.get("target") or ""),
            substitutability=None, sole_source=None, qualification_status=None,
            demand_anchor=None, demand_hops=None, evidence_class=None,
            purpose=str(e.get("purpose") or "structural_only_not_actionable"),
        ) for e in context.graph.counter_paths
    )
    coverage = dict(build.coverage or {})
    caveats: list[str] = []
    if coverage.get("canonical_edges") and coverage.get("edges_with_substitutability") is not None:
        share = coverage.get("substitutability_coverage")
        caveats.append(
            f"substitutability 覆蓋 {coverage['edges_with_substitutability']}/"
            f"{coverage['canonical_edges']}"
            f"（{share:.1%}）——排名必然偏向已被抽取過的邊，沒填的邊是隱形的"
            if isinstance(share, (int, float)) else "substitutability 覆蓋率未知"
        )
    if coverage.get("edges_with_lead_time") is not None:
        caveats.append(f"本排名不含 lead time（有值的邊只有 {coverage['edges_with_lead_time']} 條）")
    caveats.append("同一 chokepoint 的供應商計數反映的是我們研究了幾家，不是世界上有幾家")
    caveats.append("evidence 等級是研究深度的函數，不得單獨當瓶頸性證據")
    evq = build.evidence_quality
    evidence_quality = Datum(
        key="evidence_quality", label="證據品質（整體摘要，L8 獨立性）",
        value={"level": evq.level, "independent_origins": evq.independent_origins,
               "best_tier": evq.best_tier, "total_refs": evq.total_refs, "reason": evq.reason},
        status="available", basis="deterministic", authority=A_EVQ,
        method=f"alpha.evidence_quality.assess_evidence_quality（{evq.scale_version}）",
        reason="整體摘要，不是任何一軸的上限；上限逐軸算",
    )
    if build.structural is not None:
        struct_status, struct_reason = "available", None
    elif context.graph.edges or context.graph.counter_paths:
        struct_status, struct_reason = "insufficient_evidence", "有邊但 Q1 算不出來：" + "；".join(build.notes)
    else:
        struct_status, struct_reason = "missing", "圖中沒有這家公司的可行動瓶頸邊（可能是 substitutability 未填，不代表它不是瓶頸）"
    structural_section = StructuralThesisSection(
        meta=SectionMeta(
            status=struct_status,
            basis="deterministic" if struct_status == "available" else "none",
            authority=A_RANK, reason=struct_reason, as_of=graph_as_of,
            warnings=("結構重要 ≠ 可投資；瓶頸 ≠ 買進訊號。Q1 只是五分之一。",),
        ),
        structural_score=q1, scarcity_inputs=scarcity_inputs, ranking=tuple(ranking_items),
        edges=edges,
        supply_exposure=tuple(
            ExposureItem(direction=x.direction, counterparty=str(x.counterparty_id),
                         relation=x.relation, substitutability=x.substitutability,
                         evidence_refs=_refs(x.evidence))
            for x in supply_exposure
        ),
        substitution_paths=tuple(_path_item(p) for p in substitution_paths),
        evidence_quality=evidence_quality, coverage_caveats=tuple(caveats),
    )

    # =======================================================================
    # D. Causal Path（structural causal model，不是 financial causal model）
    # =======================================================================
    impact_items = tuple(
        ImpactItem(
            event_id=i.event.event_id if i.event else None,
            event_kind=i.event.kind if i.event else None,
            event_direction=i.event.direction if i.event else None,
            subject=str(i.event.subject_id) if i.event else None,
            observed_at=i.event.observed_at if i.event else None,
            impact_direction=i.direction.value, magnitude=i.magnitude.value,
            time_horizon=i.time_horizon.value, confidence=i.confidence.name.lower(),
            path=_path_item(i.path), rationale=i.rationale,
        ) for i in impacts
    )
    event_items = tuple(
        EventItem(event_id=e.event_id, kind=e.kind, subject=str(e.subject_id),
                  direction=e.direction, observed_at=e.observed_at, description=e.description,
                  evidence_refs=_refs(e.evidence))
        for e in structural_events
    )
    has_causal = bool(dependency_paths or substitution_paths or impact_items or event_items)
    causal_section = CausalPathSection(
        meta=SectionMeta(
            status="available" if has_causal else "missing",
            basis="structural_inference" if has_causal else "none",
            authority=A_GRAPH, capability=CAP_STRUCTURAL_CAUSAL,
            reason=(None if has_causal else
                    (causal_reason or "provider 沒有回傳這家公司的依賴／替代路徑或結構事件")),
            as_of=graph_as_of,
            warnings=(
                "這是 structural causal model：structural change → beneficiary／victim → "
                "direction／magnitude／horizon。它不是 financial causal model——"
                "沒有 volume／ASP／utilization／mix → revenue → margin → EPS／FCF 的橋。",
                "多跳結論永遠是 derived，不入圖；confidence 取路徑最弱的一段，不取平均；"
                "二階 magnitude 最高只到 medium。",
            ),
        ),
        dependency_paths=tuple(_path_item(p) for p in dependency_paths),
        substitution_paths=tuple(_path_item(p) for p in substitution_paths),
        impacts_on_company=impact_items, structural_events=event_items,
        financial_causal_model=not_modeled(
            "financial_causal_model", "財務因果模型（operating assumptions → revenue／margin／EPS）",
            "runtime 上不存在。" + NEXT_PHASE_NOTE,
        ),
    )

    # =======================================================================
    # E. Fundamentals（Engine C 觀測；PIT／captured-at／provenance 全保留）
    # =======================================================================
    f = context.fundamentals
    m = context.market
    fund_as_of = _freshness_as_of(build, "fundamentals")
    market_as_of = m.bar_date or _freshness_as_of(build, "market")
    reporting_unit = f"reporting_currency（{market_currency or '未知'}；未正規化）"
    quote_price_unit = f"quote_unit（{quote_unit or '未知'}）"
    fundamentals_items = (
        _observation("price", "價格", m.price, authority=A_SNAP, unit=quote_price_unit,
                     as_of=market_as_of, freshness=market_fresh, evidence_refs=market_refs,
                     method=f"price_kind={m.price_kind or '未知'}；bar_date 是交易日、snapshot_date 是 ETL 日（兩者分開，F-27）",
                     missing_reason="Engine C 無這檔的行情快照"),
        _observation("bar_date", "行情交易日（bar_date）", m.bar_date, authority=A_SNAP,
                     unit="date", as_of=market_as_of, freshness=market_fresh,
                     evidence_refs=market_refs,
                     missing_reason="快照沒有 bar_date（舊列覆蓋不全），不得用 ETL 日冒充"),
        _observation("market_cap", "市值（price × shares，未正規化）", m.market_cap,
                     authority=A_SNAP, unit=f"{quote_price_unit} × shares", as_of=market_as_of,
                     freshness=market_fresh, evidence_refs=market_refs,
                     method="provider 導出：price × shares_outstanding；報價單位≠結算幣別時會差 100 倍",
                     missing_reason="缺 price 或 shares_outstanding"),
        _observation("gross_margin", "毛利率（TTM）", f.gross_margin, authority=A_SNAP,
                     unit="ratio", as_of=fund_as_of, freshness=fund_fresh,
                     evidence_refs=snapshot_refs),
        _observation("operating_margin", "營益率（TTM）", f.operating_margin, authority=A_SNAP,
                     unit="ratio", as_of=fund_as_of, freshness=fund_fresh,
                     evidence_refs=snapshot_refs),
        _observation("revenue_ttm", "營收（TTM）", f.revenue_ttm, authority=A_SNAP,
                     unit=reporting_unit, as_of=fund_as_of, freshness=fund_fresh,
                     evidence_refs=snapshot_refs),
        _observation("free_cash_flow_ttm", "自由現金流（TTM）", f.free_cash_flow_ttm,
                     authority=A_SNAP, unit=reporting_unit, as_of=fund_as_of,
                     freshness=fund_fresh, evidence_refs=snapshot_refs,
                     missing_reason="yfinance 在財報後常暫時清空 FCF；缺席不是 0"),
        _observation("cash_and_equivalents", "現金與約當現金", f.cash_and_equivalents,
                     authority=A_SNAP, unit=reporting_unit, as_of=fund_as_of,
                     freshness=fund_fresh, evidence_refs=snapshot_refs),
        _observation("total_debt", "總負債", f.total_debt, authority=A_SNAP,
                     unit=reporting_unit, as_of=fund_as_of, freshness=fund_fresh,
                     evidence_refs=snapshot_refs),
        _observation("shares_outstanding", "流通股數", f.shares_outstanding, authority=A_SNAP,
                     unit="shares", as_of=fund_as_of, freshness=fund_fresh,
                     evidence_refs=snapshot_refs),
    )
    segment = _observation(
        "segment_revenue_share", "分部營收占比", dict(f.segment_revenue_share) if f.segment_revenue_share else None,
        authority=A_LEDGER, unit="ratio_by_segment", as_of=None, freshness=None,
        evidence_refs=snapshot_refs,
        method="Engine C 人工 ledger（verifiability=mechanical，自年報分部附註逐字讀入）；"
               "⚠ provider 目前只帶 value，不帶該筆觀測的 as_of／source_ref",
        missing_reason="Engine C 人工 ledger 無這檔的分部觀測（None，不是空 dict）",
    )
    checklist_items: list[Datum] = []
    if checklist and checklist.get("engine_c_available"):
        for key, item in (checklist.get("items") or {}).items():
            status = str(item.get("status") or "missing")
            label = str(item.get("label") or key)
            if status in ("ok", "manual_reviewed"):
                value = {k: v for k, v in item.items() if k not in ("label", "status")}
                checklist_items.append(Datum(
                    key=f"checklist_{key}", label=label, value=value or {"status": status},
                    status="available", basis="observation",
                    authority=A_LEDGER if status == "manual_reviewed" else A_CHECKLIST,
                    method="人工填入（manual ledger）" if status == "manual_reviewed" else "由 financial_snapshots 導出",
                ))
            else:
                checklist_items.append(missing(
                    f"checklist_{key}", label,
                    "需人工填入（manual_required）——未知，不是 0" if status == "manual_required"
                    else "Engine C 無資料",
                    authority=A_CHECKLIST,
                ))
        checklist_items.append(Datum(
            key="checklist_gate_pass", label="五項核驗清單是否齊備", value=bool(checklist.get("gate_pass")),
            status="available", basis="deterministic", authority=A_CHECKLIST,
            method="engine_c.checklist.get_checklist：五項皆 ok／manual_reviewed",
        ))
    else:
        checklist_items.append(missing("checklist", "五項財務核驗清單",
                                       (checklist or {}).get("note") or "本次未讀 Engine C checklist",
                                       authority=A_CHECKLIST))
    fund_status = fund_fresh or "missing"
    fundamentals_section = FundamentalsSection(
        meta=SectionMeta(
            status=fund_status if fund_status in ("available", "stale", "missing") else "missing",
            basis="observation" if fund_status in ("available", "stale") else "none",
            authority=A_SNAP, as_of=fund_as_of, freshness=fund_fresh,
            reason=(context.freshness.get("fundamentals").reason
                    if context.freshness.get("fundamentals") else None),
            warnings=("金額欄位以報表幣別計、行情欄位以報價單位計，兩者都未做 FX 正規化，不得跨標的直接比大小。",),
        ),
        items=fundamentals_items, segment_revenue_share=segment, checklist=tuple(checklist_items),
    )

    # =======================================================================
    # F. Consensus（真正存在的只有 next-FY 營收＋倍數＋目標價；標 partial）
    # =======================================================================
    c = context.consensus
    cons_as_of = _freshness_as_of(build, "consensus")
    # ⚠ 刻意不算 target_vs_price：那個比值已由 scripts/alpha_expectation_gap.py 產出，
    # view 只讀 authority，不長第二份算式（審計 2026-09-05 第 5 條）。
    consensus_items = (
        _observation("analyst_count", "分析師目標價家數", c.analyst_count, authority=A_SNAP,
                     unit="count", as_of=cons_as_of, freshness=cons_fresh,
                     evidence_refs=consensus_refs),
        _observation("target_mean", "賣方目標價均值（不是本系統的預期報酬）", c.target_mean,
                     authority=A_SNAP, unit=quote_price_unit, as_of=cons_as_of,
                     freshness=cons_fresh, evidence_refs=consensus_refs,
                     missing_reason="無分析師目標價"),
        _observation("forward_pe", "forward P/E", c.forward_pe, authority=A_SNAP, unit="multiple",
                     as_of=cons_as_of, freshness=cons_fresh, evidence_refs=consensus_refs),
        _observation("trailing_pe", "trailing P/E", c.trailing_pe, authority=A_SNAP,
                     unit="multiple", as_of=cons_as_of, freshness=cons_fresh,
                     evidence_refs=consensus_refs,
                     missing_reason="無 trailing PE——公司目前無正的 trailing EPS（多半在虧損）"),
        _observation("ev_revenue", "EV／營收", c.ev_revenue, authority=A_SNAP, unit="multiple",
                     as_of=cons_as_of, freshness=cons_fresh, evidence_refs=consensus_refs),
        _observation("forward_eps", "forward EPS（導出）", c.forward_eps, authority=A_ESTIMATES,
                     unit=f"{quote_price_unit}／share", as_of=cons_as_of, freshness=cons_fresh,
                     evidence_refs=consensus_refs,
                     method="price / pe_forward（≡ yfinance forwardEps）；以報價單位計，只能當同一標的的時間序列比值用"),
        _observation("revenue_estimate_next_fy", "下一會計年度營收共識（絕對值）",
                     c.revenue_estimate_next_fy, authority=A_SNAP, unit=reporting_unit,
                     as_of=cons_as_of, freshness=cons_fresh, evidence_refs=consensus_refs,
                     method="yfinance revenue_estimate +1y avg；不得跨標的比大小"),
        _observation("revenue_estimate_next_fy_growth", "下一會計年度營收共識成長",
                     c.revenue_estimate_next_fy_growth, authority=A_SNAP, unit="ratio",
                     as_of=cons_as_of, freshness=cons_fresh, evidence_refs=consensus_refs,
                     method="營收成長，與 market_implied_eps_growth（EPS 成長）分母不同，不得相減"),
        _observation("estimate_revision_30d", "forward EPS 30 個觀測修正幅度",
                     c.estimate_revision_30d, authority=A_ESTIMATES, unit="ratio",
                     as_of=cons_as_of, freshness=cons_fresh, evidence_refs=consensus_refs,
                     method="engine_c.estimates.revision_over：同一標的導出 forward EPS 的序列比值",
                     missing_reason="序列太短、起點為 0 或跨越正負號——算不出來不是沒修正"),
    )
    cons_has_snapshot = cons_fresh in ("available", "stale")
    consensus_section = ConsensusSection(
        meta=SectionMeta(
            status=("stale" if cons_fresh == "stale" else "partial") if cons_has_snapshot else "missing",
            basis="observation" if cons_has_snapshot else "none",
            authority=A_SNAP, as_of=cons_as_of, freshness=cons_fresh,
            reason=("Engine C 無這檔的共識快照" if not cons_has_snapshot else
                    "覆蓋只到 next-FY 營收共識、forward／trailing PE、EV/營收、目標價均值與導出 forward EPS"),
            warnings=("這不是 multi-year consensus earnings model：沒有多年度 EPS 共識、沒有目標價高低區間、"
                      "沒有逐位分析師分布；修正歷史只有由 price/pe_forward 導出的序列。",),
        ),
        items=consensus_items,
        coverage_note="partial：next-FY revenue estimate（avg／growth／n）＋ forward／trailing PE ＋ EV/Rev ＋ target mean ＋ derived forward EPS；缺 multi-year EPS、target high/low、per-analyst distribution",
    )

    # =======================================================================
    # G. Price-Implied Expectations（heuristic proxy，不是 reverse DCF）
    # =======================================================================
    v = context.valuation
    implied_reason = None
    if v.market_implied_growth is None:
        if c.trailing_pe is None:
            implied_reason = "pe_trailing_missing：無 trailing PE（多半在虧損），比值不成立"
        elif c.forward_pe is None:
            implied_reason = "pe_forward_missing：無 forward PE"
        elif c.forward_pe <= 0 or c.trailing_pe <= 0:
            implied_reason = "pe_forward_nonpositive：分析師預估下一年度仍虧損，比值無意義"
        else:
            implied_reason = "alpha.context 未算出（原因見 valuation.method）"
    price_implied_items = (
        (Datum(key="market_implied_eps_growth", label="市場隱含 EPS 成長（粗略代理）",
               value=v.market_implied_growth,
               status="stale" if cons_fresh == "stale" else "available",
               basis="heuristic_proxy", authority=A_IMPLIED, unit="ratio", as_of=cons_as_of,
               method=v.method, evidence_refs=_refs(v.evidence),
               reason="trailing_pe/forward_pe − 1，假設倍數不變——那正是要質疑的東西；"
                      "它是 EPS 成長，不是營收成長，不得與共識營收成長相減")
         if v.market_implied_growth is not None else
         Datum(key="market_implied_eps_growth", label="市場隱含 EPS 成長（粗略代理）",
               value=None, status="not_applicable" if implied_reason and "nonpositive" in implied_reason else "missing",
               basis="none", authority=A_IMPLIED, reason=implied_reason)),
        not_modeled("market_implied_margin", "市場隱含利潤率",
                    "需要 segment／margin bridge；alpha.context 恆填 None（不是 0%）"),
        (Datum(key="estimate_revision_vs_price", label="估計修正 vs 股價變動（Q4 原料）",
               value=dict(estimate_revision), status="stale" if cons_fresh == "stale" else "available",
               basis="deterministic", authority=A_ESTIMATES, unit="ratio", as_of=cons_as_of,
               method="engine_c.estimates.revision_over：forward EPS 變動與股價變動分開；estimate_vs_price 正值＝估計跑在股價前面",
               evidence_refs=consensus_refs,
               reason="這是 expectation gap 的**原料**，不是 gap 本身")
         if estimate_revision else
         missing("estimate_revision_vs_price", "估計修正 vs 股價變動（Q4 原料）",
                 "序列太短、起點為 0 或跨越正負號，或本次未取", authority=A_ESTIMATES)),
    )
    has_implied = any(d.is_known for d in price_implied_items)
    price_implied_section = PriceImpliedSection(
        meta=SectionMeta(
            status="partial" if has_implied else "missing",
            basis="heuristic_proxy" if has_implied else "none",
            authority=A_IMPLIED, as_of=cons_as_of, freshness=cons_fresh,
            reason="只有 PE 比值導出的 EPS 成長 proxy；隱含利潤率與 reverse DCF 尚未建模",
            warnings=("method quality＝heuristic／proxy。不得稱為 reverse DCF、不得當成 modeled expectations。",),
        ),
        items=price_implied_items,
        reverse_dcf=not_modeled("reverse_dcf", "Reverse DCF（價格隱含的成長／利潤率／折現率解）",
                                "runtime 上不存在任何 DCF 或反解程式路徑"),
    )

    # =======================================================================
    # H. Internal Fundamental View（not_modeled）
    # =======================================================================
    internal_reason = ("ValuationSnapshot.internal_implied_* 恆為 None、AlphaSignal 無此欄位；"
                       "沒有任何程式路徑產生內部營收／利潤率／EPS／FCF 估計。")
    internal_section = InternalFundamentalsSection(
        meta=SectionMeta(status="not_modeled", basis="none", reason=internal_reason + NEXT_PHASE_NOTE),
        items=tuple(not_modeled(k, l, internal_reason) for k, l in (
            ("internal_revenue", "內部營收估計"), ("internal_gross_margin", "內部毛利率估計"),
            ("internal_operating_margin", "內部營益率估計"), ("internal_eps", "內部 EPS 估計"),
            ("internal_fcf", "內部 FCF 估計"),
        )),
        plug_in_note=NEXT_PHASE_NOTE,
    )

    # =======================================================================
    # I. Earnings Bridge（not_modeled，但列出今天已存在的原料）
    # =======================================================================
    bridge_reason = "structural event → operating assumptions → revenue → margin → EPS 的橋不存在；Q3 分數與敘事不得冒充"
    earnings_bridge_section = EarningsBridgeSection(
        meta=SectionMeta(status="not_modeled", basis="none", reason=bridge_reason),
        steps=tuple(not_modeled(k, l, bridge_reason) for k, l in (
            ("operating_assumptions", "營運假設（volume／ASP／utilization／mix）"),
            ("revenue_impact", "營收影響"), ("margin_impact", "利潤率影響"),
            ("eps_impact", "EPS 影響"), ("fcf_impact", "FCF 影響"),
        )),
        inputs_available=(
            segment,
            Datum(key="structural_events_count", label="可用結構事件數（180 天內）",
                  value=len(event_items), status="available", basis="deterministic",
                  authority=A_GRAPH, unit="count", method="get_structural_changes_since"),
            Datum(key="dependency_paths_count", label="可用依賴路徑數", value=len(dependency_paths),
                  status="available", basis="deterministic", authority=A_GRAPH, unit="count"),
        ),
    )

    # =======================================================================
    # J. Expectation Gap（區分 session 判斷／proxy／尚未建模的數值 gap）
    # =======================================================================
    q4 = session_scores["expectation_gap"]
    gap_proxies = (price_implied_items[2], price_implied_items[0])
    gap_has = q4.is_known or any(d.is_known for d in gap_proxies)
    expectation_gap_section = ExpectationGapSection(
        meta=SectionMeta(
            status=("stale" if signal_stale and q4.is_known else "partial") if gap_has else "missing",
            basis="session_judgment" if q4.is_known else ("heuristic_proxy" if gap_has else "none"),
            authority=A_SESSION if q4.is_known else A_IMPLIED,
            reason=("Q4 是 session 的 ordinal 判斷；數值化的 internal-vs-consensus 與 internal-vs-price-implied 尚未建模"
                    if gap_has else "無 session 判斷且無 proxy 原料"),
            warnings=(
                "Q4 的 ordinal 等級不是 internal EPS − consensus EPS。",
                "market_implied_eps_growth（EPS）與 revenue_estimate_next_fy_growth（營收）分母不同，不得相減成 gap。",
                "estimate_revision_vs_price 是原料：正值只代表估計跑在股價前面，不是可行動的 gap。",
            ),
        ),
        session_judgment=q4, proxies=gap_proxies,
        internal_vs_consensus=not_modeled("internal_vs_consensus", "內部估計 vs 共識（數值）",
                                          "內部估計不存在（見 internal_fundamentals），沒有 fake numeric gap"),
        internal_vs_price_implied=not_modeled("internal_vs_price_implied", "內部估計 vs 價格隱含（數值）",
                                              "內部估計不存在；價格隱含側也只有 proxy"),
    )

    # =======================================================================
    # K. Catalyst（結構化催化劑／檢核點／散文／到期狀態；量化連結未建模）
    # =======================================================================
    q5 = session_scores["catalyst"]
    structured = tuple(
        CatalystItem(kind=cat.kind, description=cat.description, expected_at=cat.expected_at,
                     date_confidence=cat.date_confidence, basis="session_judgment",
                     evidence_refs=_refs(cat.evidence_refs))
        for cat in (signal.catalysts if signal else ())
    )
    checkpoint_items = tuple(
        CheckpointItem(date=cp["date"], what=str(cp.get("what") or ""), decides=str(cp.get("decides") or ""),
                       date_confidence=str(cp.get("date_confidence") or "estimated"),
                       source=checkpoint_source or A_THESIS_FILE)
        for cp in catalyst_checkpoints if cp.get("date")
    )
    watch_state_datum = _absent("watch_state", "到期／催化劑狀態",
                                decision_facts_reason or "本次未讀 Decision Store",
                                status=decision_absent_status, authority=A_CATALYST_STATE)
    expiry_datum = _absent("expiry", "decision 有效期（expiry）",
                           decision_facts_reason or "本次未讀 Decision Store",
                           status=decision_absent_status, authority=A_COVERAGE)
    problems: tuple[str, ...] = ()
    if decision_facts is not None:
        # as-of 模式：以 as_of 當「今天」判到期；檢核點來自沒有歷史的 thesis 檔，已被清空。
        assessed = assess_entry(
            {"company_id": company_id, "ticker": ticker, "catalyst": decision_facts.catalyst,
             "disproof": decision_facts.disproof, "expiry": decision_facts.expiry},
            today=reference_day,
            checkpoints=[{"date": cp.date.isoformat(), "date_confidence": cp.date_confidence}
                         for cp in checkpoint_items],
        )
        problems = tuple(assessed["problems"])
        watch_state_datum = Datum(
            key="watch_state", label="到期／催化劑狀態",
            value={"state": assessed["state"], "label": STATE_LABEL.get(assessed["state"]),
                   "days_to_expiry": assessed["days_to_expiry"],
                   "next_catalyst": assessed["next_catalyst"],
                   "next_catalyst_confidence": assessed["next_catalyst_confidence"]},
            status="available", basis="deterministic", authority=A_CATALYST_STATE,
            method=("shared.catalyst_state.assess_entry（與 scripts/catalyst_watch.py 同一支；只判日期，不解析散文）"
                    + (f"；as-of 模式以 {as_of_iso} 為今天、無檢核點" if as_of_mode else "")),
            as_of=reference_day,
            reason="它是條件檢查不是訊號：只回答「你寫下的到期日今天到了沒」",
        )
        expiry_datum = _observation("expiry", "decision 有效期（expiry）", decision_facts.expiry,
                                    authority=A_COVERAGE, unit="timestamp",
                                    as_of=_as_date(decision_facts.coverage_created_at), freshness=None,
                                    evidence_refs=(), missing_reason="coverage assessment 無 expiry")
    narrative_catalyst = _text_datum(
        "narrative_catalyst", "Decision Store 的 catalyst 原文（散文）",
        decision_facts.catalyst if decision_facts else None, basis="narrative", authority=A_COVERAGE,
        stale=False, as_of=_as_date(decision_facts.coverage_created_at) if decision_facts else None,
        missing_reason=("cohort 的 catalyst 未填（L7：expiry 因此是沒有內容的鬧鐘）" if decision_facts
                        else decision_facts_reason or "本次未讀 Decision Store"),
        absent_status=decision_absent_status,
    )
    has_catalyst = bool(structured or checkpoint_items or narrative_catalyst.is_known or q5.is_known)
    catalyst_section = CatalystSection(
        meta=SectionMeta(
            status="partial" if has_catalyst else "missing",
            # 檢核點是人手填進 thesis JSON 的結構化紀錄（含 estimated 標記），是 observation
            # 不是 deterministic；deterministic 的是 assess_entry 算出來的 watch_state。
            basis=("session_judgment" if structured or q5.is_known else
                   "observation" if checkpoint_items else
                   "narrative" if narrative_catalyst.is_known else "none"),
            authority=A_SESSION if structured else (checkpoint_source or A_COVERAGE),
            capability=CAP_CATALYST_UNLINKED,
            reason=("催化劑有結構化日期與狀態，但尚未量化連結到盈餘／重定價（partial capability）"
                    if has_catalyst else "沒有任何來源提供催化劑"),
            as_of=reference_day,
            warnings=("推估（estimated）日期照樣排程但必須標明；散文裡的日期不猜。",),
        ),
        catalyst_score=q5, structured=structured, checkpoints=checkpoint_items,
        narrative=narrative_catalyst, watch_state=watch_state_datum, expiry=expiry_datum,
        problems=problems,
        quantitative_link=not_modeled("quantitative_link", "催化劑 → 盈餘／重定價的量化連結",
                                      "runtime 只有日期、kind 與散文；沒有「這個事件會讓 EPS／倍數變多少」"),
    )

    # =======================================================================
    # L. Falsification（結構化條件＋到期監看；自動失效引擎未建模）
    # =======================================================================
    conditions = tuple(
        DisproofItem(condition=d.condition, check_frequency=d.check_frequency,
                     action_within_48h=d.action_within_48h, basis="session_judgment",
                     evidence_refs=_refs(d.evidence_refs))
        for d in (signal.disproof_conditions if signal else ())
    )
    narrative_disproof = _text_datum(
        "narrative_disproof", "Decision Store 的 disproof 原文（散文）",
        decision_facts.disproof if decision_facts else None, basis="narrative", authority=A_COVERAGE,
        stale=False, as_of=_as_date(decision_facts.coverage_created_at) if decision_facts else None,
        missing_reason=("cohort 的 disproof 未填（L7：沒有證偽條件的警報永遠不會響）" if decision_facts
                        else decision_facts_reason or "本次未讀 Decision Store"),
        absent_status=decision_absent_status,
    )
    thesis_status_datum = (
        Datum(key="thesis_lifecycle_status", label="thesis lifecycle 狀態", value={
                  "status": thesis_status, "next_check": next_check,
                  "next_check_source": next_source,
                  "next_check_is_catalyst": next_source == CATALYST},
              # `status` 是人在 lifecycle.json 手動維護的紀錄（observation）；
              # 只有 next_check 是 lifecycle_schedule 算出來的，寫在 method 裡。
              status="available", basis="observation", authority=A_THESIS_FILE,
              method="status 由人維護於 thesis/lifecycle.json；next_check 由 "
                     "thesis.lifecycle_schedule.effective_next_check 算出（cadence 與催化劑取較早者）",
              as_of=reference_day)
        if thesis_lifecycle else
        _absent("thesis_lifecycle_status", "thesis lifecycle 狀態",
                pit_reason or "這檔沒有 lane memo thesis（thesis/lifecycle.json 只涵蓋有 memo 的 thesis）",
                status=thesis_absent_status, authority=A_THESIS_FILE)
    )
    has_falsification = bool(conditions or narrative_disproof.is_known)
    falsification_section = FalsificationSection(
        meta=SectionMeta(
            status=("stale" if signal_stale and conditions else "available") if has_falsification else "missing",
            basis="session_judgment" if conditions else ("narrative" if narrative_disproof.is_known else "none"),
            authority=A_SESSION if conditions else A_COVERAGE,
            capability=CAP_STRUCTURED_DISPROOF,
            reason=(None if has_falsification else "沒有任何 disproof 條件——L7 要求每條 thesis 必帶"),
            warnings=("L7 三件套（條件／核查頻率／48 小時動作）由 alpha.contracts.DisproofCondition 強制；"
                      "runtime 只監看 expiry 與催化劑日期，不會自動判定條件是否已被觸發。",),
        ),
        conditions=conditions, narrative_disproof=narrative_disproof, thesis_status=thesis_status_datum,
        expiry_watch=watch_state_datum,
        automatic_invalidation=not_modeled(
            "automatic_invalidation", "自動 thesis 失效引擎（條件觸發偵測）",
            "不存在：條件是結構化文字，觸發與否仍由人在核查頻率時判讀（capability＝" + CAP_STRUCTURED_DISPROOF + "，非 " + CAP_AUTOMATIC_INVALIDATION + "）",
        ),
    )

    # =======================================================================
    # M. Scenario（narrative，不是 quantitative scenario model）
    # =======================================================================
    def _scenario(key: str, label: str, text: str | None) -> Datum:
        return _text_datum(key, label, text, basis="narrative", authority=A_SESSION,
                           stale=signal_stale, as_of=judged_on, missing_reason=no_signal,
                           absent_status=signal_absent_status)

    scenario_section = ScenarioSection(
        meta=SectionMeta(
            status=("stale" if signal_stale else "available") if signal else signal_absent_status,
            basis="narrative" if signal else "none", authority=A_SESSION if signal else None,
            capability=CAP_NARRATIVE_SCENARIOS, as_of=judged_on,
            reason=("bull／base／bear 是 session 寫的散文，沒有機率、沒有目標估值" if signal else no_signal),
            warnings=(f"scenario_type={CAP_NARRATIVE_SCENARIOS}，不是 {CAP_QUANTITATIVE_SCENARIOS}。",),
        ),
        scenario_type=CAP_NARRATIVE_SCENARIOS,
        bull=_scenario("bull_case", "Bull case（散文）", signal.bull_case if signal else None),
        base=_scenario("base_case", "Base case（散文）", signal.base_case if signal else None),
        bear=_scenario("bear_case", "Bear case（散文）", signal.bear_case if signal else None),
        probabilities=not_modeled("scenario_probabilities", "情境機率", "沒有任何機率加權"),
        target_valuation=not_modeled("target_valuation", "目標估值", "沒有任何目標價／目標倍數模型；賣方目標價住 consensus，不是這一格"),
    )

    # =======================================================================
    # N. Expected return / Downside / Entry logic（全部 not_modeled）
    # =======================================================================
    def _not_modeled_section(reason: str, items: Sequence[tuple[str, str]], confusions: Sequence[str]) -> NotModeledSection:
        return NotModeledSection(
            meta=SectionMeta(status="not_modeled", basis="none", reason=reason),
            items=tuple(not_modeled(k, l, reason) for k, l in items),
            not_to_be_confused_with=tuple(confusions),
        )

    expected_return_section = _not_modeled_section(
        "系統不產生預期報酬：沒有內部估計、沒有目標估值、沒有機率加權。等權重報酬追蹤（outcome）是事後量測，不是預期。",
        (("expected_return", "預期報酬"), ("probability_weighted_return", "機率加權報酬"),
         ("target_valuation_upside", "目標估值上檔")),
        ("consensus.target_mean 是賣方目標價，不是 StockBot 預期報酬；"
         "目標價 vs 現價的比值住 scripts/alpha_expectation_gap.py",
         "price_implied_expectations.market_implied_eps_growth 是市場已定價的成長，不是我們預期的報酬"),
    )
    downside_section = _not_modeled_section(
        "系統不產生下檔估計：沒有 bear case 的數值、沒有最大回撤模型。",
        (("downside", "下檔幅度"), ("max_drawdown_estimate", "最大回撤估計")),
        ("scenarios.bear 是散文，不是下檔數字", "falsification 的條件是出場觸發，不是下檔幅度"),
    )
    entry_section = _not_modeled_section(
        "系統不產生 required return／entry price／wait-for-price threshold／actionable-now；買多少、什麼時候買由使用者判斷。",
        (("required_return", "要求報酬"), ("entry_price", "進場價"),
         ("wait_for_price_threshold", "等待價位門檻"), ("actionable_now", "現在可行動")),
        ("structural_thesis.ranking 是 rank_bottlenecks 的研究注意力順序，不是 opportunity ranking",
         "decision_lab today 的 attention（MONITOR／REVIEW）是「今天要不要看」，不是「該不該買」；本 view 不重算它"),
    )

    # =======================================================================
    # O. Evidence / Provenance
    # =======================================================================
    selection = context.evidence_selection
    evidence_section = EvidenceSection(
        meta=SectionMeta(
            status="available" if evidence_pool else "missing",
            basis="observation" if evidence_pool else "none", authority=A_GRAPH,
            reason=(None if evidence_pool else "沒有任何 EvidenceRef"),
            warnings=("published_at＝世界知道的時間；retrieved_at＝我們抓到的時間；recorded_at＝寫進系統的時間。"
                      "as-of 模式下未標日期的證據一律排除並計數，不當成 T 之前。",),
        ),
        index=tuple(
            EvidenceItem(ref=r.ref, kind=r.kind, source_doc_id=r.source_doc_id,
                         origin_entity=r.origin_entity, url=r.url, quote=r.quote,
                         published_at=r.published_at, retrieved_at=r.retrieved_at,
                         recorded_at=r.recorded_at, evidence_tier=r.evidence_tier,
                         evidence_class=r.evidence_class, confidence=r.confidence,
                         corroborating_origins=tuple(r.corroborating_origins))
            for r in evidence_pool.values()
        ),
        selection=EvidenceSelectionCounts(
            input_count=selection.input_count, accepted_count=selection.accepted_count,
            filtered_count=selection.filtered_count, reasons=dict(selection.reasons()),
        ),
        quality=evidence_quality,
    )

    # ---- freshness 總表 ----------------------------------------------------
    freshness_items = [
        FreshnessItem(source=name, status=state.status, as_of=state.as_of,
                      age_days=state.age_days, reason=state.reason)
        for name, state in context.freshness.items()
    ]
    dated = [r.published_at for r in evidence_pool.values() if r.published_at]
    if dated:
        newest = max(dated)
        freshness_items.append(FreshnessItem(
            source="graph_evidence_latest_published", status="available", as_of=newest,
            age_days=float((today - newest).days),
            reason="最新一份引用文件的發表日；圖本身沒有「最後載入」時間"))
    else:
        freshness_items.append(FreshnessItem(source="graph_evidence_latest_published", status="missing",
                                             as_of=None, age_days=None, reason="沒有任何帶 published_at 的引用"))
    freshness_items.append(FreshnessItem(
        source="session_judgment",
        status=("stale" if signal_stale else "available") if signal else "missing",
        as_of=judged_on,
        age_days=float((today - judged_on).days) if judged_on else None,
        reason=stale_reason if signal else no_signal))
    dec_as_of = _as_date(decision_facts.coverage_created_at) if decision_facts else None
    freshness_items.append(FreshnessItem(
        source="decision_store_coverage",
        status="available" if decision_facts and dec_as_of else "missing",
        as_of=dec_as_of, age_days=float((reference_day - dec_as_of).days) if dec_as_of else None,
        reason=(None if dec_as_of else (decision_facts_reason or "無 coverage assessment"))
        if not (dec_as_of and as_of_mode) else f"距 as-of {as_of_iso} 的天數；事實已依 as_of 歷史過濾"))

    warnings = [JUDGMENT_WARNING, CORRELATION_WARNING]
    if as_of_mode:
        warnings.append(
            f"as-of 視角（{as_of_iso}）：Engine A 投影、Engine C 時序、Decision Store 事實皆已依 as_of "
            "歷史過濾（cohort／decision／coverage／lifecycle 事件／variant perception 的時間戳）；"
            "thesis/*.json 與檢核點沒有歷史，一律 not_applicable；到期狀態以 as_of 為今天判定")
    if signal_stale:
        warnings.append("session 判斷過期：" + str(stale_reason))
    if signal is None:
        warnings.append("尚無 session 判斷：Q2–Q5、thesis、variant view、情境、disproof 條件皆缺；"
                        "跑 `python -m alpha research " + ticker + " -o packet.json` 產研究包後由 session 判斷")
    warnings.extend(identity_warnings)
    if problems:
        warnings.append("Decision Store 的 catalyst／disproof／expiry 設定不完整：" + "；".join(problems))

    return AlphaInvestmentView(
        schema_version=SCHEMA_VERSION,
        identity=identity_section, variant_view=variant_section,
        structural_thesis=structural_section, causal_paths=causal_section,
        fundamentals=fundamentals_section, consensus=consensus_section,
        price_implied_expectations=price_implied_section,
        internal_fundamentals=internal_section, earnings_bridge=earnings_bridge_section,
        expectation_gap=expectation_gap_section, catalysts=catalyst_section,
        falsification=falsification_section, scenarios=scenario_section,
        expected_return=expected_return_section, downside=downside_section,
        entry_logic=entry_section, evidence=evidence_section,
        freshness=tuple(freshness_items), warnings=tuple(warnings),
    )


def _as_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Daily Brief 用的精簡摘要（純選取，不重算）
# ---------------------------------------------------------------------------

def compact_card(view: AlphaInvestmentView) -> dict[str, Any]:
    """每檔一列的摘要，給 Daily Brief 首屏之後的「Alpha Card 摘要」用。

    ⚠ 只做選取：所有值直接取自 view 的 Datum；缺席就帶 reason，不填 0。
    """
    def _val(d: Datum) -> Any:
        return d.value if d.is_known else None

    q = {d.key.removesuffix("_score"): _score_summary(d) for d in view.variant_view.scores}
    implied = next(d for d in view.price_implied_expectations.items
                   if d.key == "market_implied_eps_growth")
    cons_growth = next(d for d in view.consensus.items if d.key == "revenue_estimate_next_fy_growth")
    analysts = next(d for d in view.consensus.items if d.key == "analyst_count")
    watch = view.catalysts.watch_state
    next_cp = view.catalysts.checkpoints[0] if view.catalysts.checkpoints else None
    not_modeled_keys = [name for name, cap in view.capability_map().items() if cap["status"] == "not_modeled"]
    return {
        "ticker": view.identity.ticker,
        "company_id": view.identity.company_id,
        "company_label": view.identity.company_label,
        "as_of": view.identity.as_of.isoformat() if view.identity.as_of else None,
        "scores": q,
        "signal": {
            "has_signal": view.identity.signal.has_signal,
            "context_matches": view.identity.signal.context_matches,
            "weakest_axis": view.identity.signal.weakest_axis,
            "reason": view.identity.signal.reason,
        },
        "market_implied_eps_growth": {
            "value": _val(implied), "status": implied.status, "basis": implied.basis,
            "reason": implied.reason if not implied.is_known else None,
        },
        "consensus_revenue_growth": {
            "value": _val(cons_growth), "status": cons_growth.status, "basis": cons_growth.basis,
            "analyst_count": _val(analysts),
        },
        "catalyst": {
            "state": (watch.value or {}).get("state") if watch.is_known else None,
            "state_label": (watch.value or {}).get("label") if watch.is_known else None,
            "days_to_expiry": (watch.value or {}).get("days_to_expiry") if watch.is_known else None,
            "next_checkpoint": next_cp.date.isoformat() if next_cp else None,
            "next_checkpoint_confidence": next_cp.date_confidence if next_cp else None,
            # None＝不知道（沒有 session 判斷／as-of 模式沒有投影），不是 0
            "structured_count": (len(view.catalysts.structured)
                                 if view.identity.signal.has_signal else None),
            "checkpoint_count": (len(view.catalysts.checkpoints)
                                 if view.identity.point_in_time_mode == "current" else None),
            "reason": None if watch.is_known else watch.reason,
        },
        "disproof": {
            "condition_count": (len(view.falsification.conditions)
                                if view.identity.signal.has_signal else None),
            "narrative_present": view.falsification.narrative_disproof.is_known,
            "problems": list(view.catalysts.problems),
        },
        "research_status": view.identity.lifecycle.research_status,
        "point_in_time_mode": view.identity.point_in_time_mode,
        "not_modeled": not_modeled_keys,
        "warnings": list(view.warnings),
    }


def _score_summary(datum: Datum) -> dict[str, Any]:
    value = datum.value if datum.is_known and isinstance(datum.value, dict) else {}
    return {"status": datum.status, "basis": datum.basis,
            "effective": value.get("effective"),
            "session_level": value.get("session_level"),
            "reason": None if datum.is_known else datum.reason}


__all__ = ["DecisionFacts", "build_alpha_investment_view", "compact_card",
           "CORRELATION_WARNING", "JUDGMENT_WARNING", "NEXT_PHASE_NOTE"]
