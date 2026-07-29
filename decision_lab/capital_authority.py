"""Phase II-A household capital authority normalization and snapshot。"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, timezone
from typing import Any, Callable, Mapping, Sequence
from zoneinfo import ZoneInfo

from decision_lab.adapters.market import normalize_fx_snapshot


FxFetcher = Callable[[str, str], Mapping[str, Any]]
_TAIPEI = ZoneInfo("Asia/Taipei")
_REQUIRED_SINGLE_TYPES = {
    "portfolio_cash_authority",
    "operating_floor",
    "planned_outflows_reserve_24m",
}
_CREDIT_TYPE = "contingent_liquidity_credit_facility"
_ALLOWED_TYPES = _REQUIRED_SINGLE_TYPES | {_CREDIT_TYPE}
_CONFIRMATIONS = {"user_confirmed", "user_confirmed_partial"}


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


def _boolean(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    normalized = _text(value).casefold()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    return None


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
        "schema_version": "household-capital-view-v1",
        "status": "unavailable",
        "as_of": evaluation_at,
        "authority_as_of": None,
        "digest": None,
        "base_currency": base_currency,
        "household_cash": {
            "status": "unavailable",
            "portfolio_cash_base": None,
            "operating_floor_base": None,
            "planned_outflows_base": None,
            "alpha_reserve_base": None,
            "deployable_cash_base": 0.0,
            "blockers": unique,
        },
        "contingent_credit_available": {
            "status": "unavailable",
            "currency": base_currency,
            "undrawn_amount_base": None,
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


def _record_type(value: Any) -> str:
    return _text(value).casefold()


def build_household_capital_view(
    *,
    authority_rows: Sequence[Mapping[str, Any]] | None,
    portfolio_cash_base: Any,
    portfolio_nav_base: Any,
    base_currency: str | None,
    evaluation_at: str,
    alpha_reserve_nav_fraction: float,
    max_authority_age_days: int,
    max_fx_age_hours: int,
    fx_fetcher: FxFetcher | None,
) -> dict[str, Any]:
    """Build a safe aggregate view; raw descriptions／notes never leave this function。"""

    evaluated = _evaluation_time(evaluation_at)
    currency = _text(base_currency).upper()
    cash = _finite(portfolio_cash_base, non_negative=True)
    nav = _finite(portfolio_nav_base, non_negative=True)
    if (
        authority_rows is None
        or not authority_rows
        or len(currency) != 3
        or cash is None
        or nav is None
        or nav <= 0
    ):
        blockers = ["capital_authority_unavailable"]
        if cash is None or nav is None or nav <= 0 or len(currency) != 3:
            blockers.append("portfolio_capital_base_unavailable")
        return _unavailable_view(
            evaluation_at=evaluation_at,
            base_currency=currency or None,
            blockers=blockers,
        )

    blockers: list[str] = []
    warnings: list[str] = []
    normalized: list[dict[str, Any]] = []
    record_ids: set[str] = set()
    authority_dates: list[date] = []
    eval_date = evaluated.astimezone(_TAIPEI).date()
    for raw in authority_rows:
        if not isinstance(raw, Mapping):
            blockers.append("capital_authority_record_malformed")
            continue
        record_id = _text(raw.get("record_id"))
        capital_type = _record_type(raw.get("capital_type"))
        confirmation = _text(raw.get("confirmation_status")).casefold()
        record_date = _authority_date(raw.get("as_of"))
        if not record_id or record_id in record_ids:
            blockers.append("capital_authority_record_id_invalid")
        record_ids.add(record_id)
        if capital_type not in _ALLOWED_TYPES:
            blockers.append("capital_authority_type_invalid")
        if confirmation not in _CONFIRMATIONS:
            blockers.append("capital_authority_confirmation_invalid")
        if record_date is None:
            blockers.append("capital_authority_as_of_invalid")
        else:
            authority_dates.append(record_date)
            age_days = (eval_date - record_date).days
            if age_days < 0:
                blockers.append("capital_authority_as_of_future")
            elif age_days > max_authority_age_days:
                blockers.append("capital_authority_stale")
        normalized.append(
            {
                "record_id": record_id,
                "capital_type": capital_type,
                "confirmation_status": confirmation,
                "as_of": record_date.isoformat() if record_date else None,
                "currency": _text(raw.get("currency")).upper(),
                "amount": raw.get("amount"),
                "amount_source": _text(raw.get("amount_source")),
                "limit_amount": raw.get("limit_amount"),
                "drawn_amount": raw.get("drawn_amount"),
                "annual_rate_pct": raw.get("annual_rate_pct"),
                "interest_accrual": _text(raw.get("interest_accrual")),
                "availability": _text(raw.get("availability")).casefold(),
                "facility_term_years": raw.get("facility_term_years"),
                "repayment_structure": _text(raw.get("repayment_structure")),
                "minimum_payment_status": _text(raw.get("minimum_payment_status")),
                "minimum_payment_terms": _text(raw.get("minimum_payment_terms")),
                "deployment_mode": _text(raw.get("deployment_mode")).casefold(),
                "automatic_deployment": raw.get("automatic_deployment"),
                "include_in_net_investable_capital": raw.get(
                    "include_in_net_investable_capital"
                ),
                "include_in_deployable_cash": raw.get("include_in_deployable_cash"),
            }
        )

    by_type: dict[str, list[dict[str, Any]]] = {}
    for record in normalized:
        by_type.setdefault(record["capital_type"], []).append(record)
    for required in _REQUIRED_SINGLE_TYPES:
        if len(by_type.get(required, [])) != 1:
            blockers.append(f"capital_authority_{required}_count_invalid")
    if not by_type.get(_CREDIT_TYPE):
        blockers.append("capital_authority_credit_facility_missing")

    routing = (by_type.get("portfolio_cash_authority") or [{}])[0]
    amount_source = routing.get("amount_source", "").replace(" ", "").casefold()
    if amount_source != "portfolio.cash_twd+portfolio.cash_usd":
        blockers.append("portfolio_cash_authority_routing_mismatch")
    routing_amount = _finite(routing.get("amount"), non_negative=True)
    if routing.get("amount") not in {None, ""} and routing_amount not in {0.0, None}:
        blockers.append("portfolio_cash_authority_duplicate_amount")

    floor_record = (by_type.get("operating_floor") or [{}])[0]
    outflow_record = (by_type.get("planned_outflows_reserve_24m") or [{}])[0]
    floor_amount = _finite(floor_record.get("amount"), non_negative=True)
    outflow_amount = _finite(outflow_record.get("amount"), non_negative=True)
    if floor_amount is None:
        blockers.append("operating_floor_amount_invalid")
    if outflow_amount is None:
        blockers.append("planned_outflows_amount_invalid")
    for label, record in (("operating_floor", floor_record), ("planned_outflows", outflow_record)):
        if len(_text(record.get("currency"))) != 3:
            blockers.append(f"{label}_currency_invalid")

    fx_cache: dict[str, dict[str, Any]] = {}

    def rate_to_base(source_currency: str) -> float | None:
        source = source_currency.upper()
        if source == currency:
            fx_cache[f"{source}/{currency}"] = {
                "status": "available",
                "pair": f"{source}/{currency}",
                "rate": 1.0,
                "as_of": evaluation_at,
                "source": "identity://same-currency",
            }
            return 1.0
        pair = f"{source}/{currency}"
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
            max_age_hours=max_fx_age_hours,
        )
        fx_cache[pair] = value
        return float(value["rate"]) if value.get("status") == "available" else None

    floor_rate = rate_to_base(_text(floor_record.get("currency")).upper()) if floor_amount is not None else None
    outflow_rate = rate_to_base(_text(outflow_record.get("currency")).upper()) if outflow_amount is not None else None
    if floor_amount is not None and floor_rate is None:
        blockers.append("operating_floor_fx_unavailable")
    if outflow_amount is not None and outflow_rate is None:
        blockers.append("planned_outflows_fx_unavailable")

    facility_summaries: list[dict[str, Any]] = []
    credit_blockers: list[str] = []
    total_undrawn_base = 0.0
    total_drawn_base = 0.0
    drawn_debt_complete = True
    any_drawn = False
    for facility in by_type.get(_CREDIT_TYPE, []):
        facility_blockers: list[str] = []
        facility_currency = _text(facility.get("currency")).upper()
        limit_amount = _finite(facility.get("limit_amount"), non_negative=True)
        drawn_amount = _finite(facility.get("drawn_amount"), non_negative=True)
        automatic = _boolean(facility.get("automatic_deployment"))
        include_net = _boolean(facility.get("include_in_net_investable_capital"))
        include_cash = _boolean(facility.get("include_in_deployable_cash"))
        if len(facility_currency) != 3:
            facility_blockers.append("credit_currency_invalid")
        if limit_amount is None or drawn_amount is None or (
            limit_amount is not None and drawn_amount is not None and drawn_amount > limit_amount
        ):
            facility_blockers.append("credit_balance_invalid")
        if drawn_amount is None:
            blockers.append("drawn_debt_status_unverified")
            drawn_debt_complete = False
        elif drawn_amount > 0:
            any_drawn = True
        if automatic is not False:
            facility_blockers.append("credit_automatic_deployment_not_false")
        if include_net is not False or include_cash is not False:
            facility_blockers.append("credit_inclusion_flags_not_false")
        if facility.get("deployment_mode") != "manual_review_only":
            facility_blockers.append("credit_deployment_mode_invalid")
        if facility.get("availability") != "on_demand":
            facility_blockers.append("credit_availability_invalid")
        rate = _finite(facility.get("annual_rate_pct"), non_negative=True)
        term_years = _finite(facility.get("facility_term_years"), non_negative=True)
        if rate is not None and rate > 100:
            rate = None
        if term_years is not None and term_years <= 0:
            term_years = None
        incomplete_fields = []
        for field, value in (
            ("annual_rate_pct", rate),
            ("interest_accrual", facility.get("interest_accrual")),
            ("facility_term_years", term_years),
            ("repayment_structure", facility.get("repayment_structure")),
            ("minimum_payment_status", facility.get("minimum_payment_status")),
            ("minimum_payment_terms", facility.get("minimum_payment_terms")),
        ):
            if value is None or value == "":
                incomplete_fields.append(field)
        if facility.get("confirmation_status") == "user_confirmed_partial":
            incomplete_fields.append("confirmation_status")
        facility_fx = rate_to_base(facility_currency) if len(facility_currency) == 3 else None
        if facility_fx is None:
            facility_blockers.append("credit_fx_unavailable")
        undrawn_base = None
        drawn_base = None
        if limit_amount is not None and drawn_amount is not None and facility_fx is not None:
            undrawn_base = max(limit_amount - drawn_amount, 0.0) * facility_fx
            total_undrawn_base += undrawn_base
            drawn_base = drawn_amount * facility_fx
            total_drawn_base += drawn_base
        elif drawn_amount is not None:
            drawn_debt_complete = False
        facility_summaries.append(
            {
                "currency": facility_currency or None,
                "undrawn_amount_base": undrawn_base,
                "drawn_amount_base": drawn_base,
                "annual_rate_pct": rate,
                "terms_status": "incomplete" if incomplete_fields else "complete",
                "incomplete_fields": sorted(set(incomplete_fields)),
                "blockers": sorted(set(facility_blockers)),
            }
        )
        credit_blockers.extend(facility_blockers)
    if any_drawn:
        warnings.append("drawn_debt_present")

    household_blockers = sorted(set(blockers))
    floor_base = floor_amount * floor_rate if floor_amount is not None and floor_rate is not None else None
    outflow_base = outflow_amount * outflow_rate if outflow_amount is not None and outflow_rate is not None else None
    alpha_reserve_base = nav * float(alpha_reserve_nav_fraction)
    deployable = (
        max(cash - floor_base - outflow_base - alpha_reserve_base, 0.0)
        if not household_blockers and floor_base is not None and outflow_base is not None
        else 0.0
    )
    credit_terms_incomplete = any(
        facility["terms_status"] != "complete" for facility in facility_summaries
    )
    credit_status = (
        "unavailable"
        if not facility_summaries or credit_blockers
        else "incomplete"
        if credit_terms_incomplete
        else "available"
    )
    if credit_terms_incomplete:
        warnings.append("credit_terms_incomplete")

    digest_payload = {
        "schema_version": "household-capital-view-v1",
        "evaluation_at": evaluated.astimezone(timezone.utc).isoformat(),
        "authority_records": sorted(normalized, key=lambda item: item["record_id"]),
        "portfolio": {"cash_base": cash, "nav_base": nav, "base_currency": currency},
        "alpha_reserve_nav_fraction": float(alpha_reserve_nav_fraction),
        "fx": {key: fx_cache[key] for key in sorted(fx_cache)},
    }
    status = (
        "unavailable"
        if household_blockers
        else "partial"
        if credit_status != "available"
        else "available"
    )
    return {
        "schema_version": "household-capital-view-v1",
        "status": status,
        "as_of": evaluation_at,
        "authority_as_of": min(authority_dates).isoformat() if authority_dates else None,
        "digest": _canonical_digest(digest_payload),
        "base_currency": currency,
        "household_cash": {
            "status": "available" if not household_blockers else "unavailable",
            "portfolio_cash_base": cash,
            "operating_floor_base": floor_base,
            "planned_outflows_base": outflow_base,
            "alpha_reserve_base": alpha_reserve_base,
            "deployable_cash_base": deployable,
            "blockers": household_blockers,
        },
        "contingent_credit_available": {
            "status": credit_status,
            "currency": currency,
            "undrawn_amount_base": total_undrawn_base if facility_summaries and not credit_blockers else None,
            "facility_count": len(facility_summaries),
            "terms_status": "incomplete" if credit_terms_incomplete else "complete",
            "facilities": facility_summaries,
            "blockers": sorted(set(credit_blockers)),
        },
        "loan_funded_supported_range": {
            "status": "manual_review_required",
            "range_base": None,
            "blockers": ["exact_draw_instrument_tranche_choice_required"],
        },
        "drawn_debt_base": total_drawn_base if drawn_debt_complete else None,
        "fx": {key: fx_cache[key] for key in sorted(fx_cache)},
        "blockers": household_blockers,
        "warnings": sorted(set(warnings)),
    }


__all__ = ["build_household_capital_view"]
