"""模擬情境：在**真實 runtime state** 上疊一件假想的變化，看 refresh 引擎會把誰標成什麼。

用途是驗收與解釋（「如果明天有新指引，哪些東西會變？」），不是預測。情境事件一律標
`authority="scenario://..."`，`observed_at` 在 build 之後，所以每個成果都會把它視為新變化。
`fiscal_rollover` 例外：它不是一件事件，是「把基期換成目標期間的實際值」——需要重跑模型。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Sequence

from alpha.fundamental.contracts import FiscalPeriod, FiscalYearActuals, FundamentalModelResult
from alpha.refresh import (
    COMPANY_GUIDANCE, CONSENSUS, DISPROOF_SIGNAL, FINANCIAL_ACTUAL, GRAPH_EDGE, MARKET_PRICE,
    ChangeEvent, MetricObservation, ReviewCondition, end_of_day,
)
from alpha.contracts import EvidenceRef

SCENARIOS: tuple[str, ...] = (
    "price_only", "consensus_revision", "graph_edge", "new_guidance", "new_actual",
    "fiscal_rollover", "disproof",
)


def _at(today: date) -> datetime:
    """情境事件的時點：當天最後一秒——晚於 build（23:59:58），又不晚於 as-of cutoff。"""
    return end_of_day(today)


def scenario_changes(
    name: str, *, ticker: str, company_id: str | None, context: Any,
    model: FundamentalModelResult | None, today: date,
) -> tuple[list[ChangeEvent], list[MetricObservation]]:
    """回傳 (事件, 觀測)。找不到對應的 runtime 物件時用合成 ref，仍然是合法事件。"""
    at = _at(today)
    snap_ref = f"engine_c://financial_snapshot/{ticker}"
    events: list[ChangeEvent] = []
    observations: list[MetricObservation] = []
    if name == "price_only":
        price = context.market.price
        old = f"{price:g}" if price else "?"
        new = f"{price * 1.066:g}" if price else "?"
        events.append(ChangeEvent(change_type=MARKET_PRICE, ticker=ticker, company_id=company_id,
                                  authority="scenario://market_price", changed_ref=snap_ref, observed_at=at,
                                  effective_at=today + timedelta(days=1), old_version=old, new_version=new,
                                  material_fields=("price",), detail=f"模擬：只有價格變動 {old} → {new}"))
    elif name == "consensus_revision":
        target = model.target_period if model and model.target_period else None
        eps = next((c for c in (model.consensus if model else ()) if c.metric == "eps" and target and c.period.same_as(target)), None)
        ref = eps.refs[0] if eps and eps.refs else f"engine_c://consensus_estimate/{ticker}/eps/{target.end if target else '?'}"
        old = f"{eps.value:.4g}" if eps and eps.value else "9.42"
        new = f"{(eps.value * 1.0616):.4g}" if eps and eps.value else "10.00"
        events.append(ChangeEvent(change_type=CONSENSUS, ticker=ticker, company_id=company_id,
                                  authority="scenario://consensus", changed_ref=ref, observed_at=at,
                                  old_version=old, new_version=new, material_fields=("eps",),
                                  detail=f"模擬：{target.label if target else 'FY'} EPS 共識 {old} → {new}"))
    elif name == "graph_edge":
        edge = next((r for r in context.structural.evidence if r.kind == "graph_edge"), None)
        ref = edge.ref if edge else f"graph://edge/{company_id}/supplies_to/?"
        others = tuple(r.ref for r in context.structural.evidence if edge is None or r.ref != edge.ref)
        sub = context.structural.substitutability
        events.append(ChangeEvent(change_type=GRAPH_EDGE, ticker=ticker, company_id=company_id,
                                  authority="scenario://graph_edge", changed_ref=ref, observed_at=at,
                                  old_version=f"substitutability={sub}", new_version="substitutability=3",
                                  material_fields=("substitutability", "sole_source"),
                                  detail=f"模擬：結構邊 {ref} substitutability {sub} → 3、sole_source true → false",
                                  related_refs=others))
    elif name == "new_guidance":
        events.append(ChangeEvent(change_type=COMPANY_GUIDANCE, ticker=ticker, company_id=company_id,
                                  authority="scenario://company_guidance",
                                  changed_ref="engine_c://manual_observation/scenario_guidance", observed_at=at,
                                  effective_at=today + timedelta(days=90), published_at=today + timedelta(days=1),
                                  material_fields=("revenue_low", "revenue_high", "gross_margin_low", "gross_margin_high",
                                                   "tax_rate_low", "tax_rate_high"),
                                  detail="模擬：新一季指引（營收／毛利率／稅率）"))
    elif name == "new_actual":
        q_end = (model.base_period.end + timedelta(days=92)) if model and model.base_period else today
        events.append(ChangeEvent(change_type=FINANCIAL_ACTUAL, ticker=ticker, company_id=company_id,
                                  authority="scenario://financial_actual",
                                  changed_ref="engine_c://manual_observation/scenario_actual", observed_at=at,
                                  effective_at=q_end, published_at=today + timedelta(days=1),
                                  material_fields=("revenue", "segment_revenue", "non_gaap"),
                                  detail=f"模擬：新一季實際值（至 {q_end}）"))
    elif name == "disproof":
        condition: ReviewCondition | None = None
        for a in (model.assumptions if model else ()):
            if a.review_conditions:
                condition = a.review_conditions[0]
                break
        if condition is not None:
            breach = condition.threshold * (0.9 if condition.operator in ("<", "<=") else 1.1)
            observations.append(MetricObservation(
                metric=condition.metric, scope=condition.scope, period_end=condition.period_end,
                period_kind=condition.period_kind, value=breach,
                ref="engine_c://manual_observation/scenario_disproof", observed_at=at))
        else:
            target = next((a.assumption_id for a in (model.assumptions if model else ())), None)
            events.append(ChangeEvent(change_type=DISPROOF_SIGNAL, ticker=ticker, company_id=company_id,
                                      authority="scenario://disproof", changed_ref="library://event_watches/scenario",
                                      observed_at=at, target_artifact=target or "session_judgment",
                                      on_trigger="review_required", detail="模擬：disproof 條件被觀測滿足"))
    elif name != "fiscal_rollover":
        raise ValueError(f"未知情境：{name}；已知 {SCENARIOS}")
    return events, observations


def rollover_actuals(model: FundamentalModelResult, *, today: date) -> FiscalYearActuals | None:
    """把目前模型的**目標期間**當成已報告：用內部估計當「實際值」重跑模型（只為情境，不寫任何 authority）。"""
    if model.base_actuals is None or model.target_period is None:
        return None
    base = model.base_actuals
    revenue = model.metrics.get("revenue")
    oi = model.metrics.get("operating_income")
    if revenue is None or not revenue.is_known:
        return None
    ratio = revenue.value / base.revenue
    ref = EvidenceRef(ref="engine_c://manual_observation/scenario_fy_rollover", kind="engine_c_observation",
                      origin_entity="issuer_filing", published_at=today + timedelta(days=1),
                      retrieved_at=today + timedelta(days=1),
                      recorded_at=_at(today))
    block = {"operating_income": (oi.value if oi and oi.is_known else (base.non_gaap or base.gaap).get("operating_income", 0.0) * ratio)}
    return FiscalYearActuals(
        period=FiscalPeriod(end=model.target_period.end), currency=base.currency, revenue=revenue.value,
        segment_revenue=({k: v * ratio for k, v in base.segment_revenue.items()} if base.segment_revenue else None),
        gaap=dict(block), non_gaap=(dict(block) if base.non_gaap else None), evidence=(ref,),
        source_filed_at=today + timedelta(days=1), recorded_at=_at(today), observation_id="scenario_fy_rollover",
    )


__all__ = ["SCENARIOS", "rollover_actuals", "scenario_changes"]
