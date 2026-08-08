"""Probe lifecycle 與 claim/market/decision 分離的 immutable outcome。"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence

from .models import LifecycleResult, OutcomeResult
from .store import DecisionStore


class OutcomeError(ValueError):
    """Outcome cannot be closed without a reproducible fact envelope。"""


def _time(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise OutcomeError(f"{field} must be an ISO-8601 timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OutcomeError(f"{field} must be an ISO-8601 timestamp") from exc
    if result.tzinfo is None:
        raise OutcomeError(f"{field} must include timezone")
    return result


def _positive(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OutcomeError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise OutcomeError(f"{field} must be positive and finite")
    return result


def _refs(value: Sequence[str]) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not value:
        raise OutcomeError("outcome requires evidence_refs")
    refs = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    if len(refs) != len(value):
        raise OutcomeError("evidence_refs must be non-empty strings")
    return refs


def current_lifecycle(store: DecisionStore, cohort_id: str) -> LifecycleResult:
    return store.current_lifecycle(cohort_id)


def trigger_review_required(
    store: DecisionStore,
    cohort_id: str,
    *,
    reason: str,
    evidence_refs: Sequence[str],
    effective_at: str,
) -> LifecycleResult:
    if not reason.strip():
        raise OutcomeError("review reason is required")
    effective = _time(effective_at, "effective_at")
    refs = _refs(evidence_refs)
    due = (effective + timedelta(hours=48)).isoformat()
    try:
        return store.trigger_review_required(
            cohort_id=cohort_id,
            reason=reason.strip(),
            evidence_refs=refs,
            effective_at=effective_at,
            review_due_at=due,
        )
    except (KeyError, ValueError) as exc:
        raise OutcomeError(str(exc)) from exc


def _market_outcome(
    store: DecisionStore,
    cohort_id: str,
    current_market: Mapping[str, Any],
    benchmark: Mapping[str, Any],
    effective_at: str,
) -> dict[str, Any]:
    try:
        shadow = store.get_shadow(cohort_id)
    except KeyError:
        shadow = None
    current_status = current_market.get("status")
    benchmark_status = benchmark.get("status")
    inputs = {
        "shadow": (
            {
                "status": shadow.status,
                "price": shadow.price,
                "currency": shadow.currency,
                "source": shadow.source,
                "as_of": shadow.as_of,
            }
            if shadow is not None
            else {"status": "missing"}
        ),
        "current_market": dict(current_market),
        "benchmark": dict(benchmark),
    }
    if shadow is None or shadow.status != "observed" or shadow.price is None:
        return {
            "market_return_status": "unknown",
            "absolute_return": None,
            "benchmark_adjusted_return": None,
            "market_inputs": inputs,
        }
    if current_status != "observed":
        return {
            "market_return_status": "unknown",
            "absolute_return": None,
            "benchmark_adjusted_return": None,
            "market_inputs": inputs,
        }
    current_price = _positive(current_market.get("price"), "current_market.price")
    identity = store.cohort_identity(cohort_id)
    if current_market.get("ticker") != identity["research_ticker"]:
        raise OutcomeError("current market ticker does not match the cohort")
    if current_market.get("currency") != shadow.currency:
        raise OutcomeError("current market currency does not match Shadow inception")
    if not current_market.get("source"):
        raise OutcomeError("current market source is required")
    current_as_of = _time(current_market.get("as_of"), "current_market.as_of")
    shadow_as_of = _time(shadow.as_of, "shadow.as_of")
    if current_as_of < shadow_as_of:
        raise OutcomeError("current market observation predates Shadow inception")
    if current_as_of > _time(effective_at, "effective_at"):
        raise OutcomeError("current market observation cannot be from the future")
    absolute = current_price / shadow.price - 1.0
    adjusted: float | None = None
    status = "absolute_only"
    if benchmark_status == "observed":
        start = _positive(benchmark.get("start_price"), "benchmark.start_price")
        end = _positive(benchmark.get("end_price"), "benchmark.end_price")
        if not benchmark.get("source") or not benchmark.get("ticker"):
            raise OutcomeError("observed benchmark requires ticker and source")
        benchmark_start_as_of = _time(
            benchmark.get("start_as_of"), "benchmark.start_as_of"
        )
        benchmark_as_of = _time(benchmark.get("as_of"), "benchmark.as_of")
        # 對齊判準是「同一個交易日」，不是同一個時戳。日線 bar 的時戳帶著交易所的
        # 時區（Shadow 若錨在 SIVE.ST 是 +02:00，QQQ 是 −04:00），要求時戳完全相等
        # 等於規定「只能拿同一個市場的標的當 benchmark」——那會讓所有跨市場歸因
        # 永久不可能，而不是讓它們對齊。時戳同時承載「哪一個 session」與「哪個市場的
        # 時鐘」兩種語意，這裡只該比前者。
        if benchmark_start_as_of.date() != shadow_as_of.date():
            raise OutcomeError("benchmark start must align with Shadow inception")
        if benchmark_as_of < benchmark_start_as_of:
            raise OutcomeError("benchmark end predates its inception")
        if benchmark_as_of > _time(effective_at, "effective_at"):
            raise OutcomeError("benchmark observation cannot be from the future")
        adjusted = absolute - (end / start - 1.0)
        status = "benchmark_adjusted"
    return {
        "market_return_status": status,
        "absolute_return": absolute,
        "benchmark_adjusted_return": adjusted,
        "market_inputs": inputs,
    }


def _decision_attribution(
    store: DecisionStore,
    decision: Mapping[str, Any] | None,
    current_market: Mapping[str, Any],
    effective_at: str,
) -> dict[str, Any]:
    if decision is None:
        return {
            "decision_id": None,
            "system_paper_target": None,
            "paper_source_decision_id": None,
            "latest_recommendation_target": None,
            "user_live_weight": None,
            "user_choice_decision_id": None,
            "user_choice_type": None,
            "live_fill_ref": None,
            "live_fill_decision_id": None,
            "system_paper_return": None,
        }
    sizing = decision["payload"]["sizing"]
    context = store.get_context_bundle(decision["context_digest"]).payload
    company_id = str(context.get("identity", {}).get("company_id") or "")
    paper_state = store.paper_position_state(company_id, as_of=effective_at)
    source_decision_id = paper_state.get("decision_id")
    source_decision = (
        store.get_decision(str(source_decision_id))
        if source_decision_id is not None
        else None
    )
    choice, fill = store.latest_live_facts_for_cohort(
        str(decision["cohort_id"]), as_of=effective_at
    )
    system_return: float | None = None
    paper_context = (
        store.get_context_bundle(source_decision["context_digest"]).payload
        if source_decision is not None
        else context
    )
    decision_market = paper_context.get("market") or {}
    if (
        current_market.get("status") == "observed"
        and decision_market.get("status") == "available"
        and current_market.get("currency") == decision_market.get("currency")
    ):
        current_price = _positive(current_market.get("price"), "current_market.price")
        decision_price = _positive(decision_market.get("price"), "decision_market.price")
        system_return = current_price / decision_price - 1.0
    return {
        "decision_id": decision["decision_id"],
        "paper_source_decision_id": source_decision_id,
        "system_paper_target": paper_state["weight"],
        "latest_recommendation_target": sizing["paper_target"],
        "system_paper_max": sizing["paper_max_supported_position"],
        "user_live_weight": choice["selected_weight"] if choice else None,
        "user_choice_decision_id": choice["decision_id"] if choice else None,
        "user_choice_type": choice["choice_type"] if choice else None,
        "live_fill_ref": fill["execution_ref"] if fill else None,
        "live_fill_decision_id": fill["decision_id"] if fill else None,
        "system_paper_return": system_return,
    }


def close_probe(
    store: DecisionStore,
    cohort_id: str,
    *,
    terminal_status: str,
    claim_correctness: str,
    current_market: Mapping[str, Any],
    benchmark: Mapping[str, Any],
    reason: str,
    evidence_refs: Sequence[str],
    effective_at: str,
    _failure_at: str | None = None,
) -> OutcomeResult:
    if terminal_status not in {"promoted", "rejected", "expired", "revised"}:
        raise OutcomeError("invalid terminal_status")
    if claim_correctness not in {"true", "false", "mixed", "unknown"}:
        raise OutcomeError("invalid claim_correctness")
    if not reason.strip():
        raise OutcomeError("outcome reason is required")
    _time(effective_at, "effective_at")
    refs = _refs(evidence_refs)
    market = _market_outcome(
        store, cohort_id, current_market, benchmark, effective_at
    )
    decision = store.latest_decision_for_cohort(cohort_id, as_of=effective_at)
    sizing = decision["payload"]["sizing"] if decision is not None else {}
    payload = {
        "claim_correctness": claim_correctness,
        "reason": reason.strip(),
        "evidence_refs": refs,
        **market,
        "decision_attribution": _decision_attribution(
            store, decision, current_market, effective_at
        ),
        "source_calibration_inputs": {
            "source_ids": store.signal_sources_for_cohort(cohort_id),
            "claim_correctness": claim_correctness,
            "market_return_status": market["market_return_status"],
        },
        "calculator_version": sizing.get("calculator_version"),
        "policy_version": sizing.get("policy_version"),
        "constraint_trace": sizing.get("constraint_trace", []),
    }
    try:
        return store.close_lifecycle_with_outcome(
            cohort_id=cohort_id,
            terminal_status=terminal_status,
            outcome_payload=payload,
            effective_at=effective_at,
            failure_at=_failure_at,
        )
    except (KeyError, ValueError) as exc:
        raise OutcomeError(str(exc)) from exc
