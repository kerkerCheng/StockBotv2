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

downside／probability-weighted expected return／total return 今天 runtime 上**沒有任何程式路徑產生**。
這些格仍然存在於 view 裡，好讓下一階段有明確的插座，但值一律 `None`、status 一律 `not_modeled`——
**不得**拿 Q3 分數、分析師目標價、fair value gap、implied return 或 bull/base 散文冒充。
internal fundamentals／earnings bridge／numeric gap（2026-09-05）、valuation（2026-09-06 Step 1）、
base-case implied return（2026-09-06 Step 2）與 entry logic（2026-09-06 Step 3）**有能力了**：沒資料是
`missing`，不再是 `not_modeled`——entry logic 沒有判準時的 `missing` 理由明寫「缺的是投資門檻判斷」。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Sequence

from alpha.causal import CausalPath, CompanyImpact, StructuralEvent
from alpha.context import ContextBuild
from alpha.contracts import AXES, AlphaSignal, EvidenceRef, Score
from alpha.entry.contracts import EntryAssessmentResult, EntryCriterion
from alpha.fundamental.contracts import (
    OPINION_BEARING_DRIVERS, FundamentalModelResult, OperatingAssumption,
)
from briefing.analyst_view.contracts import PLAIN_STANCE
from alpha.implied_return.attribution import attribution_payload
from alpha.implied_return.contracts import HorizonAssumption, ImpliedReturnResult
from alpha.provider import SupplyExposure
from alpha.refresh import (
    CONTEXT_DIGEST, CURRENT, INVALIDATED, MISSING, RECALCULATE, REVIEW_REQUIRED, STALE, SUPERSEDED,
    THESIS_ARTIFACT_ID, AffectedArtifact, ChangeEvent, MetricObservation, artifacts_from_context,
    artifacts_from_entry, artifacts_from_implied_return, artifacts_from_model, artifacts_from_signal,
    artifacts_from_valuation, build_instant, resolve_refresh,
)
from alpha.valuation.contracts import ValuationAssumption, ValuationResult
from shared.catalyst_state import STATE_LABEL, assess_entry
from thesis.lifecycle_schedule import CATALYST, effective_next_check

from .contracts import (
    BASIS_LABEL, CAP_ANALYTICAL_ENTRY_THRESHOLD, CAP_AUTOMATIC_INVALIDATION, CAP_BASE_CASE_IMPLIED_RETURN,
    CAP_CATALYST_UNLINKED,
    CAP_DEPENDENCY_IMPACT, CAP_DETERMINISTIC_FAIR_VALUE, CAP_FINANCIAL_CAUSAL,
    CAP_NARRATIVE_SCENARIOS, CAP_NUMERIC_EXPECTATION_GAP, CAP_QUANTITATIVE_SCENARIOS,
    CAP_STRUCTURAL_CAUSAL,
    CAP_STRUCTURED_DISPROOF, SCHEMA_VERSION, STATUS_LABEL, AlphaInvestmentView, CatalystItem,
    CatalystSection, CausalPathSection, ChangeItem, CheckpointItem, ConsensusSection, Datum,
    DisproofItem, EarningsBridgeSection, EntryLogicSection, EventItem, EvidenceItem, EvidenceSection,
    EvidenceSelectionCounts, ExpectationGapSection, ExposureItem, FalsificationSection,
    FreshnessItem, FundamentalsSection, IdentitySection, ImpactItem, ImpliedReturnSection,
    InternalFundamentalsSection, LifecycleFacts, NotModeledSection, PathItem,
    PriceImpliedSection, RefreshItem, RefreshStatusSection, ScenarioSection, SectionMeta,
    SignalCompleteness, StructuralEdgeItem, StructuralThesisSection, ValuationSection, VariantViewSection,
    missing, not_modeled,
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
# Causal Fundamental Model（Phase 2，2026-09-05）：假設、橋、比較各自是 authority，read model 只選取。
A_ASSUMPTIONS = "alpha://fundamental/assumptions"
A_REFRESH = "alpha://refresh/resolver"

#: refresh state → Datum status。`current`／`recalculate` 在 read model 裡都是「有、可用」（確定性成果每次
#: build 都重算）；`stale`／`review_required`／`invalidated` 各自是一個 status（L12：不壓成一個 stale）。
_REFRESH_TO_STATUS: Mapping[str, str] = {
    CURRENT: "available", RECALCULATE: "available", STALE: "stale",
    REVIEW_REQUIRED: "review_required", INVALIDATED: "invalidated",
}


def _refresh_status(artifact: AffectedArtifact | None, *, fallback: str = "available") -> str:
    if artifact is None or artifact.state in (SUPERSEDED, MISSING):
        return fallback
    return _REFRESH_TO_STATUS[artifact.state]


def _refresh_deps(artifact: AffectedArtifact | None) -> dict[str, Any]:
    if artifact is None:
        return {"refresh_state": None}
    return {"refresh_state": artifact.state, "refresh_reasons": list(artifact.reasons),
            "refresh_changed_refs": list(artifact.changed_refs),
            "refresh_required_action": artifact.required_action,
            "refresh_propagated_from": list(artifact.propagated_from)}
A_BRIDGE = "alpha://fundamental/bridge"
A_COMPARE = "alpha://fundamental/compare"
A_CONSENSUS_FY = "engine_c://consensus_estimates"

#: 本圖標的高度集中的固定提醒（`AGENTS.md` Alpha 呈現契約：每次都講，不因一樣而省略）。
#: ⚠ 措辭在 2026-09-07 Coverage Pilot 修正過：舊句「本圖標的高度集中於 AI 光互連：列出 N 檔
#: 不等於 N 個獨立機會」是**無條件**掛在每一檔的單檔 view 上的，於是它對 LYC.AX（稀土）與
#: 6324.T（機器人減速機）變成一句假話——這兩檔不在那個群裡。要按產業條件化就得有一份
#: 「這檔屬於哪個群」的分類，而系統**沒有**那個 SSOT，在這裡自己猜一份正是 L16 記過的形狀。
#: 因此改成把主詞明確放回「這份圖的組成」，讓它對任何一檔都為真，且不對本檔的產業下斷言。
CORRELATION_WARNING = (
    "相關性：本圖收錄的標的高度集中於 AI 光互連。把本檔與圖中其他標的並列時，"
    "列出 N 檔不等於 N 個獨立機會，全買可能是同一賭注下 N 次。"
    "⚠ 這是對**這份圖的組成**的提醒，不是對本檔所屬產業的斷言。"
)
JUDGMENT_WARNING = "本 view 內的排序與分數是研究判斷，不是回測或統計勝率；系統不給部位尺寸。"
NEXT_PHASE_NOTE = (
    "Causal Fundamental Model（alpha/fundamental，2026-09-05 落地）：Graph Evidence → Explicit "
    "Operating Assumptions（private ledger，session 明示）→ deterministic Revenue／Margin Bridge → "
    "Internal Fundamental View → Same-period Consensus（Engine C consensus_estimates）→ Numeric "
    "Expectation Gap。沒有假設或沒有基期觀測的公司是 missing（有能力、沒資料）；"
    "估值（Step 1，2026-09-06）已落地於 valuation section（internal EPS × explicit target multiple）；"
    "base-case 隱含報酬（Step 2，2026-09-06）已落地於 implied_return section（現價＋fair value 時點語意＋明示 horizon）；"
    "進場邏輯（Step 3，2026-09-06）已落地於 entry_logic section（implied return＋明示的要求報酬判準→門檻價；"
    "不是 buy／sell）；機率加權期望報酬／總報酬／下檔仍 not_modeled。"
)
FUNDAMENTAL_EPISTEMIC_WARNING = (
    "每個內部數字的 calculation 是 deterministic，但輸入假設是 session 判斷／heuristic——"
    "看各格 dependencies.input_dependency；不得把公式算出來的數讀成事實。"
)

_INTERNAL_METRIC_LABELS: tuple[tuple[str, str, str], ...] = (
    ("revenue", "內部營收估計", "currency"),
    ("operating_margin", "內部營益率估計", "ratio"),
    ("operating_income", "內部營業利益估計", "currency"),
    ("net_income", "內部歸屬母公司淨利估計", "currency"),
    ("eps", "內部稀釋 EPS 估計", "currency_per_share"),
)
_COMPARISON_LABELS: Mapping[str, str] = {
    "revenue": "內部營收 vs 共識營收（同期）",
    "eps": "內部 EPS vs 共識 EPS（同期同口徑）",
    "operating_margin": "內部營益率 vs 共識營益率",
}
#: ⚠ 這張表必須涵蓋 `alpha.fundamental.contracts.COMPARISON_STATUSES` 的每一個值——它是直接
#: 索引（不是 `.get`），漏一個就是整個 fundamental section 在那檔標的上爆掉。
#: `tests/test_coverage_pilot_generalization.py` 斷言兩者一致（L16：字彙有 SSOT 就不要在下游自己記）。
_COMPARISON_STATUS_TO_DATUM: Mapping[str, str] = {
    "comparable": "available", "internal_missing": "missing", "consensus_missing": "missing",
    "incompatible_period": "not_applicable", "incompatible_basis": "not_applicable",
    "incompatible_unit": "not_applicable", "unreconciled_base": "not_applicable",
}
_CONSENSUS_METRIC_LABEL: Mapping[str, str] = {"eps": "EPS", "revenue": "營收"}


def _reverse_datum(reverse: Any, reason: str | None, *, reference_day: date) -> Datum:
    """Reverse Bridge → 一格 Datum。**照抄**，不重算、不排序、不挑掉解不出來的那些（INV-3）。"""
    if reverse is None:
        return missing("reverse_bridge", "現價隱含的營運假設",
                       reason or "本次未執行 reverse bridge", authority=A_COMPARE)
    payload = {
        "market_implied_eps": reverse.market_implied_eps,
        "our_eps": reverse.our_eps,
        "consensus_eps": reverse.consensus_eps,
        "target_multiple": reverse.target_multiple,
        "current_price": reverse.current_price,
        "eps_gap": reverse.eps_gap,
        "solutions": [
            {"driver": s.driver, "scope": s.scope, "unit": s.unit, "our_value": s.our_value,
             "implied_value": s.implied_value, "gap": s.gap, "status": s.status,
             "reason": s.reason, "assumption_id": s.assumption_id}
            for s in reverse.solutions
        ],
    }
    if reverse.status == "missing":
        return Datum(key="reverse_bridge", label="現價隱含的營運假設", value=None,
                     status="missing", basis="none", authority=A_COMPARE,
                     reason=reverse.reason, as_of=reference_day)
    return Datum(
        key="reverse_bridge", label="現價隱含的營運假設", value=payload,
        status=("available" if reverse.status == "available" else "partial"),
        basis="deterministic", authority=A_COMPARE, as_of=reference_day,
        method=reverse.method, reason=reverse.reason,
    )


@dataclass(frozen=True, slots=True)
class _FundamentalParts:
    """`_fundamental_parts()` 的產物：模型輸出被**選取**成各 section 要用的 Datum。"""

    internal_section: InternalFundamentalsSection
    bridge_meta: SectionMeta
    bridge_steps: tuple[Datum, ...]
    bridge_assumptions: tuple[Datum, ...]
    bridge_sensitivities: tuple[Datum, ...]
    bridge_selection: EvidenceSelectionCounts | None
    bridge_period: str | None
    comparisons: tuple[Datum, ...]
    internal_vs_consensus: Datum
    #: **不放進 comparisons**：它不是一筆「內部 vs 共識」的數值比較，混進去會讓
    #: 「所有比較都缺席」這種斷言被一格永遠 available 的東西破壞（L12：一個集合兩種語意）。
    opinion_stance: Datum
    financial_causal: Datum
    fiscal_items: tuple[Datum, ...]
    has_numeric_gap: bool
    warnings: tuple[str, ...]


def _fundamental_parts(
    model: FundamentalModelResult | None, reason: str | None, *,
    reference_day: date, reporting_unit: str,
    refresh: Mapping[str, AffectedArtifact] | None = None,
) -> _FundamentalParts:
    """把 `FundamentalModelResult` 選取成 Datum。**不算任何數字**——值、公式、依賴全部照抄。"""
    def _unit(unit: str) -> str:
        return reporting_unit if unit == "currency" else unit

    fixed_not_modeled = (
        not_modeled("internal_gross_margin", "內部毛利率估計", "bridge v1 直接建模營益率，不拆毛利率／營業費用"),
        not_modeled("internal_fcf", "內部 FCF 估計", "bridge v1 沒有現金流量表（capex／營運資金）"),
    )
    if model is None:
        absent = reason or "本次未執行 fundamental model（呼叫端未注入）"
        internal_items = tuple(missing(f"internal_{k}", l, absent, authority=A_BRIDGE)
                               for k, l, _u in _INTERNAL_METRIC_LABELS) + fixed_not_modeled
        meta = SectionMeta(status="missing", basis="none", authority=A_BRIDGE,
                           capability=CAP_FINANCIAL_CAUSAL, reason=absent, as_of=reference_day)
        absent_cmp = tuple(missing(f"internal_vs_consensus_{m}", l, absent, authority=A_COMPARE)
                           for m, l in _COMPARISON_LABELS.items())
        return _FundamentalParts(
            internal_section=InternalFundamentalsSection(meta=meta, items=internal_items,
                                                         plug_in_note=NEXT_PHASE_NOTE),
            bridge_meta=SectionMeta(status="missing", basis="none", authority=A_BRIDGE,
                                    capability=CAP_FINANCIAL_CAUSAL, reason=absent, as_of=reference_day),
            bridge_steps=(), bridge_assumptions=(), bridge_sensitivities=(), bridge_selection=None,
            bridge_period=None, comparisons=absent_cmp,
            internal_vs_consensus=missing("internal_vs_consensus", "內部估計 vs 共識（數值）", absent,
                                          authority=A_COMPARE),
            opinion_stance=missing("opinion_stance", "我們有沒有形成自己的觀點", absent,
                                   authority=A_COMPARE),
            financial_causal=missing("financial_causal_model",
                                     "財務因果模型（operating assumptions → revenue／margin／EPS）",
                                     absent, authority=A_BRIDGE),
            fiscal_items=(), has_numeric_gap=False, warnings=(),
        )

    target = model.target_period
    # ---- 內部估計 ------------------------------------------------------------
    internal_items: list[Datum] = []
    for key, label, unit in _INTERNAL_METRIC_LABELS:
        metric = model.metrics.get(key)
        if metric is None or not metric.is_known:
            why = (metric.reason if metric and metric.reason else model.reason or "模型無此輸出")
            internal_items.append(missing(f"internal_{key}", label, f"{why}（缺席不是 0）",
                                          authority=A_BRIDGE))
            continue
        # refresh：數字算法確定，但它依賴的假設若被動搖，這一格不得再當 current（傳播來的 state 現形）。
        refreshed = (refresh or {}).get(f"modeled_metric:{key}")
        refresh_note = (f"；refresh={refreshed.state}：{refreshed.reasons[0]}"
                        if refreshed is not None and refreshed.state != CURRENT else "")
        internal_items.append(Datum(
            key=f"internal_{key}", label=label, value=metric.value, status=_refresh_status(refreshed),
            basis="deterministic", authority=A_BRIDGE,
            method=f"{metric.formula}（{model.bridge_version}）", unit=_unit(unit),
            as_of=reference_day, evidence_refs=tuple(metric.observation_refs),
            reason=(f"calculation=deterministic；input_dependency={metric.input_dependency}"
                    f"（{BASIS_LABEL.get(str(metric.input_dependency), metric.input_dependency)}）" + refresh_note),
            dependencies={
                "period": metric.period.label, "fiscal_period_end": metric.period.end.isoformat(),
                "accounting_basis": metric.accounting_basis,
                "input_dependency": metric.input_dependency,
                "assumption_ids": list(metric.assumption_ids),
                "observation_refs": list(metric.observation_refs),
                **_refresh_deps(refreshed),
            },
        ))
    internal_items.extend(fixed_not_modeled)
    section_basis = "deterministic" if model.status != "missing" else "none"
    internal_meta = SectionMeta(
        status=model.status, basis=section_basis, authority=A_BRIDGE,
        capability=CAP_FINANCIAL_CAUSAL, reason=model.reason, as_of=reference_day,
        warnings=(FUNDAMENTAL_EPISTEMIC_WARNING,
                  f"口徑：{model.accounting_basis}；與共識比較只在同期、同口徑時成立。",
                  *model.warnings),
    )
    internal_section = InternalFundamentalsSection(
        meta=internal_meta, items=tuple(internal_items), plug_in_note=NEXT_PHASE_NOTE,
        period=target.label if target else None, period_end=target.end if target else None,
        base_period_end=model.base_period.end if model.base_period else None,
        accounting_basis=model.accounting_basis,
    )

    # ---- 橋 --------------------------------------------------------------------
    steps: list[Datum] = []
    for step in model.steps:
        if step.value is None:
            steps.append(missing(step.key, step.label, step.reason or "上游缺料（不是 0）",
                                 authority=A_BRIDGE if step.kind == "derived" else
                                 (A_ASSUMPTIONS if step.kind == "assumption" else A_LEDGER)))
            continue
        authority = {"observation": A_LEDGER, "assumption": A_ASSUMPTIONS, "derived": A_BRIDGE}[step.kind]
        steps.append(Datum(
            key=step.key, label=step.label, value=step.value, status="available", basis=step.basis,
            authority=authority, method=step.formula, unit=_unit(step.unit), as_of=reference_day,
            evidence_refs=tuple(step.observation_refs), reason=step.reason,
            dependencies={"kind": step.kind, "assumption_ids": list(step.assumption_ids),
                          "scope": step.scope},
        ))
    assumptions: list[Datum] = []
    for a in model.assumptions:
        refreshed = (refresh or {}).get(f"operating_assumption:{a.assumption_id}")
        assumptions.append(Datum(
            key=f"assumption:{a.driver}:{a.scope}", label=f"假設 {a.driver}[{a.scope}]",
            value=a.value, status=_refresh_status(refreshed), basis=a.basis, authority=A_ASSUMPTIONS,
            unit=_unit(a.unit), as_of=a.created_on, evidence_refs=tuple(a.evidence_refs),
            reason=a.rationale,
            dependencies={"assumption_id": a.assumption_id, "period": a.period.label,
                          "fiscal_period_end": a.period.end.isoformat(),
                          "created_at": a.created_at.isoformat(), "author": a.author,
                          "accounting_basis": a.accounting_basis, "supersedes_id": a.supersedes_id,
                          # Step 0.5：supporting／calibration 分開、legacy 標記、machine-readable 條件
                          "provenance_semantics": a.provenance_semantics,
                          "dependency_roles": {r: a.role_of(r) for r in a.evidence_refs},
                          "review_conditions": [c.to_dict() for c in a.review_conditions],
                          # 「60% 是判斷不是觀測」：basis 已說；這個旗標讓 consumer 不必讀 basis 也知道
                          # 支持證據一變就該重看（heuristic／judgment 都是）。
                          "requires_review_on_support_change": a.basis != "observation",
                          **_refresh_deps(refreshed)},
        ))
    sensitivities: list[Datum] = []
    for s in model.sensitivities:
        bump_text = f"+{s.bump:.2f}" if s.bump_unit == "absolute_ratio" else f"×{1 + s.bump:.2f}"
        sensitivities.append(Datum(
            key=f"sensitivity:{s.driver}:{s.scope}", label=f"敏感度 {s.driver}[{s.scope}] {bump_text}",
            value={"delta_revenue": s.delta_revenue, "delta_operating_income": s.delta_operating_income,
                   "delta_eps": s.delta_eps, "eps_relative": s.eps_relative,
                   "bump": s.bump, "bump_unit": s.bump_unit},
            status="available", basis="deterministic", authority=A_BRIDGE,
            method="重跑 bridge，只動這一條假設；不是機率、不是情境", as_of=reference_day,
            dependencies={"assumption_id": s.assumption_id},
        ))
    selection = EvidenceSelectionCounts(
        input_count=model.selection.input_count, accepted_count=model.selection.accepted_count,
        filtered_count=model.selection.filtered_count, reasons=dict(model.selection.reasons),
    )
    bridge_meta = SectionMeta(
        status=model.status, basis=section_basis, authority=A_BRIDGE,
        capability=CAP_FINANCIAL_CAUSAL, reason=model.reason, as_of=reference_day,
        warnings=("橋的每一格：observation＝基期觀測、assumption＝明示假設（各自標知識種類）、"
                  "derived＝確定性算術；缺任何一條假設就是 missing，不補 0。",
                  FUNDAMENTAL_EPISTEMIC_WARNING),
    )

    # ---- 比較 ------------------------------------------------------------------
    comparisons: list[Datum] = []
    comparable: dict[str, Any] = {}
    for metric, label in _COMPARISON_LABELS.items():
        cmp = model.comparisons.get(metric)
        key = f"internal_vs_consensus_{metric}"
        if cmp is None:
            comparisons.append(missing(key, label, "模型未比較此指標", authority=A_COMPARE))
            continue
        status = _COMPARISON_STATUS_TO_DATUM[cmp.status]
        if cmp.status != "comparable":
            comparisons.append(Datum(key=key, label=label, value=None, status=status, basis="none",
                                     authority=A_COMPARE, reason=f"{cmp.status}：{cmp.reason}"))
            continue
        payload = {
            "internal": cmp.internal, "consensus": cmp.consensus,
            "absolute_gap": cmp.absolute_gap, "relative_gap": cmp.relative_gap,
            "period": cmp.internal_period.label if cmp.internal_period else None,
            "fiscal_period_end": cmp.internal_period.end.isoformat() if cmp.internal_period else None,
            "analyst_count": cmp.analyst_count,
            "consensus_captured_at": cmp.consensus_captured_at.isoformat() if cmp.consensus_captured_at else None,
            "accounting_basis": cmp.accounting_basis_internal,
        }
        comparable[metric] = payload
        refreshed = (refresh or {}).get(f"expectation_comparison:{metric}")
        comparisons.append(Datum(
            key=key, label=label, value=payload, status=_refresh_status(refreshed), basis="deterministic",
            authority=A_COMPARE, unit=_unit(cmp.unit or ""), as_of=cmp.consensus_captured_at,
            method="absolute = internal − consensus；relative = internal／consensus − 1（同期、同口徑、同幣別才算）",
            evidence_refs=tuple(cmp.observation_refs) + tuple(cmp.consensus_refs), reason=cmp.reason,
            dependencies={"assumption_ids": list(cmp.assumption_ids), "status": cmp.status,
                          "accounting_basis_consensus": cmp.accounting_basis_consensus,
                          **_refresh_deps(refreshed)},
        ))
    if comparable:
        summary = Datum(
            key="internal_vs_consensus", label="內部估計 vs 共識（數值）",
            value={m: {"relative_gap": p["relative_gap"], "absolute_gap": p["absolute_gap"],
                       "period": p["period"]} for m, p in comparable.items()},
            status="available" if len(comparable) == len(_COMPARISON_LABELS) else "partial",
            basis="deterministic", authority=A_COMPARE, as_of=reference_day,
            method="逐指標見 numeric_comparisons；未列的指標是不可比或缺料",
            reason="它是內部假設推出的數字與共識的差，不是 Q4；Q4 仍是 session 的 ordinal 判斷",
        )
    else:
        reasons = "；".join(f"{d.key.removeprefix('internal_vs_consensus_')}={d.reason}" for d in comparisons)
        summary = Datum(key="internal_vs_consensus", label="內部估計 vs 共識（數值）", value=None,
                        status=("not_applicable" if all(d.status == "not_applicable" for d in comparisons)
                                else "missing"),
                        basis="none", authority=A_COMPARE, reason=reasons)

    # ---- 我們有沒有形成自己的觀點（2026-09-10）---------------------------------
    # ⚠ 這一格**由模型層宣告**，呈現層不得 parse rationale 去猜（APP 呈現契約；L16）。
    # 它與 status／readiness 正交：`available` 的模型完全可以是 `consensus_inverted`——
    # 每一格都有數字，而每一個數字都是共識反解出來的，於是「我們比市場 −0.0%」不攜帶資訊。
    stance = model.stance
    stance_detail = {a.driver: {"scope": a.scope, "derivation": a.derivation,
                                "assumption_id": a.assumption_id}
                     for a in model.assumptions if a.driver in OPINION_BEARING_DRIVERS}
    stance_datum = Datum(
        key="opinion_stance", label="我們有沒有形成自己的觀點", value=stance,
        status="available", basis="deterministic", authority=A_COMPARE, as_of=reference_day,
        method="由核心 driver（revenue_growth／operating_margin_delta）的 derivation 聚合；"
               "任一條 independent 即 independent，未宣告永遠不算 independent",
        reason=PLAIN_STANCE.get(stance, {}).get("reason", stance),
        dependencies={"by_driver": stance_detail,
                      "opinion_bearing_drivers": sorted(OPINION_BEARING_DRIVERS)},
    )

    # ---- 因果 section 的財務橋一格 -----------------------------------------------
    if model.status != "missing":
        financial_causal = Datum(
            key="financial_causal_model", label="財務因果模型（operating assumptions → revenue／margin／EPS）",
            value={"period": target.label if target else None, "status": model.status,
                   "accounting_basis": model.accounting_basis, "bridge_version": model.bridge_version,
                   "metrics_known": [m for m, v in model.metrics.items() if v.is_known]},
            status="available" if model.status == "available" else "partial",
            basis="deterministic", authority=A_BRIDGE, as_of=reference_day,
            reason="橋住 earnings_bridge section；結構事件 → 假設的連結靠假設的 evidence_refs 指回圖上證據",
        )
    else:
        financial_causal = missing("financial_causal_model",
                                   "財務因果模型（operating assumptions → revenue／margin／EPS）",
                                   model.reason or "缺基期或缺假設", authority=A_BRIDGE)

    # ---- 會計年度別共識 --------------------------------------------------------
    fiscal_items: list[Datum] = []
    for c in model.consensus:
        basis = model.consensus_bases.get(f"{c.metric}:{c.period.end.isoformat()}", "unverified")
        metric_label = _CONSENSUS_METRIC_LABEL.get(c.metric, c.metric)
        if c.value is None:
            fiscal_items.append(missing(f"consensus_{c.metric}_{c.period.label}",
                                        f"{c.period.label} {metric_label} 共識", "provider 該期無估計值",
                                        authority=A_CONSENSUS_FY))
            continue
        fiscal_items.append(Datum(
            key=f"consensus_{c.metric}_{c.period.label}",
            label=f"{c.period.label} {metric_label} 共識（至 {c.period.end.isoformat()}）",
            value={"avg": c.value, "low": c.low, "high": c.high, "analyst_count": c.analyst_count,
                   "year_ago_actual": c.year_ago_actual, "growth": c.growth, "currency": c.currency,
                   "relative_label": c.relative_label, "accounting_basis": basis},
            status="available", basis="observation", authority=A_CONSENSUS_FY,
            unit=_unit("currency_per_share" if c.metric == "eps" else "currency"),
            as_of=c.captured_at, evidence_refs=c.refs,
            method=f"{c.source}；provider 相對標籤 {c.relative_label} 於抓取日解析成 fiscal_period_end",
            reason=(f"口徑 {basis}：EPS 以 year_ago_actual 與一手財報稀釋 EPS 核對；unverified 不得與內部相減"
                    if c.metric == "eps" else "營收無口徑之分"),
        ))

    return _FundamentalParts(
        internal_section=internal_section, bridge_meta=bridge_meta, bridge_steps=tuple(steps),
        bridge_assumptions=tuple(assumptions), bridge_sensitivities=tuple(sensitivities),
        bridge_selection=selection, bridge_period=target.label if target else None,
        comparisons=tuple(comparisons), internal_vs_consensus=summary,
        opinion_stance=stance_datum,
        financial_causal=financial_causal, fiscal_items=tuple(fiscal_items),
        has_numeric_gap=bool(comparable), warnings=tuple(model.warnings),
    )


# ---------------------------------------------------------------------------
# 估值（Step 1）：只選取 `alpha.valuation` 的輸出。**本檔沒有 fair value 公式**——
# 值、公式字串、依賴全部照抄 `ValuationResult`；builder 不乘任何數。
# ---------------------------------------------------------------------------
A_VALUATION = "alpha://valuation/model"
A_VALUATION_ASSUMPTIONS = "alpha://valuation/assumptions"

#: gap 不是什麼——每次都列，讀者不必靠記憶區分（AGENTS：不含欄逐項寫出最相鄰的未授權語意）。
GAP_IS_NOT: tuple[str, ...] = (
    "不是 expected return（沒有 horizon、沒有報酬語意——那些住 implied_return section，且那也只是 base-case 隱含報酬）",
    "不是 upside／downside forecast（沒有機率、沒有情境加權）",
    "不是 entry signal、不是 buy／sell、不是 required return 或 entry price",
    "不是 opportunity ranking——它是一檔的 fair value 與現價之差，不跨標的比較",
)
VALUATION_EPISTEMIC_WARNING = (
    "fair value 是判斷的確定性函數，不是事實：內部 EPS 的每條營運假設與目標倍數都是 session 判斷／heuristic——"
    "看 fair_value.dependencies.input_dependency 與 epistemics；不得把公式算出來的價格讀成觀測。"
)


def _valuation_section(
    valuation: Any, reason: str | None, *, reference_day: date, reporting_unit: str,
    refresh: Mapping[str, AffectedArtifact],
) -> ValuationSection:
    def _unit(unit: str) -> str:
        return reporting_unit if unit == "currency" else unit

    def _absent_section(why: str, *, status: str = "missing") -> ValuationSection:
        meta = SectionMeta(status=status, basis="none", authority=A_VALUATION,
                           capability=CAP_DETERMINISTIC_FAIR_VALUE, reason=why, as_of=reference_day)
        return ValuationSection(
            meta=meta,
            method=missing("valuation_method", "估值方法", why, authority=A_VALUATION),
            fundamental_input=missing("valuation_fundamental_input", "估值消費的內部指標", why, authority=A_VALUATION),
            assumptions=(), fair_value=missing("fair_value", "Fair value", why, authority=A_VALUATION),
            current_price=missing("current_price", "現價（Engine C）", why, authority=A_SNAP),
            fair_value_gap=missing("fair_value_gap", "Fair value vs 現價（gap）", why, authority=A_VALUATION),
            trace=(), sensitivities=(),
            epistemics=missing("valuation_epistemics", "fair value 的認識論分解", why, authority=A_VALUATION),
            selection=None, gap_is_not=GAP_IS_NOT,
            value_date=missing("value_date", "fair value 是哪一天的值（value_date）", why, authority=A_VALUATION),
        )

    if valuation is None:
        return _absent_section(reason or "本次未執行 valuation model（呼叫端未注入）")

    target = valuation.target_period
    fv_refresh = refresh.get("fair_value:fair_value")
    gap_refresh = refresh.get("fair_value_gap:fair_value_gap")
    fi = valuation.fundamental_input
    fundamental_datum = (
        Datum(key="valuation_fundamental_input", label=f"估值消費的內部指標：{fi.metric}（{fi.period.label}，{fi.accounting_basis}）",
              value=fi.value, status="available", basis="deterministic", authority=A_BRIDGE,
              method=fi.formula, unit=_unit(fi.unit or "currency_per_share"), as_of=reference_day,
              evidence_refs=tuple(fi.observation_refs),
              reason=f"照抄 internal_fundamentals.internal_{fi.metric}；calculation=deterministic；input_dependency={fi.input_dependency}",
              dependencies={"period": fi.period.label, "fiscal_period_end": fi.period.end.isoformat(),
                            "accounting_basis": fi.accounting_basis, "input_dependency": fi.input_dependency,
                            "assumption_ids": list(fi.assumption_ids), "currency": fi.currency})
        if fi is not None and fi.is_known else
        missing("valuation_fundamental_input", "估值消費的內部指標",
                (fi.reason if fi and fi.reason else valuation.reason or "內部指標缺席") + "（不是 0）", authority=A_BRIDGE)
    )
    assumption_data: list[Datum] = []
    for a in valuation.assumptions:
        refreshed = refresh.get(f"valuation_assumption:{a.assumption_id}")
        assumption_data.append(Datum(
            key=f"valuation_assumption:{a.method}:{a.parameter}", label=f"估值假設 {a.parameter}（{a.method}）",
            value=a.value, status=_refresh_status(refreshed), basis=a.basis, authority=A_VALUATION_ASSUMPTIONS,
            unit=a.unit, as_of=a.created_on, evidence_refs=tuple(a.evidence_refs), reason=a.rationale,
            dependencies={"assumption_id": a.assumption_id, "period": a.period.label,
                          "fiscal_period_end": a.period.end.isoformat(), "accounting_basis": a.accounting_basis,
                          "created_at": a.created_at.isoformat(), "author": a.author,
                          "supersedes_id": a.supersedes_id, "provenance_semantics": a.provenance_semantics,
                          "dependency_roles": {r: a.role_of(r) for r in a.evidence_refs},
                          "review_conditions": [c.to_dict() for c in a.review_conditions],
                          "requires_review_on_support_change": a.basis != "observation",
                          **_refresh_deps(refreshed)}))
    method_datum = Datum(
        key="valuation_method", label="估值方法", value=valuation.method, status="available", basis="deterministic",
        authority=A_VALUATION, method=valuation.model_version, as_of=reference_day,
        reason=("forward_earnings_multiple＝內部 EPS × 目標本益比（盈餘為正）；ev_to_sales（2026-09-09 P6）＝"
                "(內部營收 × 目標 EV/Sales − 淨負債快照) / 稀釋股數（forward EPS 非正時、且 ledger 有該假設才用）。"
                "無內部 FCF／EBITDA，所以 EV/EBITDA、DCF、reverse DCF 仍沒有資料可餵——不為完整硬做"))
    if valuation.is_known:
        fv_note = (f"；refresh={fv_refresh.state}：{fv_refresh.reasons[0]}"
                   if fv_refresh is not None and fv_refresh.state != CURRENT else "")
        fair_value_datum = Datum(
            key="fair_value", label=f"Fair value（{target.label if target else '?'}，{valuation.accounting_basis}）",
            value=valuation.fair_value, status=_refresh_status(fv_refresh), basis="deterministic",
            authority=A_VALUATION, method=f"{valuation.formula}（{valuation.model_version}）",
            unit=_unit("currency_per_share"), as_of=reference_day,
            evidence_refs=tuple(fi.observation_refs) if fi else (),
            reason=(f"calculation=deterministic；input_dependency={valuation.input_dependency}"
                    f"（{BASIS_LABEL.get(str(valuation.input_dependency), valuation.input_dependency)}）" + fv_note),
            dependencies={"period": target.label if target else None,
                          "fiscal_period_end": target.end.isoformat() if target else None,
                          "accounting_basis": valuation.accounting_basis, "currency": valuation.currency,
                          "input_dependency": valuation.input_dependency,
                          "assumption_ids": list(valuation.assumption_ids),
                          "observation_refs": list(fi.observation_refs) if fi else [],
                          "price_in_formula": False, **_refresh_deps(fv_refresh)})
    else:
        fair_value_datum = missing("fair_value", "Fair value", f"{valuation.reason}（缺席不是 0）",
                                   authority=A_VALUATION, absence_kind=valuation.effective_absence_kind)
    # Step 2：fair value 是哪一天的值——抄估值層的 value_date／value_date_semantics，不猜。
    if valuation.is_known and valuation.value_date is not None:
        value_date_datum = Datum(
            key="value_date", label=f"fair value 是哪一天的值（value_date；{valuation.value_date_semantics}）",
            value=valuation.value_date, status="available", basis="session_judgment", authority=A_VALUATION_ASSUMPTIONS,
            method=valuation.value_date_formula, unit="date", as_of=reference_day,
            reason="由生效估值假設的 value_date_convention 宣告；它是判斷的一部分，不是觀測",
            dependencies={"value_date_semantics": valuation.value_date_semantics,
                          "assumption_ids": [a.assumption_id for a in valuation.assumptions]})
    else:
        value_date_datum = missing(
            "value_date", "fair value 是哪一天的值（value_date）",
            ("估值假設未宣告 value_date_convention——時點語意 unspecified（不猜；報酬層拒算）"
             if valuation.is_known else f"{valuation.reason}（fair value 缺席）"),
            authority=A_VALUATION_ASSUMPTIONS,
            absence_kind=None if valuation.is_known else "upstream_unavailable")
    price = valuation.current_price
    current_price_datum = (
        Datum(key="current_price", label="現價（Engine C）", value=price.value, status="available", basis="observation",
              authority=A_SNAP, unit=f"quote_unit（{price.unit or '未知'}）", as_of=price.bar_date,
              evidence_refs=tuple(price.evidence_refs), reason="估值層只讀現價；它不進 fair value，只進 gap",
              # 報價單位以**欄位**帶著走，不要讓消費端去 parse `unit` 那句中文。
              # GBp（便士）與 GBP（英鎊）差 100 倍，而字串解析正是 2026-09-07 那個 100 倍陷阱的近親（L16）。
              dependencies={"quote_unit": price.unit})
        if price.is_known else
        missing("current_price", "現價（Engine C）", price.reason or "無現價", authority=A_SNAP))
    gap = valuation.gap
    if gap.is_known:
        gap_note = (f"；refresh={gap_refresh.state}：{gap_refresh.reasons[0]}"
                    if gap_refresh is not None and gap_refresh.state != CURRENT else "")
        gap_datum = Datum(
            key="fair_value_gap", label="Fair value vs 現價（gap；不是 expected return）",
            value={"absolute_gap": gap.absolute_gap, "relative_gap": gap.relative_gap,
                   "implied_multiple_at_price": gap.implied_multiple_at_price,
                   "fair_value": valuation.fair_value, "current_price": price.value, "unit": gap.unit},
            status=_refresh_status(gap_refresh), basis="deterministic", authority=A_VALUATION,
            method=valuation.gap_formula, unit=_unit("currency_per_share"), as_of=price.bar_date,
            evidence_refs=tuple(gap.price_refs) + (tuple(fi.observation_refs) if fi else ()),
            reason="它是 fair value 與現價的差，" + "；".join(GAP_IS_NOT[:2]) + gap_note,
            dependencies={"assumption_ids": list(valuation.assumption_ids), "status": gap.status,
                          "implied_multiple_formula": valuation.implied_multiple_formula, **_refresh_deps(gap_refresh)})
    else:
        gap_status = "not_applicable" if gap.status in ("incompatible_unit", "unverified_unit") else "missing"
        # gap 缺席的原因分兩種：**單位不可比**（報價單位 ≠ 結算幣別，兩個數不同尺度）
        # 與**上游沒有 fair value**。前者是 inputs_incompatible，後者繼承估值層的 kind——
        # 「刻意不主張」與「還沒寫」的區別必須一路傳到 gap 這一格，不能在這裡被抹平。
        gap_kind = ("inputs_incompatible" if gap_status == "not_applicable"
                    else (valuation.effective_absence_kind if not valuation.is_known else "upstream_unavailable"))
        gap_datum = Datum(key="fair_value_gap", label="Fair value vs 現價（gap；不是 expected return）", value=None,
                          status=gap_status, basis="none", authority=A_VALUATION, reason=f"{gap.status}：{gap.reason}",
                          absence_kind=gap_kind)
    trace: list[Datum] = []
    for step in valuation.steps:
        authority = {"fundamental_input": A_BRIDGE, "assumption": A_VALUATION_ASSUMPTIONS, "derived": A_VALUATION}[step.kind]
        if step.value is None:
            trace.append(missing(f"valuation_step:{step.key}", step.label, step.reason or "上游缺料（不是 0）", authority=authority))
            continue
        trace.append(Datum(
            key=f"valuation_step:{step.key}", label=step.label, value=step.value, status="available", basis=step.basis,
            authority=authority, method=step.formula, unit=_unit(step.unit), as_of=reference_day,
            evidence_refs=tuple(step.observation_refs), reason=step.reason,
            dependencies={"kind": step.kind, "assumption_ids": list(step.assumption_ids),
                          "input_dependency": step.input_dependency}))
    sens: list[Datum] = []
    for s in valuation.sensitivities:
        bump_text = f"+{s.bump:.2f}" if s.bump_unit == "absolute_ratio" else f"×{1 + s.bump:.2f}"
        sens.append(Datum(
            key=f"fair_value_sensitivity:{s.driver}:{s.scope}", label=f"fair value 敏感度 {s.driver}[{s.scope}] {bump_text}",
            value={"delta_fair_value": s.delta_fair_value, "fair_value_relative": s.fair_value_relative,
                   "bump": s.bump, "bump_unit": s.bump_unit},
            status="available", basis="deterministic", authority=A_VALUATION,
            method="只動這一條判斷重算 fair value；確定性微擾，不是機率、不是情境", as_of=reference_day,
            dependencies={"assumption_id": s.assumption_id}))
    epistemics_datum = (
        Datum(key="valuation_epistemics", label="fair value 的認識論分解（算術 vs 判斷）", value=dict(valuation.epistemics),
              status="available", basis="deterministic", authority=A_VALUATION, as_of=reference_day,
              method="純計數與選取：列出哪些是確定性算術、哪些輸入是判斷（按 basis 計數）；不是新判斷")
        if valuation.epistemics else
        missing("valuation_epistemics", "fair value 的認識論分解（算術 vs 判斷）", "fair value 缺席，無可分解",
                authority=A_VALUATION, absence_kind="upstream_unavailable"))
    selection = EvidenceSelectionCounts(
        input_count=valuation.selection.input_count, accepted_count=valuation.selection.accepted_count,
        filtered_count=valuation.selection.filtered_count, reasons=dict(valuation.selection.reasons))
    section_status = fair_value_datum.status if valuation.is_known else "missing"
    meta = SectionMeta(
        status=section_status, basis="deterministic" if valuation.is_known else "none", authority=A_VALUATION,
        capability=CAP_DETERMINISTIC_FAIR_VALUE, reason=valuation.reason, as_of=reference_day,
        absence_kind=valuation.effective_absence_kind,
        warnings=(VALUATION_EPISTEMIC_WARNING,
                  "fair value 不含現價：price-only 變化只動 gap，不動 fair value。",
                  "gap " + "；".join(GAP_IS_NOT), *valuation.warnings),
    )
    return ValuationSection(
        meta=meta, method=method_datum, fundamental_input=fundamental_datum, assumptions=tuple(assumption_data),
        fair_value=fair_value_datum, current_price=current_price_datum, fair_value_gap=gap_datum,
        trace=tuple(trace), sensitivities=tuple(sens), epistemics=epistemics_datum, selection=selection,
        gap_is_not=GAP_IS_NOT, value_date=value_date_datum,
        period=target.label if target else None, period_end=target.end if target else None,
        accounting_basis=valuation.accounting_basis,
    )


# ---------------------------------------------------------------------------
# Base-case implied return（Step 2）：只選取 `alpha.implied_return` 的輸出。**本檔沒有報酬公式**——
# 值、公式字串、依賴全部照抄 `ImpliedReturnResult`；builder 不除任何數、不算任何年化。
# ---------------------------------------------------------------------------
A_IMPLIED_RETURN = "alpha://implied_return/model"
A_HORIZON_ASSUMPTIONS = "alpha://implied_return/horizon"

#: implied return 不是什麼——每次都列，讀者不必靠記憶區分。
RETURN_IS_NOT: tuple[str, ...] = (
    "不是 probability-weighted expected return（沒有 bull／base／bear 機率；名稱刻意用 implied）",
    "不是 total return（沒有股利／分配預測；只有價格報酬）",
    "不是 required return、不是 entry price（那兩格住 entry_logic section，且要有明示的投資人判準）、不是 buy／sell、不是 actionable-now",
    "不是 opportunity ranking、不是回測或統計勝率——它是一檔在 base case 下從 bar_date 到 horizon_end 的隱含價格報酬",
)
RETURN_EPISTEMIC_WARNING = (
    "implied return 是判斷的確定性函數，不是預測：內部 EPS 的營運假設、目標倍數、value-date 語意、horizon 全是 session "
    "判斷——看 price_return.dependencies.input_dependency 與 epistemics；不得把公式算出來的報酬讀成期望值。"
)


def _implied_return_section(
    result: Any, reason: str | None, *, reference_day: date, reporting_unit: str,
    refresh: Mapping[str, AffectedArtifact],
) -> ImpliedReturnSection:
    def _unit(unit: str) -> str:
        return reporting_unit if unit == "currency" else unit

    fixed = (
        not_modeled("total_return", "總報酬（含股利／分配）", "本層沒有股利／分配預測能力——不是 0，也不是 price_return 的別名"),
        not_modeled("probability_weighted_return", "機率加權期望報酬", "沒有 bull／base／bear 機率；本 section 只有 base case 的隱含報酬"),
    )

    def _absent(why: str, *, status: str = "missing") -> ImpliedReturnSection:
        meta = SectionMeta(status=status, basis="none", authority=A_IMPLIED_RETURN,
                           capability=CAP_BASE_CASE_IMPLIED_RETURN, reason=why, as_of=reference_day)
        return ImpliedReturnSection(
            meta=meta,
            return_convention=missing("return_convention", "報酬種類", why, authority=A_IMPLIED_RETURN),
            current_price=missing("current_price", "現價（Engine C）", why, authority=A_SNAP),
            fair_value=missing("fair_value", "Fair value（照抄 valuation）", why, authority=A_VALUATION),
            value_date=missing("value_date", "fair value 是哪一天的值", why, authority=A_VALUATION_ASSUMPTIONS),
            horizon=missing("horizon", "Horizon 判斷（fair value 何時被市場定價到）", why, authority=A_HORIZON_ASSUMPTIONS),
            horizon_window=missing("horizon_window", "Horizon 區間（起／迄／天數）", why, authority=A_IMPLIED_RETURN),
            price_return=missing("base_case_implied_price_return", "Base-case 隱含價格報酬（simple）", why, authority=A_IMPLIED_RETURN),
            annualized_price_return=missing("annualized_price_return", "年化隱含價格報酬", why, authority=A_IMPLIED_RETURN),
            total_return=fixed[0], probability_weighted_return=fixed[1], trace=(),
            epistemics=missing("return_epistemics", "implied return 的認識論分解", why, authority=A_IMPLIED_RETURN),
            selection=None, is_not=RETURN_IS_NOT,
            eps_contribution=missing("eps_contribution", "其中：EPS 差異貢獻", why, authority=A_IMPLIED_RETURN),
            multiple_contribution=missing("multiple_contribution", "其中：倍數差異貢獻", why, authority=A_IMPLIED_RETURN),
            attribution=missing("return_attribution", "兩桿拆解（EPS 差異 × 倍數差異）", why, authority=A_IMPLIED_RETURN),
        )

    if result is None:
        return _absent(reason or "本次未執行 implied return model（呼叫端未注入）")

    ret_refresh = refresh.get("implied_return:implied_return")
    target = result.target_period
    price = result.current_price
    current_price_datum = (
        Datum(key="current_price", label="現價（Engine C；horizon 起點）", value=price.value, status="available",
              basis="observation", authority=A_SNAP, unit=f"quote_unit（{price.unit or '未知'}）", as_of=price.bar_date,
              evidence_refs=tuple(price.evidence_refs), reason="報酬從這個價格所屬的 bar_date 起算",
              dependencies={"quote_unit": price.unit})
        if price.is_known else missing("current_price", "現價（Engine C）", price.reason or "無現價", authority=A_SNAP))
    fair_value_datum = (
        Datum(key="fair_value", label=f"Fair value（{target.label if target else '?'}；照抄 valuation）", value=result.fair_value,
              status="available", basis="deterministic", authority=A_VALUATION, unit=_unit("currency_per_share"),
              as_of=result.fair_value_as_of, reason="照抄 valuation.fair_value，不重算",
              dependencies={"currency": result.fair_value_currency,
                            "assumption_ids": [a for a in result.assumption_ids if not a.startswith("ha_")]})
        if result.fair_value is not None else
        missing("fair_value", "Fair value（照抄 valuation）", result.reason or "fair value 缺席",
                authority=A_VALUATION, absence_kind=result.effective_absence_kind))
    value_date_datum = (
        Datum(key="value_date", label=f"fair value 是哪一天的值（{result.value_date_semantics}）", value=result.value_date,
              status="available", basis="session_judgment", authority=A_VALUATION_ASSUMPTIONS, unit="date",
              as_of=reference_day, reason="由估值假設的 value_date_convention 宣告（判斷，不是觀測）",
              dependencies={"value_date_semantics": result.value_date_semantics})
        if result.value_date is not None else
        missing("value_date", "fair value 是哪一天的值",
                "估值假設未宣告 value_date_convention——時點語意 unspecified，不猜" if result.fair_value is not None
                else "fair value 缺席", authority=A_VALUATION_ASSUMPTIONS,
                absence_kind=None if result.fair_value is not None else "upstream_unavailable"))
    h = result.horizon
    if h is not None:
        h_refresh = refresh.get(f"horizon_assumption:{h.assumption_id}")
        horizon_datum = Datum(
            key="horizon", label=f"Horizon 判斷：{h.period.label} fair value 於此日前實現", value=h.horizon_end,
            status=_refresh_status(h_refresh), basis=h.basis, authority=A_HORIZON_ASSUMPTIONS, unit="date",
            as_of=h.created_on, evidence_refs=tuple(h.evidence_refs), reason=h.rationale,
            dependencies={"assumption_id": h.assumption_id, "period": h.period.label,
                          "fiscal_period_end": h.period.end.isoformat(), "created_at": h.created_at.isoformat(),
                          "author": h.author, "supersedes_id": h.supersedes_id,
                          "provenance_semantics": h.provenance_semantics,
                          "dependency_roles": {r: h.role_of(r) for r in h.evidence_refs},
                          "review_conditions": [c.to_dict() for c in h.review_conditions],
                          "requires_review_on_support_change": h.basis != "observation",
                          **_refresh_deps(h_refresh)})
    else:
        horizon_datum = missing("horizon", "Horizon 判斷（fair value 何時被市場定價到）",
                                result.reason or "沒有生效的 horizon 判斷", authority=A_HORIZON_ASSUMPTIONS)
    if result.is_known:
        note = (f"；refresh={ret_refresh.state}：{ret_refresh.reasons[0]}"
                if ret_refresh is not None and ret_refresh.state != CURRENT else "")
        deps = {"input_dependency": result.input_dependency, "assumption_ids": list(result.assumption_ids),
                "observation_refs": list(result.observation_refs), "horizon_start": result.horizon_start.isoformat(),
                "horizon_end": result.horizon_end.isoformat(), "holding_period_days": result.holding_period_days,
                "value_date": result.value_date.isoformat() if result.value_date else None,
                "value_date_semantics": result.value_date_semantics, "alignment": result.alignment,
                "return_convention": result.return_convention, **_refresh_deps(ret_refresh)}
        window_datum = Datum(
            key="horizon_window", label="Horizon 區間（起＝現價 bar_date／迄＝horizon_end）",
            value={"horizon_start": result.horizon_start, "horizon_end": result.horizon_end,
                   "holding_period_days": result.holding_period_days, "holding_period_years": result.holding_period_years,
                   "alignment": result.alignment},
            status=_refresh_status(ret_refresh), basis="deterministic", authority=A_IMPLIED_RETURN,
            method=result.formulas["holding_period"], as_of=reference_day,
            dependencies={"horizon_assumption_id": h.assumption_id if h else None, "alignment": result.alignment})
        price_return_datum = Datum(
            key="base_case_implied_price_return", label=f"Base-case 隱含價格報酬（simple；{result.horizon_start} → {result.horizon_end}）",
            value=result.price_return, status=_refresh_status(ret_refresh), basis="deterministic", authority=A_IMPLIED_RETURN,
            method=f"{result.formulas['price_return']}（{result.model_version}）", unit="ratio", as_of=price.bar_date,
            evidence_refs=tuple(result.observation_refs),
            reason=(f"calculation=deterministic；input_dependency={result.input_dependency}"
                    f"（{BASIS_LABEL.get(str(result.input_dependency), result.input_dependency)}）；" + "；".join(RETURN_IS_NOT[:2]) + note),
            dependencies=deps)
        annualized_datum = (
            Datum(key="annualized_price_return", label="年化隱含價格報酬（compound，365.25 天）", value=result.annualized_price_return,
                  status=_refresh_status(ret_refresh), basis="deterministic", authority=A_IMPLIED_RETURN,
                  method=result.formulas["annualized_price_return"], unit="ratio", as_of=price.bar_date,
                  reason=f"持有期間 {result.holding_period_days} 天；年化只是換算，不是另一個判斷", dependencies=deps)
            if result.annualized_price_return is not None else
            missing("annualized_price_return", "年化隱含價格報酬", "持有期間不足 1 天，不年化", authority=A_IMPLIED_RETURN))
        epistemics_datum = Datum(
            key="return_epistemics", label="implied return 的認識論分解（算術 vs 判斷）", value=dict(result.epistemics),
            status="available", basis="deterministic", authority=A_IMPLIED_RETURN, as_of=reference_day,
            method="純計數與選取：列出哪些是確定性算術、哪些輸入是判斷；one_sentence 是機器組出的一句話，不是新判斷")
    else:
        why = f"{result.reason}（缺席不是 0）"
        # 缺席語意由報酬層宣告（它自己知道是上游 deliberate_abstention 還是 horizon 還沒寫）；
        # 呈現端不得從 `why` 這段散文回推（L16）。
        kind = result.effective_absence_kind
        window_datum = missing("horizon_window", "Horizon 區間（起／迄／天數）", why, authority=A_IMPLIED_RETURN, absence_kind=kind)
        price_return_datum = missing("base_case_implied_price_return", "Base-case 隱含價格報酬（simple）", why,
                                     authority=A_IMPLIED_RETURN, absence_kind=kind)
        annualized_datum = missing("annualized_price_return", "年化隱含價格報酬", why, authority=A_IMPLIED_RETURN, absence_kind=kind)
        epistemics_datum = missing("return_epistemics", "implied return 的認識論分解", why, authority=A_IMPLIED_RETURN, absence_kind=kind)
    convention_datum = Datum(
        key="return_convention", label="報酬種類", value=result.return_convention, status="available", basis="deterministic",
        authority=A_IMPLIED_RETURN, method=result.model_version, as_of=reference_day,
        reason="base case 的隱含價格報酬；total return 與機率加權期望報酬各自 not_modeled")
    trace: list[Datum] = []
    for step in result.steps:
        authority = {"price_input": A_SNAP, "valuation_input": A_VALUATION, "horizon_input": A_HORIZON_ASSUMPTIONS,
                     "derived": A_IMPLIED_RETURN}[step.kind]
        if step.value is None:
            trace.append(missing(f"return_step:{step.key}", step.label, step.reason or "上游缺料（不是 0）", authority=authority))
            continue
        trace.append(Datum(
            key=f"return_step:{step.key}", label=step.label, value=step.value, status="available", basis=step.basis,
            authority=authority, method=step.formula, unit=_unit(step.unit), as_of=reference_day,
            evidence_refs=tuple(step.observation_refs), reason=step.reason,
            dependencies={"kind": step.kind, "assumption_ids": list(step.assumption_ids),
                          "input_dependency": step.input_dependency}))
    selection = EvidenceSelectionCounts(
        input_count=result.horizon_selection.input_count, accepted_count=result.horizon_selection.accepted_count,
        filtered_count=result.horizon_selection.filtered_count, reasons=dict(result.horizon_selection.reasons))
    # ---- 兩桿拆解（2026-09-09 P2）：照抄 result.attribution，不算任何數 ----------------------------
    attribution = result.attribution
    if attribution is not None and attribution.is_known:
        attr_deps = {"consensus_eps": attribution.consensus_eps, "internal_eps": attribution.internal_eps,
                     "target_multiple": attribution.target_multiple,
                     "market_multiple_on_consensus": attribution.market_multiple_on_consensus,
                     "analyst_count": attribution.analyst_count, "input_dependency": result.input_dependency}
        eps_datum = Datum(
            key="eps_contribution", label="其中：EPS 差異貢獻（我們的 EPS vs 共識）", value=attribution.eps_contribution,
            status="available", basis="deterministic", authority=A_IMPLIED_RETURN, method=attribution.formula,
            unit="ratio", as_of=reference_day, evidence_refs=tuple(attribution.consensus_refs),
            reason=f"內部 EPS {attribution.internal_eps:g} ÷ 共識 EPS {attribution.consensus_eps:g} − 1", dependencies=attr_deps)
        multiple_datum = Datum(
            key="multiple_contribution", label="其中：倍數差異貢獻（我們的倍數 vs 市場對共識付的倍數）",
            value=attribution.multiple_contribution, status="available", basis="deterministic", authority=A_IMPLIED_RETURN,
            method=attribution.formula, unit="ratio", as_of=reference_day, evidence_refs=tuple(attribution.consensus_refs),
            reason=attribution.principle_note, dependencies=attr_deps)
        attribution_datum = Datum(
            key="return_attribution", label="兩桿拆解（EPS 差異 × 倍數差異；恆等式）", value=attribution_payload(attribution),
            status="available", basis="deterministic", authority=A_IMPLIED_RETURN, method=attribution.formula,
            as_of=reference_day, evidence_refs=tuple(attribution.consensus_refs),
            reason="price_return 的確定性恆等分解；判斷都在輸入（內部 EPS 的假設、目標倍數），拆解本身不是新判斷")
    else:
        if attribution is None:
            attr_why = f"報酬缺席，沒有可拆的東西（{result.reason or '未知'}）"
            attr_kind = result.effective_absence_kind
        else:
            attr_why = f"{attribution.reason}（缺席不是 0；報酬本身不受影響）"
            attr_kind = attribution.absence_kind
        eps_datum = missing("eps_contribution", "其中：EPS 差異貢獻", attr_why, authority=A_IMPLIED_RETURN, absence_kind=attr_kind)
        multiple_datum = missing("multiple_contribution", "其中：倍數差異貢獻", attr_why, authority=A_IMPLIED_RETURN, absence_kind=attr_kind)
        attribution_datum = missing("return_attribution", "兩桿拆解（EPS 差異 × 倍數差異）", attr_why,
                                    authority=A_IMPLIED_RETURN, absence_kind=attr_kind)

    section_status = price_return_datum.status if result.is_known else "missing"
    meta = SectionMeta(
        status=section_status, basis="deterministic" if result.is_known else "none", authority=A_IMPLIED_RETURN,
        capability=CAP_BASE_CASE_IMPLIED_RETURN, reason=result.reason, as_of=reference_day,
        absence_kind=result.effective_absence_kind,
        warnings=(RETURN_EPISTEMIC_WARNING,
                  "四個輸入缺一就 missing：現價（含 bar_date）、fair value（同單位）、fair value 的時點語意、生效的 horizon 判斷；不補 12 個月。",
                  "implied return " + "；".join(RETURN_IS_NOT), *result.warnings),
    )
    return ImpliedReturnSection(
        meta=meta, return_convention=convention_datum, current_price=current_price_datum, fair_value=fair_value_datum,
        value_date=value_date_datum, horizon=horizon_datum, horizon_window=window_datum, price_return=price_return_datum,
        annualized_price_return=annualized_datum, total_return=fixed[0], probability_weighted_return=fixed[1],
        trace=tuple(trace), epistemics=epistemics_datum, selection=selection, is_not=RETURN_IS_NOT,
        eps_contribution=eps_datum, multiple_contribution=multiple_datum, attribution=attribution_datum,
        period=target.label if target else None, period_end=target.end if target else None,
    )


# ---------------------------------------------------------------------------
# Entry logic（Step 3）：只選取 `alpha.entry` 的輸出。**本檔沒有門檻價公式**——值、公式字串、依賴全部照抄
# `EntryAssessmentResult`；builder 不折現任何數、不比較任何價格、不把 comparison 翻譯成 action。
# ---------------------------------------------------------------------------
A_ENTRY = "alpha://entry/model"
A_ENTRY_CRITERIA = "alpha://entry/criterion"

#: entry logic 不是什麼——每次都列，讀者不必靠記憶區分。
ENTRY_IS_NOT: tuple[str, ...] = (
    "不是 buy／sell／hold 建議——meets_analytical_hurdle 只是「現價 ≤ 門檻價」的算術事實",
    "不是 position size／capital allocation／order——系統不給部位尺寸，買多少、何時買由使用者判斷",
    "不是 portfolio permission——A5（Decision Store）是唯一能授權資本的地方，且 live 100% 人工",
    "不是 opportunity ranking、不是回測或統計勝率——它是一檔在明示 hurdle 下的門檻價",
    "hurdle 是投資人政策（investor_policy），不是研究對公司的判斷；沒有宣告就是 missing，不補 10%／15%／20%",
)
ENTRY_EPISTEMIC_WARNING = (
    "entry price 是判斷的確定性函數：研究側（營運假設、目標倍數、value-date、horizon）是 session 判斷，hurdle 是投資人"
    "政策——看 entry_price.dependencies.input_dependency 與 criterion；不得把門檻價讀成「該買的價格」。"
)
_STATUS_RANK: Mapping[str, int] = {"available": 0, "stale": 1, "review_required": 2, "invalidated": 3}


def _worst_status(*statuses: str) -> str:
    return max(statuses, key=lambda s: _STATUS_RANK.get(s, 0))


def _entry_logic_section(
    result: Any, reason: str | None, *, reference_day: date, reporting_unit: str,
    refresh: Mapping[str, AffectedArtifact],
) -> EntryLogicSection:
    def _unit(unit: str) -> str:
        return reporting_unit if unit == "currency" else unit

    def _absent(why: str, *, status: str = "missing") -> EntryLogicSection:
        meta = SectionMeta(status=status, basis="none", authority=A_ENTRY, capability=CAP_ANALYTICAL_ENTRY_THRESHOLD,
                           reason=why, as_of=reference_day)
        return EntryLogicSection(
            meta=meta,
            convention=missing("entry_convention", "要求報酬的 convention", why, authority=A_ENTRY),
            criterion=missing("entry_criterion", "Entry criterion（投資人的要求報酬判準）", why, authority=A_ENTRY_CRITERIA),
            required_annualized_return=missing("required_annualized_return", "要求年化價格報酬", why, authority=A_ENTRY_CRITERIA),
            current_price=missing("current_price", "現價（Engine C）", why, authority=A_SNAP),
            fair_value=missing("fair_value", "Fair value（照抄 implied return）", why, authority=A_VALUATION),
            value_date=missing("value_date", "fair value 是哪一天的值", why, authority=A_VALUATION_ASSUMPTIONS),
            horizon_window=missing("horizon_window", "Horizon 區間（照抄 implied return）", why, authority=A_IMPLIED_RETURN),
            current_annualized_implied_return=missing("current_annualized_implied_return", "現價的年化隱含價格報酬", why,
                                                      authority=A_IMPLIED_RETURN),
            entry_price=missing("entry_price", "Analytical entry price", why, authority=A_ENTRY),
            price_to_entry_gap=missing("price_to_entry_gap", "現價相對門檻價", why, authority=A_ENTRY),
            hurdle_comparison=missing("hurdle_comparison", "現價 vs 門檻價（算術比較）", why, authority=A_ENTRY),
            assessment=missing("entry_assessment", "這次評估能不能當 clean 讀", why, authority=A_ENTRY),
            trace=(), epistemics=missing("entry_epistemics", "entry logic 的認識論分解", why, authority=A_ENTRY),
            selection=None, is_not=ENTRY_IS_NOT,
        )

    if result is None:
        return _absent(reason or "本次未執行 entry model（呼叫端未注入）")

    ent_refresh = refresh.get("entry_assessment:entry_assessment")
    base_status = _refresh_status(ent_refresh)
    target = result.target_period
    price = result.current_price
    upstream_known = result.implied_return_status == "available" and result.fair_value is not None
    upstream_why = f"上游 implied return 缺席：{result.implied_return_reason or '未知'}（缺席不是 0）"

    convention_datum = Datum(
        key="entry_convention", label="要求報酬的 convention", value=result.convention, status="available",
        basis="deterministic", authority=A_ENTRY, method=result.model_version, as_of=reference_day,
        reason="v1 只有一種：年化要求價格報酬；多一種 convention 就要多一段算術")
    c = result.criterion
    if c is not None:
        c_refresh = refresh.get(f"entry_criterion:{c.criterion_id}")
        c_deps = {"criterion_id": c.criterion_id, "convention": c.convention, "author": c.author,
                  "created_at": c.created_at.isoformat(), "supersedes_id": c.supersedes_id,
                  "reference_refs": list(c.reference_refs), "persisted": c.author.lower() != "sandbox",
                  "basis": c.basis, **_refresh_deps(c_refresh)}
        criterion_datum = Datum(
            key="entry_criterion", label=f"Entry criterion：要求年化價格報酬（{c.author} 宣告）", value=c.value,
            status=_refresh_status(c_refresh), basis=c.basis, authority=A_ENTRY_CRITERIA, unit="ratio",
            as_of=c.created_on, reason=c.rationale, dependencies=c_deps)
        required_datum = Datum(
            key="required_annualized_return", label="要求年化價格報酬（投資人政策，不是研究判斷）", value=c.value,
            status=_refresh_status(c_refresh), basis=c.basis, authority=A_ENTRY_CRITERIA, unit="ratio",
            as_of=c.created_on, dependencies={"criterion_id": c.criterion_id, "persisted": c.author.lower() != "sandbox"})
    else:
        why_c = result.criterion_reason or "沒有生效的 entry criterion"
        criterion_datum = missing("entry_criterion", "Entry criterion（投資人的要求報酬判準）", why_c, authority=A_ENTRY_CRITERIA)
        required_datum = missing("required_annualized_return", "要求年化價格報酬", why_c, authority=A_ENTRY_CRITERIA)
    current_price_datum = (
        Datum(key="current_price", label="現價（Engine C；照抄 implied return 的起點）", value=price.value, status="available",
              basis="observation", authority=A_SNAP, unit=f"quote_unit（{price.unit or '未知'}）", as_of=price.bar_date,
              evidence_refs=tuple(price.evidence_refs))
        if price.is_known else missing("current_price", "現價（Engine C）", price.reason or "無現價", authority=A_SNAP))
    fair_value_datum = (
        Datum(key="fair_value", label=f"Fair value（{target.label if target else '?'}；照抄 implied return）",
              value=result.fair_value, status="available", basis="deterministic", authority=A_VALUATION,
              unit=_unit("currency_per_share"), as_of=reference_day, reason="照抄，不重算",
              dependencies={"currency": result.fair_value_currency,
                            "assumption_ids": [a for a in result.research_assumption_ids if not a.startswith("ha_")]})
        if result.fair_value is not None else
        missing("fair_value", "Fair value（照抄 implied return）", upstream_why, authority=A_VALUATION))
    value_date_datum = (
        Datum(key="value_date", label=f"fair value 是哪一天的值（{result.value_date_semantics}）", value=result.value_date,
              status="available", basis="session_judgment", authority=A_VALUATION_ASSUMPTIONS, unit="date",
              as_of=reference_day, dependencies={"value_date_semantics": result.value_date_semantics})
        if result.value_date is not None else
        missing("value_date", "fair value 是哪一天的值", upstream_why, authority=A_VALUATION_ASSUMPTIONS))
    window_datum = (
        Datum(key="horizon_window", label="Horizon 區間（照抄 implied return）",
              value={"horizon_start": result.horizon_start, "horizon_end": result.horizon_end,
                     "holding_period_days": result.holding_period_days, "alignment": result.alignment},
              status="available", basis="deterministic", authority=A_IMPLIED_RETURN, as_of=reference_day,
              dependencies={"horizon_assumption_id": result.horizon.assumption_id if result.horizon else None,
                            "alignment": result.alignment})
        if result.horizon_start is not None and result.horizon_end is not None and result.holding_period_days is not None
        else missing("horizon_window", "Horizon 區間（照抄 implied return）", upstream_why, authority=A_IMPLIED_RETURN))
    current_ann_datum = (
        Datum(key="current_annualized_implied_return", label="現價的年化隱含價格報酬（照抄 implied return）",
              value=result.current_annualized_implied_return, status="available", basis="deterministic",
              authority=A_IMPLIED_RETURN, unit="ratio", as_of=price.bar_date,
              dependencies={"input_dependency": result.input_dependency})
        if result.current_annualized_implied_return is not None else
        missing("current_annualized_implied_return", "現價的年化隱含價格報酬",
                upstream_why if not upstream_known else "上游未年化（持有期間不足 1 天）", authority=A_IMPLIED_RETURN))
    # ⚠ 這一格是上游照抄值：**缺判準時仍然看得見**（fair value／horizon 也是）——讀者要先知道「現在的年化隱含報酬
    # 是多少」才知道自己要不要宣告 hurdle；把它跟本層自己算的門檻價一起吞掉會讓 missing 看起來比實際更空。

    if result.is_known:
        note = (f"；refresh={ent_refresh.state}：{ent_refresh.reasons[0]}"
                if ent_refresh is not None and ent_refresh.state != CURRENT else "")
        deps = {"input_dependency": result.input_dependency, "criterion_basis": result.criterion_basis,
                "criterion_id": result.criterion_id, "research_assumption_ids": list(result.research_assumption_ids),
                "observation_refs": list(result.observation_refs),
                "horizon_start": result.horizon_start.isoformat(), "horizon_end": result.horizon_end.isoformat(),
                "holding_period_days": result.holding_period_days,
                "value_date": result.value_date.isoformat() if result.value_date else None,
                "value_date_semantics": result.value_date_semantics, "alignment": result.alignment,
                "convention": result.convention, **_refresh_deps(ent_refresh)}
        assessment_status = ("review_required" if result.assessment == "review_required" else base_status)
        entry_price_datum = Datum(
            key="entry_price", label=f"Analytical entry price（現價等於它時年化隱含報酬＝要求報酬；{result.horizon_start} → {result.horizon_end}）",
            value=result.entry_price, status=base_status, basis="deterministic", authority=A_ENTRY,
            method=f"{result.formulas['entry_price']}（{result.model_version}）", unit=_unit("currency_per_share"),
            as_of=price.bar_date, evidence_refs=tuple(result.observation_refs),
            reason=(f"calculation=deterministic；input_dependency={result.input_dependency}"
                    f"（{BASIS_LABEL.get(str(result.input_dependency), result.input_dependency)}）；hurdle 是投資人政策；"
                    + ENTRY_IS_NOT[0] + note),
            dependencies=deps)
        gap_datum = Datum(
            key="price_to_entry_gap", label="現價相對門檻價（正值＝現價高於門檻價）",
            value={"relative": result.price_to_entry_gap, "absolute": result.price_to_entry_gap_abs},
            status=base_status, basis="deterministic", authority=A_ENTRY, method=result.formulas["price_to_entry_gap"],
            unit=f"ratio／{_unit('currency_per_share')}", as_of=price.bar_date, dependencies=deps)
        comparison_datum = Datum(
            key="hurdle_comparison", label="現價 vs 門檻價（算術比較，不是 action）", value=result.hurdle_comparison,
            status=base_status, basis="deterministic", authority=A_ENTRY, method=result.formulas["hurdle_comparison"],
            as_of=price.bar_date, reason=ENTRY_IS_NOT[0], dependencies=deps)
        assessment_datum = Datum(
            key="entry_assessment", label="這次評估能不能當 clean 讀（alignment／refresh）",
            value={"state": result.assessment, "alignment": result.alignment, "reason": result.assessment_reason},
            status=assessment_status, basis="deterministic", authority=A_ENTRY, as_of=reference_day,
            reason=result.assessment_reason, dependencies=deps)
        epistemics_datum = Datum(
            key="entry_epistemics", label="entry logic 的認識論分解（算術 vs 研究判斷 vs 投資人政策）",
            value=dict(result.epistemics), status="available", basis="deterministic", authority=A_ENTRY, as_of=reference_day,
            method="純計數與選取：列出哪些是確定性算術、哪些輸入是研究判斷、哪一格是投資人政策；one_sentence 是機器組出的一句話")
        section_status = _worst_status(base_status, assessment_status)
        meta_reason = result.assessment_reason if result.assessment == "review_required" else None
    else:
        why = f"{result.reason}（缺席不是 0）"
        entry_price_datum = missing("entry_price", "Analytical entry price", why, authority=A_ENTRY)
        gap_datum = missing("price_to_entry_gap", "現價相對門檻價", why, authority=A_ENTRY)
        comparison_datum = missing("hurdle_comparison", "現價 vs 門檻價（算術比較）", why, authority=A_ENTRY)
        assessment_datum = missing("entry_assessment", "這次評估能不能當 clean 讀", why, authority=A_ENTRY)
        epistemics_datum = missing("entry_epistemics", "entry logic 的認識論分解", why, authority=A_ENTRY)
        section_status = "missing"
        meta_reason = result.reason
    trace: list[Datum] = []
    for step in result.steps:
        authority = {"criterion_input": A_ENTRY_CRITERIA, "return_input": A_IMPLIED_RETURN, "price_input": A_SNAP,
                     "derived": A_ENTRY}[step.kind]
        if step.value is None:
            trace.append(missing(f"entry_step:{step.key}", step.label, step.reason or "上游缺料（不是 0）", authority=authority))
            continue
        trace.append(Datum(
            key=f"entry_step:{step.key}", label=step.label, value=step.value, status="available", basis=step.basis,
            authority=authority, method=step.formula, unit=_unit(step.unit), as_of=reference_day,
            evidence_refs=tuple(step.observation_refs), reason=step.reason,
            dependencies={"kind": step.kind, "assumption_ids": list(step.assumption_ids),
                          "input_dependency": step.input_dependency}))
    selection = EvidenceSelectionCounts(
        input_count=result.criterion_selection.input_count, accepted_count=result.criterion_selection.accepted_count,
        filtered_count=result.criterion_selection.filtered_count, reasons=dict(result.criterion_selection.reasons))
    meta = SectionMeta(
        status=section_status, basis="deterministic" if result.is_known else "none", authority=A_ENTRY,
        capability=CAP_ANALYTICAL_ENTRY_THRESHOLD, reason=meta_reason, as_of=reference_day,
        warnings=(ENTRY_EPISTEMIC_WARNING,
                  "判準缺席就 missing（理由明寫「缺的是投資門檻判斷」）；alignment 不對齊只能 review_required，不得冒充 clean。",
                  "entry logic " + "；".join(ENTRY_IS_NOT), *result.warnings),
    )
    return EntryLogicSection(
        meta=meta, convention=convention_datum, criterion=criterion_datum, required_annualized_return=required_datum,
        current_price=current_price_datum, fair_value=fair_value_datum, value_date=value_date_datum,
        horizon_window=window_datum, current_annualized_implied_return=current_ann_datum, entry_price=entry_price_datum,
        price_to_entry_gap=gap_datum, hurdle_comparison=comparison_datum, assessment=assessment_datum,
        trace=tuple(trace), epistemics=epistemics_datum, selection=selection, is_not=ENTRY_IS_NOT,
        period=target.label if target else None, period_end=target.end if target else None,
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
    judged_on: date | None = None, absent_status: str = "missing", status: str | None = None,
    refresh: AffectedArtifact | None = None,
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
    note = trace.note if trace else None
    if refresh is not None and refresh.state != CURRENT:
        note = f"[refresh={refresh.state}] {refresh.reasons[0]}" + (f"｜{note}" if note else "")
    return Datum(
        key=f"{axis}_score", label=label, value=value,
        status=status or ("stale" if stale else "available"), basis="session_judgment", authority=A_SESSION,
        method=(trace.rule_version if trace else None), unit="ordinal_0_1",
        as_of=judged_on or signal.as_of, evidence_refs=_refs(trace.evidence_refs) if trace else (),
        reason=note, dependencies=(_refresh_deps(refresh) if refresh is not None else None),
    )


def _text_datum(
    key: str, label: str, text: str | None, *, basis: str, authority: str,
    stale: bool, as_of: date | None, missing_reason: str, absent_status: str = "missing",
    status: str | None = None,
) -> Datum:
    if not text or not str(text).strip():
        return _absent(key, label, missing_reason, status=absent_status, authority=authority)
    return Datum(key=key, label=label, value=str(text), status=status or ("stale" if stale else "available"),
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
    fundamental_model: FundamentalModelResult | None = None,
    fundamental_model_reason: str | None = None,
    valuation: ValuationResult | None = None,
    valuation_reason: str | None = None,
    valuation_records: Sequence[ValuationAssumption] = (),
    implied_return: ImpliedReturnResult | None = None,
    implied_return_reason: str | None = None,
    horizon_records: Sequence[HorizonAssumption] = (),
    entry: EntryAssessmentResult | None = None,
    entry_reason: str | None = None,
    entry_records: Sequence[EntryCriterion] = (),
    reverse: Any = None,
    reverse_reason: str | None = None,
    today: date | None = None,
    refresh_changes: Sequence[ChangeEvent] | None = None,
    assumption_records: Sequence[OperatingAssumption] = (),
    metric_observations: Sequence[MetricObservation] = (),
    change_detection: str | None = None,
    refresh_notes: Sequence[str] = (),
) -> AlphaInvestmentView:
    """組裝一家公司的 `AlphaInvestmentView`。所有參數都是已取好的既有 authority 輸出。"""
    today = today or date.today()
    context = build.context
    ticker = str(context.ticker)
    company_id = str(context.company_id) if context.company_id else None
    identity = dict(identity or {})
    quote_unit = identity.get("market_quote_unit")
    market_currency = identity.get("market_currency")

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
        # fundamental model 自己帶 as_of（假設 created_at／觀測 recorded_at／共識 captured_at 都
        # 依它過濾）；標記不符就是呼叫端拿別的時點跑的，拒收（INV-6）。
        if fundamental_model is not None and fundamental_model.as_of != context.as_of:
            fundamental_model_reason = (
                f"as-of {as_of_iso} 模式：傳入的 fundamental model 以 as_of="
                f"{fundamental_model.as_of} 執行，與 context 不符，拒收（INV-6）")
            fundamental_model = None
        if valuation is not None and valuation.as_of != context.as_of:
            valuation_reason = (f"as-of {as_of_iso} 模式：傳入的 valuation 以 as_of={valuation.as_of} 執行，"
                                "與 context 不符，拒收（INV-6）")
            valuation = None
        if implied_return is not None and implied_return.as_of != context.as_of:
            implied_return_reason = (f"as-of {as_of_iso} 模式：傳入的 implied return 以 as_of={implied_return.as_of} 執行，"
                                     "與 context 不符，拒收（INV-6）")
            implied_return = None
        if entry is not None and entry.as_of != context.as_of:
            entry_reason = (f"as-of {as_of_iso} 模式：傳入的 entry assessment 以 as_of={entry.as_of} 執行，"
                            "與 context 不符，拒收（INV-6）")
            entry = None
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

    # ---- Refresh／dependency impact：單一 authority（alpha.refresh），這裡只消費 -------------
    # digest mismatch 只是「判斷對的是舊 context」這個**事實**（留在 identity.signal.context_matches）；
    # 它**不再**自動讓 Q2–Q5／thesis／情境全部 stale——那是 Step 0（2026-09-06）抓到的 over-invalidation。
    # 判斷型成果的 status 改由 resolver 依變化的種類決定；呼叫端沒跑變更偵測（refresh_changes=None）時
    # 退回舊行為（digest 不符即 stale）並在 refresh section 標 change_detection=not_run。
    build_at = build_instant(reference_day)
    judged_at = build_instant(judged_on) if judged_on else None
    artifacts = artifacts_from_signal(signal, judged_at=judged_at,
                                      structural_trace=build.structural_trace, build_at=build_at)
    artifacts += artifacts_from_model(fundamental_model, build_at=build_at,
                                      assumption_records=assumption_records)
    artifacts += artifacts_from_valuation(
        valuation, build_at=build_at, assumption_records=valuation_records,
        base_period_end=(fundamental_model.base_period.end if fundamental_model and fundamental_model.base_period else None))
    artifacts += artifacts_from_implied_return(
        implied_return, build_at=build_at, horizon_records=horizon_records,
        base_period_end=(fundamental_model.base_period.end if fundamental_model and fundamental_model.base_period else None))
    artifacts += artifacts_from_entry(entry, build_at=build_at, criterion_records=entry_records)
    artifacts += artifacts_from_context(context, build_at=build_at)
    detection = change_detection or ("not_run" if refresh_changes is None else "authority_time_series")
    changes = list(refresh_changes or ())
    if (refresh_changes is not None and signal_stale and judged_at is not None
            and not any(c.observed_at > judged_at for c in changes)):
        # 殘餘：digest 變了但沒有任何已分類的變化——必須現形，不得靜默當 current（保守：review_required）。
        changes.append(ChangeEvent(
            change_type=CONTEXT_DIGEST, ticker=ticker, company_id=company_id, authority=A_SESSION,
            changed_ref=context.digest, observed_at=build_at,
            old_version=judged_digest, new_version=context.digest,
            material_fields=("research_context_digest",),
            detail="ResearchContext digest 已變，但變更偵測沒有任何已分類的變化能解釋——殘餘差異未分類"))
    report = resolve_refresh(ticker=ticker, company_id=company_id, artifacts=artifacts, changes=changes,
                             observations=metric_observations, as_of=context.as_of, today=today)
    refresh_by_key = {a.key: a for a in report.artifacts}
    thesis_refresh = refresh_by_key.get(f"thesis:{THESIS_ARTIFACT_ID}")
    axis_refresh = {axis: refresh_by_key.get(f"axis:{axis}") for axis in AXES}
    if refresh_changes is None:
        judgment_status = "stale" if signal_stale else "available"
        axis_status = {axis: judgment_status for axis in AXES}
    else:
        judgment_status = _refresh_status(thesis_refresh)
        axis_status = {axis: _refresh_status(axis_refresh[axis]) for axis in AXES}
        if signal is not None:
            if judgment_status != "available":
                stale_reason = "；".join(thesis_refresh.reasons[:2]) if thesis_refresh else stale_reason
            elif signal_stale:
                kinds = sorted({c.change_type for c in report.changes})
                stale_reason = ("判斷對的是舊 context（digest 已變），但已分類的變化不動搖這份判斷"
                                f"（{', '.join(kinds) or '無變化'}）")
            else:
                stale_reason = None
    judgment_not_current = judgment_status != "available"

    fund = _fundamental_parts(
        fundamental_model, fundamental_model_reason, reference_day=reference_day,
        reporting_unit=f"reporting_currency（{market_currency or '未知'}；未正規化）",
        refresh=refresh_by_key,
    )
    valuation_section = _valuation_section(
        valuation, valuation_reason, reference_day=reference_day,
        reporting_unit=f"reporting_currency（{market_currency or '未知'}；未正規化）",
        refresh=refresh_by_key,
    )
    implied_return_section = _implied_return_section(
        implied_return, implied_return_reason, reference_day=reference_day,
        reporting_unit=f"reporting_currency（{market_currency or '未知'}；未正規化）",
        refresh=refresh_by_key,
    )
    entry_section = _entry_logic_section(
        entry, entry_reason, reference_day=reference_day,
        reporting_unit=f"reporting_currency（{market_currency or '未知'}；未正規化）",
        refresh=refresh_by_key,
    )

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
    # Phase 2 驗收（2026-09-06）抓到：假設引用的 engine_c://manual_observation／consensus_estimate
    # 在模型端解析得到，卡片自己的 evidence index 卻沒有——讀者拿著卡片對不回引用。
    # 模型的 evidence 已在 as-of 下過濾（recorded_at／captured_at ≤ T），放進來不會漏未來。
    if fundamental_model is not None:
        for ref in fundamental_model.evidence:
            evidence_pool.setdefault(ref.ref, ref)
    if valuation is not None:
        for ref in valuation.evidence:
            evidence_pool.setdefault(ref.ref, ref)
    if implied_return is not None:
        for ref in implied_return.evidence:
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
        refresh_state=(thesis_refresh.state if (signal is not None and thesis_refresh) else None),
    )
    identity_warnings: list[str] = []
    if quote_unit and market_currency and quote_unit != market_currency:
        identity_warnings.append(
            f"報價單位 {quote_unit} ≠ 結算幣別 {market_currency}：以報價單位計的欄位"
            "（price／forward_eps／market_cap）與結算幣別差 100 倍，跨標的比較前必須正規化"
        )
    identity_section = IdentitySection(
        ticker=ticker, company_id=company_id,
        # 面向人的標籤。registry 有 `display_name` 就用它，沒有就退回 `co:*（ticker）`——
        # **不從 company_id 猜名字**（`co:iqe` → 「Iqe」是編出來的）。AGENTS 的判準是
        # 「不得假設使用者能從 co:* ID 或內部術語自行還原主詞」，而缺名字時誠實露出 ID
        # 比編一個像模像樣的名字安全。
        company_label=(str(identity.get("display_name")) if identity.get("display_name")
                       else (f"{company_id}（{ticker}）" if company_id else ticker)),
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
                                   judged_on=judged_on, absent_status=signal_absent_status,
                                   status=axis_status[axis],
                                   refresh=(axis_refresh[axis] if refresh_changes is not None else None))
        for axis in AXES if axis != "structural"
    }
    all_scores = tuple(q1 if axis == "structural" else session_scores[axis] for axis in AXES)
    vp_as_of = None
    if decision_facts and decision_facts.variant_perception_created_at:
        vp_as_of = _as_date(decision_facts.variant_perception_created_at)
    variant_section = VariantViewSection(
        meta=SectionMeta(
            status=judgment_status if signal else signal_absent_status,
            basis="session_judgment" if signal else "none",
            authority=A_SESSION if signal else None,
            reason=(stale_reason if signal else no_signal),
            as_of=judged_on,
            freshness=("stale" if judgment_not_current else "available") if signal else "missing",
            warnings=("thesis／variant view／bull-base-bear 是 session（LLM）判斷，"
                      "不是 deterministic model output；引用皆已解析到 ResearchContext 內的證據",),
        ),
        thesis=_text_datum("thesis", "Thesis", signal.thesis if signal else None,
                           basis="session_judgment", authority=A_SESSION, stale=signal_stale,
                           as_of=judged_on, missing_reason=no_signal,
                           absent_status=signal_absent_status, status=judgment_status),
        variant_view=_text_datum("variant_view", "Variant perception（市場隱含 X／本 thesis 認為 Y／催化劑 Z）",
                                 signal.variant_view if signal else None,
                                 basis="session_judgment", authority=A_SESSION, stale=signal_stale,
                                 as_of=judged_on, missing_reason=no_signal,
                                 absent_status=signal_absent_status, status=judgment_status),
        direction=(Datum(key="direction", label="方向", value=signal.direction,
                         status=judgment_status,
                         basis="session_judgment", authority=A_SESSION, as_of=judged_on)
                   if signal else _absent("direction", "方向", no_signal,
                                          status=signal_absent_status, authority=A_SESSION)),
        confidence=(Datum(key="confidence", label="信心（session 自評）", value=signal.confidence,
                          status=judgment_status,
                          basis="session_judgment", authority=A_SESSION, unit="confidence_0_1",
                          as_of=judged_on,
                          reason="session 自評的信心（0..1），不是量測的勝率")
                    if signal else _absent("confidence", "信心（session 自評）", no_signal,
                                           status=signal_absent_status, authority=A_SESSION)),
        expected_horizon=_text_datum("expected_horizon", "預期期間",
                                     signal.expected_horizon if signal else None,
                                     basis="session_judgment", authority=A_SESSION,
                                     stale=signal_stale, as_of=judged_on,
                                     missing_reason=no_signal, absent_status=signal_absent_status,
                                     status=judgment_status),
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
        financial_causal_model=fund.financial_causal,
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
        _observation("revenue_estimate_next_fy", "「下一會計年度」營收共識（yfinance +1y，絕對值）",
                     c.revenue_estimate_next_fy, authority=A_SNAP, unit=reporting_unit,
                     as_of=cons_as_of, freshness=cons_fresh, evidence_refs=consensus_refs,
                     method="yfinance revenue_estimate +1y avg；不得跨標的比大小",
                     reason="⚠ +1y 是相對於抓取日的標籤，不是會計年度身分（COHR 在 FY2026 財報後它指 FY2028）；"
                            "要與內部估計同期比較請用 fiscal_items（帶 fiscal_period_end）"),
        _observation("revenue_estimate_next_fy_growth", "下一會計年度營收共識成長",
                     c.revenue_estimate_next_fy_growth, authority=A_SNAP, unit="ratio",
                     as_of=cons_as_of, freshness=cons_fresh, evidence_refs=consensus_refs,
                     method="營收成長，與 market_implied_eps_growth（EPS 成長）分母不同，不得相減"),
        _observation("estimate_revision_30d", "forward EPS 30 個觀測修正幅度",
                     c.estimate_revision_30d, authority=A_ESTIMATES, unit="ratio",
                     as_of=cons_as_of, freshness=cons_fresh, evidence_refs=consensus_refs,
                     method="engine_c.estimates.revision_over：同一標的、**同一個 forward 會計年度**"
                            "導出 forward EPS 的序列比值",
                     missing_reason="序列太短、起點為 0、跨越正負號，或窗口兩端的 forward 會計年度"
                                    "身分不明／不相同（rollover）——算不出來不是沒修正"),
    )
    cons_has_snapshot = cons_fresh in ("available", "stale")
    fiscal_periods = sorted({d.dependencies.get("period") if d.dependencies else d.key.rsplit("_", 1)[-1]
                             for d in fund.fiscal_items})
    consensus_section = ConsensusSection(
        meta=SectionMeta(
            status=("stale" if cons_fresh == "stale" else "partial") if cons_has_snapshot else "missing",
            basis="observation" if cons_has_snapshot else "none",
            authority=A_SNAP, as_of=cons_as_of, freshness=cons_fresh,
            reason=("Engine C 無這檔的共識快照" if not cons_has_snapshot else
                    "快照欄位覆蓋到 next-FY 營收共識、forward／trailing PE、EV/營收、目標價均值與導出 forward EPS；"
                    + (f"會計年度別 EPS／營收共識（fiscal_items）覆蓋 {'、'.join(fiscal_periods)}" if fund.fiscal_items
                       else "會計年度別 EPS／營收共識（consensus_estimates）尚無列")),
            warnings=("這不是 multi-year consensus earnings model：fiscal_items 只到 provider 的 0y／+1y 兩個年度，"
                      "沒有目標價高低區間、沒有逐位分析師分布；修正歷史只有由 price/pe_forward 導出的序列。",
                      "快照裡的 forward_eps 是 price/pe_forward 導出、revenue_estimate_next_fy 是相對標籤 +1y——"
                      "兩者都不是會計年度身分明確的共識；同期比較只用 fiscal_items。")
            + ((f"⚠ 估計修正不可比：{estimate_revision.get('not_comparable_reason')}"
                f"（同窗口股價 {estimate_revision.get('price_change', 0):+.1%}）。"
                "forward year rollover 不是 analyst estimate revision，不得當 Q4 正向證據。",)
               if estimate_revision and not estimate_revision.get("comparable") else ()),
        ),
        items=consensus_items,
        coverage_note=("partial：snapshot（next-FY revenue estimate ＋ forward／trailing PE ＋ EV/Rev ＋ target mean ＋ "
                       "derived forward EPS）＋ fiscal_items（FY-identified EPS／revenue avg／low／high／n／year_ago，"
                       "只到 0y 與 +1y）；缺 multi-year EPS（第三年起）、target high/low、per-analyst distribution、"
                       "margin consensus"),
        fiscal_items=fund.fiscal_items,
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
         if estimate_revision and estimate_revision.get("comparable") else
         # ⚠ 不可比不是缺料：序列在、股價變動也算得出來，但兩端不是同一個會計年度的估計。
         # 用 not_applicable ＋ 原文理由，讓「換了一把尺」不會被讀成「分析師上修」（2026-09-07）。
         Datum(key="estimate_revision_vs_price", label="估計修正 vs 股價變動（Q4 原料）",
               value=None, status="not_applicable", basis="none", authority=A_ESTIMATES,
               reason=f"不可比：{estimate_revision.get('not_comparable_reason')}"
                      f"（同窗口股價 {estimate_revision.get('price_change', 0):+.1%}）"
                      "。⚠ forward year rollover 不是 analyst estimate revision，不得當 Q4 正向證據")
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
    # H. Internal Fundamental View（alpha/fundamental 的輸出；read model 只選取）
    # =======================================================================
    internal_section = fund.internal_section

    # =======================================================================
    # I. Earnings Bridge（每一格：基期觀測／明示假設／確定性 derived；缺假設＝missing）
    # =======================================================================
    earnings_bridge_section = EarningsBridgeSection(
        meta=fund.bridge_meta,
        steps=fund.bridge_steps,
        assumptions=fund.bridge_assumptions,
        sensitivities=fund.bridge_sensitivities,
        selection=fund.bridge_selection,
        period=fund.bridge_period,
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
    gap_has = q4.is_known or any(d.is_known for d in gap_proxies) or fund.has_numeric_gap
    if q4.is_known:
        gap_basis, gap_authority = "session_judgment", A_SESSION
    elif fund.has_numeric_gap:
        gap_basis, gap_authority = "deterministic", A_COMPARE
    elif gap_has:
        gap_basis, gap_authority = "heuristic_proxy", A_IMPLIED
    else:
        gap_basis, gap_authority = "none", A_IMPLIED
    expectation_gap_section = ExpectationGapSection(
        meta=SectionMeta(
            status=((q4.status if q4.status in ("stale", "review_required", "invalidated") else "partial")
                    if gap_has else "missing"),
            basis=gap_basis, authority=gap_authority,
            capability=CAP_NUMERIC_EXPECTATION_GAP if fund.has_numeric_gap else None,
            reason=(("Q4 是 session 的 ordinal 判斷；numeric_comparisons 是內部假設推出的數字與同期共識的差——"
                     "兩者並存、各自標示，數值 gap 不取代 Q4" if fund.has_numeric_gap else
                     "Q4 是 session 的 ordinal 判斷；數值 gap 見 internal_vs_consensus 的缺席原因；"
                     "internal-vs-price-implied 尚未建模")
                    if gap_has else "無 session 判斷、無 proxy 原料、無數值 gap"),
            warnings=(
                "Q4 的 ordinal 等級不是 internal EPS − consensus EPS；numeric_comparisons 才是那個差，且它的輸入是假設。",
                "market_implied_eps_growth（EPS）與 revenue_estimate_next_fy_growth（營收）分母不同，不得相減成 gap。",
                "estimate_revision_vs_price 是原料：正值只代表估計跑在股價前面，不是可行動的 gap。",
                "數值 gap 只在同一會計期間、同一口徑（GAAP／non-GAAP）、同幣別時才算；不合就標 not_applicable，不硬減。",
            ),
        ),
        session_judgment=q4, proxies=gap_proxies,
        internal_vs_consensus=fund.internal_vs_consensus,
        internal_vs_price_implied=not_modeled("internal_vs_price_implied", "內部估計 vs 價格隱含（數值）",
                                              "價格隱含側只有 PE 比值 proxy，沒有 reverse DCF（價格隱含的成長／利潤率解）；"
                                              "fair value 與現價的差住 valuation section，它是 fair_value − price，"
                                              "不是內部基本面 vs 價格隱含基本面"),
        numeric_comparisons=fund.comparisons,
        opinion_stance=fund.opinion_stance,
        reverse_bridge=_reverse_datum(reverse, reverse_reason, reference_day=today),
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
            status=(judgment_status if conditions else "available") if has_falsification else "missing",
            basis="session_judgment" if conditions else ("narrative" if narrative_disproof.is_known else "none"),
            authority=A_SESSION if conditions else A_COVERAGE,
            capability=CAP_STRUCTURED_DISPROOF,
            reason=(None if has_falsification else "沒有任何 disproof 條件——L7 要求每條 thesis 必帶"),
            warnings=("L7 三件套（條件／核查頻率／48 小時動作）由 alpha.contracts.DisproofCondition 強制；"
                      "runtime 只監看 expiry 與催化劑日期，不會自動判定條件是否已被觸發。",),
        ),
        conditions=conditions, narrative_disproof=narrative_disproof, thesis_status=thesis_status_datum,
        expiry_watch=watch_state_datum,
        automatic_invalidation=Datum(
            key="automatic_invalidation", label="依賴失效引擎（refresh／dependency impact）",
            value={"capability": CAP_DEPENDENCY_IMPACT, "overall": report.overall,
                   "evaluates": ["已分類的 ChangeEvent（authority 時序）", "假設自帶的 machine-readable review_conditions",
                                 "Event Watch 喚醒（disproof_signal）", "L7 核查頻率到期（stale）"],
                   "does_not": ["解析自然語言的 disproof 條件", "改 thesis／假設／判斷", "自動呼叫 LLM"]},
            status="partial", basis="deterministic", authority=A_REFRESH, as_of=reference_day,
            method="alpha.refresh.resolve_refresh（" + report.policy_version + "）",
            reason=("它決定 impact state（review_required／invalidated／recalculate／stale），不決定真假；"
                    "自然語言條件仍由人在核查頻率時判讀（capability＝" + CAP_DEPENDENCY_IMPACT
                    + "，非 " + CAP_AUTOMATIC_INVALIDATION + "）"),
        ),
    )

    # =======================================================================
    # M. Scenario（narrative，不是 quantitative scenario model）
    # =======================================================================
    def _scenario(key: str, label: str, text: str | None) -> Datum:
        return _text_datum(key, label, text, basis="narrative", authority=A_SESSION,
                           stale=signal_stale, as_of=judged_on, missing_reason=no_signal,
                           absent_status=signal_absent_status, status=judgment_status)

    scenario_section = ScenarioSection(
        meta=SectionMeta(
            status=judgment_status if signal else signal_absent_status,
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
        # Step 1：單點 fair value 有了（valuation section）；**逐情境**的目標估值仍然沒有。
        target_valuation=(
            Datum(key="target_valuation", label="目標估值（單點 fair value；非逐情境）",
                  value=valuation_section.fair_value.value, status=valuation_section.fair_value.status,
                  basis="deterministic", authority=A_VALUATION, unit=valuation_section.fair_value.unit,
                  as_of=reference_day, method=valuation_section.fair_value.method,
                  reason="照抄 valuation.fair_value；bull／base／bear 各自的目標估值與機率加權仍未建模")
            if valuation_section.fair_value.is_known else
            Datum(key="target_valuation", label="目標估值（單點 fair value；非逐情境）", value=None,
                  status=valuation_section.fair_value.status, basis="none", authority=A_VALUATION,
                  reason=f"valuation section：{valuation_section.fair_value.reason}；逐情境目標估值仍未建模")),
    )

    # =======================================================================
    # N. Downside（not_modeled）；implied return／entry logic 已於上方由 alpha.implied_return／alpha.entry 組裝
    # =======================================================================
    def _not_modeled_section(reason: str, items: Sequence[tuple[str, str]], confusions: Sequence[str]) -> NotModeledSection:
        return NotModeledSection(
            meta=SectionMeta(status="not_modeled", basis="none", reason=reason),
            items=tuple(not_modeled(k, l, reason) for k, l in items),
            not_to_be_confused_with=tuple(confusions),
        )

    downside_section = _not_modeled_section(
        "系統不產生下檔估計：沒有 bear case 的數值、沒有最大回撤模型。",
        (("downside", "下檔幅度"), ("max_drawdown_estimate", "最大回撤估計")),
        ("scenarios.bear 是散文，不是下檔數字", "falsification 的條件是出場觸發，不是下檔幅度",
         "entry_logic.entry_price 是門檻價不是下檔估計——現價高於它多少不是「會跌多少」"),
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
        status=("stale" if judgment_not_current else "available") if signal else "missing",
        as_of=judged_on,
        age_days=float((today - judged_on).days) if judged_on else None,
        reason=(f"refresh={thesis_refresh.state}：{stale_reason}" if (thesis_refresh and judgment_not_current)
                else stale_reason) if signal else no_signal))
    dec_as_of = _as_date(decision_facts.coverage_created_at) if decision_facts else None
    freshness_items.append(FreshnessItem(
        source="decision_store_coverage",
        status="available" if decision_facts and dec_as_of else "missing",
        as_of=dec_as_of, age_days=float((reference_day - dec_as_of).days) if dec_as_of else None,
        reason=(None if dec_as_of else (decision_facts_reason or "無 coverage assessment"))
        if not (dec_as_of and as_of_mode) else f"距 as-of {as_of_iso} 的天數；事實已依 as_of 歷史過濾"))

    # =======================================================================
    # P. Refresh／dependency status（只組裝 alpha.refresh 的輸出）
    # =======================================================================
    attention = report.attention
    refresh_section = RefreshStatusSection(
        meta=SectionMeta(
            status="available" if report.artifacts else "missing",
            basis="deterministic" if report.artifacts else "none", authority=A_REFRESH,
            capability=CAP_DEPENDENCY_IMPACT, as_of=reference_day,
            reason=(f"overall={report.overall}；需要動作 {len(attention)} 項；變更偵測={detection}"
                    if report.artifacts else "沒有任何研究成果可評估（無判斷、無模型）"),
            warnings=("state 只回答「相對於依賴，這個成果還能不能當 current」——不是新事實、不是新判斷、不改 thesis。",
                      "recalculate＝確定性輸入變了（不需判斷）；review_required＝依據 material change（要人重看）；"
                      "invalidated＝前提不成立；stale＝只是排程到期；superseded＝歷史。",
                      "price-only 變化不觸發任何研究判斷複查（v1 materiality 立場，見 alpha/refresh/policy.py）。"),
        ),
        overall=report.overall, policy_version=report.policy_version, counts=report.counts,
        items=tuple(RefreshItem(
            artifact_type=a.artifact_type, artifact_id=a.artifact_id, label=a.label, state=a.state,
            reasons=a.reasons, changed_refs=a.changed_refs, dependency_refs=a.dependency_refs,
            detected_at=a.detected_at, established_at=a.established_at,
            required_action=a.required_action, propagated_from=a.propagated_from, kind=a.kind,
        ) for a in report.artifacts),
        changes=tuple(ChangeItem(
            change_id=c.change_id, change_type=c.change_type, authority=c.authority,
            changed_ref=c.changed_ref, observed_at=c.observed_at, effective_at=c.effective_at,
            old_version=c.old_version, new_version=c.new_version, material_fields=c.material_fields,
            detail=c.detail, target_artifact=c.target_artifact,
        ) for c in report.changes),
        excluded_changes=dict(report.excluded_changes), excluded_artifacts=dict(report.excluded_artifacts),
        notes=tuple(refresh_notes) + report.notes, digest=report.digest, change_detection=detection,
        judged_context_matches=(None if signal is None else not signal_stale),
    )

    warnings = [JUDGMENT_WARNING, CORRELATION_WARNING]
    if as_of_mode:
        warnings.append(
            f"as-of 視角（{as_of_iso}）：Engine A 投影、Engine C 時序、Decision Store 事實皆已依 as_of "
            "歷史過濾（cohort／decision／coverage／lifecycle 事件／variant perception 的時間戳）；"
            "thesis/*.json 與檢核點沒有歷史，一律 not_applicable；到期狀態以 as_of 為今天判定")
    if signal is not None and judgment_not_current:
        warnings.append(f"session 判斷 {STATUS_LABEL.get(judgment_status, judgment_status)}：{stale_reason}")
    if attention:
        counts = report.counts
        warnings.append(
            f"⚠ {len(attention)} 項研究成果需要動作（review_required {counts['review_required']}／"
            f"invalidated {counts['invalidated']}／recalculate {counts['recalculate']}／stale {counts['stale']}）"
            "——見 refresh_status；引擎不改任何判斷，只標 state")
    if detection == "not_run":
        warnings.append("refresh：本次未執行 authority 變更偵測，只評估了 core 可導出的變化"
                        "（排程到期、review 條件、會計期間推進）；digest 不符時沿用整份 stale 的舊語意")
    if signal is None:
        warnings.append("尚無 session 判斷：Q2–Q5、thesis、variant view、情境、disproof 條件皆缺；"
                        "跑 `python -m alpha research " + ticker + " -o packet.json` 產研究包後由 session 判斷")
    warnings.extend(identity_warnings)
    if problems:
        warnings.append("Decision Store 的 catalyst／disproof／expiry 設定不完整：" + "；".join(problems))
    if fund.has_numeric_gap:
        warnings.append(FUNDAMENTAL_EPISTEMIC_WARNING)
    warnings.extend(f"fundamental model：{w}" for w in fund.warnings)
    if valuation_section.fair_value.is_known:
        warnings.append(VALUATION_EPISTEMIC_WARNING)
    if implied_return_section.price_return.is_known:
        warnings.append(RETURN_EPISTEMIC_WARNING)
    if entry_section.entry_price.is_known:
        warnings.append(ENTRY_EPISTEMIC_WARNING)

    return AlphaInvestmentView(
        schema_version=SCHEMA_VERSION,
        identity=identity_section, variant_view=variant_section,
        structural_thesis=structural_section, causal_paths=causal_section,
        fundamentals=fundamentals_section, consensus=consensus_section,
        price_implied_expectations=price_implied_section,
        internal_fundamentals=internal_section, earnings_bridge=earnings_bridge_section,
        expectation_gap=expectation_gap_section, catalysts=catalyst_section,
        falsification=falsification_section, scenarios=scenario_section, valuation=valuation_section,
        implied_return=implied_return_section, downside=downside_section,
        entry_logic=entry_section, evidence=evidence_section,
        freshness=tuple(freshness_items), refresh_status=refresh_section, warnings=tuple(warnings),
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
    comparisons = {d.key.removeprefix("internal_vs_consensus_"): d
                   for d in view.expectation_gap.numeric_comparisons}
    internal_vs_consensus = {
        metric: ({"status": d.status, "relative_gap": (d.value or {}).get("relative_gap") if d.is_known else None,
                  "period": (d.value or {}).get("period") if d.is_known else None,
                  "reason": None if d.is_known else d.reason}
                 if d is not None else None)
        for metric, d in ((m, comparisons.get(m)) for m in ("eps", "revenue"))
    }
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
        # Step 0.5：refresh 摘要——只抄 refresh_status，不重算 impact
        "refresh": {
            "overall": view.refresh_status.overall,
            "change_detection": view.refresh_status.change_detection,
            "counts": {k: view.refresh_status.counts.get(k, 0)
                       for k in ("review_required", "invalidated", "recalculate", "stale")},
            "attention": [{"artifact": f"{i.artifact_type}:{i.artifact_id}", "state": i.state,
                           "reason": (i.reasons[0] if i.reasons else None)}
                          for i in view.refresh_status.items
                          if i.state in ("review_required", "invalidated", "recalculate", "stale")][:6],
        },
        # 內部假設推出的數字 vs 同期共識；None＝不可比／缺料（原因在 reason），不是 0
        "internal_vs_consensus": internal_vs_consensus,
        # Step 1：估值摘要——只抄 valuation section；gap 不是 expected return（renderer 不得改稱）
        "valuation": {
            "status": view.valuation.meta.status,
            "method": _val(view.valuation.method),
            "fair_value": _val(view.valuation.fair_value),
            "current_price": _val(view.valuation.current_price),
            "relative_gap": ((view.valuation.fair_value_gap.value or {}).get("relative_gap")
                             if view.valuation.fair_value_gap.is_known else None),
            "gap_status": view.valuation.fair_value_gap.status,
            "period": view.valuation.period,
            "reason": None if view.valuation.fair_value.is_known else view.valuation.fair_value.reason,
        },
        # Step 2：base-case implied return 摘要——只抄 implied_return section；**不是 expected return**
        "implied_return": {
            "status": view.implied_return.meta.status,
            "price_return": _val(view.implied_return.price_return),
            "annualized_price_return": _val(view.implied_return.annualized_price_return),
            "horizon_start": ((view.implied_return.horizon_window.value or {}).get("horizon_start").isoformat()
                              if view.implied_return.horizon_window.is_known else None),
            "horizon_end": ((view.implied_return.horizon_window.value or {}).get("horizon_end").isoformat()
                            if view.implied_return.horizon_window.is_known else None),
            "value_date_semantics": ((view.implied_return.value_date.dependencies or {}).get("value_date_semantics")
                                     if view.implied_return.value_date.is_known else None),
            "total_return_status": view.implied_return.total_return.status,
            "reason": None if view.implied_return.price_return.is_known else view.implied_return.price_return.reason,
        },
        # Step 3：entry logic 摘要——只抄 entry_logic section；**不是 buy／sell**，comparison 是算術比較
        "entry_logic": {
            "status": view.entry_logic.meta.status,
            "entry_price": _val(view.entry_logic.entry_price),
            "current_price": _val(view.entry_logic.current_price),
            "price_to_entry_gap": ((view.entry_logic.price_to_entry_gap.value or {}).get("relative")
                                   if view.entry_logic.price_to_entry_gap.is_known else None),
            "required_annualized_return": _val(view.entry_logic.required_annualized_return),
            "current_annualized_implied_return": _val(view.entry_logic.current_annualized_implied_return),
            "hurdle_comparison": _val(view.entry_logic.hurdle_comparison),
            "assessment": ((view.entry_logic.assessment.value or {}).get("state")
                           if view.entry_logic.assessment.is_known else None),
            "criterion_persisted": ((view.entry_logic.criterion.dependencies or {}).get("persisted")
                                    if view.entry_logic.criterion.is_known else None),
            "reason": None if view.entry_logic.entry_price.is_known else view.entry_logic.entry_price.reason,
        },
        "internal_fundamentals_status": view.internal_fundamentals.meta.status,
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
           "CORRELATION_WARNING", "FUNDAMENTAL_EPISTEMIC_WARNING", "JUDGMENT_WARNING",
           "NEXT_PHASE_NOTE", "RETURN_IS_NOT"]
