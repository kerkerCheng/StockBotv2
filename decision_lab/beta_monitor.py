"""Deterministic Engine D beta signal and conservative contribution monitor。"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .beta_policy import load_beta_policy


_ACTIONS = {"HOLD", "PAUSE CONTRIBUTION", "CONTRIBUTE REVIEW"}


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


def build_beta_monitor(
    *,
    observations_by_benchmark: Mapping[str, Mapping[str, Any] | None],
    history_by_benchmark: Mapping[str, Sequence[Mapping[str, Any]]],
    holdings_rows: Sequence[Mapping[str, Any]] | None,
    as_of: str,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one public, non-executing beta contribution report。"""

    evaluation_at = _timestamp(as_of)
    resolved_policy = dict(policy or load_beta_policy())
    portfolio = _portfolio_snapshot(holdings_rows, resolved_policy)
    nav = float(portfolio["nav_base"])
    remaining_cash = float(portfolio["deployable_cash_base"])
    risk = resolved_policy["risk"]
    projected_leverage_nominal = float(portfolio["leveraged_nominal_base"])
    projected_leverage_effective = float(portfolio["leveraged_effective_base"])
    projected_technology_effective = float(portfolio["technology_effective_base"])
    projected_issuer_effective = {
        str(key): float(value)
        for key, value in portfolio["issuer_effective_base"].items()
    }
    claimed_groups: set[str] = set()
    items: list[dict[str, Any]] = []
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
        blockers = list(state["blockers"])
        warnings: list[str] = []
        action = "HOLD"
        constraints: dict[str, float] = {}
        safe_max = 0.0
        binding: list[str] = []
        group = str(instrument["allocation_group"])
        if portfolio["status"] != "available":
            blockers.extend(portfolio["blockers"])
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
                * float(resolved_policy["campaign_budget_fraction_by_sleeve"][instrument["sleeve"]])
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
        current_value = float(portfolio["instrument_values"].get(instrument["ticker"], 0.0))
        indicator = {
            key: observation.get(key) if observation else None
            for key in (
                "session_date",
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
                "supported_order_range_base": [0.0, safe_max],
                "binding_constraints": binding,
                "blockers": sorted(set(blockers)),
                "warnings": sorted(set(warnings)),
                "action": action,
            }
        )
    warning_flags = _warning_flags(portfolio, resolved_policy)
    technical_statuses = {str(item["technical_status"]) for item in items}
    report_status = (
        "degraded"
        if portfolio["status"] != "available"
        or not technical_statuses <= {"observed", "insufficient_history"}
        else "partial"
        if "insufficient_history" in technical_statuses
        else "ok"
    )
    report = {
        "schema_version": "engine-d-beta-monitor-v1",
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
            "allocated_review_base": portfolio["deployable_cash_base"] - remaining_cash,
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
        "blockers": list(portfolio["blockers"]),
        "warnings": sorted(set(portfolio["warnings"] + warning_flags)),
        "items": items,
    }
    return report


def _pct(value: Any) -> str:
    parsed = _finite(value)
    return "未知" if parsed is None else f"{parsed * 100:.1f}%"


def _money(value: Any, currency: str | None) -> str:
    parsed = _finite(value, non_negative=True)
    return "未知" if parsed is None else f"{currency or ''} {parsed:,.0f}".strip()


def render_beta_monitor_markdown(report: Mapping[str, Any]) -> str:
    """Render only aggregate holdings and public signal scalars。"""

    portfolio = report["portfolio"]
    currency = portfolio.get("base_currency")
    lines = [
        "# Beta Technical Monitor",
        "",
        f"- 狀態：{report['status']}",
        f"- Policy：{report['policy_version']}（{report['policy_mode']}）",
        f"- 資本範圍：{report['capital_scope']}（不是 household-level safe maximum）",
        f"- NAV／現金／保留：{_money(portfolio.get('nav_base'), currency)}／"
        f"{_money(portfolio.get('cash_base'), currency)}／{_money(portfolio.get('reserve_base'), currency)}",
        f"- 本輪可部署／已分配：{_money(portfolio.get('deployable_cash_base'), currency)}／"
        f"{_money(portfolio.get('allocated_review_base'), currency)}",
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

    reviews = [item for item in report["items"] if item["action"] == "CONTRIBUTE REVIEW"]
    paused = [item for item in report["items"] if item["action"] == "PAUSE CONTRIBUTION"]
    holds = [item for item in report["items"] if item["action"] == "HOLD"]
    lines += ["", "## 需要人工判斷"]
    if not reviews:
        lines.append("- NO ACTION")
    for item in reviews:
        indicator = item["indicator"]
        lines.append(
            f"- {item['ticker']} — {item['signal_tier']} / pace {item['signal_pace']:.2f}｜"
            f"RSI {_finite(indicator.get('rsi_14')) or 0:.1f}｜drawdown {_pct(indicator.get('drawdown_252'))}｜"
            f"候選上限 {_money(item['supported_order_range_base'][1], currency)}｜"
            f"約束 {','.join(item['binding_constraints']) or 'none'}"
        )
    if paused:
        lines += ["", "## 暫停新增"]
        for item in paused:
            lines.append(
                f"- {item['ticker']} — {item['technical_status']}｜"
                f"{','.join(item['blockers']) or 'safe capacity exhausted'}"
            )
    lines += ["", "## 正常監控"]
    if holds:
        lines.append(
            "- "
            + "；".join(
                f"{item['ticker']}={item['signal_tier']}/pace {item['signal_pace']:.2f}"
                + (f" ({','.join(item['blockers'])})" if item["blockers"] else "")
                for item in holds
            )
        )
    else:
        lines.append("- 無")
    lines += [
        "",
        "> 所有金額均為 Sheet-only conservative review range；不代表已核准、已下單或已寫回 Google Sheet。",
    ]
    return "\n".join(lines)


__all__ = ["build_beta_monitor", "render_beta_monitor_markdown", "signal_state"]
