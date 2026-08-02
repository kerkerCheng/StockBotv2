"""Coverage Gate 與 bounded Minimum Viable Research Packet。"""
from __future__ import annotations

from dataclasses import replace
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
_EXECUTION_INTENTS = {"research", "paper", "live"}

# Coverage blocker 分兩類，因為它們擋的是完全不同的東西。
#
# 「研究還不完整」＝知道在講哪家公司、也有可稽核的骨架，只是功課沒做完。這類
# 不該歸零資本，該讓 Confidence 的 axis_ceiling 生效——證據不完備就只能小注，
# 但不是不能參與。等到每一項都補齊，alpha 通常也已經被市場定價完畢。
#
# 「連在講什麼都不確定」＝身分無法解析、圖裡沒有這家公司、一份來源都沒有、
# 財務 authority 掛掉、沒有證偽條件、決策沒有有效期。這類仍然歸零：它們不是
# 「還沒被證實的好消息」，而是讓整筆決策無法被稽核或事後檢驗的缺陷。
#
# 未列入 _INCOMPLETE 的一律當致命處理（fail closed）。新增 blocker 時
# tests/test_coverage_severity.py 會失敗，強迫做出分類決定而不是預設放行。
_INCOMPLETE_COVERAGE_BLOCKERS = frozenset(
    {
        # 只有當事人來源；證據弱，但主張本身是明確的。
        "independent_source_missing",
        # 圖裡還沒有反面路徑。
        "counter_path_missing",
        # Engine C 算不出 runway（yfinance 在財報後常暫時缺 FCF）。
        "financial_runway_manual_required",
        # 還沒寫催化劑。disproof 是硬性的（L7），catalyst 不是。
        "catalyst_missing",
    }
)


def _is_incomplete_research(blocker: str) -> bool:
    if blocker in _INCOMPLETE_COVERAGE_BLOCKERS:
        return True
    # 財務核驗清單五項的各種缺漏：功課沒做完，不是不知道在講誰。
    return any(blocker.startswith(f"financial_{item}_") for item in _CHECKLIST_ITEMS)


def fatal_blockers(blockers: tuple[str, ...]) -> tuple[str, ...]:
    """回傳應使資本歸零的 blocker；研究不完整的項目不在其中。"""

    return tuple(b for b in blockers if not _is_incomplete_research(b))


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
    return replace(
        coverage,
        paper_blockers=normalized_paper,
        live_blockers=normalized_live,
        paper_context_ready=(
            coverage.status == "analyzable" and not normalized_paper
        ),
        live_context_ready=(
            coverage.status == "analyzable" and not normalized_live
        ),
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
