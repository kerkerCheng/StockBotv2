"""Dependency Impact Resolver：`ChangeEvent[]` × `ArtifactDependency[]` → `RefreshReport`。

```
ChangeEvent[]（組裝層由 authority 時序導出）─┐
core 自己導出的變化（review condition 觸發、  ├─► resolve_refresh ─► AffectedArtifact[]
排程到期、會計期間推進）─────────────────────┘        │
                                                       ├─ 第一輪：逐成果套 policy（class 規則＋引用命中）
                                                       └─ 第二輪：沿 assumption_ids 往下游傳播
```

## 三條不變式

1. **只有 `observed_at` 晚於成果 `established_at` 的變化才算新變化。** 判斷寫於 T、變化在 T
   之前就知道 → 判斷已經看過它，不是「變了」。這也是 as-of 的骨架：T 之後的變化在 T 不存在。
2. **不 cascade。** 一個變化只影響 policy 表與引用命中指到的成果；傳播只沿宣告的
   `assumption_ids` 走一層（模型輸出 ← 假設），不沿「同一份 context」走。
3. **不自動呼叫 LLM、不改任何 authority。** 本檔的輸出是 state＋理由，沒有副作用。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Mapping, Sequence

from ..fundamental.contracts import PERIOD_MATCH_TOLERANCE_DAYS
from .artifacts import THESIS_ARTIFACT_ID, end_of_day
from .contracts import (
    ARTIFACT_ASSUMPTION, ARTIFACT_AXIS, ARTIFACT_COMPARISON, ARTIFACT_FAIR_VALUE, ARTIFACT_FAIR_VALUE_GAP,
    ARTIFACT_HORIZON_ASSUMPTION, ARTIFACT_IMPLIED_RETURN,
    ARTIFACT_MARKET_IMPLIED, ARTIFACT_METRIC, ARTIFACT_MODEL, ARTIFACT_THESIS, ARTIFACT_VALUATION_ASSUMPTION,
    ASSUMPTION_ARTIFACT_TYPES, CONSENSUS, CONTEXT_DIGEST, CURRENT,
    DISPROOF_SIGNAL, FISCAL_PERIOD_ROLLOVER, HORIZON_ASSUMPTION, INVALIDATED, KIND_DETERMINISTIC, KIND_JUDGMENT,
    MISSING, OPERATING_ASSUMPTION, RECALCULATE, REVIEW_REQUIRED, ROLE_CALIBRATION, ROLE_LEGACY,
    ROLE_SUPPORTING, STALE, SUPERSEDED, THESIS_REVIEW_DUE, COMPANY_GUIDANCE, VALUATION_ASSUMPTION,
    AffectedArtifact, ArtifactDependency, ChangeEvent, MetricObservation, RefreshReport,
    merge_states,
)
from .policy import (
    ASSUMPTION_CLASS_POLICY, AXIS_POLICY, DERIVED_CLASS_POLICY, POLICY_VERSION,
    STRUCTURAL_CHANGE_TYPES, THESIS_POLICY, guidance_driver,
)

_ORDER = {ARTIFACT_AXIS: 0, ARTIFACT_THESIS: 1, ARTIFACT_ASSUMPTION: 2, ARTIFACT_METRIC: 3,
          ARTIFACT_COMPARISON: 4, ARTIFACT_MARKET_IMPLIED: 5, ARTIFACT_MODEL: 6,
          ARTIFACT_VALUATION_ASSUMPTION: 7, ARTIFACT_FAIR_VALUE: 8, ARTIFACT_FAIR_VALUE_GAP: 9,
          ARTIFACT_HORIZON_ASSUMPTION: 10, ARTIFACT_IMPLIED_RETURN: 11}
#: 「自己就是那筆新紀錄」的 change class（新紀錄的建立不是對它自己的變化）。
_LEDGER_CHANGE_TYPES: frozenset[str] = frozenset({OPERATING_ASSUMPTION, VALUATION_ASSUMPTION, HORIZON_ASSUMPTION})
_AXIS_ORDER = {"structural": 0, "value_capture": 1, "earnings_exposure": 2, "expectation_gap": 3,
               "catalyst": 4}

_RETRACTED_MARKERS = ("retracted", "removed", "withdrawn")


class _Hit:
    __slots__ = ("state", "reason", "changed_ref", "observed_at", "dependency_ref")

    def __init__(self, state: str, reason: str, changed_ref: str, observed_at: datetime,
                 dependency_ref: str | None = None) -> None:
        self.state, self.reason, self.changed_ref = state, reason, changed_ref
        self.observed_at, self.dependency_ref = observed_at, dependency_ref


def _is_retraction(event: ChangeEvent) -> bool:
    fields = {f.lower() for f in event.material_fields}
    return any(marker in fields for marker in _RETRACTED_MARKERS)


def _same_period(a: date | None, b: date | None) -> bool:
    return (a is not None and b is not None
            and abs((a - b).days) <= PERIOD_MATCH_TOLERANCE_DAYS)


# ---------------------------------------------------------------------------
# core 自己導出的變化
# ---------------------------------------------------------------------------

def _condition_events(
    artifacts: Sequence[ArtifactDependency], observations: Sequence[MetricObservation],
    *, ticker: str, company_id: str | None, cutoff: datetime, notes: list[str],
) -> list[ChangeEvent]:
    """review_conditions × observations → `disproof_signal`。沒有可對照的觀測就是「等待中」，不是觸發。"""
    out: list[ChangeEvent] = []
    for artifact in artifacts:
        for condition in artifact.review_conditions:
            matched = [
                obs for obs in observations
                if obs.metric == condition.metric and obs.scope == condition.scope
                and obs.period_kind == condition.period_kind
                and _same_period(obs.period_end, condition.period_end)
                and obs.observed_at <= cutoff
            ]
            if not matched:
                notes.append(
                    f"{artifact.key}：條件「{condition.metric}[{condition.scope}] "
                    f"{condition.period_kind} {condition.period_end} {condition.operator} "
                    f"{condition.threshold:g}」尚無可對照的觀測——等待中，不是觸發")
                continue
            latest = max(matched, key=lambda o: o.observed_at)
            if condition.holds(latest.value):
                out.append(ChangeEvent(
                    change_type=DISPROOF_SIGNAL, ticker=ticker, company_id=company_id,
                    authority="alpha://refresh/review_conditions", changed_ref=latest.ref,
                    observed_at=latest.observed_at, effective_at=latest.period_end,
                    old_version=None, new_version=f"{latest.value:g}",
                    material_fields=(condition.metric,),
                    detail=(f"觀測 {condition.metric}[{condition.scope}] {condition.period_end} = "
                            f"{latest.value:g} 滿足 {condition.operator} {condition.threshold:g}"
                            + (f"；人寫的下一步：{condition.note}" if condition.note else "")),
                    target_artifact=artifact.artifact_id, on_trigger=condition.on_trigger,
                ))
            else:
                notes.append(
                    f"{artifact.key}：條件已對照（{latest.value:g} 不滿足 {condition.operator} "
                    f"{condition.threshold:g}），未觸發")
    return out


def _schedule_events(
    artifacts: Sequence[ArtifactDependency], *, ticker: str, company_id: str | None,
    cutoff: datetime, notes: list[str],
) -> list[ChangeEvent]:
    out: list[ChangeEvent] = []
    for artifact in artifacts:
        if artifact.expires_at is not None and artifact.preset_state is None:
            # Step 2：絕對到期（horizon_end）。到期就是排程事件；成果自己說「等到那天」，那天到了就 stale。
            expiry = end_of_day(artifact.expires_at)
            if expiry <= cutoff:
                out.append(ChangeEvent(
                    change_type=THESIS_REVIEW_DUE, ticker=ticker, company_id=company_id,
                    authority="alpha://refresh/schedule", changed_ref=artifact.key,
                    observed_at=expiry, effective_at=artifact.expires_at,
                    material_fields=("expires_at",),
                    detail=f"到期日 {artifact.expires_at} 已到（成果自帶的絕對到期；INV-2）",
                    target_artifact=artifact.artifact_id,
                ))
        if artifact.check_frequency_days is None or artifact.established_at is None:
            if artifact.extras.get("unparsed_frequencies"):
                notes.append(f"{artifact.key}：核查頻率無法解析成天數："
                             f"{artifact.extras['unparsed_frequencies']}——不排程 stale")
            continue
        due_at = artifact.established_at + timedelta(days=artifact.check_frequency_days)
        if due_at <= cutoff:
            out.append(ChangeEvent(
                change_type=THESIS_REVIEW_DUE, ticker=ticker, company_id=company_id,
                authority="alpha://refresh/schedule", changed_ref=artifact.key,
                observed_at=due_at, effective_at=due_at.date(),
                material_fields=("check_frequency",),
                detail=f"核查週期 {artifact.check_frequency_days} 天已到（自 {artifact.established_at.date()}）",
                target_artifact=artifact.artifact_id,
            ))
    return out


def _rollover_events(
    artifacts: Sequence[ArtifactDependency], *, ticker: str, company_id: str | None, notes: list[str],
) -> list[ChangeEvent]:
    model = next((a for a in artifacts if a.artifact_type == ARTIFACT_MODEL), None)
    if model is None:
        return []
    base_end: date | None = model.extras.get("base_period_end")
    if base_end is None:
        return []
    rolled = [a for a in artifacts if a.artifact_type == ARTIFACT_ASSUMPTION
              and a.preset_state == SUPERSEDED and _same_period(a.period_end, base_end)]
    if not rolled:
        return []
    if model.extras.get("status") == "available":
        notes.append(f"基期已推進到 {base_end}，且新目標期間已有生效假設——期間推進已被處理")
        return []
    recorded = model.extras.get("base_recorded_at") or model.established_at
    target_end = model.period_end
    return [ChangeEvent(
        change_type=FISCAL_PERIOD_ROLLOVER, ticker=ticker, company_id=company_id,
        authority="engine_c://manual_observations", changed_ref=next(iter(model.refs), "fiscal_year_results"),
        observed_at=recorded, effective_at=base_end,
        old_version=f"target={base_end.isoformat()}",
        new_version=f"target={target_end.isoformat() if target_end else '?'}",
        material_fields=("base_period", "target_period"),
        detail=(f"new fiscal base available（{base_end} 已有實際值）；target period advanced"
                f"（→ {target_end or '?'}）；new operating assumptions required——"
                f"{len(rolled)} 條 {base_end.year} 年度假設是歷史，不沿用"),
        target_artifact=model.artifact_id,
    )]


# ---------------------------------------------------------------------------
# 逐成果套規則
# ---------------------------------------------------------------------------

def _touches(event: ChangeEvent, refs: frozenset[str]) -> str | None:
    hit = sorted(event.refs & refs)
    return hit[0] if hit else None


def _axis_hits(artifact: ArtifactDependency, event: ChangeEvent) -> list[_Hit]:
    axis = artifact.artifact_id
    hits: list[_Hit] = []
    if artifact.kind == KIND_DETERMINISTIC:                    # Q1
        if event.change_type in STRUCTURAL_CHANGE_TYPES:
            hits.append(_Hit(RECALCULATE, f"這家公司的結構事實變了（{event.detail or event.changed_ref}）"
                                          "——Q1 是已入圖事實的確定性函數，重算即可",
                             event.changed_ref, event.observed_at))
        return hits
    state = AXIS_POLICY.get(event.change_type, {}).get(axis)
    if state is not None:
        hits.append(_Hit(state, f"{event.change_type}：{event.detail or event.changed_ref}",
                         event.changed_ref, event.observed_at))
    if event.change_type in STRUCTURAL_CHANGE_TYPES:
        touched = _touches(event, artifact.refs_with_role(ROLE_SUPPORTING, ROLE_LEGACY))
        if touched:
            if _is_retraction(event):
                hits.append(_Hit(INVALIDATED, f"引用的 supporting evidence 已撤回：{touched}",
                                 event.changed_ref, event.observed_at, touched))
            else:
                hits.append(_Hit(REVIEW_REQUIRED, f"引用的 supporting evidence 變了：{touched}"
                                                  f"（{event.detail or event.change_type}）",
                                 event.changed_ref, event.observed_at, touched))
    if event.change_type == THESIS_REVIEW_DUE and event.target_artifact in (None, THESIS_ARTIFACT_ID, axis):
        hits.append(_Hit(STALE, f"排程複查到期：{event.detail}", event.changed_ref, event.observed_at))
    if event.change_type == DISPROOF_SIGNAL and event.target_artifact in (axis, THESIS_ARTIFACT_ID, f"axis:{axis}"):
        hits.append(_Hit(event.on_trigger or REVIEW_REQUIRED, f"disproof／review 條件觸發：{event.detail}",
                         event.changed_ref, event.observed_at))
    return hits


def _thesis_hits(artifact: ArtifactDependency, event: ChangeEvent) -> list[_Hit]:
    hits: list[_Hit] = []
    state = THESIS_POLICY.get(event.change_type)
    if state is not None:
        hits.append(_Hit(state, f"{event.change_type}：{event.detail or event.changed_ref}",
                         event.changed_ref, event.observed_at))
    if event.change_type in STRUCTURAL_CHANGE_TYPES:
        touched = _touches(event, artifact.refs_with_role(ROLE_SUPPORTING, ROLE_LEGACY))
        if touched:
            hits.append(_Hit(INVALIDATED if _is_retraction(event) else REVIEW_REQUIRED,
                             f"thesis 引用的證據{'已撤回' if _is_retraction(event) else '變了'}：{touched}",
                             event.changed_ref, event.observed_at, touched))
    if event.change_type == THESIS_REVIEW_DUE and event.target_artifact in (None, THESIS_ARTIFACT_ID):
        hits.append(_Hit(STALE, f"排程複查到期：{event.detail}", event.changed_ref, event.observed_at))
    if event.change_type == DISPROOF_SIGNAL and event.target_artifact == THESIS_ARTIFACT_ID:
        hits.append(_Hit(event.on_trigger or REVIEW_REQUIRED, f"disproof 條件觸發：{event.detail}",
                         event.changed_ref, event.observed_at))
    return hits


def _assumption_hits(artifact: ArtifactDependency, event: ChangeEvent) -> list[_Hit]:
    hits: list[_Hit] = []
    by_basis = ASSUMPTION_CLASS_POLICY.get(event.change_type, {})
    state = by_basis.get(artifact.basis or "") or by_basis.get("*")
    if state is not None:
        hits.append(_Hit(state, (f"{event.change_type}：{event.detail or event.changed_ref}；"
                                 f"這條假設的 basis 是 {artifact.basis}（沿用較舊的觀測），新的觀測到了就該重看"),
                         event.changed_ref, event.observed_at))
    if event.change_type in STRUCTURAL_CHANGE_TYPES:
        touched = _touches(event, artifact.refs_with_role(ROLE_SUPPORTING, ROLE_LEGACY))
        if touched:
            hits.append(_Hit(INVALIDATED if _is_retraction(event) else REVIEW_REQUIRED,
                             (f"supporting evidence {touched} "
                              f"{'已撤回' if _is_retraction(event) else '變了'}（{event.detail or event.change_type}）"
                              "——證據物件還在不等於仍支持這個假設"),
                             event.changed_ref, event.observed_at, touched))
    if event.change_type == CONSENSUS:
        touched = _touches(event, artifact.refs_with_role(ROLE_CALIBRATION))
        if touched:
            hits.append(_Hit(REVIEW_REQUIRED,
                             f"assumption calibrated relative to market consensus：校準用的共識 {touched} 變了"
                             f"（{event.detail or ''}）",
                             event.changed_ref, event.observed_at, touched))
    if event.change_type == COMPANY_GUIDANCE and artifact.driver:
        relevant = sorted({f for f in event.material_fields if guidance_driver(f) == artifact.driver})
        if relevant:
            hits.append(_Hit(REVIEW_REQUIRED,
                             (f"新指引欄位 {relevant}（{event.effective_at or event.observed_at.date()}）"
                              f"直接對應 driver {artifact.driver}；是否矛盾未由機器判定"),
                             event.changed_ref, event.observed_at))
    if event.change_type == DISPROOF_SIGNAL and event.target_artifact == artifact.artifact_id:
        hits.append(_Hit(event.on_trigger or REVIEW_REQUIRED, f"review 條件觸發：{event.detail}",
                         event.changed_ref, event.observed_at))
    if event.change_type == THESIS_REVIEW_DUE and event.target_artifact == artifact.artifact_id:
        hits.append(_Hit(STALE, f"到期：{event.detail}", event.changed_ref, event.observed_at))
    return hits


def _derived_hits(artifact: ArtifactDependency, event: ChangeEvent) -> list[_Hit]:
    hits: list[_Hit] = []
    if event.change_type in DERIVED_CLASS_POLICY.get(artifact.artifact_type, frozenset()):
        hits.append(_Hit(RECALCULATE, f"{event.change_type}：{event.detail or event.changed_ref}——確定性輸入變了，重算即可",
                         event.changed_ref, event.observed_at))
    touched = _touches(event, frozenset(artifact.refs))
    if touched and event.change_type not in (THESIS_REVIEW_DUE, DISPROOF_SIGNAL, FISCAL_PERIOD_ROLLOVER):
        hits.append(_Hit(RECALCULATE, f"輸入 {touched} 變了（{event.change_type}）——重算即可",
                         event.changed_ref, event.observed_at, touched))
    if event.change_type in _LEDGER_CHANGE_TYPES:
        superseded = _touches(event, frozenset(artifact.assumption_ids))
        if superseded:
            hits.append(_Hit(RECALCULATE, f"輸入假設 {superseded} 已被取代——用新假設重算即可",
                             event.changed_ref, event.observed_at, superseded))
    if (event.change_type == FISCAL_PERIOD_ROLLOVER and artifact.artifact_type == ARTIFACT_MODEL
            and event.target_artifact == artifact.artifact_id):
        hits.append(_Hit(REVIEW_REQUIRED, f"會計期間推進：{event.detail}", event.changed_ref, event.observed_at))
    return hits


def _hits_for(artifact: ArtifactDependency, event: ChangeEvent) -> list[_Hit]:
    if artifact.artifact_type == ARTIFACT_AXIS:
        return _axis_hits(artifact, event)
    if artifact.artifact_type == ARTIFACT_THESIS:
        return _thesis_hits(artifact, event)
    if artifact.artifact_type in ASSUMPTION_ARTIFACT_TYPES:
        return _assumption_hits(artifact, event)
    return _derived_hits(artifact, event)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def resolve_refresh(
    *,
    ticker: str,
    company_id: str | None,
    artifacts: Sequence[ArtifactDependency],
    changes: Sequence[ChangeEvent] = (),
    observations: Sequence[MetricObservation] = (),
    as_of: date | None = None,
    today: date,
) -> RefreshReport:
    """單一 authority 的 impact resolution。read model 只消費它的輸出，不自己判 impact。"""
    reference_day = as_of or today
    cutoff = end_of_day(reference_day)
    notes: list[str] = []

    excluded_changes: dict[str, int] = {}
    accepted: list[ChangeEvent] = []
    for event in changes:
        if event.observed_at > cutoff:
            excluded_changes["observed_after_as_of"] = excluded_changes.get("observed_after_as_of", 0) + 1
            continue
        accepted.append(event)

    excluded_artifacts: dict[str, int] = {}
    visible: list[ArtifactDependency] = []
    for artifact in artifacts:
        if artifact.established_at is not None and artifact.established_at > cutoff:
            excluded_artifacts["established_after_as_of"] = excluded_artifacts.get("established_after_as_of", 0) + 1
            continue
        visible.append(artifact)

    accepted.extend(_condition_events(visible, observations, ticker=ticker, company_id=company_id,
                                      cutoff=cutoff, notes=notes))
    accepted.extend(_schedule_events(visible, ticker=ticker, company_id=company_id, cutoff=cutoff, notes=notes))
    accepted.extend(_rollover_events(visible, ticker=ticker, company_id=company_id, notes=notes))
    accepted.sort(key=lambda e: (e.observed_at, e.change_type, e.changed_ref))

    legacy = [a for a in visible if a.artifact_type in ASSUMPTION_ARTIFACT_TYPES
              and a.extras.get("provenance_semantics") == "legacy" and a.preset_state is None]
    if legacy:
        notes.append(f"{len(legacy)} 條生效假設是 legacy provenance（未宣告 ref 角色）：未分類 ref 一律當 "
                     "supporting、同期共識 ref 依前綴當 calibration（fail safe）")

    # ---- 第一輪：逐成果套規則 ------------------------------------------------
    resolved: dict[str, AffectedArtifact] = {}
    for artifact in visible:
        if artifact.preset_state is not None:
            resolved[artifact.key] = AffectedArtifact(
                artifact_type=artifact.artifact_type, artifact_id=artifact.artifact_id,
                label=artifact.label, state=artifact.preset_state, reasons=(artifact.preset_reason or "",),
                established_at=artifact.established_at, kind=artifact.kind,
            )
            continue
        hits: list[_Hit] = []
        for event in accepted:
            if artifact.established_at is not None and event.known_at() <= artifact.established_at:
                continue                       # 建立當時已經知道（世界或系統）——不是新變化
            if event.change_type in _LEDGER_CHANGE_TYPES and event.changed_ref == artifact.artifact_id:
                continue                       # 自己就是那筆新紀錄
            hits.extend(_hits_for(artifact, event))
        resolved[artifact.key] = _compose(artifact, hits)

    # ---- 第二輪：沿 assumption_ids 往下游傳播（只一層、只沿宣告的依賴）--------------
    for artifact in visible:
        if artifact.kind != KIND_DETERMINISTIC or not artifact.assumption_ids:
            continue
        current = resolved[artifact.key]
        if current.state in (SUPERSEDED, MISSING):
            continue
        propagated: list[str] = []
        states: list[str] = [current.state]
        inherited: list[tuple[str, str]] = []
        for aid in artifact.assumption_ids:
            # 上游可能是營運假設（oa_*）、估值假設（va_*）或 horizon 假設（ha_*）；都是宣告過的依賴，都沿一層傳播。
            upstream = next((resolved[f"{t}:{aid}"] for t in sorted(ASSUMPTION_ARTIFACT_TYPES)
                             if f"{t}:{aid}" in resolved), None)
            if upstream is None or upstream.state in (CURRENT, MISSING):
                continue
            mapped = {REVIEW_REQUIRED: REVIEW_REQUIRED, INVALIDATED: INVALIDATED,
                      SUPERSEDED: RECALCULATE, RECALCULATE: RECALCULATE, STALE: STALE}[upstream.state]
            states.append(mapped)
            propagated.append(upstream.key)
            inherited.append((mapped, f"[{mapped}] 輸入假設 {aid} 是 {upstream.state}"
                                      f"（{upstream.reasons[0] if upstream.reasons else ''}）"
                                      "——這個數字算法確定，但它依賴的判斷已被動搖"))
        if propagated:
            merged = merge_states(states)
            # 決定 state 的理由排最前面：傳播來的 review 若壓過自己的 recalculate，讀者第一眼要看到的是前者。
            ordered_reasons = ([r for st, r in inherited if st == merged] + list(current.reasons)
                               + [r for st, r in inherited if st != merged])
            resolved[artifact.key] = AffectedArtifact(
                artifact_type=current.artifact_type, artifact_id=current.artifact_id, label=current.label,
                state=merged, reasons=tuple(dict.fromkeys(ordered_reasons)),
                changed_refs=current.changed_refs, dependency_refs=current.dependency_refs,
                detected_at=current.detected_at, established_at=current.established_at,
                propagated_from=tuple(propagated), kind=current.kind,
            )

    ordered = sorted(resolved.values(), key=lambda a: (
        _ORDER.get(a.artifact_type, 9), _AXIS_ORDER.get(a.artifact_id, 9) if a.artifact_type == ARTIFACT_AXIS else 0,
        a.artifact_id))
    return RefreshReport(
        ticker=ticker, company_id=company_id, as_of=as_of, reference_day=reference_day,
        policy_version=POLICY_VERSION, changes=tuple(accepted), artifacts=tuple(ordered),
        excluded_changes=excluded_changes, excluded_artifacts=excluded_artifacts, notes=tuple(notes),
    )


def _compose(artifact: ArtifactDependency, hits: Sequence[_Hit]) -> AffectedArtifact:
    if not hits:
        return AffectedArtifact(artifact_type=artifact.artifact_type, artifact_id=artifact.artifact_id,
                                label=artifact.label, state=CURRENT, established_at=artifact.established_at,
                                kind=artifact.kind)
    state = merge_states([h.state for h in hits])
    # 理由依「對 state 的貢獻」排：讓決定 state 的那條理由排第一，其餘保留（stale 與 review 同時成立時兩者都看得到）。
    ranked = sorted(hits, key=lambda h: (-_rank(h.state), h.observed_at))
    return AffectedArtifact(
        artifact_type=artifact.artifact_type, artifact_id=artifact.artifact_id, label=artifact.label,
        state=state, reasons=tuple(dict.fromkeys(f"[{h.state}] {h.reason}" for h in ranked)),
        changed_refs=tuple(dict.fromkeys(h.changed_ref for h in ranked)),
        dependency_refs=tuple(dict.fromkeys(h.dependency_ref for h in ranked if h.dependency_ref)),
        detected_at=max(h.observed_at for h in hits), established_at=artifact.established_at,
        kind=artifact.kind,
    )


def _rank(state: str) -> int:
    return {CURRENT: 0, STALE: 1, RECALCULATE: 2, REVIEW_REQUIRED: 3, INVALIDATED: 4}[state]


__all__ = ["resolve_refresh"]
