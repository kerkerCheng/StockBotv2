"""外部 market／FX payload 的 fail-closed normalization。"""
from __future__ import annotations

import math
import re
from datetime import datetime, timedelta
from typing import Any, Mapping


def _time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    converted = float(value)
    return converted if math.isfinite(converted) else None


def _quarantined(*blockers: str) -> dict[str, Any]:
    return {"status": "quarantined", "blockers": sorted(set(blockers))}


def normalize_market_snapshot(
    payload: Mapping[str, Any],
    *,
    expected_ticker: str,
    expected_currency: str,
    evaluation_at: str,
    max_age_hours: int = 36,
) -> dict[str, Any]:
    upstream = payload.get("status")
    if upstream in {"missing", "unavailable"}:
        return {"status": upstream, "blockers": [f"market_{upstream}"]}
    blockers: list[str] = []
    if payload.get("ticker") != expected_ticker:
        blockers.append("market_ticker_mismatch")
    if payload.get("currency") != expected_currency:
        blockers.append("market_currency_mismatch")
    price = _finite(payload.get("price"))
    if price is None or price <= 0:
        blockers.append("market_price_invalid")
    elif price > 10_000_000:
        blockers.append("market_price_anomaly")
    adv20 = _finite(payload.get("adv20"))
    if adv20 is None or adv20 < 0 or adv20 > 1e15:
        blockers.append("market_adv_invalid")
    if payload.get("unit_status") != "ok":
        blockers.append("market_unit_unverified")
    as_of = _time(payload.get("as_of"))
    fetched_at = _time(payload.get("fetched_at"))
    evaluation = _time(evaluation_at)
    if as_of is None or fetched_at is None or evaluation is None:
        blockers.append("market_timestamp_invalid")
    elif as_of > evaluation or fetched_at > evaluation:
        blockers.append("market_timestamp_future")
    if not payload.get("source"):
        blockers.append("market_source_missing")
    if blockers:
        return _quarantined(*blockers)
    assert as_of is not None and evaluation is not None and price is not None
    status = "stale" if evaluation - as_of > timedelta(hours=max_age_hours) else "available"
    return {
        "status": status,
        "ticker": expected_ticker,
        "price": price,
        "currency": expected_currency,
        "adv20": adv20,
        "as_of": payload["as_of"],
        "fetched_at": payload["fetched_at"],
        "source": payload["source"],
        "blockers": [] if status == "available" else ["market_stale"],
    }


def normalize_fx_snapshot(
    payload: Mapping[str, Any],
    *,
    expected_pair: str,
    evaluation_at: str,
    max_age_hours: int = 36,
) -> dict[str, Any]:
    upstream = payload.get("status")
    if upstream in {"missing", "unavailable"}:
        return {"status": upstream, "blockers": [f"fx_{upstream}"]}
    blockers: list[str] = []
    if payload.get("pair") != expected_pair:
        blockers.append("fx_pair_mismatch")
    rate = _finite(payload.get("rate"))
    if rate is None or rate <= 0 or rate > 1e6:
        blockers.append("fx_rate_invalid")
    as_of = _time(payload.get("as_of"))
    fetched_at = _time(payload.get("fetched_at"))
    evaluation = _time(evaluation_at)
    if as_of is None or fetched_at is None or evaluation is None:
        blockers.append("fx_timestamp_invalid")
    elif as_of > evaluation or fetched_at > evaluation:
        blockers.append("fx_timestamp_future")
    if not payload.get("source"):
        blockers.append("fx_source_missing")
    if blockers:
        return _quarantined(*blockers)
    assert as_of is not None and evaluation is not None and rate is not None
    status = "stale" if evaluation - as_of > timedelta(hours=max_age_hours) else "available"
    return {
        "status": status,
        "pair": expected_pair,
        "rate": rate,
        "as_of": payload["as_of"],
        "fetched_at": payload["fetched_at"],
        "source": payload["source"],
        "blockers": [] if status == "available" else ["fx_stale"],
    }
