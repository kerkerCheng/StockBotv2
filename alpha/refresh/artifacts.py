"""把既有研究成果的 provenance 攤平成 `ArtifactDependency`。**不另建一套依賴圖。**

依賴來源固定（F. 原則：優先利用既有 dependency information）：

| 成果 | 依賴來源 |
|---|---|
| Q1 `axis:structural` | `ComponentTrace.evidence_refs`（公司層級：任何結構事件都重算） |
| Q2–Q5 `axis:*` | `AlphaSignal.model_components[trace].evidence_refs` |
| thesis／disproof | 全部 session 軸引用的聯集＋`DisproofCondition.check_frequency`（L7） |
| 假設 | `OperatingAssumption.evidence_refs`＋`dependency_roles`＋`review_conditions` |
| 模型輸出 | `ModeledMetric.assumption_ids`＋`observation_refs` |
| 數值 gap | `ExpectationComparison.assumption_ids`＋`consensus_refs` |
| 市場隱含 | `ValuationSnapshot.evidence`＋`MarketSnapshot.evidence` |
| 估值假設（Step 1） | `ValuationAssumption.evidence_refs`＋`dependency_roles`＋`review_conditions` |
| fair value（Step 1） | `ValuationResult.assumption_ids`（營運＋估值假設）＋內部 EPS 的 `observation_refs`——**不含現價** |
| fair value gap（Step 1） | fair value 的依賴＋`CurrentPrice.evidence_refs` |
| horizon 假設（Step 2） | `HorizonAssumption.evidence_refs`＋`dependency_roles`＋`review_conditions`；`expires_at`＝`horizon_end` |
| implied return（Step 2） | fair value 的依賴＋`CurrentPrice.evidence_refs`＋horizon 假設（`assumption_ids` 含 `ha_*`） |
| entry criterion（Step 3） | 投資人政策紀錄：**沒有** supporting evidence（機會成本不是公司文件）；只有 supersede／retract／as-of 的終局 state |
| entry assessment（Step 3） | implied return 的依賴＋entry criterion（`assumption_ids` 含 `ec_*`） |

`established_at` 是 PIT 的錨：session 判斷＝判斷檔自報的產出日；假設＝`created_at`；
確定性輸出＝這次 build 的參考時點（它們每次都重算，所以在 build 之前發生的變化都已納入）。
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Sequence

from ..contracts import AXES, AlphaSignal, ComponentTrace, ResearchContext
from ..fundamental.contracts import (
    FiscalPeriod, FundamentalModelResult, OperatingAssumption,
)
from ..entry.contracts import EntryAssessmentResult, EntryCriterion
from ..implied_return.contracts import HorizonAssumption, ImpliedReturnResult
from ..valuation.contracts import ValuationAssumption, ValuationResult
from .contracts import (
    ARTIFACT_ASSUMPTION, ARTIFACT_AXIS, ARTIFACT_COMPARISON, ARTIFACT_ENTRY_ASSESSMENT, ARTIFACT_ENTRY_CRITERION,
    ARTIFACT_FAIR_VALUE, ARTIFACT_FAIR_VALUE_GAP, ARTIFACT_HORIZON_ASSUMPTION, ARTIFACT_IMPLIED_RETURN,
    ARTIFACT_MARKET_IMPLIED, ARTIFACT_METRIC, ARTIFACT_MODEL, ARTIFACT_THESIS, ARTIFACT_VALUATION_ASSUMPTION,
    INVALIDATED, KIND_DETERMINISTIC, KIND_JUDGMENT, MISSING, ROLE_CALIBRATION, ROLE_COMPARISON, ROLE_INPUT,
    ROLE_LEGACY, ROLE_OBSERVATION, ROLE_SUPPORTING, SUPERSEDED, ArtifactDependency,
)
from .policy import frequency_to_days

AXIS_LABEL = {
    "structural": "Q1 結構稀缺", "value_capture": "Q2 價值攫取",
    "earnings_exposure": "Q3 盈餘曝險", "expectation_gap": "Q4 預期落差（session）",
    "catalyst": "Q5 催化劑",
}
THESIS_ARTIFACT_ID = "session_judgment"


def end_of_day(day: date) -> datetime:
    """一個日期的「當天結束」（UTC）。用來把只有日期的建立時點放到那一天的最後一刻，
    讓同一天稍早發生的變化被視為已納入、之後的才算新變化。"""
    return datetime.combine(day, time(23, 59, 59), tzinfo=timezone.utc)


def start_of_day(day: date) -> datetime:
    return datetime.combine(day, time(0, 0), tzinfo=timezone.utc)


def build_instant(day: date) -> datetime:
    """同一天內建立的成果的錨點：比 `end_of_day` 早一秒。當天稍早抓到的資料已納入（不是新變化）；
    情境模擬把事件放在 `end_of_day`，剛好晚於 build、又不晚於 as-of cutoff。"""
    return datetime.combine(day, time(23, 59, 58), tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# session 判斷（Q2–Q5、thesis／disproof）＋ Q1
# ---------------------------------------------------------------------------

def artifacts_from_signal(
    signal: AlphaSignal | None,
    *,
    judged_at: datetime | None,
    structural_trace: ComponentTrace | None,
    build_at: datetime,
) -> list[ArtifactDependency]:
    """Q1 由 build 時點錨定（每次重算）；Q2–Q5 與 thesis 由判斷日錨定。"""
    out: list[ArtifactDependency] = []
    if structural_trace is not None:
        out.append(ArtifactDependency(
            artifact_type=ARTIFACT_AXIS, artifact_id="structural", label=AXIS_LABEL["structural"],
            kind=KIND_DETERMINISTIC, established_at=build_at,
            refs={r.ref: ROLE_SUPPORTING for r in structural_trace.evidence_refs},
        ))
    if signal is None:
        return out
    union: dict[str, str] = {}
    for axis in AXES:
        if axis == "structural":
            continue
        score = signal.score_for(axis)
        if score is None:
            out.append(ArtifactDependency(
                artifact_type=ARTIFACT_AXIS, artifact_id=axis, label=AXIS_LABEL[axis],
                kind=KIND_JUDGMENT, established_at=judged_at,
                preset_state=MISSING, preset_reason="session 回答 unknown——不知道，不是 0；沒有可被推翻的判斷",
            ))
            continue
        trace = signal.model_components.get(score.trace_id)
        refs = {r.ref: ROLE_SUPPORTING for r in (trace.evidence_refs if trace else ())}
        union.update(refs)
        out.append(ArtifactDependency(
            artifact_type=ARTIFACT_AXIS, artifact_id=axis, label=AXIS_LABEL[axis],
            kind=KIND_JUDGMENT, established_at=judged_at, refs=refs, basis="session_judgment",
        ))
    # thesis／variant view／disproof：一份判斷的敘事層。核查頻率取所有 disproof 中最短的一個（L7）。
    frequencies = [frequency_to_days(d.check_frequency) for d in signal.disproof_conditions]
    known = [f for f in frequencies if f is not None]
    out.append(ArtifactDependency(
        artifact_type=ARTIFACT_THESIS, artifact_id=THESIS_ARTIFACT_ID,
        label="Thesis／variant view／disproof（session 判斷）", kind=KIND_JUDGMENT,
        established_at=judged_at, refs=union, basis="session_judgment",
        check_frequency_days=(min(known) if known else None),
        extras={"unparsed_frequencies": [d.check_frequency for d, f in
                                          zip(signal.disproof_conditions, frequencies) if f is None]},
    ))
    return out


# ---------------------------------------------------------------------------
# 假設（含被取代／撤回／其他期間的歷史紀錄）＋ 模型輸出 ＋ 數值 gap
# ---------------------------------------------------------------------------

def _assumption_refs(record: OperatingAssumption | ValuationAssumption | HorizonAssumption) -> dict[str, str]:
    roles: dict[str, str] = {}
    for ref in record.evidence_refs:
        role = record.role_of(ref)
        roles[ref] = {
            "supporting": ROLE_SUPPORTING, "calibration": ROLE_CALIBRATION,
            "comparison": ROLE_COMPARISON, "legacy_unclassified": ROLE_LEGACY,
        }[role]
    return roles


def _assumption_label(record: OperatingAssumption) -> str:
    return f"假設 {record.driver}[{record.scope}] {record.period.label}"


def artifacts_from_model(
    model: FundamentalModelResult | None,
    *,
    build_at: datetime,
    assumption_records: Sequence[OperatingAssumption] = (),
) -> list[ArtifactDependency]:
    """生效假設＋歷史假設（superseded／retracted／other_period 各自帶終局 state）＋模型輸出。"""
    out: list[ArtifactDependency] = []
    if model is None:
        return out
    accepted = {a.assumption_id: a for a in model.assumptions}
    rejection = {aid: reason for aid, reason in model.selection.rejected}
    base_end = model.base_period.end if model.base_period else None
    base_recorded = (model.base_actuals.recorded_at if model.base_actuals and model.base_actuals.recorded_at
                     else None)

    seen: set[str] = set()
    for record in (*model.assumptions, *assumption_records):
        if record.assumption_id in seen:
            continue
        seen.add(record.assumption_id)
        preset: str | None = None
        why: str | None = None
        if record.assumption_id not in accepted:
            reason = rejection.get(record.assumption_id, "")
            if record.retracted:
                preset, why = SUPERSEDED, "已撤回（retracted）——歷史紀錄"
            elif reason.startswith("superseded"):
                preset, why = SUPERSEDED, f"已被較新的同 key 紀錄取代（{reason}）——歷史紀錄"
            elif reason.startswith("unresolved_evidence"):
                preset, why = INVALIDATED, f"supporting evidence 解析不到（{reason}）——前提不成立，不得當 current"
            elif reason == "other_period":
                if base_end is not None and record.period.same_as(FiscalPeriod(end=base_end)):
                    preset, why = SUPERSEDED, (
                        f"{record.period.label} 已有實際值（基期已推進到 {record.period.label}）——"
                        "這條是歷史預測，不沿用到新目標期間")
                else:
                    preset, why = MISSING, f"針對 {record.period.label}，不是目前目標期間；本視角不評估"
            elif reason == "created_after_as_of":
                preset, why = MISSING, "as-of 之後才建立——在此時點不存在（INV-6）"
            else:
                preset, why = MISSING, f"未被模型選取（{reason or '原因未知'}）"
        out.append(ArtifactDependency(
            artifact_type=ARTIFACT_ASSUMPTION, artifact_id=record.assumption_id,
            label=_assumption_label(record), kind=KIND_JUDGMENT, established_at=record.created_at,
            refs=_assumption_refs(record), basis=record.basis, driver=record.driver,
            scope=record.scope, period_end=record.period.end,
            review_conditions=tuple(record.review_conditions),
            preset_state=preset, preset_reason=why,
            extras={"provenance_semantics": record.provenance_semantics, "value": record.value},
        ))

    for name, metric in model.metrics.items():
        if not metric.is_known:
            continue
        refs = {r: ROLE_OBSERVATION for r in metric.observation_refs}
        refs.update({a: ROLE_INPUT for a in metric.assumption_ids})
        out.append(ArtifactDependency(
            artifact_type=ARTIFACT_METRIC, artifact_id=name,
            label=f"內部 {name}（{metric.period.label}）", kind=KIND_DETERMINISTIC,
            established_at=build_at, refs=refs, assumption_ids=tuple(metric.assumption_ids),
            basis=metric.input_dependency, period_end=metric.period.end,
        ))
    for name, cmp in model.comparisons.items():
        if cmp.status != "comparable":
            continue
        refs = {r: ROLE_OBSERVATION for r in cmp.observation_refs}
        refs.update({r: ROLE_COMPARISON for r in cmp.consensus_refs})
        refs.update({a: ROLE_INPUT for a in cmp.assumption_ids})
        out.append(ArtifactDependency(
            artifact_type=ARTIFACT_COMPARISON, artifact_id=name,
            label=f"內部 vs 共識 {name}（數值 gap）", kind=KIND_DETERMINISTIC,
            established_at=build_at, refs=refs, assumption_ids=tuple(cmp.assumption_ids),
            period_end=(cmp.internal_period.end if cmp.internal_period else None),
        ))
    if model.base_period is not None:
        out.append(ArtifactDependency(
            artifact_type=ARTIFACT_MODEL, artifact_id="fundamental_model",
            label=f"Causal Fundamental Model（基期 {model.base_period.label} → 目標 "
                  f"{model.target_period.label if model.target_period else '?'}）",
            kind=KIND_DETERMINISTIC, established_at=build_at,
            refs={r.ref: ROLE_OBSERVATION for r in (model.base_actuals.evidence if model.base_actuals else ())},
            assumption_ids=tuple(a.assumption_id for a in model.assumptions),
            period_end=(model.target_period.end if model.target_period else None),
            extras={"base_period_end": base_end, "base_recorded_at": base_recorded,
                    "status": model.status},
        ))
    return out


# ---------------------------------------------------------------------------
# 估值（Step 1）：估值假設（判斷型）＋ fair value（確定性，不含現價）＋ gap（確定性，含現價）
# ---------------------------------------------------------------------------

def _historical_state(record, *, accepted: set[str], rejection: dict[str, str],
                      base_end: date | None, target_end: date | None) -> tuple[str | None, str | None]:
    """未被選取的 ledger 紀錄各自的終局 state（與 `artifacts_from_model` 同一套判準）。"""
    if record.assumption_id in accepted:
        return None, None
    reason = rejection.get(record.assumption_id, "")
    if record.retracted:
        return SUPERSEDED, "已撤回（retracted）——歷史紀錄"
    if reason.startswith("superseded"):
        return SUPERSEDED, f"已被較新的同 key 紀錄取代（{reason}）——歷史紀錄"
    if reason.startswith("unresolved_evidence"):
        return INVALIDATED, f"supporting evidence 解析不到（{reason}）——前提不成立，不得當 current"
    if reason == "other_period":
        if base_end is not None and record.period.same_as(FiscalPeriod(end=base_end)):
            return SUPERSEDED, f"{record.period.label} 已有實際值——這條是歷史判斷，不沿用到新目標期間"
        return MISSING, f"針對 {record.period.label}，不是目前目標期間（{target_end}）；本視角不評估"
    if reason == "created_after_as_of":
        return MISSING, "as-of 之後才建立——在此時點不存在（INV-6）"
    return MISSING, f"未被模型選取（{reason or '原因未知'}）"


def artifacts_from_valuation(
    valuation: ValuationResult | None,
    *,
    build_at: datetime,
    assumption_records: Sequence[ValuationAssumption] = (),
    base_period_end: date | None = None,
) -> list[ArtifactDependency]:
    """估值假設（含歷史紀錄）＋ fair value ＋ gap。

    fair value 的 refs **刻意不含現價的 ref**：它只依賴內部 EPS 與估值假設，所以 price-only 變化
    不會讓它 recalculate；gap 才帶現價 ref。這是「price 不進 fair value」在依賴層的形狀。
    """
    out: list[ArtifactDependency] = []
    if valuation is None:
        return out
    accepted = {a.assumption_id for a in valuation.assumptions}
    rejection = {aid: reason for aid, reason in valuation.selection.rejected}
    target_end = valuation.target_period.end if valuation.target_period else None
    seen: set[str] = set()
    for record in (*valuation.assumptions, *assumption_records):
        if record.assumption_id in seen:
            continue
        seen.add(record.assumption_id)
        preset, why = _historical_state(record, accepted=accepted, rejection=rejection,
                                        base_end=base_period_end, target_end=target_end)
        out.append(ArtifactDependency(
            artifact_type=ARTIFACT_VALUATION_ASSUMPTION, artifact_id=record.assumption_id,
            label=f"估值假設 {record.driver} {record.period.label}（{record.accounting_basis}）",
            kind=KIND_JUDGMENT, established_at=record.created_at, refs=_assumption_refs(record),
            basis=record.basis, driver=record.driver, scope=record.scope, period_end=record.period.end,
            review_conditions=tuple(record.review_conditions), preset_state=preset, preset_reason=why,
            extras={"provenance_semantics": record.provenance_semantics, "value": record.value,
                    "method": record.method, "parameter": record.parameter},
        ))
    if not valuation.is_known:
        return out
    fundamental = valuation.fundamental_input
    fv_refs: dict[str, str] = {r: ROLE_OBSERVATION for r in (fundamental.observation_refs if fundamental else ())}
    fv_refs.update({a: ROLE_INPUT for a in valuation.assumption_ids})
    out.append(ArtifactDependency(
        artifact_type=ARTIFACT_FAIR_VALUE, artifact_id="fair_value",
        label=f"Fair value（{valuation.method}，{valuation.target_period.label if valuation.target_period else '?'}）",
        kind=KIND_DETERMINISTIC, established_at=build_at, refs=fv_refs,
        assumption_ids=tuple(valuation.assumption_ids), basis=valuation.input_dependency,
        period_end=target_end, extras={"method": valuation.method},
    ))
    if valuation.gap.is_known:
        gap_refs = dict(fv_refs)
        gap_refs.update({r: ROLE_OBSERVATION for r in valuation.current_price.evidence_refs})
        out.append(ArtifactDependency(
            artifact_type=ARTIFACT_FAIR_VALUE_GAP, artifact_id="fair_value_gap",
            label="Fair value vs 現價（gap；不是 expected return）", kind=KIND_DETERMINISTIC,
            established_at=build_at, refs=gap_refs, assumption_ids=tuple(valuation.assumption_ids),
            basis=valuation.input_dependency, period_end=target_end,
        ))
    return out


# ---------------------------------------------------------------------------
# 報酬（Step 2）：horizon 假設（判斷型，帶絕對到期）＋ implied return（確定性，含現價與 horizon）
# ---------------------------------------------------------------------------

def artifacts_from_implied_return(
    result: ImpliedReturnResult | None,
    *,
    build_at: datetime,
    horizon_records: Sequence[HorizonAssumption] = (),
    base_period_end: date | None = None,
) -> list[ArtifactDependency]:
    """horizon 假設（含歷史紀錄）＋ implied return。

    horizon 假設帶 `expires_at=horizon_end`：到那天就 stale（INV-2：每個等待都必須有到期）。
    implied return 的依賴＝fair value 的依賴（營運＋估值假設、基期觀測）＋現價 ref＋horizon 假設——
    所以 price-only → recalculate；估值假設 review → 傳播成 review；horizon 被取代 → recalculate；
    無關的圖變化（沒命中任何 supporting ref）→ current。
    """
    out: list[ArtifactDependency] = []
    if result is None:
        return out
    accepted = {result.horizon.assumption_id} if result.horizon is not None else set()
    rejection = {aid: reason for aid, reason in result.horizon_selection.rejected}
    target_end = result.target_period.end if result.target_period else None
    seen: set[str] = set()
    for record in (*((result.horizon,) if result.horizon is not None else ()), *horizon_records):
        if record.assumption_id in seen:
            continue
        seen.add(record.assumption_id)
        preset, why = _historical_state(record, accepted=accepted, rejection=rejection,
                                        base_end=base_period_end, target_end=target_end)
        out.append(ArtifactDependency(
            artifact_type=ARTIFACT_HORIZON_ASSUMPTION, artifact_id=record.assumption_id,
            label=f"Horizon 判斷 {record.period.label} fair value 於 {record.horizon_end} 前實現",
            kind=KIND_JUDGMENT, established_at=record.created_at, refs=_assumption_refs(record),
            basis=record.basis, driver=record.driver, scope=record.scope, period_end=record.period.end,
            review_conditions=tuple(record.review_conditions), preset_state=preset, preset_reason=why,
            expires_at=(record.horizon_end if preset is None else None),
            extras={"provenance_semantics": record.provenance_semantics, "horizon_end": record.horizon_end.isoformat()},
        ))
    if not result.is_known:
        return out
    refs: dict[str, str] = {r: ROLE_OBSERVATION for r in result.observation_refs}
    refs.update({a: ROLE_INPUT for a in result.assumption_ids})
    out.append(ArtifactDependency(
        artifact_type=ARTIFACT_IMPLIED_RETURN, artifact_id="implied_return",
        label=(f"Base-case implied return（{result.target_period.label if result.target_period else '?'}；"
               f"{result.horizon_start} → {result.horizon_end}；不是 expected return）"),
        kind=KIND_DETERMINISTIC, established_at=build_at, refs=refs,
        assumption_ids=tuple(result.assumption_ids), basis=result.input_dependency, period_end=target_end,
        extras={"return_convention": result.return_convention, "horizon_end": result.horizon_end.isoformat() if result.horizon_end else None},
    ))
    return out


# ---------------------------------------------------------------------------
# Entry（Step 3）：entry criterion（投資人政策紀錄）＋ entry assessment（確定性，含現價／研究假設／criterion）
# ---------------------------------------------------------------------------

def _criterion_state(record: EntryCriterion, *, accepted: set[str], rejection: dict[str, str]) -> tuple[str | None, str | None]:
    """未被選取的 criterion 紀錄各自的終局 state（與其他判斷型紀錄同一套判準；沒有 other_period／unresolved_evidence）。"""
    if record.criterion_id in accepted:
        return None, None
    reason = rejection.get(record.criterion_id, "")
    if record.retracted:
        return SUPERSEDED, "已撤回（retracted）——歷史紀錄"
    if reason.startswith("superseded"):
        return SUPERSEDED, f"已被較新的同 convention 紀錄取代（{reason}）——歷史紀錄"
    if reason == "created_after_as_of":
        return MISSING, "as-of 之後才建立——在此時點不存在（INV-6）"
    return MISSING, f"未被選取（{reason or '原因未知'}）"


def artifacts_from_entry(
    result: EntryAssessmentResult | None,
    *,
    build_at: datetime,
    criterion_records: Sequence[EntryCriterion] = (),
) -> list[ArtifactDependency]:
    """entry criterion（含歷史紀錄）＋ entry assessment。

    criterion 是投資人政策：`refs` 為空（沒有 supporting evidence，結構事件／共識／指引都不會動它），只有
    supersede／retract／as-of 決定它的 state。entry assessment 的依賴＝implied return 的依賴（現價 ref＋基期觀測＋
    營運／估值／horizon 假設）＋criterion——所以 price-only → recalculate；上游假設 review → 傳播成 review；
    criterion 被取代 → recalculate；無關的圖變化 → current。

    ⚠ **criterion 同時列在 `refs` 與 `assumption_ids`，但今天只有 refs 那條路徑會發動**（2026-09-06 突變實測）：
    判準沒有 supporting evidence，所以它不可能變成 `review_required`／`invalidated`——第二輪傳播（上游 state →
    下游）對它是 no-op。`assumption_ids` 留著是為了讓依賴宣告完整（讀者與未來的 expiry 機制），不是一道已量測的
    守衛；**不得**因為「它在 assumption_ids 裡」就相信有東西在守（L14）。
    """
    out: list[ArtifactDependency] = []
    if result is None:
        return out
    accepted = {result.criterion.criterion_id} if result.criterion is not None else set()
    rejection = {cid: reason for cid, reason in result.criterion_selection.rejected}
    seen: set[str] = set()
    for record in (*((result.criterion,) if result.criterion is not None else ()), *criterion_records):
        if record.criterion_id in seen:
            continue
        seen.add(record.criterion_id)
        preset, why = _criterion_state(record, accepted=accepted, rejection=rejection)
        out.append(ArtifactDependency(
            artifact_type=ARTIFACT_ENTRY_CRITERION, artifact_id=record.criterion_id,
            label=f"Entry criterion：要求年化價格報酬 {record.value:+.1%}（{record.basis}，{record.author}）",
            kind=KIND_JUDGMENT, established_at=record.created_at, refs={}, basis=record.basis,
            driver=record.driver, scope=record.scope, preset_state=preset, preset_reason=why,
            extras={"convention": record.convention, "value": record.value, "author": record.author},
        ))
    if not result.is_known or result.criterion is None:
        return out
    refs: dict[str, str] = {r: ROLE_OBSERVATION for r in result.observation_refs}
    refs.update({a: ROLE_INPUT for a in result.research_assumption_ids})
    refs[result.criterion.criterion_id] = ROLE_INPUT
    out.append(ArtifactDependency(
        artifact_type=ARTIFACT_ENTRY_ASSESSMENT, artifact_id="entry_assessment",
        label=(f"Entry assessment（{result.target_period.label if result.target_period else '?'}；門檻價 vs 現價；"
               "不是 buy／sell）"),
        kind=KIND_DETERMINISTIC, established_at=build_at, refs=refs,
        assumption_ids=tuple(result.research_assumption_ids) + (result.criterion.criterion_id,),
        basis=result.input_dependency, period_end=(result.target_period.end if result.target_period else None),
        extras={"convention": result.convention, "hurdle_comparison": result.hurdle_comparison,
                "assessment": result.assessment, "alignment": result.alignment},
    ))
    return out


# ---------------------------------------------------------------------------
# 市場導出量（確定性 proxy）
# ---------------------------------------------------------------------------

def artifacts_from_context(context: ResearchContext, *, build_at: datetime) -> list[ArtifactDependency]:
    out: list[ArtifactDependency] = []
    if context.valuation.market_implied_growth is not None:
        refs = {r.ref: ROLE_OBSERVATION for r in (*context.valuation.evidence, *context.market.evidence)}
        out.append(ArtifactDependency(
            artifact_type=ARTIFACT_MARKET_IMPLIED, artifact_id="market_implied_eps_growth",
            label="市場隱含 EPS 成長（proxy）", kind=KIND_DETERMINISTIC, established_at=build_at,
            refs=refs, basis="heuristic_proxy",
        ))
    if context.consensus.estimate_revision_30d is not None:
        refs = {r.ref: ROLE_OBSERVATION for r in (*context.consensus.evidence, *context.market.evidence)}
        out.append(ArtifactDependency(
            artifact_type=ARTIFACT_MARKET_IMPLIED, artifact_id="estimate_revision_vs_price",
            label="估計修正 vs 股價變動（Q4 原料）", kind=KIND_DETERMINISTIC, established_at=build_at,
            refs=refs, basis="deterministic",
        ))
    return out


__all__ = [
    "AXIS_LABEL", "THESIS_ARTIFACT_ID", "artifacts_from_context", "artifacts_from_entry",
    "artifacts_from_implied_return", "artifacts_from_model", "artifacts_from_signal", "artifacts_from_valuation",
    "build_instant", "end_of_day", "start_of_day",
]
