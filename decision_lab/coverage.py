"""Coverage Gate 與 bounded Minimum Viable Research Packet。"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from .blocker_severity import CHECKLIST_ITEMS as _CHECKLIST_ITEMS, fatal_blockers
from .models import ContextBundle, CoverageResult
from .store import DecisionStore


_EXECUTION_INTENTS = {"research", "paper", "live"}


def apply_execution_intent(
    coverage: CoverageResult, execution_intent: str
) -> CoverageResult:
    """Apply lane permission as blockers on the existing Coverage result。"""

    if execution_intent not in _EXECUTION_INTENTS:
        raise ValueError("execution_intent must be research, paper, or live")
    paper_blockers = list(coverage.paper_blockers)
    live_blockers = list(coverage.live_blockers)
    if execution_intent == "research":
        paper_blockers.append("execution_intent_research_only")
        live_blockers.append("execution_intent_research_only")
    elif execution_intent == "paper":
        live_blockers.append("execution_intent_paper_only")
    normalized_paper = tuple(sorted(set(paper_blockers)))
    normalized_live = tuple(sorted(set(live_blockers)))
    # readiness 判準必須和 store.get_coverage_result 一致：看致命 blocker，不看
    # status 這個二元標籤。這裡先前用 status，於是它會把 store 剛算對的 readiness
    # 覆寫回去——同一個 bug 的第四個現場。
    fatal = fatal_blockers(coverage.blockers)
    return replace(
        coverage,
        paper_blockers=normalized_paper,
        live_blockers=normalized_live,
        paper_context_ready=not fatal
        and not fatal_blockers(normalized_paper, lane="paper"),
        live_context_ready=not fatal
        and not fatal_blockers(normalized_live, lane="live"),
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
    execution_intent: str = "live",
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
    permissioned = apply_execution_intent(
        CoverageResult(
            assessment_id="pending",
            cohort_id=bundle.cohort_id,
            context_digest=bundle.digest,
            status=status,
            blockers=tuple(sorted(set(blockers))),
            paper_blockers=paper_blockers,
            live_blockers=live_blockers,
            paper_context_ready=False,
            live_context_ready=False,
            paper_supported_position=0.0,
            live_supported_range=(0.0, 0.0),
            work_order_id=None,
        ),
        execution_intent,
    )
    paper_blockers = permissioned.paper_blockers
    live_blockers = permissioned.live_blockers
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
        # lane readiness 只看「對該 lane 致命」的 blocker。先前是 `not paper_blockers`
        # ／`not live_blockers`——任一非致命 lane blocker 也會打成 not ready。
        # holdings 的確認需求不在此硬編碼：它由 holdings_unavailable（fatal，僅 live）
        # 與 holdings_unconfirmed（diagnostic）表達，寫在這裡等於同一條政策的第三份
        # 表示，且會覆寫剛做完的嚴重度分類。
        paper_context_ready=not fatal_blockers(tuple(sorted(set(blockers))))
        and not fatal_blockers(paper_blockers, lane="paper"),
        live_context_ready=(
            not fatal_blockers(tuple(sorted(set(blockers))))
            and not fatal_blockers(live_blockers, lane="live")
        ),
        paper_supported_position=0.0,
        live_supported_range=(0.0, 0.0),
        work_order_id=stored["work_order_id"],
    )
