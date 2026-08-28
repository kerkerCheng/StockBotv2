"""從原始 Signal 到 Action Card 的唯一高階 application workflow。"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from urllib.parse import urlparse

from identity.registry import get_registry
from thesis.investment_policy import load_policy

from .action_card import assert_safe_payload, build_action_card, markdown_text, render_markdown
from .context import build_context_bundle, holdings_snapshot_digest
from .coverage import assess_coverage
from .execution import assess_probe
from .intake import SignalSourceRegistry, capture_signal
from .models import TERMINAL_LIFECYCLE_STATUSES, MarketObservation, SignalInput
from .sizing import AXES
from .store import DecisionStore
from .workflow_ports import AuthoritySnapshot, IdentityAuthority, WorkflowDataProvider


_LOG = logging.getLogger(__name__)

_INTENTS = {"research", "paper", "live"}


@dataclass(frozen=True)
class EvaluationRequest:
    """人類／research agent 可提供的欄位；不暴露 Engine D internal IDs。"""

    raw_signal: str
    source_url: str | None = None
    ticker_hint: str | None = None
    company_hint: str | None = None
    company_id_hint: str | None = None
    thesis: str | None = None
    catalyst: str | None = None
    disproof: str | None = None
    expiry: str | None = None
    as_of: str | None = None
    execution_intent: str = "research"
    direction: str = "neutral"
    source_id: str = "unattributed"
    source_traced: bool = False
    evidence_tier: int = 4
    confirm_holdings: bool = False
    assessment: Mapping[str, Any] | None = None


class WorkflowError(ValueError):
    """Public request 或 immutable workflow contract 不成立。"""


class _StaticMarketObserver:
    def __init__(self, payload: Mapping[str, Any]):
        self._payload = payload

    def observe(
        self, company_id: str, research_ticker: str, observed_at: str
    ) -> MarketObservation:
        del company_id, observed_at
        payload = self._payload
        status = str(payload.get("status") or "missing")
        if status not in {"observed", "available"}:
            return MarketObservation(
                status="unavailable" if status == "unavailable" else "missing"
            )
        return MarketObservation(
            status="observed",
            ticker=str(payload.get("ticker") or research_ticker),
            price=payload.get("price"),
            currency=payload.get("currency"),
            source=payload.get("source"),
            as_of=payload.get("as_of"),
            fetched_at=payload.get("fetched_at"),
        )


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _time(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise WorkflowError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise WorkflowError(f"{field} must include timezone")
    return parsed.astimezone(timezone.utc)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validated_request(request: EvaluationRequest) -> EvaluationRequest:
    if not isinstance(request.raw_signal, str) or not request.raw_signal.strip():
        raise WorkflowError("raw_signal is required")
    if request.execution_intent not in _INTENTS:
        raise WorkflowError("execution_intent must be research, paper, or live")
    if request.direction not in {"long", "short", "neutral"}:
        raise WorkflowError("direction must be long, short, or neutral")
    if request.source_url:
        parsed = urlparse(request.source_url)
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
            raise WorkflowError("source_url must be a public http(s) URL")
    if request.as_of:
        _time(request.as_of, "as_of")
    if request.expiry:
        _time(request.expiry, "expiry")
    assert_safe_payload(asdict(request))
    return request


def _operation_key(request: EvaluationRequest, *, reassess_from: str | None = None) -> str:
    payload = {
        "kind": "reassess" if reassess_from else "evaluate",
        "reassess_from": reassess_from,
        "raw_signal": request.raw_signal.strip(),
        "source_url": request.source_url,
        "ticker_hint": request.ticker_hint,
        "company_hint": request.company_hint,
        "company_id_hint": request.company_id_hint,
        "thesis": request.thesis,
        "catalyst": request.catalyst,
        "disproof": request.disproof,
        "expiry": request.expiry,
        "explicit_as_of": request.as_of,
        "execution_intent": request.execution_intent,
        "direction": request.direction,
        "source_id": request.source_id,
        "source_traced": request.source_traced,
        "evidence_tier": request.evidence_tier,
        "confirm_holdings": request.confirm_holdings,
        "assessment": request.assessment,
    }
    return "ewo_" + _digest(payload)[:32]


def _default_expiry(evaluation_at: str, policy: Mapping[str, Any]) -> str:
    review_hours = float(policy["probe_lane"]["review_hours"])
    return (_time(evaluation_at, "evaluation_at") + timedelta(hours=review_hours)).isoformat()


def _source_uri(request: EvaluationRequest) -> str:
    if request.source_url:
        return request.source_url
    return "signal:" + hashlib.sha256(request.raw_signal.encode("utf-8")).hexdigest()


def _unknown_assessment() -> dict[str, dict[str, Any]]:
    return {
        axis: {
            "level": "unknown",
            "evidence_refs": [],
            "reason": "尚未提供語意研究評估。",
            "missing_data": ["research_assessment_missing"],
        }
        for axis in AXES
    }


def _unavailable_snapshot(
    identity: IdentityAuthority, *, failure: str | None = None
) -> AuthoritySnapshot:
    """整份 snapshot 不可用時的 fail-closed 佔位。

    `failure` 帶的是**例外類型名**（例如 `HttpError`、`TimeoutError`），不是訊息本文——
    訊息可能含憑證路徑或 token 片段，只寫進 log，不進 decision payload。
    """
    company_id = identity.company_id
    return AuthoritySnapshot(
        identity=identity,
        evidence={
            "status": "unresolved_identity" if not company_id else "graph_unavailable",
            "focus_company": {"id": company_id} if company_id else {},
            "subject_origin_entity": "",
            "sources": [],
            "causal_paths": [],
            "counter_paths": [],
            "blockers": [
                "identity_unresolved" if not company_id else "graph_unavailable"
            ],
        },
        financial={"status": "unavailable"},
        market={"status": "unavailable"},
        fx={"status": "unavailable"},
        holdings={"status": "unavailable"},
        statuses={
            "identity": identity.status,
            "graph": "unresolved_identity" if not company_id else "graph_unavailable",
            "financial": "unavailable",
            "market": "unavailable",
            "fx": "unavailable",
            "holdings": "unavailable",
            # 沒有 failure 就不寫這個 key：它的存在本身就代表「這批 unavailable 是同一次
            # 取得失敗的投影」，而不是各自獨立缺資料。少了它，下游只看到五個互不相關的
            # blocker，會把一次 provider 例外誤讀成研究不足（2026-08-28 實測）。
            **({"snapshot_failure": failure} if failure else {}),
        },
    )


def _snapshot(
    provider: WorkflowDataProvider,
    identity: IdentityAuthority,
    evaluation_at: str,
) -> AuthoritySnapshot:
    try:
        snapshot = provider.snapshot(identity=identity, evaluation_at=evaluation_at)
    except Exception as exc:
        # fail closed，但不要靜默：訊息進 log、類型進 payload。
        _LOG.warning(
            "authority snapshot failed for %s at %s: %s",
            identity.company_id or "unresolved",
            evaluation_at,
            exc,
            exc_info=True,
        )
        return _unavailable_snapshot(identity, failure=type(exc).__name__)
    if not isinstance(snapshot, AuthoritySnapshot):
        _LOG.warning(
            "authority provider returned %s for %s, expected AuthoritySnapshot",
            type(snapshot).__name__,
            identity.company_id or "unresolved",
        )
        return _unavailable_snapshot(identity, failure="InvalidSnapshotType")
    return snapshot


def _confirm_holdings_if_requested(
    store: DecisionStore,
    snapshot: AuthoritySnapshot,
    *,
    requested: bool,
    confirmed_at: str,
) -> str | None:
    if not requested:
        return None
    holdings = snapshot.holdings
    if holdings.get("status") != "available" or not isinstance(
        holdings.get("rows"), list
    ):
        return None
    digest = holdings_snapshot_digest(
        holdings["rows"],
        nav_base=holdings.get("nav_base"),
        base_currency=holdings.get("base_currency"),
    )
    return store.record_holdings_confirmation(digest, confirmed_at=confirmed_at)


def _paper_exposure(store: DecisionStore, policy: Mapping[str, Any]) -> Mapping[str, Any]:
    return store.paper_exposure_snapshot(
        paper_nav=float(policy["probe_lane"]["paper_nav"]),
    )


def _completed_result(
    store: DecisionStore,
    *,
    operation_id: str,
    cohort_id: str,
    decision_id: str,
    authority_statuses: Mapping[str, str] | None = None,
    work_orders: list[Mapping[str, Any]] | None = None,
    delta: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    decision = store.get_decision(decision_id)
    coverage = store.get_coverage_result(decision["payload"]["request"]["coverage"]["assessment_id"])
    bundle = store.get_context_bundle(str(decision["context_digest"]))
    card = build_action_card(store, decision_id, as_of=str(decision["effective_at"]))
    final_statuses = {
        section: str((bundle.payload.get(section) or {}).get("status") or "missing")
        for section in (
            "identity",
            "evidence",
            "financial",
            "market",
            "fx",
            "execution_market",
            "execution_fx",
            "holdings",
        )
    }
    final_statuses.update(dict(authority_statuses or {}))
    # Frozen normalized statuses own freshness/confirmation semantics.
    for section in tuple(final_statuses):
        frozen = bundle.payload.get(section)
        if isinstance(frozen, Mapping) and frozen.get("status"):
            final_statuses[section] = str(frozen["status"])
    blockers = sorted(
        set(card.get("blockers") or [])
        | set(coverage.blockers)
        | set(coverage.paper_blockers)
        | set(coverage.live_blockers)
    )
    result = {
        "schema_version": "engine-d-operational-result-v1",
        "operation_id": operation_id,
        "status": "completed_with_blockers" if blockers else "completed",
        "cohort_id": cohort_id,
        "identity": {
            "status": final_statuses["identity"],
            "company_id": (bundle.payload.get("identity") or {}).get("company_id")
            or "unresolved",
        },
        "authority_statuses": final_statuses,
        "context_digest": decision["context_digest"],
        "coverage_assessment_id": coverage.assessment_id,
        "decision_id": decision_id,
        "decision_digest": decision["decision_digest"],
        "paper_event_id": (
            (store.paper_event_for_decision(decision_id) or {}).get("paper_event_id")
        ),
        "blockers": blockers,
        "work_orders": list(work_orders or [])
        + (
            [
                {
                    "code": "coverage_deficit",
                    "work_order_id": coverage.work_order_id,
                    "missing_fields": list(coverage.blockers),
                    "next_step": "補齊列出的 point-in-time evidence／資料後執行 reassess。",
                }
            ]
            if coverage.work_order_id
            and not any(
                item.get("work_order_id") == coverage.work_order_id
                for item in (work_orders or [])
            )
            else []
        ),
        "action_card": card,
    }
    if delta is not None:
        result["delta"] = dict(delta)
    assert_safe_payload(result)
    return result


def _record_completion(
    store: DecisionStore,
    *,
    cohort_id: str,
    operation_id: str,
    decision_id: str,
    observed_at: str,
) -> None:
    store.append_event(
        cohort_id=cohort_id,
        event_type="workflow_evaluation_completed",
        payload={"operation_id": operation_id, "decision_id": decision_id},
        observed_at=observed_at,
    )


def evaluate_signal(
    store: DecisionStore,
    provider: WorkflowDataProvider,
    request: EvaluationRequest,
    *,
    _existing_cohort_id: str | None = None,
    _reassess_from: str | None = None,
) -> dict[str, Any]:
    """由 raw Signal 自動組合 context／coverage／decision／Action Card。"""

    request = _validated_request(request)
    policy = load_policy()
    operation_id = _operation_key(request, reassess_from=_reassess_from)
    completed = store.find_workflow_operation(operation_id, completed=True)
    if completed is not None:
        return _completed_result(
            store,
            operation_id=operation_id,
            cohort_id=str(completed["cohort_id"]),
            decision_id=str(completed["payload"]["decision_id"]),
        )
    started = store.find_workflow_operation(operation_id, completed=False)
    evaluation_at = (
        str(started["payload"]["evaluation_at"])
        if started is not None
        else (_time(request.as_of, "as_of").isoformat() if request.as_of else _now())
    )
    expiry = request.expiry or _default_expiry(evaluation_at, policy)
    if _time(expiry, "expiry") <= _time(evaluation_at, "evaluation_at"):
        raise WorkflowError("expiry must follow evaluation time")

    identity = provider.resolve_identity(
        company_id_hint=request.company_id_hint,
        ticker_hint=request.ticker_hint,
        company_hint=request.company_hint,
    )
    snapshot = _snapshot(provider, identity, evaluation_at)
    if started is None and _existing_cohort_id is None:
        signal = SignalInput(
            raw_text=request.raw_signal.strip(),
            source_id=request.source_id.strip().lower() or "unattributed",
            source_uri=_source_uri(request),
            origin_event="manual:" + operation_id,
            observed_at=evaluation_at,
            atomic_claim=(request.thesis or "").strip(),
            direction=request.direction,
            expiry=expiry,
            disproof=(request.disproof or "").strip(),
            evidence_tier=request.evidence_tier,
            company_id=identity.company_id,
            research_ticker=identity.research_ticker,
            capture_mode="manual",
            source_traced=request.source_traced,
        )
        captured = capture_signal(
            store,
            signal,
            market=_StaticMarketObserver(snapshot.market),
            source_registry=SignalSourceRegistry.from_path(),
            allow_incomplete=True,
            allow_unresolved=True,
        )
        cohort_id = captured.cohort_id
        store.append_event(
            cohort_id=cohort_id,
            event_type="workflow_evaluation_started",
            payload={
                "operation_id": operation_id,
                "evaluation_at": evaluation_at,
                "execution_intent": request.execution_intent,
            },
            observed_at=evaluation_at,
        )
    elif started is not None:
        cohort_id = str(started["cohort_id"])
    else:
        cohort_id = str(_existing_cohort_id)
        store.append_event(
            cohort_id=cohort_id,
            event_type="workflow_evaluation_started",
            payload={
                "operation_id": operation_id,
                "evaluation_at": evaluation_at,
                "execution_intent": request.execution_intent,
                "reassess_from": _reassess_from,
            },
            observed_at=evaluation_at,
        )

    if identity.company_id and identity.research_ticker:
        store.bind_cohort_identity(
            cohort_id,
            company_id=identity.company_id,
            research_ticker=identity.research_ticker,
            resolved_at=evaluation_at,
        )
    _confirm_holdings_if_requested(
        store,
        snapshot,
        requested=request.confirm_holdings,
        confirmed_at=evaluation_at,
    )
    inputs = snapshot.as_context_inputs()
    bundle = build_context_bundle(
        store,
        cohort_id=cohort_id,
        evaluation_at=evaluation_at,
        policy_version=str(policy["policy_version"]),
        paper_exposure=_paper_exposure(store, policy),
        freshness_policy={
            name: policy["probe_lane"][name]
            for name in (
                "market_freshness_sessions",
                "fx_freshness_sessions",
                "holdings_freshness_days",
                "financial_freshness_days",
                "financial_runway_freshness_days",
            )
        },
        **inputs,
    )
    coverage = assess_coverage(
        store,
        bundle,
        catalyst=(request.catalyst or "").strip(),
        disproof=(request.disproof or "").strip(),
        expiry=expiry,
        decision_relevance=0,
        falsifiability=0,
        information_value=0,
        execution_intent=request.execution_intent,
    )
    assessment = request.assessment or _unknown_assessment()
    # Operation identity owns retry semantics. If an interrupted retry observes
    # different authority content, the store rejects the changed request digest
    # instead of creating a second decision or paper event.
    idempotency_key = "evaluate:" + operation_id
    decision = assess_probe(
        store,
        bundle,
        coverage,
        assessment,
        idempotency_key=idempotency_key,
        effective_at=evaluation_at,
        execution_intent=request.execution_intent,
        policy=policy,
    )
    _record_completion(
        store,
        cohort_id=cohort_id,
        operation_id=operation_id,
        decision_id=decision.decision_id,
        observed_at=evaluation_at,
    )
    work_orders = [order.as_dict() for order in snapshot.work_orders]
    return _completed_result(
        store,
        operation_id=operation_id,
        cohort_id=cohort_id,
        decision_id=decision.decision_id,
        authority_statuses=snapshot.public_statuses(),
        work_orders=work_orders,
    )


def ensure_shadow_for_company(
    store: DecisionStore,
    provider: WorkflowDataProvider,
    *,
    company_id: str,
    ticker: str | None = None,
    as_of: str | None = None,
    thesis: str | None = None,
) -> dict[str, Any]:
    """入圖後自動追蹤（plan R13）：若該公司尚無 active cohort，用 research intent
    建立零資本 Shadow Observation；已有 probe 則回既有、改走 evidence-delta。

    這是 composition（workflow 編排），不是 Engine A 呼叫 Engine D——由 dispatch
    層在 admission 成功後呼叫。research intent 不建 funded paper、不給 live
    permission，只保存 Signal／Shadow／cohort。
    """
    now = as_of or _now()
    target = str(company_id or "").strip()
    for summary in store.list_operational_cohorts(as_of=now):
        # `list_operational_cohorts` 回傳所有 cohort（名稱有誤導性），終態的必須跳過：
        # 否則對一個已 promoted／rejected／expired 的公司再次入圖，會把 handoff 指向
        # 一個死掉的 cohort，看起來「已在追蹤」但實際不會再產生任何 decision。
        if str(summary.get("lifecycle_status") or "") in TERMINAL_LIFECYCLE_STATUSES:
            continue
        # 未上市公司沒有 research_ticker，`bind_cohort_identity` 要求 company_id 與
        # ticker 成對才綁定，於是 store 的 company_id 永遠是 None——而去重只比對它，
        # 導致每次入圖都新建一個 cohort。實測 co:agility_robotics 因此累積四個重複
        # cohort（2026-08-12 合併）。真正的意圖一直存在於 company_id_hint，只是沒被讀。
        # 這裡只用 hint 做**去重**，不寫回 identity、不提升 authority——與 store 註解
        # 「hint 只供顯示，不提升 identity authority」一致：避免重複建立不是身分主張。
        if target and target in {
            str(summary.get("company_id") or ""),
            str(summary.get("company_id_hint") or ""),
        }:
            return {"created": False, "cohort_id": str(summary["cohort_id"])}
    result = evaluate_signal(
        store,
        provider,
        EvaluationRequest(
            raw_signal=f"入圖後自動追蹤 {company_id}",
            # atomic_claim 是「當初我們認為這件事是什麼」的唯一可回溯紀錄。
            # 先前這條路徑不帶 thesis，於是 10/10 個 cohort 的 claim 都是空的——
            # 事後想問「7/28 那天我們的判斷是什麼」只能去翻 intake 報告反推。
            # 而 dedupe_key 含 atomic_claim，空 claim 一旦建立就永久補不回來。
            thesis=(thesis or "").strip() or None,
            ticker_hint=ticker,
            company_id_hint=company_id,
            execution_intent="research",
            as_of=now,
        ),
    )
    return {
        "created": True,
        "cohort_id": result["cohort_id"],
        "decision_id": result["decision_id"],
    }


def _context_delta(
    old_context: Mapping[str, Any],
    new_context: Mapping[str, Any],
    *,
    old_action: str,
    new_action: str,
) -> dict[str, Any]:
    old_refs = set((old_context.get("reference_index") or {}).keys())
    new_refs = set((new_context.get("reference_index") or {}).keys())
    return {
        "automatic_repair": False,
        "evidence": {
            "added_refs": sorted(new_refs - old_refs),
            "removed_refs": sorted(old_refs - new_refs),
        },
        "financial_changed": old_context.get("financial") != new_context.get("financial"),
        "holdings_changed": (old_context.get("holdings") or {}).get("digest")
        != (new_context.get("holdings") or {}).get("digest"),
        "policy_changed": old_context.get("policy_version")
        != new_context.get("policy_version"),
        "system_action": {"from": old_action, "to": new_action},
    }


def reassess(
    store: DecisionStore,
    provider: WorkflowDataProvider,
    target_id: str,
    *,
    as_of: str | None = None,
    execution_intent: str | None = None,
    ticker_hint: str | None = None,
    company_hint: str | None = None,
    company_id_hint: str | None = None,
    confirm_holdings: bool = False,
    assessment: Mapping[str, Any] | None = None,
    catalyst: str | None = None,
    disproof: str | None = None,
    expiry: str | None = None,
) -> dict[str, Any]:
    """以既有 Signal 建立新 decision；明確 research overrides 不改寫舊 facts。"""

    baseline = (
        store.get_decision(target_id)
        if target_id.startswith("pd_")
        else store.latest_decision_for_cohort(target_id)
    )
    if baseline is None:
        raise KeyError("baseline decision not found")
    signal = store.latest_signal_payload(str(baseline["cohort_id"]))
    old_request = baseline["payload"]["request"]
    old_coverage = old_request["coverage"]
    old_coverage_metadata = store.get_coverage_metadata(
        str(old_coverage["assessment_id"])
    )
    identity = store.cohort_identity(str(baseline["cohort_id"]))
    signal_hints = signal.get("identity_hints") or {}
    evaluation_at = _time(as_of, "as_of").isoformat() if as_of else _now()
    request = EvaluationRequest(
        raw_signal=str(signal.get("raw_text") or ""),
        source_url=(
            str(signal.get("source_uri"))
            if str(signal.get("source_uri") or "").startswith(("http://", "https://"))
            else None
        ),
        ticker_hint=ticker_hint
        or identity.get("research_ticker")
        or signal_hints.get("research_ticker"),
        company_hint=company_hint,
        company_id_hint=company_id_hint
        or identity.get("company_id")
        or signal_hints.get("company_id"),
        thesis=str(signal.get("atomic_claim") or "") or None,
        catalyst=catalyst or str(old_coverage_metadata.get("catalyst") or "") or None,
        # disproof 與 catalyst 同樣存在 coverage metadata。少了這道 fallback，凡是
        # 在 evaluate 階段用 --disproof 提供的 thesis 都會被 reassess 靜默清空，只
        # 留下 decision payload 裡的 disproof_missing（不進 action card，很難察覺）。
        # 可證偽是一等公民（L7），不得因為換一次 context 就退化成空字串。
        disproof=(
            disproof
            or str(old_coverage_metadata.get("disproof") or "")
            or str(signal.get("disproof") or "")
            or None
        ),
        # expiry 與 catalyst／disproof 是同一組人工核准的可證偽契約。若 reassess
        # 沒有 explicit override，不能偷偷回退成 policy 的三天預設值；那會把原本
        # 以財報／量產里程碑定錨的期限改造成假急件，並讓 daily brief 反覆喚醒。
        # 舊期限若已過，evaluate_signal 會誠實拒絕而要求新的 catalyst window，
        # 不替使用者猜一個新日期。
        expiry=(
            expiry
            or str(old_coverage_metadata.get("expiry") or "")
            or None
        ),
        as_of=evaluation_at,
        execution_intent=execution_intent
        or str(old_request.get("execution_intent") or "research"),
        direction=str(signal.get("direction") or "neutral"),
        source_id=str(signal.get("source_id") or "unattributed"),
        source_traced=bool(signal.get("source_traced")),
        evidence_tier=int(signal.get("evidence_tier") or 4),
        confirm_holdings=confirm_holdings,
        assessment=assessment or old_request.get("assessment"),
    )
    # Explicit as-of guarantees a fresh operation/context; evaluate remains the only composer.
    result = evaluate_signal(
        store,
        provider,
        request,
        _existing_cohort_id=str(baseline["cohort_id"]),
        _reassess_from=str(baseline["decision_id"]),
    )
    old_bundle = store.get_context_bundle(str(baseline["context_digest"]))
    new_bundle = store.get_context_bundle(str(result["context_digest"]))
    old_card = build_action_card(store, str(baseline["decision_id"]), as_of=evaluation_at)
    new_card = result["action_card"]
    delta = _context_delta(
        old_bundle.payload,
        new_bundle.payload,
        old_action=str(old_card["action"]),
        new_action=str(new_card["action"]),
    )
    store.append_event(
        cohort_id=str(result["cohort_id"]),
        event_type="workflow_reassessment_delta",
        payload={
            "from_decision_id": baseline["decision_id"],
            "to_decision_id": result["decision_id"],
            "delta": delta,
        },
        observed_at=evaluation_at,
    )
    result["delta"] = delta
    assert_safe_payload(result)
    return result


def render_workflow_markdown(result: Mapping[str, Any]) -> str:
    """由 operational public DTO 與同一 Action Card 產生 Markdown。"""

    assert_safe_payload(result)
    card = result["action_card"]
    blockers = "、".join(markdown_text(item) for item in result.get("blockers") or []) or "無"
    return "\n".join(
        [
            render_markdown(card),
            "",
            "## Audit trail",
            f"- Cohort：`{result['cohort_id']}`",
            f"- Context digest：`{result['context_digest']}`",
            f"- Coverage：`{result['coverage_assessment_id']}`",
            f"- Decision：`{result['decision_id']}`",
            f"- Blockers：{blockers}",
        ]
    )
