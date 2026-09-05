"""`build_fundamental_model()`——把觀測、假設與共識接成一次可稽核的模型執行。

所有輸入由呼叫端（`briefing/alpha_view/sources.py` 或測試）取好注入；本檔不開任何連線。

```
FiscalYearActuals（Engine C）─┐
OperatingAssumption[]（ledger）┼─ select_assumptions(as_of) ─► build_bridge ─► metrics／steps
ConsensusEstimate[]（Engine C）┘                                     │
                                                    verify_consensus_basis ─► compare_metric
```

## as-of 的三道門

1. 假設：`created_at <= T`（`select_assumptions`）。
2. 觀測與共識：provider 端已依 `recorded_at`／`bar_date` 過濾，本檔只核對它們沒有晚於 T。
3. 目標期間：由**基期觀測**推（下一個會計年度），不由今天的日期推。
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Any, Mapping, Sequence

from ..contracts import EvidenceRef, content_digest
from ..errors import ContractViolation
from .assumptions import select_assumptions
from .bridge import build_bridge
from .compare import compare_metric, verify_consensus_basis
from .contracts import (
    ASSUMPTION_DRIVERS, AssumptionSelection, ConsensusEstimate, ExpectationComparison,
    FiscalPeriod, FiscalYearActuals, FundamentalModelResult, GuidanceObservation, ModeledMetric,
    OperatingAssumption, Sensitivity,
)

#: 敏感度微擾：比率型 +0.01（一個百分點），金額／股數型 ×1.01。
_RATIO_BUMP = 0.01
_RELATIVE_BUMP = 0.01

_CORE_METRICS = ("revenue", "operating_margin", "eps")


def _sensitivities(
    actuals: FiscalYearActuals, accepted: Sequence[OperatingAssumption], target: FiscalPeriod,
    baseline: Mapping[str, ModeledMetric],
) -> tuple[Sensitivity, ...]:
    out: list[Sensitivity] = []
    base_rev = baseline["revenue"].value
    base_oi = baseline["operating_income"].value
    base_eps = baseline["eps"].value
    for item in accepted:
        spec = ASSUMPTION_DRIVERS[item.driver]
        if spec.unit == "ratio":
            bumped, bump, bump_unit = item.value + _RATIO_BUMP, _RATIO_BUMP, "absolute_ratio"
        else:
            bumped, bump, bump_unit = item.value * (1.0 + _RELATIVE_BUMP), _RELATIVE_BUMP, "relative"
        perturbed = [replace(a, value=bumped) if a.assumption_id == item.assumption_id else a
                     for a in accepted]
        try:
            result = build_bridge(actuals, perturbed, target)
        except ContractViolation:
            continue
        rev = result.metrics["revenue"].value
        oi = result.metrics["operating_income"].value
        eps = result.metrics["eps"].value

        def _delta(after: float | None, before: float | None) -> float | None:
            return (after - before) if (after is not None and before is not None) else None

        d_eps = _delta(eps, base_eps)
        out.append(Sensitivity(
            assumption_id=item.assumption_id, driver=item.driver, scope=item.scope,
            bump=bump, bump_unit=bump_unit,
            delta_revenue=_delta(rev, base_rev), delta_operating_income=_delta(oi, base_oi),
            delta_eps=d_eps,
            eps_relative=(d_eps / base_eps) if (d_eps is not None and base_eps) else None,
        ))
    return tuple(out)


def build_fundamental_model(
    *,
    company_id: str,
    ticker: str,
    as_of: date | None,
    today: date,
    actuals: FiscalYearActuals | None,
    actuals_reason: str | None,
    consensus: Sequence[ConsensusEstimate],
    guidance: Sequence[GuidanceObservation],
    assumption_records: Sequence[OperatingAssumption],
    evidence_index: Mapping[str, EvidenceRef],
    parse_errors: Sequence[str] = (),
    target_period: FiscalPeriod | None = None,
) -> FundamentalModelResult:
    """一次模型執行。任何一段缺料都以 `missing`＋理由現形，不讓整體失敗、也不補預設值。"""
    cutoff = as_of or today
    warnings: list[str] = []

    # ---- 0. PIT 自我核對：注入的觀測／共識不得晚於 T -------------------------
    if actuals is not None:
        if actuals.recorded_at is not None and actuals.recorded_at.date() > cutoff:
            warnings.append("基期觀測的 recorded_at 晚於 as_of，拒用（INV-6）")
            actuals, actuals_reason = None, "基期觀測寫入時間晚於 as_of（lookahead，拒用）"
        elif actuals.period.end > cutoff:
            warnings.append("基期觀測的會計年度尚未結束於 as_of，拒用（INV-6）")
            actuals, actuals_reason = None, "基期會計年度在 as_of 之後才結束（lookahead，拒用）"
    # ⚠ 共識的 `captured_at` 是行情交易日（bar_date），`fetched_at` 才是我們何時取得。
    # 週六 11:53 UTC 抓到的共識會標成週五的 bar_date——as_of=週五 時它其實還不存在（INV-6）。
    # 兩個時間都必須 ≤ T；價格可以用 bar_date 定日，分析師共識不行。
    def _known_by_cutoff(item: ConsensusEstimate) -> bool:
        if item.captured_at is not None and item.captured_at > cutoff:
            return False
        if item.fetched_at is not None and item.fetched_at.date() > cutoff:
            return False
        return True

    usable_consensus = tuple(c for c in consensus if _known_by_cutoff(c))
    if len(usable_consensus) != len(consensus):
        warnings.append(f"{len(consensus) - len(usable_consensus)} 筆共識晚於 as_of"
                        "（captured_at 或 fetched_at 在 T 之後），排除")
    usable_guidance = tuple(g for g in guidance if g.issued_at is None or g.issued_at <= cutoff)

    # ---- 1. 目標期間 ---------------------------------------------------------
    target = target_period
    if target is None and actuals is not None:
        target = actuals.period.shifted(1)
    if target is None and usable_consensus:
        target = min((c.period for c in usable_consensus), key=lambda p: p.end)

    # ---- 2. 證據索引：context ＋ 觀測 ＋ 共識 ＋ 指引 ----------------------
    index: dict[str, EvidenceRef] = dict(evidence_index)
    model_evidence: list[EvidenceRef] = []
    for source in ((actuals.evidence if actuals else ()),
                   *(c.evidence for c in usable_consensus), *(g.evidence for g in usable_guidance)):
        for ref in source:
            index.setdefault(ref.ref, ref)
            model_evidence.append(ref)

    # ---- 3. 假設選取 ---------------------------------------------------------
    if target is not None:
        accepted, selection = select_assumptions(
            assumption_records, target=target, as_of=as_of, today=today,
            evidence_index=index, parse_errors=parse_errors)
    else:
        accepted = ()
        selection = AssumptionSelection(
            input_count=len(assumption_records) + len(parse_errors), accepted_count=0,
            reasons={"no_target_period": len(assumption_records) + len(parse_errors)})

    # ---- 4. 橋 ---------------------------------------------------------------
    metrics: dict[str, ModeledMetric] = {}
    steps = ()
    sensitivities: tuple[Sensitivity, ...] = ()
    basis = "not_applicable"
    reason: str | None = None
    if actuals is None or target is None:
        reason = actuals_reason or "Engine C 無 fiscal_year_results 觀測——沒有基期就沒有橋"
        for name in ("revenue", "operating_margin", "operating_income", "net_income", "eps"):
            metrics[name] = ModeledMetric(metric=name, period=target or FiscalPeriod(end=cutoff),
                                          value=None, unit="currency", accounting_basis="not_applicable",
                                          reason=reason)
    else:
        bridge = build_bridge(actuals, accepted, target)
        metrics = dict(bridge.metrics)
        steps = bridge.steps
        basis = bridge.accounting_basis
        warnings.extend(bridge.warnings)
        if accepted:
            sensitivities = _sensitivities(actuals, accepted, target, metrics)
        if not accepted:
            reason = ("沒有任何可用的 OperatingAssumption（" + "；".join(
                f"{k}={v}" for k, v in selection.reasons.items()) + "）"
                      if selection.input_count else "尚未寫入任何 OperatingAssumption")

    # ---- 5. 共識與比較 --------------------------------------------------------
    consensus_bases = {
        f"{c.metric}:{c.period.end.isoformat()}": verify_consensus_basis(c, actuals)
        for c in usable_consensus
    }
    consensus_for_target: dict[str, ConsensusEstimate] = {}
    if target is not None:
        for item in usable_consensus:
            if item.period.same_as(target) and item.metric not in consensus_for_target:
                consensus_for_target[item.metric] = item
    comparisons: dict[str, ExpectationComparison] = {}
    for metric in ("revenue", "eps", "operating_margin"):
        estimate = consensus_for_target.get(metric)
        comparisons[metric] = compare_metric(
            metric, metrics.get(metric), estimate,
            consensus_basis=(consensus_bases[f"{estimate.metric}:{estimate.period.end.isoformat()}"]
                             if estimate else "unverified"),
            internal_currency=actuals.currency if actuals else None,
        )

    # ---- 6. 狀態 -------------------------------------------------------------
    known = [m for m in _CORE_METRICS if metrics.get(m) is not None and metrics[m].is_known]
    if len(known) == len(_CORE_METRICS):
        status = "available"
    elif known:
        status = "partial"
        reason = reason or "部分指標缺假設：" + "；".join(
            f"{m}={metrics[m].reason}" for m in _CORE_METRICS if m not in known)
    else:
        status = "missing"
        reason = reason or (metrics["revenue"].reason if metrics.get("revenue") else "無輸出")

    digest = content_digest({
        "company_id": company_id, "ticker": ticker, "as_of": as_of, "target": target,
        "base": actuals.period if actuals else None,
        "assumptions": [a.assumption_id for a in accepted],
        "consensus": [(c.metric, c.period.end, c.value, c.captured_at) for c in usable_consensus],
        "observations": actuals.refs if actuals else (),
    })
    return FundamentalModelResult(
        company_id=company_id, ticker=ticker, as_of=as_of, target_period=target,
        base_period=actuals.period if actuals else None, accounting_basis=basis, status=status,
        reason=reason, metrics=metrics, steps=steps, assumptions=tuple(accepted),
        selection=selection, sensitivities=sensitivities, comparisons=comparisons,
        consensus=usable_consensus, guidance=usable_guidance, base_actuals=actuals,
        consensus_bases=consensus_bases, digest=digest, warnings=tuple(warnings),
        evidence=tuple({r.ref: r for r in model_evidence}.values()),
    )


__all__ = ["build_fundamental_model"]
