"""Deterministic Engine D beta signal and conservative contribution monitor。"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .beta_policy import load_beta_policy
from .capital_authority import build_household_capital_view


_ACTIONS = {"HOLD", "PAUSE CONTRIBUTION", "CONTRIBUTE REVIEW"}
_PRIMARY_DISPLAY_ORDER = (
    "QQQ",
    "TQQQ",
    "LON:VWRA",
    "SOXX",
    "00631L.TW",
    "2330.TW",
    "00981A.TW",
)


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


def _timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("as_of must include timezone")
    return parsed.isoformat()


def _fresh_observation(
    observation: Mapping[str, Any] | None,
    *,
    evaluation_at: str,
    max_age_hours: int,
) -> Mapping[str, Any] | None:
    if observation is None:
        return None
    fetched_raw = observation.get("fetched_at")
    if not isinstance(fetched_raw, str):
        return {
            "data_status": "quarantined",
            "blockers": ["technical_fetched_at_missing"],
        }
    try:
        fetched = datetime.fromisoformat(fetched_raw.replace("Z", "+00:00"))
        evaluated = datetime.fromisoformat(evaluation_at.replace("Z", "+00:00"))
    except ValueError:
        return {
            "data_status": "quarantined",
            "blockers": ["technical_fetched_at_invalid"],
        }
    if fetched.tzinfo is None or evaluated.tzinfo is None:
        return {
            "data_status": "quarantined",
            "blockers": ["technical_fetched_at_invalid"],
        }
    age_hours = (evaluated.astimezone(timezone.utc) - fetched.astimezone(timezone.utc)).total_seconds() / 3600
    if age_hours < -1:
        return {
            "data_status": "quarantined",
            "blockers": ["technical_fetched_at_future"],
        }
    if age_hours > max_age_hours:
        return {
            "data_status": "stale",
            "blockers": ["technical_observation_stale"],
        }
    return observation


def signal_state(observation: Mapping[str, Any] | None, policy: Mapping[str, Any]) -> dict[str, Any]:
    """Convert one observed scalar snapshot into a closed signal state。"""

    if not observation:
        return {
            "data_status": "missing",
            "tier": "unavailable",
            "pace": 0.0,
            "turning": False,
            "regime": "unknown",
            "blockers": ["technical_observation_missing"],
        }
    status = str(observation.get("data_status") or "missing")
    if status != "observed":
        return {
            "data_status": status,
            "tier": "unavailable",
            "pace": 0.0,
            "turning": False,
            "regime": "unknown",
            "blockers": sorted(
                {str(item) for item in observation.get("blockers") or []}
                or {f"technical_{status}"}
            ),
        }
    required = {
        key: _finite(observation.get(key))
        for key in (
            "drawdown_252",
            "rsi_14",
            "macd_histogram_slope",
            "distance_sma_200",
            "sma_50_slope_5",
        )
    }
    if any(value is None for value in required.values()):
        return {
            "data_status": "quarantined",
            "tier": "unavailable",
            "pace": 0.0,
            "turning": False,
            "regime": "unknown",
            "blockers": ["technical_signal_metric_missing"],
        }
    drawdown = required["drawdown_252"]
    rsi = required["rsi_14"]
    histogram_slope = required["macd_histogram_slope"]
    distance_200 = required["distance_sma_200"]
    slope_50 = required["sma_50_slope_5"]
    assert drawdown is not None and rsi is not None
    assert histogram_slope is not None and distance_200 is not None and slope_50 is not None
    matched: Mapping[str, Any] | None = None
    for tier in reversed(list(policy["signal"]["tiers"])):
        if drawdown <= float(tier["drawdown_at_most"]) and rsi <= float(tier["rsi_at_most"]):
            matched = tier
            break
    if matched is None:
        pace = 0.0
        tier_name = "none"
        turning = histogram_slope > 0
    else:
        turning = histogram_slope > 0
        bearish_regime = distance_200 < 0 and slope_50 < 0
        pace = float(matched["turning_pace"] if turning else matched["base_pace"])
        # 長均線與中期斜率同時偏空時，MACD 單日改善不足以直接使用最高 pace。
        if bearish_regime and pace > float(matched["base_pace"]):
            pace = float(matched["base_pace"])
        tier_name = str(matched["name"])
    regime = (
        "below_sma200_falling_sma50"
        if distance_200 < 0 and slope_50 < 0
        else "below_sma200_stabilizing"
        if distance_200 < 0
        else "above_sma200"
    )
    return {
        "data_status": "observed",
        "tier": tier_name,
        "pace": pace,
        "turning": turning,
        "regime": regime,
        "blockers": [],
    }


def _review_cadence(
    current: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    pace = float(current["pace"])
    if pace == 0:
        return {"review_due": False, "consecutive_sessions": 0, "reason": "no_signal"}
    states = [signal_state(item, policy) for item in history]
    if not states or states[0]["tier"] != current["tier"] or states[0]["pace"] != pace:
        states.insert(0, dict(current))
    consecutive = 0
    for state in states:
        if state["tier"] == current["tier"] and float(state["pace"]) == pace:
            consecutive += 1
        else:
            break
    previous_pace = float(states[1]["pace"]) if len(states) > 1 else 0.0
    escalated = pace > previous_pace
    repeat = int(policy["signal"]["repeat_after_sessions"])
    repeated = consecutive == 1 or (consecutive - 1) % repeat == 0
    return {
        "review_due": escalated or repeated,
        "consecutive_sessions": consecutive,
        "reason": "signal_escalated" if escalated else "repeat_cadence" if repeated else "cooldown",
    }


def _portfolio_snapshot(
    holdings_rows: Sequence[Mapping[str, Any]] | None,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    if holdings_rows is None:
        return {
            "status": "unavailable",
            "blockers": ["holdings_unavailable"],
            "nav_base": 0.0,
            "base_currency": None,
            "cash_base": 0.0,
            "deployable_cash_base": 0.0,
            "instrument_values": {},
            "leveraged_nominal_base": 0.0,
            "leveraged_effective_base": 0.0,
            "technology_effective_base": 0.0,
            "issuer_effective_base": {},
            "warnings": [],
        }
    aliases = {
        alias: instrument
        for instrument in policy["instruments"]
        for alias in instrument["sheet_aliases"]
    }
    cash_aliases = set(policy["capital"]["cash_bucket_aliases"])
    nav_values: list[float] = []
    currencies: set[str] = set()
    cash = 0.0
    instrument_values = {instrument["ticker"]: 0.0 for instrument in policy["instruments"]}
    leverage_nominal = 0.0
    leverage_effective = 0.0
    technology_effective = 0.0
    issuer_effective: dict[str, float] = {}
    unmapped_non_cash = 0.0
    market_total = 0.0
    for row in holdings_rows:
        if not isinstance(row, Mapping):
            blockers.append("holdings_malformed")
            continue
        nav = _finite(row.get("nav_base"), non_negative=True)
        value = _finite(row.get("market_value_base"), non_negative=True)
        ticker = str(row.get("ticker") or "").strip().upper()
        currency = str(row.get("base_currency") or "").strip().upper()
        bucket = str(row.get("bucket") or "").strip().casefold()
        if nav is None or nav <= 0 or value is None or not ticker or len(currency) != 3:
            blockers.append("holdings_malformed")
            continue
        nav_values.append(nav)
        currencies.add(currency)
        market_total += value
        is_cash = bucket in cash_aliases or ticker.casefold() in cash_aliases
        if is_cash:
            cash += value
            continue
        instrument = aliases.get(ticker)
        if instrument is None:
            unmapped_non_cash += value
            continue
        canonical = str(instrument["ticker"])
        instrument_values[canonical] += value
        leverage = float(instrument["leverage_multiple"])
        if leverage > 1:
            leverage_nominal += value
            leverage_effective += value * leverage
        technology_effective += value * leverage * float(instrument["technology_proxy_load"])
        for issuer, load in instrument["issuer_loads"].items():
            issuer_effective[issuer] = issuer_effective.get(issuer, 0.0) + value * leverage * float(load)
    if not nav_values:
        blockers.append("holdings_empty")
        nav_base = 0.0
    else:
        nav_base = nav_values[0]
        if any(not math.isclose(value, nav_base, rel_tol=1e-9, abs_tol=1e-6) for value in nav_values[1:]):
            blockers.append("holdings_nav_inconsistent")
    if len(currencies) != 1:
        blockers.append("holdings_base_currency_inconsistent")
    if nav_base > 0 and not math.isclose(market_total, nav_base, rel_tol=1e-6, abs_tol=0.01):
        blockers.append("holdings_market_value_nav_mismatch")
    if cash <= 0:
        blockers.append("cash_bucket_missing")
    technology_effective += unmapped_non_cash * float(policy["risk"]["unmapped_technology_proxy_load"])
    reserve = nav_base * (
        float(policy["capital"]["operating_reserve_nav_fraction"])
        + float(policy["capital"]["alpha_reserve_nav_fraction"])
    )
    deployable = max(cash - reserve, 0.0) if not blockers else 0.0
    warnings = ["unmapped_holdings_counted_as_full_technology_proxy"] if unmapped_non_cash else []
    return {
        "status": "available" if not blockers else "malformed",
        "blockers": sorted(set(blockers)),
        "nav_base": nav_base,
        "base_currency": next(iter(currencies)) if len(currencies) == 1 else None,
        "cash_base": cash,
        "reserve_base": reserve,
        "deployable_cash_base": deployable,
        "instrument_values": instrument_values,
        "leveraged_nominal_base": leverage_nominal,
        "leveraged_effective_base": leverage_effective,
        "technology_effective_base": technology_effective,
        "issuer_effective_base": issuer_effective,
        "unmapped_non_cash_base": unmapped_non_cash,
        "warnings": warnings,
    }


def _warning_flags(portfolio: Mapping[str, Any], policy: Mapping[str, Any]) -> list[str]:
    nav = float(portfolio.get("nav_base") or 0.0)
    if nav <= 0:
        return []
    risk = policy["risk"]
    flags: list[str] = []
    ratios = {
        "leveraged_nominal_warning": float(portfolio["leveraged_nominal_base"]) / nav,
        "leveraged_effective_warning": float(portfolio["leveraged_effective_base"]) / nav,
        "technology_effective_warning": float(portfolio["technology_effective_base"]) / nav,
    }
    for key, value in ratios.items():
        if value >= float(risk[key]):
            flags.append(key)
    for issuer, value in portfolio["issuer_effective_base"].items():
        if float(value) / nav >= float(risk["single_company_warning"]):
            flags.append(f"single_company_warning:{issuer}")
    return sorted(flags)


def _allocate_ranges(
    *,
    prepared: Sequence[Mapping[str, Any]],
    portfolio: Mapping[str, Any],
    policy: Mapping[str, Any],
    deployable_cash: float,
    capital_available: bool,
    capital_blockers: Sequence[str],
) -> tuple[list[dict[str, Any]], float]:
    """Run one independent sequential allocation view against shared hard caps。"""

    nav = float(portfolio["nav_base"])
    remaining_cash = max(float(deployable_cash), 0.0) if capital_available else 0.0
    risk = policy["risk"]
    projected_leverage_nominal = float(portfolio["leveraged_nominal_base"])
    projected_leverage_effective = float(portfolio["leveraged_effective_base"])
    projected_technology_effective = float(portfolio["technology_effective_base"])
    projected_issuer_effective = {
        str(key): float(value)
        for key, value in portfolio["issuer_effective_base"].items()
    }
    claimed_groups: set[str] = set()
    allocations: list[dict[str, Any]] = []
    for candidate in prepared:
        instrument = candidate["instrument"]
        state = candidate["state"]
        cadence = candidate["cadence"]
        blockers = list(state["blockers"])
        warnings: list[str] = []
        action = "HOLD"
        constraints: dict[str, float] = {}
        safe_max = 0.0
        binding: list[str] = []
        group = str(instrument["allocation_group"])
        if not capital_available:
            blockers.extend(str(item) for item in capital_blockers)
            action = "PAUSE CONTRIBUTION"
        elif state["data_status"] != "observed":
            action = "PAUSE CONTRIBUTION"
        elif float(state["pace"]) == 0:
            action = "HOLD"
        elif not cadence["review_due"]:
            action = "HOLD"
            blockers.append("signal_review_cooldown")
        elif group in claimed_groups:
            action = "HOLD"
            blockers.append("overlapping_instrument_deferred")
        else:
            claimed_groups.add(group)
            leverage = float(instrument["leverage_multiple"])
            constraints["campaign_budget"] = (
                nav
                * float(policy["campaign_budget_fraction_by_sleeve"][instrument["sleeve"]])
                * float(state["pace"])
            )
            constraints["deployable_cash"] = remaining_cash
            tech_load = leverage * float(instrument["technology_proxy_load"])
            if tech_load > 0:
                constraints["technology_effective_capacity"] = max(
                    nav * float(risk["technology_effective_cap"])
                    - projected_technology_effective,
                    0.0,
                ) / tech_load
            if leverage > 1:
                constraints["leveraged_nominal_capacity"] = max(
                    nav * float(risk["leveraged_nominal_cap"])
                    - projected_leverage_nominal,
                    0.0,
                )
                constraints["leveraged_effective_capacity"] = max(
                    nav * float(risk["leveraged_effective_cap"])
                    - projected_leverage_effective,
                    0.0,
                ) / leverage
            for issuer, load in instrument["issuer_loads"].items():
                exposure = float(projected_issuer_effective.get(issuer, 0.0))
                constraints[f"single_company_capacity:{issuer}"] = max(
                    nav * float(risk["single_company_cap"]) - exposure,
                    0.0,
                ) / (leverage * float(load))
            safe_max = max(min(constraints.values()), 0.0)
            minimum = min(constraints.values())
            binding = sorted(
                key
                for key, value in constraints.items()
                if math.isclose(value, minimum, rel_tol=1e-9, abs_tol=1e-6)
            )
            if safe_max > 0:
                action = "CONTRIBUTE REVIEW"
                remaining_cash = max(remaining_cash - safe_max, 0.0)
                projected_technology_effective += safe_max * tech_load
                if leverage > 1:
                    projected_leverage_nominal += safe_max
                    projected_leverage_effective += safe_max * leverage
                for issuer, load in instrument["issuer_loads"].items():
                    projected_issuer_effective[issuer] = (
                        projected_issuer_effective.get(issuer, 0.0)
                        + safe_max * leverage * float(load)
                    )
            else:
                action = "PAUSE CONTRIBUTION"
                blockers.extend(binding or ["safe_capacity_exhausted"])
        if action not in _ACTIONS:
            raise AssertionError("unexpected beta action")
        allocations.append(
            {
                "action": action,
                "supported_order_range_base": [0.0, safe_max],
                "binding_constraints": binding,
                "blockers": sorted(set(blockers)),
                "warnings": sorted(set(warnings)),
            }
        )
    return allocations, remaining_cash


def build_beta_monitor(
    *,
    observations_by_benchmark: Mapping[str, Mapping[str, Any] | None],
    history_by_benchmark: Mapping[str, Sequence[Mapping[str, Any]]],
    holdings_rows: Sequence[Mapping[str, Any]] | None,
    capital_authority_rows: Sequence[Mapping[str, Any]] | None = None,
    fx_fetcher=None,
    as_of: str,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one public, non-executing beta contribution report。"""

    evaluation_at = _timestamp(as_of)
    resolved_policy = dict(policy or load_beta_policy())
    portfolio = _portfolio_snapshot(holdings_rows, resolved_policy)
    nav = float(portfolio["nav_base"])
    prepared: list[dict[str, Any]] = []
    for instrument in resolved_policy["instruments"]:
        benchmark_key = str(instrument["benchmark_key"])
        observation = _fresh_observation(
            observations_by_benchmark.get(benchmark_key),
            evaluation_at=evaluation_at,
            max_age_hours=int(resolved_policy["signal"]["max_refresh_age_hours"]),
        )
        state = signal_state(observation, resolved_policy)
        cadence = _review_cadence(
            state,
            history_by_benchmark.get(benchmark_key, ()),
            resolved_policy,
        )
        prepared.append(
            {
                "instrument": instrument,
                "observation": observation,
                "state": state,
                "cadence": cadence,
            }
        )

    sheet_allocations, remaining_cash = _allocate_ranges(
        prepared=prepared,
        portfolio=portfolio,
        policy=resolved_policy,
        deployable_cash=float(portfolio["deployable_cash_base"]),
        capital_available=portfolio["status"] == "available",
        capital_blockers=portfolio["blockers"],
    )
    capital_view = build_household_capital_view(
        authority_rows=capital_authority_rows,
        portfolio_cash_base=portfolio["cash_base"],
        portfolio_nav_base=portfolio["nav_base"],
        base_currency=portfolio["base_currency"],
        evaluation_at=evaluation_at,
        alpha_reserve_nav_fraction=float(
            resolved_policy["capital"]["alpha_reserve_nav_fraction"]
        ),
        max_authority_age_days=int(
            resolved_policy["capital"]["household_authority_max_age_days"]
        ),
        max_fx_age_hours=int(resolved_policy["capital"]["household_fx_max_age_hours"]),
        fx_fetcher=fx_fetcher,
    )
    household_cash = capital_view["household_cash"]
    household_available = (
        portfolio["status"] == "available"
        and household_cash["status"] == "available"
    )
    household_allocations, household_remaining_cash = _allocate_ranges(
        prepared=prepared,
        portfolio=portfolio,
        policy=resolved_policy,
        deployable_cash=float(household_cash["deployable_cash_base"]),
        capital_available=household_available,
        capital_blockers=household_cash["blockers"],
    )

    items: list[dict[str, Any]] = []
    for candidate, sheet_allocation, household_allocation in zip(
        prepared, sheet_allocations, household_allocations, strict=True
    ):
        instrument = candidate["instrument"]
        observation = candidate["observation"]
        state = candidate["state"]
        cadence = candidate["cadence"]
        current_value = float(portfolio["instrument_values"].get(instrument["ticker"], 0.0))
        indicator = {
            key: observation.get(key) if observation else None
            for key in (
                "session_date",
                "return_1d",
                "return_5d",
                "return_20d",
                "rsi_14",
                "drawdown_252",
                "macd_histogram",
                "macd_histogram_slope",
                "distance_sma_20",
                "distance_sma_50",
                "distance_sma_200",
                "sma_50_slope_5",
                "realized_vol_20",
                "realized_vol_60",
            )
        }
        items.append(
            {
                "ticker": instrument["ticker"],
                "sleeve": instrument["sleeve"],
                "signal_benchmark": instrument["benchmark_symbol"],
                "technical_status": state["data_status"],
                "signal_tier": state["tier"],
                "signal_pace": state["pace"],
                "signal_regime": state["regime"],
                "review_cadence": cadence,
                "indicator": indicator,
                "current_nominal_weight": current_value / nav if nav > 0 else None,
                "current_effective_weight": (
                    current_value * float(instrument["leverage_multiple"]) / nav
                    if nav > 0
                    else None
                ),
                "supported_order_range_base": sheet_allocation["supported_order_range_base"],
                "sheet_conservative_order_range_base": sheet_allocation["supported_order_range_base"],
                "binding_constraints": sheet_allocation["binding_constraints"],
                "blockers": sheet_allocation["blockers"],
                "warnings": sheet_allocation["warnings"],
                "action": sheet_allocation["action"],
                "household_cash_supported_order_range_base": household_allocation[
                    "supported_order_range_base"
                ],
                "household_binding_constraints": household_allocation["binding_constraints"],
                "household_blockers": household_allocation["blockers"],
                "household_action": household_allocation["action"],
            }
        )
    warning_flags = _warning_flags(portfolio, resolved_policy)
    technical_statuses = {str(item["technical_status"]) for item in items}
    base_status = (
        "degraded"
        if portfolio["status"] != "available"
        or not technical_statuses <= {"observed", "insufficient_history"}
        else "partial"
        if "insufficient_history" in technical_statuses
        else "ok"
    )
    report_status = (
        base_status
        if base_status == "degraded"
        else "partial"
        if base_status == "partial" or capital_view["status"] != "available"
        else "ok"
    )
    sheet_allocated = float(portfolio["deployable_cash_base"]) - remaining_cash
    household_allocated = (
        float(household_cash["deployable_cash_base"]) - household_remaining_cash
    )
    report = {
        "schema_version": "engine-d-beta-monitor-v2",
        "as_of": evaluation_at,
        "policy_version": resolved_policy["policy_version"],
        "policy_mode": resolved_policy["mode"],
        "capital_scope": resolved_policy["capital_scope"],
        "status": report_status,
        "portfolio": {
            "status": portfolio["status"],
            "nav_base": nav if nav > 0 else None,
            "base_currency": portfolio["base_currency"],
            "cash_base": portfolio["cash_base"],
            "reserve_base": portfolio.get("reserve_base", 0.0),
            "deployable_cash_base": portfolio["deployable_cash_base"],
            "allocated_review_base": sheet_allocated,
            "remaining_cash_base": remaining_cash,
            "leveraged_nominal_weight": portfolio["leveraged_nominal_base"] / nav if nav > 0 else None,
            "leveraged_effective_weight": portfolio["leveraged_effective_base"] / nav if nav > 0 else None,
            "technology_effective_proxy_weight": portfolio["technology_effective_base"] / nav if nav > 0 else None,
            "known_issuer_effective_weights": {
                issuer: value / nav for issuer, value in sorted(portfolio["issuer_effective_base"].items())
            }
            if nav > 0
            else {},
        },
        "capital_view": {
            key: capital_view[key]
            for key in (
                "schema_version",
                "status",
                "as_of",
                "authority_as_of",
                "digest",
                "base_currency",
                "household_cash",
                "fx",
                "blockers",
                "warnings",
            )
        },
        "sheet_conservative_range": [0.0, sheet_allocated],
        "household_cash_supported_range": [0.0, household_allocated],
        "contingent_credit_available": capital_view["contingent_credit_available"],
        "loan_funded_supported_range": capital_view["loan_funded_supported_range"],
        "blockers": sorted(set(portfolio["blockers"] + capital_view["blockers"])),
        "warnings": sorted(
            set(portfolio["warnings"] + warning_flags + capital_view["warnings"])
        ),
        "items": items,
    }
    return report


def _pct(value: Any) -> str:
    parsed = _finite(value)
    return "未知" if parsed is None else f"{parsed * 100:.1f}%"


def _signed_pct(value: Any) -> str:
    parsed = _finite(value)
    if parsed is None:
        return "未知"
    percentage = parsed * 100
    if abs(percentage) < 0.05:
        percentage = 0.0
    return f"{percentage:+.1f}%"


def _moves(indicator: Mapping[str, Any]) -> str:
    return (
        f"1日 {_signed_pct(indicator.get('return_1d'))}｜"
        f"5日 {_signed_pct(indicator.get('return_5d'))}｜"
        f"20日 {_signed_pct(indicator.get('return_20d'))}"
    )


def _display_label(item: Mapping[str, Any], *, household_path_available: bool) -> str:
    if item["action"] == "CONTRIBUTE REVIEW" or (
        household_path_available and item["household_action"] == "CONTRIBUTE REVIEW"
    ):
        return "🟢 可評估"
    if item["technical_status"] != "observed":
        return "🔴 資料不足"
    blockers = set(item.get("blockers") or [])
    if household_path_available:
        blockers |= set(item.get("household_blockers") or [])
    if "signal_review_cooldown" in blockers or "overlapping_instrument_deferred" in blockers:
        return "🟡 冷卻／排序中"
    if item["action"] == "PAUSE CONTRIBUTION" or (
        household_path_available and item["household_action"] == "PAUSE CONTRIBUTION"
    ):
        return "🔴 暫停新增"
    return "⚪ 觀察"


def _compact_monitor_item(
    item: Mapping[str, Any], *, household_path_available: bool
) -> str:
    return (
        f"{item['ticker']} {_display_label(item, household_path_available=household_path_available)}"
        f"（{_moves(item['indicator'])}，"
        f"{item['signal_tier']}/pace {item['signal_pace']:.2f}"
        + (f"，{','.join(item['blockers'])}" if item["blockers"] else "")
        + "）"
    )


def _money(value: Any, currency: str | None) -> str:
    parsed = _finite(value, non_negative=True)
    return "未知" if parsed is None else f"{currency or ''} {parsed:,.0f}".strip()


def render_beta_monitor_markdown(report: Mapping[str, Any]) -> str:
    """Render safe aggregates, dual cash ranges and the manual loan boundary。"""

    portfolio = report["portfolio"]
    currency = portfolio.get("base_currency")
    capital_view = report["capital_view"]
    household_cash = capital_view["household_cash"]
    contingent = report["contingent_credit_available"]
    loan_range = report["loan_funded_supported_range"]
    lines = [
        "# Beta Technical Monitor",
        "",
        f"- 狀態：{report['status']}",
        f"- Policy：{report['policy_version']}（{report['policy_mode']}）",
        f"- 資本範圍：Sheet-only conservative（{report['capital_scope']}）＋"
        "household_cash paper observation（並列、不互相覆寫）",
        f"- NAV／現金／保留：{_money(portfolio.get('nav_base'), currency)}／"
        f"{_money(portfolio.get('cash_base'), currency)}／{_money(portfolio.get('reserve_base'), currency)}",
        f"- Sheet conservative 可部署／本輪 range：{_money(portfolio.get('deployable_cash_base'), currency)}／"
        f"{_money(report['sheet_conservative_range'][1], currency)}",
        f"- Household cash 可部署／本輪 range："
        f"{_money(household_cash.get('deployable_cash_base'), currency)}／"
        f"{_money(report['household_cash_supported_range'][1], currency)}"
        f"（{household_cash.get('status', 'unknown')}）",
        f"- Contingent credit：{_money(contingent.get('undrawn_amount_base'), currency)}"
        f"（{contingent.get('status', 'unknown')}；terms={contingent.get('terms_status', 'unknown')}；不算資本）",
        f"- Loan-funded range：{loan_range.get('status', 'manual_review_required')}（不自動給金額）",
        f"- 槓桿名目／effective：{_pct(portfolio.get('leveraged_nominal_weight'))}／"
        f"{_pct(portfolio.get('leveraged_effective_weight'))}",
        f"- 科技 effective proxy：{_pct(portfolio.get('technology_effective_proxy_weight'))}",
    ]
    blockers = report.get("blockers") or []
    warnings = report.get("warnings") or []
    if blockers:
        lines.append(f"- Portfolio blockers：{'、'.join(str(item) for item in blockers)}")
    if warnings:
        lines.append(f"- Warnings：{'、'.join(str(item) for item in warnings)}")

    household_path_available = household_cash.get("status") == "available"
    reviews = [
        item
        for item in report["items"]
        if item["action"] == "CONTRIBUTE REVIEW"
        or (
            household_path_available
            and item["household_action"] == "CONTRIBUTE REVIEW"
        )
    ]
    paused = [
        item
        for item in report["items"]
        if item not in reviews
        and (
            item["action"] == "PAUSE CONTRIBUTION"
            or (
                household_path_available
                and item["household_action"] == "PAUSE CONTRIBUTION"
            )
        )
    ]
    holds = [item for item in report["items"] if item not in reviews and item not in paused]
    lines += ["", "## 需要人工判斷"]
    if not reviews:
        lines.append("- NO ACTION")
    for item in reviews:
        indicator = item["indicator"]
        lines.append(
            f"- {_display_label(item, household_path_available=household_path_available)}｜"
            f"{item['ticker']}｜{_moves(indicator)}｜"
            f"RSI {_finite(indicator.get('rsi_14')) or 0:.1f}｜距高點 {_pct(indicator.get('drawdown_252'))}｜"
            f"{item['signal_tier']} / pace {item['signal_pace']:.2f}｜"
            f"Sheet／household 上限 {_money(item['supported_order_range_base'][1], currency)}／"
            f"{_money(item['household_cash_supported_order_range_base'][1], currency)}｜"
            f"Sheet 約束 {','.join(item['binding_constraints']) or 'none'}｜"
            f"household 約束 {','.join(item['household_binding_constraints']) or 'none'}"
        )
    if paused:
        lines += ["", "## 暫停新增"]
        for item in paused:
            indicator = item["indicator"]
            lines.append(
                f"- {_display_label(item, household_path_available=household_path_available)}｜"
                f"{item['ticker']}｜{_moves(indicator)}｜"
                f"{item['technical_status']}｜"
                f"Sheet={','.join(item['blockers']) or item['action']}｜"
                f"household={','.join(item['household_blockers']) or item['household_action']}"
            )
    primary_rank = {ticker: index for index, ticker in enumerate(_PRIMARY_DISPLAY_ORDER)}
    primary_holds = sorted(
        (item for item in holds if item["ticker"] in primary_rank),
        key=lambda item: primary_rank[item["ticker"]],
    )
    secondary_holds = [item for item in holds if item["ticker"] not in primary_rank]
    lines += ["", "## 主力 ETF／權值"]
    if primary_holds:
        for item in primary_holds:
            indicator = item["indicator"]
            lines.append(
                f"- {_display_label(item, household_path_available=household_path_available)}｜"
                f"{item['ticker']}｜{_moves(indicator)}｜"
                f"RSI {_finite(indicator.get('rsi_14')) or 0:.1f}｜"
                f"距高點 {_pct(indicator.get('drawdown_252'))}｜"
                f"{item['signal_tier']} / pace {item['signal_pace']:.2f}"
            )
    else:
        lines.append("- 無")
    lines += ["", "## 個股與其他（摘要）"]
    if secondary_holds:
        other_etfs = [item for item in secondary_holds if item["ticker"] in {"0050.TW", "006208.TW"}]
        individual_names = [item for item in secondary_holds if item not in other_etfs]
        if other_etfs:
            lines.append(
                "- 其他 ETF："
                + "；".join(
                    _compact_monitor_item(
                        item, household_path_available=household_path_available
                    )
                    for item in other_etfs
                )
            )
        if individual_names:
            lines.append(
                "- 個股："
                + "；".join(
                    _compact_monitor_item(
                        item, household_path_available=household_path_available
                    )
                    for item in individual_names
                )
            )
    else:
        lines.append("- 無")
    lines += [
        "",
        "> 所有金額均為 paper observation review range；未動用額度不進 NAV／cash，且不代表已核准、已下單或已寫回 Google Sheet；貸款另不代表已提款。",
    ]
    return "\n".join(lines)


__all__ = ["build_beta_monitor", "render_beta_monitor_markdown", "signal_state"]
