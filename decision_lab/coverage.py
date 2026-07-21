"""Coverage Gate 與 bounded Minimum Viable Research Packet。"""
from __future__ import annotations

from datetime import datetime

from .models import ContextBundle, CoverageResult
from .store import DecisionStore


_CHECKLIST_ITEMS = (
    "gross_margin_trend",
    "customer_concentration",
    "backlog",
    "dilution",
    "valuation_pressure",
)


def _valid_future_time(expiry: str, evaluation_at: str) -> bool:
    try:
        end = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
        now = datetime.fromisoformat(evaluation_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    return end.tzinfo is not None and now.tzinfo is not None and end > now


def assess_coverage(
    store: DecisionStore,
    bundle: ContextBundle,
    *,
    catalyst: str,
    disproof: str,
    expiry: str,
    decision_relevance: int,
    falsifiability: int,
    information_value: int,
) -> CoverageResult:
    payload = bundle.payload
    blockers: list[str] = []
    identity = payload["identity"]
    evidence = payload["evidence"]
    financial = payload["financial"]
    if identity.get("status") != "resolved":
        blockers.append("identity_unresolved")
    focus = evidence.get("focus_company") or {}
    if focus.get("id") != identity.get("company_id"):
        blockers.append("graph_company_missing")
    sources = evidence.get("sources") or []
    if not sources:
        blockers.append("best_source_missing")
    subject_origin = str(evidence.get("subject_origin_entity") or "").casefold()
    if not any(
        str(source.get("origin_entity") or "").casefold() not in {"", subject_origin}
        for source in sources
        if isinstance(source, dict)
    ):
        blockers.append("independent_source_missing")
    if not evidence.get("causal_paths"):
        blockers.append("causal_path_missing")
    if not evidence.get("counter_paths"):
        blockers.append("counter_path_missing")
    if financial.get("status") in {"missing", "unavailable", "quarantined"}:
        blockers.append(f"financial_{financial.get('status')}")
    checklist = financial.get("checklist") or {}
    for item_name in _CHECKLIST_ITEMS:
        status = (checklist.get(item_name) or {}).get("status", "missing")
        if status not in {"ok", "manual_reviewed"}:
            blockers.append(f"financial_{item_name}_{status}")
        elif status == "manual_reviewed":
            item = checklist.get(item_name) or {}
            if not str(item.get("value") or "").strip() or not item.get("source"):
                blockers.append(f"financial_{item_name}_manual_source_missing")
    if (financial.get("runway") or {}).get("status") not in {
        "calculated",
        "self_funding",
    }:
        blockers.append("financial_runway_manual_required")
    if not catalyst.strip():
        blockers.append("catalyst_missing")
    if not disproof.strip():
        blockers.append("disproof_missing")
    if not _valid_future_time(expiry, str(payload["evaluation_at"])):
        blockers.append("expiry_invalid")

    paper_blockers = tuple(
        blocker
        for section in (
            payload["market"],
            payload["fx"],
            payload["financial"],
            payload["paper_exposure"],
        )
        if section.get("status") != "available"
        for blocker in (section.get("blockers") or [f"{section.get('status')}_data"])
    )
    holdings = payload["holdings"]
    live_blockers = tuple(
        blocker
        for section in (
            holdings,
            payload.get("execution_market") or {},
            payload.get("execution_fx") or {},
        )
        if section.get("status")
        not in {"confirmed", "confirmed_empty", "available", "observed"}
        for blocker in (section.get("blockers") or [f"{section.get('status')}_data"])
    )
    status = "coverage_pending" if blockers else "analyzable"
    stored = store.record_coverage_assessment(
        cohort_id=bundle.cohort_id,
        context_digest=bundle.digest,
        status=status,
        blockers=tuple(sorted(set(blockers))),
        paper_blockers=paper_blockers,
        live_blockers=live_blockers,
        catalyst=catalyst,
        disproof=disproof,
        expiry=expiry,
        decision_relevance=decision_relevance,
        falsifiability=falsifiability,
        information_value=information_value,
    )
    return CoverageResult(
        assessment_id=stored["assessment_id"],
        cohort_id=bundle.cohort_id,
        context_digest=bundle.digest,
        status=status,
        blockers=tuple(sorted(set(blockers))),
        paper_blockers=paper_blockers,
        live_blockers=live_blockers,
        paper_context_ready=status == "analyzable" and not paper_blockers,
        live_context_ready=(
            status == "analyzable"
            and holdings.get("status") in {"confirmed", "confirmed_empty"}
            and not live_blockers
        ),
        paper_supported_position=0.0,
        live_supported_range=(0.0, 0.0),
        work_order_id=stored["work_order_id"],
    )
