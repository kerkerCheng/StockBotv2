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
from .models import ContextBundle
from .store import DecisionStore


_SECRET_KEY = re.compile(
    r"password|passwd|token|secret|credential|service.?account|dsn|private.?key",
    re.IGNORECASE,
)


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
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _SECRET_KEY.search(str(key)):
                raise ValueError(f"secret-bearing field rejected at {path}.{key}")
            _reject_secrets(child, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, child in enumerate(value):
            _reject_secrets(child, f"{path}[{index}]")


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
    payload: Mapping[str, Any], *, expected_ticker: str, evaluation_at: str
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
    status = "stale" if evaluation - as_of > timedelta(days=14) else "available"
    checklist = deepcopy(payload.get("checklist") or {})
    return {
        "status": status,
        "ticker": expected_ticker,
        "as_of": payload["as_of"],
        "fetched_at": payload["fetched_at"],
        "source": payload["source"],
        "checklist": checklist,
        "runway": derive_runway(
            payload,
            manual_observation=payload.get("manual_runway"),
        ),
        "blockers": [] if status == "available" else ["financial_stale"],
    }


def _normalize_holdings(
    store: DecisionStore,
    payload: Mapping[str, Any],
    *,
    evaluation_at: str,
    expected_symbol: str | None,
    expected_currency: str | None,
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
        normalized.append(
            {"ticker": ticker.strip().upper(), "shares": shares, "currency": currency}
        )
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
    digest = holdings_digest(normalized)
    confirmation = store.latest_holdings_confirmation(digest)
    if confirmation is None:
        return {
            "status": "unconfirmed",
            "digest": digest,
            "rows": normalized,
            "blockers": ["holdings_unconfirmed"],
        }
    evaluation = _parse_time(evaluation_at, "evaluation_at")
    confirmed_at = _parse_time(confirmation["confirmed_at"], "holdings.confirmed_at")
    if confirmed_at > evaluation:
        return {
            "status": "unconfirmed",
            "digest": digest,
            "rows": normalized,
            "blockers": ["holdings_confirmation_future"],
        }
    if evaluation - confirmed_at > timedelta(days=7):
        return {
            "status": "stale",
            "digest": digest,
            "rows": normalized,
            "confirmed_at": confirmation["confirmed_at"],
            "blockers": ["holdings_stale"],
        }
    return {
        "status": "confirmed_empty" if not normalized else "confirmed",
        "digest": digest,
        "rows": normalized,
        "confirmed_at": confirmation["confirmed_at"],
        "blockers": [],
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
) -> ContextBundle:
    """Validate every external scalar, then persist one content-addressed bundle。"""

    _parse_time(evaluation_at, "evaluation_at")
    for value in (identity, evidence, financial, market, fx, holdings, paper_exposure):
        _reject_secrets(value)
    company_id = identity.get("company_id")
    research_ticker = identity.get("research_ticker")
    execution_symbol = identity.get("execution_symbol")
    if not all(isinstance(value, str) and value for value in (
        company_id, research_ticker, execution_symbol
    )):
        normalized_identity = {"status": "unresolved", "blockers": ["identity_unresolved"]}
    else:
        normalized_identity = {
            "status": "resolved",
            "company_id": company_id,
            "research_ticker": research_ticker,
            "execution_symbol": execution_symbol,
            "blockers": [],
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
    )
    expected_pair = f"{expected_currency}/USD"
    normalized_fx = normalize_fx_snapshot(
        fx,
        expected_pair=expected_pair,
        evaluation_at=evaluation_at,
    )
    normalized_financial = _normalize_financial(
        financial,
        expected_ticker=str(research_ticker or ""),
        evaluation_at=evaluation_at,
    )
    normalized_holdings = _normalize_holdings(
        store,
        holdings,
        evaluation_at=evaluation_at,
        expected_symbol=str(execution_symbol or "") or None,
        expected_currency=str(identity.get("execution_currency") or "") or None,
    )
    nav = _finite(paper_exposure.get("nav"), non_negative=True)
    total_weight = _finite(paper_exposure.get("total_weight"), non_negative=True)
    if nav is None or nav <= 0 or total_weight is None:
        normalized_paper = {
            "status": "quarantined",
            "blockers": ["paper_exposure_invalid"],
        }
    else:
        normalized_paper = deepcopy(dict(paper_exposure)) | {
            "status": "available",
            "nav": nav,
            "total_weight": total_weight,
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
        "holdings": normalized_holdings,
        "paper_exposure": normalized_paper,
    }
    digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return store.freeze_context_bundle(
        cohort_id=cohort_id,
        digest=digest,
        evaluation_at=evaluation_at,
        payload=payload,
    )
