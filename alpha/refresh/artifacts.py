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
from .contracts import (
    ARTIFACT_ASSUMPTION, ARTIFACT_AXIS, ARTIFACT_COMPARISON, ARTIFACT_MARKET_IMPLIED,
    ARTIFACT_METRIC, ARTIFACT_MODEL, ARTIFACT_THESIS, INVALIDATED, KIND_DETERMINISTIC,
    KIND_JUDGMENT, MISSING, ROLE_CALIBRATION, ROLE_COMPARISON, ROLE_INPUT, ROLE_LEGACY,
    ROLE_OBSERVATION, ROLE_SUPPORTING, SUPERSEDED, ArtifactDependency,
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

def _assumption_refs(record: OperatingAssumption) -> dict[str, str]:
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
    "AXIS_LABEL", "THESIS_ARTIFACT_ID", "artifacts_from_context", "artifacts_from_model",
    "artifacts_from_signal", "build_instant", "end_of_day", "start_of_day",
]
