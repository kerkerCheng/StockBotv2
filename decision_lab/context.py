"""建立可離線重算的 point-in-time context bundle。"""
from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence

from .adapters.market import normalize_fx_snapshot, normalize_market_snapshot
from .adapters.holdings import execution_aliases
from .identity import resolve_identity
from .models import ContextBundle
from .redaction import sensitive_payload_path
from .store import DecisionStore


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include timezone")
    return parsed


def _reject_secrets(value: Any, path: str = "root") -> None:
    sensitive = sensitive_payload_path(value, path)
    if sensitive is not None:
        raise ValueError(f"secret-bearing value rejected at {sensitive}")


def _finite(value: Any, *, non_negative: bool = False) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    if not math.isfinite(result) or (non_negative and result < 0):
        return None
    return result


def holdings_digest(rows: Sequence[Mapping[str, Any]]) -> str:
    normalized = sorted(
        (dict(row) for row in rows),
        key=lambda row: _canonical(row),
    )
    return hashlib.sha256(_canonical(normalized).encode("utf-8")).hexdigest()


def holdings_snapshot_digest(
    rows: Sequence[Mapping[str, Any]],
    *,
    nav_base: float | None = None,
    base_currency: str | None = None,
) -> str:
    """Bind optional mark-to-market NAV to the same explicit confirmation."""

    payload: list[Mapping[str, Any]] = list(rows)
    if nav_base is not None:
        payload.append(
            {"portfolio_nav_base": nav_base, "base_currency": base_currency}
        )
    return holdings_digest(payload)


def derive_runway(
    financial: Mapping[str, Any],
    *,
    manual_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source = financial
    required = ("cash_and_equivalents", "total_debt", "free_cash_flow_ttm")
    if any(financial.get(key) is None for key in required):
        if manual_observation is None:
            return {"status": "manual_required", "runway_months": None}
        if not manual_observation.get("source") or not manual_observation.get("as_of"):
            raise ValueError("manual runway observation requires source and as_of")
        _parse_time(manual_observation["as_of"], "manual_runway.as_of")
        source = manual_observation
    cash = _finite(source.get("cash_and_equivalents"), non_negative=True)
    debt = _finite(source.get("total_debt"), non_negative=True)
    free_cash_flow = _finite(source.get("free_cash_flow_ttm"))
    if cash is None or debt is None or free_cash_flow is None:
        return {"status": "manual_required", "runway_months": None}
    if not source.get("source") or not source.get("as_of"):
        return {"status": "manual_required", "runway_months": None}
    _parse_time(source["as_of"], "runway.as_of")
    result = {
        "cash_and_equivalents": cash,
        "total_debt": debt,
        "free_cash_flow_ttm": free_cash_flow,
        "source": source["source"],
        "as_of": source["as_of"],
    }
    if free_cash_flow >= 0:
        return result | {"status": "self_funding", "runway_months": None}
    return result | {
        "status": "calculated",
        "runway_months": cash / (-free_cash_flow / 12.0),
    }


def _normalize_financial(
    payload: Mapping[str, Any],
    *,
    expected_ticker: str,
    evaluation_at: str,
    freshness_days: float = 14,
) -> dict[str, Any]:
    if payload.get("status") in {"missing", "unavailable"}:
        status = str(payload["status"])
        return {"status": status, "blockers": [f"financial_{status}"]}
    if payload.get("ticker") != expected_ticker:
        return {"status": "quarantined", "blockers": ["financial_ticker_mismatch"]}
    try:
        as_of = _parse_time(payload.get("as_of"), "financial.as_of")
        fetched_at = _parse_time(payload.get("fetched_at"), "financial.fetched_at")
        evaluation = _parse_time(evaluation_at, "evaluation_at")
    except ValueError:
        return {"status": "quarantined", "blockers": ["financial_timestamp_invalid"]}
    if as_of > evaluation or fetched_at > evaluation:
        return {"status": "quarantined", "blockers": ["financial_timestamp_future"]}
    if not payload.get("source"):
        return {"status": "quarantined", "blockers": ["financial_source_missing"]}
    status = (
        "stale"
        if evaluation - as_of > timedelta(days=freshness_days)
        else "available"
    )
    checklist = deepcopy(payload.get("checklist") or {})
    runway = derive_runway(
        payload,
        manual_observation=payload.get("manual_runway"),
    )
    runway_blockers: list[str] = []
    manual_runway_used = any(
        payload.get(key) is None
        for key in ("cash_and_equivalents", "total_debt", "free_cash_flow_ttm")
    ) and payload.get("manual_runway") is not None
    if manual_runway_used and runway.get("status") in {"calculated", "self_funding"}:
        runway_as_of = _parse_time(runway.get("as_of"), "runway.as_of")
        if runway_as_of > evaluation:
            runway = {"status": "manual_required", "runway_months": None}
            runway_blockers.append("financial_runway_timestamp_future")
        elif evaluation - runway_as_of > timedelta(days=freshness_days):
            runway = {"status": "manual_required", "runway_months": None}
            runway_blockers.append("financial_runway_stale")
    return {
        "status": status,
        "ticker": expected_ticker,
        "as_of": payload["as_of"],
        "fetched_at": payload["fetched_at"],
        "source": payload["source"],
        "checklist": checklist,
        "runway": runway,
        "blockers": (
            ([] if status == "available" else ["financial_stale"])
            + runway_blockers
        ),
    }


def _normalize_holdings(
    store: DecisionStore,
    payload: Mapping[str, Any],
    *,
    evaluation_at: str,
    expected_symbol: str | None,
    expected_currency: str | None,
    freshness_days: float = 7,
) -> dict[str, Any]:
    upstream = payload.get("status")
    if upstream in {"malformed", "missing", "unavailable"}:
        return {"status": upstream, "blockers": [f"holdings_{upstream}"]}
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return {"status": "malformed", "blockers": ["holdings_malformed"]}
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            return {"status": "malformed", "blockers": ["holdings_malformed"]}
        ticker = row.get("ticker")
        currency = row.get("currency")
        shares = _finite(row.get("shares"))
        if (
            not isinstance(ticker, str)
            or not ticker.strip()
            or not isinstance(currency, str)
            or not re.fullmatch(r"[A-Z]{3}", currency)
            or shares is None
        ):
            return {"status": "malformed", "blockers": ["holdings_malformed"]}
        normalized_row = {
            "ticker": ticker.strip().upper(),
            "shares": shares,
            "currency": currency,
        }
        if row.get("is_cash"):
            # 現金身分要進 frozen context：sizing 依它排除 company／factor mapping，
            # 舊 bundle 沒有此欄位時行為不變。
            normalized_row["is_cash"] = True
        company_id = row.get("company_id")
        if company_id is not None:
            if not isinstance(company_id, str) or not company_id.startswith("co:"):
                return {"status": "malformed", "blockers": ["holdings_company_id_invalid"]}
            normalized_row["company_id"] = company_id
        if "market_value_base" in row:
            market_value = _finite(row.get("market_value_base"), non_negative=True)
            if market_value is None:
                return {
                    "status": "malformed",
                    "blockers": ["holdings_market_value_invalid"],
                }
            normalized_row["market_value_base"] = market_value
        normalized.append(normalized_row)
        if (
            expected_symbol
            and ticker.strip().upper() == expected_symbol.upper()
            and expected_currency
            and currency != expected_currency
        ):
            return {
                "status": "malformed",
                "blockers": ["holdings_currency_mismatch"],
            }
    nav_base = payload.get("nav_base")
    base_currency = payload.get("base_currency")
    normalized_nav: float | None = None
    if nav_base is not None or base_currency is not None:
        normalized_nav = _finite(nav_base, non_negative=True)
        if (
            normalized_nav is None
            or normalized_nav <= 0
            or not isinstance(base_currency, str)
            or not re.fullmatch(r"[A-Z]{3}", base_currency)
        ):
            return {"status": "malformed", "blockers": ["holdings_nav_invalid"]}
    digest = holdings_snapshot_digest(
        normalized,
        nav_base=normalized_nav,
        base_currency=base_currency if isinstance(base_currency, str) else None,
    )
    common = {
        "digest": digest,
        "rows": normalized,
        "nav_base": normalized_nav,
        "base_currency": base_currency,
    }
    confirmation = store.latest_holdings_confirmation(digest)
    if confirmation is None:
        return common | {
            "status": "unconfirmed",
            "blockers": ["holdings_unconfirmed"],
        }
    evaluation = _parse_time(evaluation_at, "evaluation_at")
    confirmed_at = _parse_time(confirmation["confirmed_at"], "holdings.confirmed_at")
    if confirmed_at > evaluation:
        return common | {
            "status": "unconfirmed",
            "blockers": ["holdings_confirmation_future"],
        }
    if evaluation - confirmed_at > timedelta(days=freshness_days):
        return common | {
            "status": "stale",
            "confirmed_at": confirmation["confirmed_at"],
            "blockers": ["holdings_stale"],
        }
    return common | {
        "status": "confirmed_empty" if not normalized else "confirmed",
        "confirmed_at": confirmation["confirmed_at"],
        "blockers": [],
    }


def _normalize_weights(value: Any, field: str) -> dict[str, float] | None:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        return None
    normalized: dict[str, float] = {}
    for key, raw_weight in value.items():
        weight = _finite(raw_weight, non_negative=True)
        if not isinstance(key, str) or not key.strip() or weight is None or weight > 10:
            return None
        normalized[key.strip()] = weight
    return normalized


def _reference_id(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for field in ("reference_id", "ref", "id", "source"):
            candidate = value.get(field)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return None


def _add_reference(
    index: dict[str, set[str]], value: Any, *authorities: str
) -> None:
    reference = _reference_id(value)
    if reference is None:
        return
    index.setdefault(reference, set()).update(authorities)


def _explicit_authorities(value: Any, default: str) -> tuple[str, ...]:
    if not isinstance(value, Mapping):
        return (default,)
    raw = value.get("authorities")
    if raw is None:
        raw = [value.get("authority")] if value.get("authority") else []
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return (default,)
    allowed = {
        "graph_source_assertion",
        "source_trace",
        "graph_entity",
        "graph_causal",
        "graph_commercial",
    }
    parsed = tuple(
        str(authority)
        for authority in raw
        if isinstance(authority, str) and authority in allowed
    )
    return parsed or (default,)


def _build_reference_index(
    *,
    policy_version: str,
    evidence: Mapping[str, Any],
    financial: Mapping[str, Any],
    market: Mapping[str, Any],
    fx: Mapping[str, Any],
    execution_market: Mapping[str, Any],
    execution_fx: Mapping[str, Any],
    holdings: Mapping[str, Any],
    paper_exposure: Mapping[str, Any],
) -> dict[str, dict[str, list[str]]]:
    """Build the context-owned capability index used by confidence axes。"""

    index: dict[str, set[str]] = {}
    focus = evidence.get("focus_company")
    _add_reference(index, focus, "graph_entity")
    for item in evidence.get("entities") or []:
        _add_reference(index, item, *_explicit_authorities(item, "graph_entity"))
    for item in evidence.get("sources") or []:
        _add_reference(
            index,
            item,
            *_explicit_authorities(item, "graph_source_assertion"),
        )
        if isinstance(item, Mapping):
            _add_reference(
                index,
                item.get("source_uri"),
                *_explicit_authorities(item, "graph_source_assertion"),
            )
    for item in evidence.get("source_trace_refs") or []:
        _add_reference(index, item, "source_trace")
    for field in ("causal_paths", "counter_paths"):
        for item in evidence.get(field) or []:
            _add_reference(index, item, *_explicit_authorities(item, "graph_causal"))
    for item in evidence.get("commercial_assertions") or []:
        _add_reference(index, item, *_explicit_authorities(item, "graph_commercial"))

    _add_reference(index, financial.get("source"), "engine_c_financial")
    runway = financial.get("runway") or {}
    _add_reference(index, runway.get("source"), "engine_c_financial")
    checklist_authorities = {
        "customer_concentration": "engine_c_customer",
        "backlog": "engine_c_backlog",
        "valuation_pressure": "engine_c_valuation",
    }
    for item_name, item in (financial.get("checklist") or {}).items():
        if not isinstance(item, Mapping):
            continue
        authorities = [checklist_authorities.get(item_name, "engine_c_financial")]
        if item.get("status") == "manual_reviewed":
            authorities.append("engine_c_manual")
        _add_reference(index, item.get("source"), *authorities)

    _add_reference(index, market.get("source"), "market")
    _add_reference(index, fx.get("source"), "fx")
    _add_reference(index, execution_market.get("source"), "market")
    _add_reference(index, execution_fx.get("source"), "fx")
    holdings_ref = holdings.get("digest")
    if isinstance(holdings_ref, str) and holdings_ref:
        _add_reference(index, f"holdings:{holdings_ref}", "holdings")
    _add_reference(index, f"policy:{policy_version}", "policy")
    paper_ref = hashlib.sha256(_canonical(paper_exposure).encode("utf-8")).hexdigest()
    _add_reference(index, f"paper-exposure:{paper_ref}", "paper_ledger")
    return {
        reference: {"authorities": sorted(authorities)}
        for reference, authorities in sorted(index.items())
    }


def build_context_bundle(
    store: DecisionStore,
    *,
    cohort_id: str,
    evaluation_at: str,
    policy_version: str,
    identity: Mapping[str, Any],
    evidence: Mapping[str, Any],
    financial: Mapping[str, Any],
    market: Mapping[str, Any],
    fx: Mapping[str, Any],
    holdings: Mapping[str, Any],
    paper_exposure: Mapping[str, Any],
    execution_market: Mapping[str, Any] | None = None,
    execution_fx: Mapping[str, Any] | None = None,
    freshness_policy: Mapping[str, Any] | None = None,
) -> ContextBundle:
    """Validate every external scalar, then persist one content-addressed bundle。"""

    _parse_time(evaluation_at, "evaluation_at")
    for value in (
        identity,
        evidence,
        financial,
        market,
        fx,
        holdings,
        paper_exposure,
        execution_market or {},
        execution_fx or {},
        freshness_policy or {},
    ):
        _reject_secrets(value)
    freshness = {
        "market_freshness_hours": 36.0,
        "fx_freshness_hours": 36.0,
        "holdings_freshness_days": 7.0,
        "financial_freshness_days": 14.0,
    }
    if freshness_policy is not None:
        for field in freshness:
            parsed = _finite(freshness_policy.get(field), non_negative=True)
            if parsed is None or parsed <= 0:
                raise ValueError(f"{field} must be positive and finite")
            freshness[field] = parsed
    company_id = identity.get("company_id")
    research_ticker = identity.get("research_ticker")
    execution_symbol = identity.get("execution_symbol")
    resolved = resolve_identity(
        company_id=company_id if isinstance(company_id, str) else None,
        research_ticker=(
            research_ticker if isinstance(research_ticker, str) else None
        ),
        execution_aliases=execution_aliases(),
    )
    # 核心 identity（company_id／research_ticker／execution_symbol）決定 freeze／
    # cohort 是否 resolved；execution metadata（currency／venue）缺失只是 live／
    # execution lane 的 blocker，不讓整個 capture／freeze 失敗（plan R14／KTD3）。
    # 大多數 registry 條目沒填 execution metadata，若當成 identity 失敗會使 frozen
    # identity 丟掉 company_id、與已綁定的 cohort 衝突並在 freeze 拋 ValueError。
    core_fields = {
        "company_id": resolved.company_id,
        "research_ticker": resolved.research_ticker,
        "execution_symbol": resolved.execution_symbol,
    }
    execution_profile = {
        "market_currency": resolved.market_currency,
        "execution_currency": resolved.execution_currency,
        "execution_venue": resolved.execution_venue,
    }
    core_unresolved = (
        bool(resolved.blockers)
        or any(value is None for value in core_fields.values())
        or any(identity.get(field) != value for field, value in core_fields.items())
    )
    # 防偽：caller 與 registry 都非 None 且相異才算 conflict。caller 傳 None＝
    # 「未指定，以 registry 為準」；registry 未列（None）＝未知，之後以 lane
    # blocker 呈現。兩者都不該讓已解析的 identity 變 unresolved。
    execution_conflict = any(
        identity.get(field) is not None
        and value is not None
        and identity.get(field) != value
        for field, value in execution_profile.items()
    )
    if core_unresolved or execution_conflict:
        normalized_identity = {"status": "unresolved", "blockers": ["identity_unresolved"]}
    else:
        missing_execution = sorted(
            f"{field}_missing"
            for field, value in execution_profile.items()
            if value is None
        )
        normalized_identity = {
            "status": "resolved",
            **core_fields,
            **execution_profile,
            "blockers": missing_execution,
        }
    normalized_evidence = deepcopy(dict(evidence))
    expected_currency = str(
        identity.get("market_currency") or market.get("currency") or ""
    )
    normalized_market = normalize_market_snapshot(
        market,
        expected_ticker=str(research_ticker or ""),
        expected_currency=expected_currency,
        evaluation_at=evaluation_at,
        max_age_hours=freshness["market_freshness_hours"],
    )
    expected_pair = f"{expected_currency}/USD"
    normalized_fx = normalize_fx_snapshot(
        fx,
        expected_pair=expected_pair,
        evaluation_at=evaluation_at,
        max_age_hours=freshness["fx_freshness_hours"],
    )
    normalized_financial = _normalize_financial(
        financial,
        expected_ticker=str(research_ticker or ""),
        evaluation_at=evaluation_at,
        freshness_days=freshness["financial_freshness_days"],
    )
    normalized_holdings = _normalize_holdings(
        store,
        holdings,
        evaluation_at=evaluation_at,
        expected_symbol=str(execution_symbol or "") or None,
        expected_currency=str(identity.get("execution_currency") or "") or None,
        freshness_days=freshness["holdings_freshness_days"],
    )
    execution_currency = str(identity.get("execution_currency") or "")
    if execution_market is None and execution_symbol == research_ticker:
        normalized_execution_market = deepcopy(normalized_market)
    elif execution_market is None:
        normalized_execution_market = {
            "status": "missing",
            "blockers": ["execution_market_missing"],
        }
    else:
        normalized_execution_market = normalize_market_snapshot(
            execution_market,
            expected_ticker=str(execution_symbol or ""),
            expected_currency=execution_currency,
            evaluation_at=evaluation_at,
            max_age_hours=freshness["market_freshness_hours"],
        )
        normalized_execution_market["blockers"] = [
            blocker.replace("market_", "execution_market_", 1)
            for blocker in normalized_execution_market.get("blockers", [])
        ]
    live_base_currency = str(normalized_holdings.get("base_currency") or "")
    execution_pair = f"{execution_currency}/{live_base_currency}"
    if execution_currency and execution_currency == live_base_currency and execution_fx is None:
        normalized_execution_fx = {
            "status": "available",
            "pair": execution_pair,
            "rate": 1.0,
            "as_of": evaluation_at,
            "fetched_at": evaluation_at,
            "source": "identity://base-currency",
            "blockers": [],
        }
    elif (
        execution_fx is None
        and live_base_currency == "USD"
        and execution_pair == expected_pair
    ):
        normalized_execution_fx = deepcopy(normalized_fx)
    elif execution_fx is None:
        normalized_execution_fx = {
            "status": "missing",
            "blockers": ["execution_fx_missing"],
        }
    else:
        normalized_execution_fx = normalize_fx_snapshot(
            execution_fx,
            expected_pair=execution_pair,
            evaluation_at=evaluation_at,
            max_age_hours=freshness["fx_freshness_hours"],
        )
        normalized_execution_fx["blockers"] = [
            blocker.replace("fx_", "execution_fx_", 1)
            for blocker in normalized_execution_fx.get("blockers", [])
        ]
    nav = _finite(paper_exposure.get("nav"), non_negative=True)
    total_weight = _finite(paper_exposure.get("total_weight"), non_negative=True)
    factor_weights = _normalize_weights(paper_exposure.get("factor_weights"), "factor_weights")
    company_weights = _normalize_weights(
        paper_exposure.get("company_weights"), "company_weights"
    )
    if (
        nav is None
        or nav <= 0
        or total_weight is None
        or factor_weights is None
        or company_weights is None
    ):
        normalized_paper = {
            "status": "quarantined",
            "blockers": ["paper_exposure_invalid"],
        }
    else:
        normalized_paper = deepcopy(dict(paper_exposure)) | {
            "status": "available",
            "nav": nav,
            "total_weight": total_weight,
            "factor_weights": factor_weights,
            "company_weights": company_weights,
            "blockers": [],
        }
    payload = {
        "cohort_id": cohort_id,
        "evaluation_at": evaluation_at,
        "policy_version": policy_version,
        "identity": normalized_identity,
        "evidence": normalized_evidence,
        "financial": normalized_financial,
        "market": normalized_market,
        "fx": normalized_fx,
        "execution_market": normalized_execution_market,
        "execution_fx": normalized_execution_fx,
        "holdings": normalized_holdings,
        "paper_exposure": normalized_paper,
        "freshness_policy": freshness,
    }
    payload["reference_index"] = _build_reference_index(
        policy_version=policy_version,
        evidence=normalized_evidence,
        financial=normalized_financial,
        market=normalized_market,
        fx=normalized_fx,
        execution_market=normalized_execution_market,
        execution_fx=normalized_execution_fx,
        holdings=normalized_holdings,
        paper_exposure=normalized_paper,
    )
    digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return store.freeze_context_bundle(
        cohort_id=cohort_id,
        digest=digest,
        evaluation_at=evaluation_at,
        payload=payload,
    )
