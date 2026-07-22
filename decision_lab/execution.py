"""System paper 與 explicit user live facts 的 application boundary。"""
from __future__ import annotations

import math
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Mapping

from identity.registry import IdentityRegistry, get_registry
from thesis.investment_policy import load_policy, validate_policy

from .models import (
    ContextBundle,
    CoverageResult,
    DecisionExecutionResult,
    PreparedAction,
)
from .coverage import apply_execution_intent
from .sizing import calculate_probe_limits
from .store import DecisionStore


class ExecutionError(ValueError):
    """Mutation request did not satisfy an explicit authority boundary。"""


def _utc_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ExecutionError("effective_at must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ExecutionError("effective_at must include timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def assess_probe(
    store: DecisionStore,
    bundle: ContextBundle,
    coverage: CoverageResult,
    assessment: Mapping[str, Any],
    *,
    idempotency_key: str,
    effective_at: str,
    policy: Mapping[str, Any] | None = None,
    registry: IdentityRegistry | None = None,
    execution_intent: str = "live",
    _failure_at: str | None = None,
) -> DecisionExecutionResult:
    """Atomically persist a system decision and any eligible paper target。"""

    effective_at = _utc_timestamp(effective_at)
    try:
        authoritative_bundle = store.get_context_bundle(bundle.digest)
        authoritative_coverage = store.get_coverage_result(coverage.assessment_id)
    except KeyError as exc:
        raise ExecutionError(str(exc)) from exc
    if (
        authoritative_bundle.cohort_id != bundle.cohort_id
        or authoritative_coverage.cohort_id != authoritative_bundle.cohort_id
        or authoritative_coverage.context_digest != authoritative_bundle.digest
    ):
        raise ExecutionError("context and coverage do not belong to the same stored cohort")
    bundle = authoritative_bundle
    try:
        coverage = apply_execution_intent(
            authoritative_coverage,
            execution_intent,
        )
    except ValueError as exc:
        raise ExecutionError(str(exc)) from exc

    current_policy = validate_policy(policy) if policy is not None else load_policy()
    probe = current_policy.get("probe_lane")
    if not isinstance(probe, Mapping):
        raise ExecutionError("investment policy has no Probe lane")
    registry = registry or get_registry()
    company_id = str(bundle.payload.get("identity", {}).get("company_id") or "")
    request_payload = {
        "cohort_id": bundle.cohort_id,
        "context_digest": bundle.digest,
        "coverage": asdict(coverage),
        "assessment": assessment,
        "policy_version": current_policy["policy_version"],
        "calculator_version": probe["calculator_version"],
        "effective_at": effective_at,
        "execution_intent": execution_intent,
    }

    def calculator(paper_exposure: Mapping[str, Any]):
        return calculate_probe_limits(
            bundle,
            coverage,
            assessment,
            policy=current_policy,
            registry=registry,
            paper_exposure_override=paper_exposure,
        )

    try:
        return store.atomic_assess_probe(
            cohort_id=bundle.cohort_id,
            context_digest=bundle.digest,
            coverage_assessment_id=coverage.assessment_id,
            idempotency_key=idempotency_key,
            effective_at=effective_at,
            request_payload=request_payload,
            paper_nav=float(probe["paper_nav"]),
            company_id=company_id,
            factor_resolver=registry.factor_tags,
            calculator=calculator,
            failure_at=_failure_at,
        )
    except ValueError as exc:
        if "idempotency" in str(exc):
            raise ExecutionError(str(exc)) from exc
        raise


def record_live_choice(
    store: DecisionStore,
    decision_id: str,
    *,
    selected_weight: float,
    decided_at: str,
    explicit: bool,
    reason: str | None = None,
    confirmation_ref: str | None = None,
) -> str:
    if not explicit:
        raise ExecutionError("live choice requires explicit user confirmation")
    try:
        return store.record_live_choice(
            decision_id=decision_id,
            selected_weight=selected_weight,
            decided_at=decided_at,
            reason=reason,
            confirmation_ref=confirmation_ref,
        )
    except (KeyError, ValueError) as exc:
        raise ExecutionError(str(exc)) from exc


def record_live_fill(
    store: DecisionStore,
    decision_id: str,
    *,
    execution_ref: str,
    shares: float,
    price: float,
    currency: str,
    executed_at: str,
    explicit: bool,
) -> str:
    if not explicit:
        raise ExecutionError("live fill requires explicit user report")
    try:
        return store.record_live_fill(
            decision_id=decision_id,
            execution_ref=execution_ref,
            shares=shares,
            price=price,
            currency=currency,
            executed_at=executed_at,
        )
    except (KeyError, ValueError) as exc:
        raise ExecutionError(str(exc)) from exc


def prepare_managed_action(
    store: DecisionStore,
    *,
    action_type: str,
    target_id: str,
    payload: Mapping[str, Any],
    prepared_at: str,
    expires_at: str,
) -> PreparedAction:
    reason = payload.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ExecutionError("managed action requires an explicit reason")
    if action_type == "live_override":
        selected = payload.get("selected_weight")
        if (
            isinstance(selected, bool)
            or not isinstance(selected, (int, float))
            or not math.isfinite(float(selected))
            or float(selected) < 0
        ):
            raise ExecutionError("live override selected_weight is invalid")
    elif action_type == "paper_correction":
        target = payload.get("target_weight")
        if (
            isinstance(target, bool)
            or not isinstance(target, (int, float))
            or not math.isfinite(float(target))
            or float(target) < 0
        ):
            raise ExecutionError("paper correction target_weight is invalid")
    elif action_type != "paper_reversal":
        raise ExecutionError("unsupported managed action")
    try:
        return store.prepare_action(
            action_type=action_type,
            target_id=target_id,
            payload=payload,
            prepared_at=prepared_at,
            expires_at=expires_at,
        )
    except ValueError as exc:
        raise ExecutionError(str(exc)) from exc


def apply_live_override(
    store: DecisionStore,
    action_id: str,
    digest: str,
    *,
    native_approved: bool,
    decided_at: str,
) -> str:
    if not native_approved:
        raise ExecutionError("native approval is required")
    try:
        return store.apply_live_override(
            action_id=action_id,
            digest=digest,
            decided_at=decided_at,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ExecutionError(str(exc)) from exc


def apply_paper_amendment(
    store: DecisionStore,
    action_id: str,
    digest: str,
    *,
    native_approved: bool,
    effective_at: str,
) -> str:
    if not native_approved:
        raise ExecutionError("native approval is required")
    try:
        return store.apply_paper_amendment(
            action_id=action_id,
            digest=digest,
            effective_at=effective_at,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ExecutionError(str(exc)) from exc
