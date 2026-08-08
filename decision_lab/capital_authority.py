"""Shared investable-cash floor and separate loan telemetry。"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, timezone
from typing import Any, Callable, Mapping, Sequence
from zoneinfo import ZoneInfo

from decision_lab.adapters.market import normalize_fx_snapshot
from identity.currency import is_settlement_currency


FxFetcher = Callable[[str, str], Mapping[str, Any]]
_TAIPEI = ZoneInfo("Asia/Taipei")
_CASH_FLOOR_TYPE = "cash_floor"
_CREDIT_TYPE = "credit_facility"
_ALLOWED_TYPES = {_CASH_FLOOR_TYPE, _CREDIT_TYPE}


def _finite(value: Any, *, non_negative: bool = False) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or (non_negative and parsed < 0):
        return None
    return parsed


def _text(value: Any) -> str:
    return str(value or "").strip()


def _evaluation_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("evaluation_at must include timezone")
    return parsed


def _authority_date(value: Any) -> date | None:
    raw = _text(value)
    if not raw:
        return None
    try:
        if "T" not in raw:
            return date.fromisoformat(raw)
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(_TAIPEI).date()


def _canonical_digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _unavailable_view(
    *,
    evaluation_at: str,
    base_currency: str | None,
    blockers: Sequence[str],
) -> dict[str, Any]:
    unique = sorted({str(item) for item in blockers})
    return {
        "schema_version": "capital-view-v2",
        "status": "unavailable",
        "as_of": evaluation_at,
        "authority_as_of": None,
        "digest": None,
        "base_currency": base_currency,
        "self_funded_cash": {
            "status": "unavailable",
            "portfolio_cash_base": None,
            "cash_floor_base": None,
            "deployable_cash_base": 0.0,
            "blockers": unique,
        },
        "contingent_credit_available": {
            "status": "unavailable",
            "currency": base_currency,
            "undrawn_amount_base": None,
            "drawn_amount_base": None,
            "estimated_daily_interest_base": None,
            "estimated_monthly_interest_base": None,
            "estimated_annual_interest_base": None,
            "facility_count": 0,
            "terms_status": "unknown",
            "blockers": unique,
        },
        "loan_funded_supported_range": {
            "status": "manual_review_required",
            "range_base": None,
            "blockers": ["exact_draw_instrument_tranche_choice_required"],
        },
        "drawn_debt_base": None,
        "fx": {},
        "blockers": unique,
        "warnings": [],
    }


def build_capital_view(
    *,
    authority_rows: Sequence[Mapping[str, Any]] | None,
    portfolio_cash_base: Any,
    base_currency: str | None,
    evaluation_at: str,
    max_authority_age_days: int,
    max_fx_age_sessions: int,
    fx_fetcher: FxFetcher | None,
) -> dict[str, Any]:
    """Build one shared Alpha/Beta cash pool plus non-cash loan telemetry。"""

    evaluated = _evaluation_time(evaluation_at)
    currency = _text(base_currency).upper()
    cash = _finite(portfolio_cash_base, non_negative=True)
    valid_currency = is_settlement_currency(currency)
    if authority_rows is None or not authority_rows or not valid_currency or cash is None:
        blockers = ["capital_authority_unavailable"]
        if cash is None or not valid_currency:
            blockers.append("portfolio_cash_base_unavailable")
        return _unavailable_view(
            evaluation_at=evaluation_at,
            base_currency=currency or None,
            blockers=blockers,
        )

    eval_date = evaluated.astimezone(_TAIPEI).date()
    normalized: list[dict[str, Any]] = []
    authority_dates: list[date] = []
    record_ids: set[str] = set()
    duplicate_ids: set[str] = set()
    global_blockers: list[str] = []
    for raw in authority_rows:
        if not isinstance(raw, Mapping):
            global_blockers.append("capital_authority_record_malformed")
            continue
        record_id = _text(raw.get("record_id"))
        capital_type = _text(raw.get("capital_type")).casefold()
        record_date = _authority_date(raw.get("as_of"))
        row_blockers: list[str] = []
        if not record_id:
            row_blockers.append("capital_authority_record_id_invalid")
        elif record_id in record_ids:
            duplicate_ids.add(record_id)
            row_blockers.append("capital_authority_record_id_invalid")
        record_ids.add(record_id)
        if capital_type not in _ALLOWED_TYPES:
            row_blockers.append("capital_authority_type_invalid")
        if record_date is None:
            row_blockers.append("capital_authority_as_of_invalid")
        else:
            authority_dates.append(record_date)
            age_days = (eval_date - record_date).days
            if age_days < 0:
                row_blockers.append("capital_authority_as_of_future")
            elif age_days > max_authority_age_days:
                row_blockers.append("capital_authority_stale")
        normalized.append(
            {
                "record_id": record_id,
                "capital_type": capital_type,
                "as_of": record_date.isoformat() if record_date else None,
                "currency": _text(raw.get("currency")).upper(),
                "amount": raw.get("amount"),
                "limit_amount": raw.get("limit_amount"),
                "drawn_amount": raw.get("drawn_amount"),
                "annual_rate_pct": raw.get("annual_rate_pct"),
                "interest_accrual": _text(raw.get("interest_accrual")).casefold(),
                "facility_term_years": raw.get("facility_term_years"),
                "repayment_structure": _text(raw.get("repayment_structure")).casefold(),
                "blockers": sorted(set(row_blockers)),
            }
        )
    if duplicate_ids:
        global_blockers.append("capital_authority_record_id_invalid")

    by_type: dict[str, list[dict[str, Any]]] = {}
    for record in normalized:
        by_type.setdefault(record["capital_type"], []).append(record)

    fx_cache: dict[str, dict[str, Any]] = {}

    def rate_to_base(source_currency: str) -> float | None:
        source = source_currency.upper()
        if len(source) != 3:
            return None
        pair = f"{source}/{currency}"
        if source == currency:
            fx_cache[pair] = {
                "status": "available",
                "pair": pair,
                "rate": 1.0,
                "as_of": evaluation_at,
                "source": "identity://same-currency",
            }
            return 1.0
        if pair in fx_cache:
            value = fx_cache[pair]
            return float(value["rate"]) if value.get("status") == "available" else None
        if fx_fetcher is None:
            fx_cache[pair] = {"status": "missing", "pair": pair, "blockers": ["fx_missing"]}
            return None
        try:
            raw_fx = dict(fx_fetcher(pair, evaluation_at))
        except Exception:
            raw_fx = {"status": "unavailable"}
        value = normalize_fx_snapshot(
            raw_fx,
            expected_pair=pair,
            evaluation_at=evaluation_at,
            max_age_sessions=max_fx_age_sessions,
        )
        fx_cache[pair] = value
        return float(value["rate"]) if value.get("status") == "available" else None

    cash_blockers = list(global_blockers)
    floor_records = by_type.get(_CASH_FLOOR_TYPE, [])
    if len(floor_records) != 1:
        cash_blockers.append("capital_authority_cash_floor_count_invalid")
    floor = floor_records[0] if len(floor_records) == 1 else {}
    cash_blockers.extend(str(value) for value in floor.get("blockers", []))
    floor_amount = _finite(floor.get("amount"), non_negative=True)
    floor_currency = _text(floor.get("currency")).upper()
    if floor_amount is None:
        cash_blockers.append("cash_floor_amount_invalid")
    if len(floor_currency) != 3:
        cash_blockers.append("cash_floor_currency_invalid")
    floor_rate = (
        rate_to_base(floor_currency)
        if floor_amount is not None and len(floor_currency) == 3
        else None
    )
    if floor_amount is not None and len(floor_currency) == 3 and floor_rate is None:
        cash_blockers.append("cash_floor_fx_unavailable")
    floor_base = floor_amount * floor_rate if floor_amount is not None and floor_rate is not None else None
    cash_blockers = sorted(set(cash_blockers))
    deployable = (
        max(cash - floor_base, 0.0)
        if not cash_blockers and floor_base is not None
        else 0.0
    )

    facility_summaries: list[dict[str, Any]] = []
    credit_blockers: list[str] = []
    warnings: list[str] = []
    total_undrawn_base = 0.0
    total_drawn_base = 0.0
    total_daily_interest_base = 0.0
    total_monthly_interest_base = 0.0
    total_annual_interest_base = 0.0
    drawn_debt_complete = True
    interest_complete = True
    for facility in by_type.get(_CREDIT_TYPE, []):
        facility_blockers = list(facility.get("blockers", []))
        facility_currency = _text(facility.get("currency")).upper()
        limit_amount = _finite(facility.get("limit_amount"), non_negative=True)
        drawn_amount = _finite(facility.get("drawn_amount"), non_negative=True)
        annual_rate_pct = _finite(facility.get("annual_rate_pct"), non_negative=True)
        term_years = _finite(facility.get("facility_term_years"), non_negative=True)
        if len(facility_currency) != 3:
            facility_blockers.append("credit_currency_invalid")
        if limit_amount is None or drawn_amount is None or (
            limit_amount is not None and drawn_amount is not None and drawn_amount > limit_amount
        ):
            facility_blockers.append("credit_balance_invalid")
        if annual_rate_pct is not None and annual_rate_pct > 100:
            annual_rate_pct = None
        if term_years is not None and term_years <= 0:
            term_years = None
        incomplete_fields = [
            field
            for field, value in (
                ("annual_rate_pct", annual_rate_pct),
                ("interest_accrual", facility.get("interest_accrual")),
                ("facility_term_years", term_years),
                ("repayment_structure", facility.get("repayment_structure")),
            )
            if value is None or value == ""
        ]
        facility_fx = rate_to_base(facility_currency) if len(facility_currency) == 3 else None
        if facility_fx is None:
            facility_blockers.append("credit_fx_unavailable")
        undrawn_base = None
        drawn_base = 0.0 if drawn_amount == 0 else None
        if limit_amount is not None and drawn_amount is not None and facility_fx is not None:
            undrawn_base = max(limit_amount - drawn_amount, 0.0) * facility_fx
            drawn_base = drawn_amount * facility_fx
            total_undrawn_base += undrawn_base
            total_drawn_base += drawn_base
        elif drawn_amount not in {0.0, None}:
            drawn_debt_complete = False

        daily_interest = monthly_interest = annual_interest = None
        if drawn_base is not None and annual_rate_pct is not None:
            annual_interest = drawn_base * annual_rate_pct / 100.0
            monthly_interest = annual_interest / 12.0
            daily_interest = annual_interest / 365.0
            total_annual_interest_base += annual_interest
            total_monthly_interest_base += monthly_interest
            total_daily_interest_base += daily_interest
        else:
            interest_complete = False
        if drawn_base and drawn_base > 0:
            warnings.append("drawn_debt_present")
        summary = {
            "currency": facility_currency or None,
            "undrawn_amount_base": undrawn_base,
            "drawn_amount_base": drawn_base,
            "annual_rate_pct": annual_rate_pct,
            "interest_accrual": facility.get("interest_accrual") or None,
            "facility_term_years": term_years,
            "repayment_structure": facility.get("repayment_structure") or None,
            "estimated_daily_interest_base": daily_interest,
            "estimated_monthly_interest_base": monthly_interest,
            "estimated_annual_interest_base": annual_interest,
            "terms_status": "incomplete" if incomplete_fields else "complete",
            "incomplete_fields": sorted(set(incomplete_fields)),
            "blockers": sorted(set(facility_blockers)),
        }
        facility_summaries.append(summary)
        credit_blockers.extend(summary["blockers"])

    if not facility_summaries:
        credit_status = "not_configured"
        credit_terms_status = "unknown"
        drawn_debt_base: float | None = 0.0
    else:
        credit_terms_incomplete = any(
            facility["terms_status"] != "complete" for facility in facility_summaries
        )
        if credit_terms_incomplete:
            warnings.append("credit_terms_incomplete")
        credit_status = (
            "unavailable"
            if credit_blockers
            else "incomplete"
            if credit_terms_incomplete
            else "available"
        )
        credit_terms_status = "incomplete" if credit_terms_incomplete else "complete"
        drawn_debt_base = total_drawn_base if drawn_debt_complete else None

    digest_payload = {
        "schema_version": "capital-view-v2",
        "evaluation_at": evaluated.astimezone(timezone.utc).isoformat(),
        "authority_records": sorted(normalized, key=lambda item: item["record_id"]),
        "portfolio": {"cash_base": cash, "base_currency": currency},
        "fx": {key: fx_cache[key] for key in sorted(fx_cache)},
    }
    status = (
        "unavailable"
        if cash_blockers
        else "partial"
        if credit_status not in {"available", "not_configured"}
        else "available"
    )
    return {
        "schema_version": "capital-view-v2",
        "status": status,
        "as_of": evaluation_at,
        "authority_as_of": min(authority_dates).isoformat() if authority_dates else None,
        "digest": _canonical_digest(digest_payload),
        "base_currency": currency,
        "self_funded_cash": {
            "status": "available" if not cash_blockers else "unavailable",
            "portfolio_cash_base": cash,
            "cash_floor_base": floor_base,
            "deployable_cash_base": deployable,
            "blockers": cash_blockers,
        },
        "contingent_credit_available": {
            "status": credit_status,
            "currency": currency,
            "undrawn_amount_base": (
                total_undrawn_base if facility_summaries and not credit_blockers else None
            ),
            "drawn_amount_base": drawn_debt_base,
            "estimated_daily_interest_base": (
                total_daily_interest_base if facility_summaries and interest_complete else None
            ),
            "estimated_monthly_interest_base": (
                total_monthly_interest_base if facility_summaries and interest_complete else None
            ),
            "estimated_annual_interest_base": (
                total_annual_interest_base if facility_summaries and interest_complete else None
            ),
            "facility_count": len(facility_summaries),
            "terms_status": credit_terms_status,
            "facilities": facility_summaries,
            "blockers": sorted(set(credit_blockers)),
        },
        "loan_funded_supported_range": {
            "status": "manual_review_required",
            "range_base": None,
            "blockers": ["exact_draw_instrument_tranche_choice_required"],
        },
        "drawn_debt_base": drawn_debt_base,
        "fx": {key: fx_cache[key] for key in sorted(fx_cache)},
        "blockers": sorted(set(cash_blockers + credit_blockers)),
        "warnings": sorted(set(warnings)),
    }


__all__ = ["build_capital_view"]
