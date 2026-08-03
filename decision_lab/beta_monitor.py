"""Deterministic Engine D beta signal and conservative contribution monitor。"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .beta_policy import instrument_price_key, load_beta_policy
from .capital_authority import build_capital_view
from .portfolio_risk import (
    build_portfolio_components,
    compose_risk_snapshot,
    event_search_requests,
    risk_changes,
)


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
    stretched = False
    matched: Mapping[str, Any] | None = None
    for tier in reversed(list(policy["signal"]["tiers"])):
        if drawdown <= float(tier["drawdown_at_most"]) and rsi <= float(tier["rsi_at_most"]):
            matched = tier
            break
    baseline_pace = float(policy["signal"]["baseline_pace"])
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
        # 對稱的另一側：回撤 tier 只看「跌了多少」，看不出「跌之前漲了多少」。
        # 仍遠高於 200 日均線時降一級——買在趨勢之上不該與買在趨勢附近同速。
        stretched_threshold = _finite(
            policy["signal"].get("stretched_above_sma200"), non_negative=True
        )
        if stretched_threshold is not None and distance_200 > stretched_threshold:
            allowed = sorted(
                float(value) for value in policy["signal"]["allowed_paces"]
            )
            lower = [value for value in allowed if value < pace]
            pace = lower[-1] if lower else 0.0
            stretched = True
        else:
            stretched = False
        tier_name = str(matched["name"])
    # 例行投入下限：訊號只能把 pace 往上加，不能把它壓到 baseline 以下。
    # 2026-08-01 實測，以訊號 gate 自有現金投入使終值輸給無腦定投 8.5%
    # （QQQ 91.5%、SOXX 91.9%）；訊號調節借款提取則無可測得效果。
    # 因此 baseline 之上的部分屬未驗證的行為輔助，baseline 本身才是有證據的機制。
    signal_pace = pace
    pace = max(pace, baseline_pace)
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
        "baseline_pace": baseline_pace,
        # 訊號自身算出的 pace；低於 baseline 時代表本期投入完全來自例行時間表
        "signal_pace_raw": signal_pace,
        "pace_source": "baseline" if signal_pace <= baseline_pace else "signal",
        "turning": turning,
        "regime": regime,
        "stretched_above_sma200": stretched,
        "blockers": [],
    }


def _review_cadence(
    current: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
    observed_session_count: int | None = None,
) -> dict[str, Any]:
    pace = float(current["pace"])
    repeat = int(policy["signal"]["repeat_after_sessions"])
    session_count = (
        int(observed_session_count)
        if isinstance(observed_session_count, int) and observed_session_count > 0
        else max(len(history), 1)
    )
    routine_due = session_count == 1 or (session_count - 1) % repeat == 0
    sessions_until_routine = repeat - ((session_count - 1) % repeat)
    if pace == 0:
        return {
            "review_due": False,
            "routine_due": routine_due,
            "observed_session_count": session_count,
            "sessions_until_routine": sessions_until_routine,
            "consecutive_sessions": 0,
            "reason": "data_unavailable",
        }
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
    signal_active = str(current.get("pace_source") or "baseline") == "signal"
    escalated = signal_active and pace > previous_pace
    signal_repeated = signal_active and (
        consecutive == 1 or (consecutive - 1) % repeat == 0
    )
    review_due = routine_due or escalated or signal_repeated
    return {
        "review_due": review_due,
        "routine_due": routine_due,
        "observed_session_count": session_count,
        "sessions_until_routine": sessions_until_routine,
        "consecutive_sessions": consecutive,
        "reason": (
            "signal_escalated"
            if escalated
            else "signal_repeat"
            if signal_repeated
            else "routine_reminder"
            if routine_due
            else "cooldown"
        ),
    }


def _portfolio_snapshot(
    holdings_rows: Sequence[Mapping[str, Any]] | None,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    components = build_portfolio_components(holdings_rows, policy)
    blockers = list(components["blockers"])
    cash = float(components["cash_base"])
    if holdings_rows is not None and cash <= 0:
        blockers.append("cash_bucket_missing")
    return dict(components) | {
        "status": "available" if not blockers else "malformed",
        "blockers": sorted(set(blockers)),
    }


def _allocate_ranges(
    *,
    prepared: Sequence[Mapping[str, Any]],
    portfolio: Mapping[str, Any],
    policy: Mapping[str, Any],
    deployable_cash: float,
    capital_available: bool,
    capital_blockers: Sequence[str],
    global_risk_blocks: Sequence[str],
) -> tuple[list[dict[str, Any]], float]:
    """Run one independent sequential allocation view against shared hard caps。"""

    nav = float(portfolio["nav_base"])
    remaining_cash = max(float(deployable_cash), 0.0) if capital_available else 0.0
    risk = policy["risk"]
    projected_leverage_nominal = float(portfolio["leveraged_nominal_base"])
    projected_leverage_effective = float(portfolio["leveraged_effective_base"])
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
        if global_risk_blocks:
            blockers.extend(str(item) for item in global_risk_blocks)
            action = "PAUSE CONTRIBUTION"
        elif not capital_available:
            blockers.extend(str(item) for item in capital_blockers)
            action = "PAUSE CONTRIBUTION"
        elif state["data_status"] != "observed":
            action = "PAUSE CONTRIBUTION"
        elif float(state["pace"]) == 0:
            action = "HOLD"
        elif not cadence["review_due"]:
            action = "HOLD"
            blockers.append("routine_review_cooldown")
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
                if leverage > 1:
                    projected_leverage_nominal += safe_max
                    projected_leverage_effective += safe_max * leverage
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
    previous_risk_snapshot: Mapping[str, Any] | None = None,
    session_counts_by_benchmark: Mapping[str, int] | None = None,
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
        price_key = instrument_price_key(instrument)
        price_observation = (
            observation
            if price_key == benchmark_key
            else _fresh_observation(
                observations_by_benchmark.get(price_key),
                evaluation_at=evaluation_at,
                max_age_hours=int(
                    resolved_policy["signal"]["max_refresh_age_hours"]
                ),
            )
        )
        state = signal_state(observation, resolved_policy)
        cadence = _review_cadence(
            state,
            history_by_benchmark.get(benchmark_key, ()),
            resolved_policy,
            (session_counts_by_benchmark or {}).get(benchmark_key),
        )
        prepared.append(
            {
                "instrument": instrument,
                "observation": observation,
                "price_key": price_key,
                "price_observation": price_observation,
                "state": state,
                "cadence": cadence,
            }
        )

    capital_view = build_capital_view(
        authority_rows=capital_authority_rows,
        portfolio_cash_base=portfolio["cash_base"],
        base_currency=portfolio["base_currency"],
        evaluation_at=evaluation_at,
        max_authority_age_days=int(resolved_policy["capital"]["authority_max_age_days"]),
        max_fx_age_hours=int(resolved_policy["capital"]["fx_max_age_hours"]),
        fx_fetcher=fx_fetcher,
    )
    risk_snapshot = compose_risk_snapshot(
        portfolio,
        capital_view,
        resolved_policy,
        as_of=evaluation_at,
    )
    self_funded_cash = capital_view["self_funded_cash"]
    capital_available = (
        portfolio["status"] == "available"
        and self_funded_cash["status"] == "available"
    )
    allocations, remaining_cash = _allocate_ranges(
        prepared=prepared,
        portfolio=portfolio,
        policy=resolved_policy,
        deployable_cash=float(self_funded_cash["deployable_cash_base"]),
        capital_available=capital_available,
        capital_blockers=sorted(
            set(portfolio["blockers"] + self_funded_cash["blockers"])
        ),
        global_risk_blocks=risk_snapshot["hard_blocks"],
    )

    items: list[dict[str, Any]] = []
    for candidate, allocation in zip(prepared, allocations, strict=True):
        instrument = candidate["instrument"]
        observation = candidate["observation"]
        price_observation = candidate["price_observation"]
        state = candidate["state"]
        cadence = candidate["cadence"]
        current_value = float(portfolio["instrument_values"].get(instrument["ticker"], 0.0))
        indicator = {
            key: price_observation.get(key) if price_observation else None
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
        reference = (
            price_observation.get("_twse_reference")
            if price_observation
            else None
        )
        if isinstance(reference, Mapping):
            indicator.update(
                {
                    "twse_session_date": reference.get("session_date"),
                    "twse_close_raw": reference.get("close_raw"),
                    "twse_change_raw": reference.get("change_raw"),
                    "twse_change_pct": reference.get("change_pct"),
                    "twse_status": reference.get("status"),
                    "twse_source": reference.get("source"),
                }
            )
        items.append(
            {
                "ticker": instrument["ticker"],
                "sleeve": instrument["sleeve"],
                "signal_benchmark": instrument["benchmark_symbol"],
                "price_symbol": instrument["provider_symbol"],
                "price_series_key": candidate["price_key"],
                "price_status": (
                    str(price_observation.get("data_status") or "missing")
                    if price_observation
                    else "missing"
                ),
                "technical_status": state["data_status"],
                "signal_tier": state["tier"],
                "signal_pace": state["pace"],
                "signal_pace_raw": state.get("signal_pace_raw", 0.0),
                "pace_source": state.get("pace_source", "baseline"),
                "signal_regime": state["regime"],
                "review_cadence": cadence,
                "routine_schedule": {
                    "cadence_sessions": int(
                        resolved_policy["signal"]["repeat_after_sessions"]
                    ),
                    "due": bool(cadence.get("routine_due")),
                    "sessions_until_next": (
                        0
                        if cadence.get("routine_due")
                        else cadence.get("sessions_until_routine")
                    ),
                    "baseline_pace": float(
                        state.get(
                            "baseline_pace",
                            resolved_policy["signal"]["baseline_pace"],
                        )
                    ),
                    "scope": "self_funded_cash_only",
                },
                "signal_add_on": {
                    "tier": state["tier"],
                    "raw_pace": float(state.get("signal_pace_raw") or 0.0),
                    "incremental_pace": max(
                        float(state.get("signal_pace_raw") or 0.0)
                        - float(
                            state.get(
                                "baseline_pace",
                                resolved_policy["signal"]["baseline_pace"],
                            )
                        ),
                        0.0,
                    ),
                    "validated": False,
                },
                "indicator": indicator,
                "current_nominal_weight": current_value / nav if nav > 0 else None,
                "current_effective_weight": (
                    current_value * float(instrument["leverage_multiple"]) / nav
                    if nav > 0
                    else None
                ),
                "supported_order_range_base": allocation["supported_order_range_base"],
                "binding_constraints": allocation["binding_constraints"],
                "capital_constraints": {
                    "status": (
                        "review_open"
                        if allocation["action"] == "CONTRIBUTE REVIEW"
                        else "blocked"
                        if allocation["action"] == "PAUSE CONTRIBUTION"
                        else "not_open_today"
                    ),
                    "supported_order_range_base": allocation[
                        "supported_order_range_base"
                    ],
                    "binding_constraints": allocation["binding_constraints"],
                    "hard_blockers": [
                        blocker
                        for blocker in allocation["blockers"]
                        if blocker
                        not in {
                            "routine_review_cooldown",
                            "overlapping_instrument_deferred",
                        }
                    ],
                },
                "blockers": allocation["blockers"],
                "warnings": allocation["warnings"],
                "action": allocation["action"],
            }
        )
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
    self_funded_allocated = (
        float(self_funded_cash["deployable_cash_base"]) - remaining_cash
    )
    repeat_sessions = int(resolved_policy["signal"]["repeat_after_sessions"])
    routine_due_items = [
        item
        for item in items
        if item["technical_status"] == "observed"
        and bool(item["review_cadence"].get("routine_due"))
    ]
    observed_cadences = [
        item["review_cadence"]
        for item in items
        if item["technical_status"] == "observed"
    ]
    report = {
        "schema_version": "engine-d-beta-monitor-v6",
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
            "cash_floor_base": self_funded_cash["cash_floor_base"],
            "deployable_cash_base": self_funded_cash["deployable_cash_base"],
            "allocated_review_base": self_funded_allocated,
            "remaining_cash_base": remaining_cash,
            "leveraged_nominal_weight": portfolio["leveraged_nominal_base"] / nav if nav > 0 else None,
            "leveraged_effective_weight": portfolio["leveraged_effective_base"] / nav if nav > 0 else None,
            "alpha_total_weight": risk_snapshot["alpha_total_weight"],
            "known_issuer_exposures": risk_snapshot["issuer_exposures"],
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
                "self_funded_cash",
                "fx",
                "blockers",
                "warnings",
                "drawn_debt_base",
            )
        },
        "self_funded_supported_range": [0.0, self_funded_allocated],
        "contingent_credit_available": capital_view["contingent_credit_available"],
        "loan_funded_supported_range": capital_view["loan_funded_supported_range"],
        "routine_reminder": {
            "cadence_sessions": repeat_sessions,
            "due": bool(routine_due_items),
            "due_tickers": [str(item["ticker"]) for item in routine_due_items],
            "sessions_until_next": (
                0
                if routine_due_items
                else min(
                    (
                        int(cadence["sessions_until_routine"])
                        for cadence in observed_cadences
                    ),
                    default=None,
                )
            ),
            "scope": "self_funded_cash_only",
            "loan_included": False,
        },
        "risk_snapshot": risk_snapshot,
        "risk_changes": risk_changes(risk_snapshot, previous_risk_snapshot, resolved_policy),
        "event_search_requests": event_search_requests(
            risk_snapshot,
            observations_by_benchmark=observations_by_benchmark,
            history_by_benchmark=history_by_benchmark,
            policy=resolved_policy,
        ),
        "blockers": sorted(
            set(portfolio["blockers"] + capital_view["blockers"] + risk_snapshot["hard_blocks"])
        ),
        "warnings": sorted(
            set(portfolio["warnings"] + risk_snapshot["warnings"] + capital_view["warnings"])
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
    """顯示商品自身的短中期價格變化；訊號基準另列。"""

    return (
        f"1日 {_signed_pct(indicator.get('return_1d'))}｜"
        f"5日 {_signed_pct(indicator.get('return_5d'))}｜"
        f"20日 {_signed_pct(indicator.get('return_20d'))}"
    )


def _twse_snapshot(indicator: Mapping[str, Any]) -> str:
    session = indicator.get("twse_session_date")
    change_pct = _finite(indicator.get("twse_change_pct"))
    if not session or change_pct is None:
        return ""
    return f"TWSE 官方 {session} {_signed_pct(change_pct)}｜"


def _heat(indicator: Mapping[str, Any]) -> str:
    """距 200 日均線＝單一「熱度」讀數。

    距高點只說跌了多少，不說跌之前漲了多少。兩者合看才知道現在是回到趨勢
    還是仍在趨勢之上：SOXX 曾同時出現「距高點 -23%」與「距 200 日均線 +26%」。
    """
    value = _finite(indicator.get("distance_sma_200"))
    if value is None:
        return "距200日均線 n/a"
    if value > 0.20:
        tag = "偏熱"
    elif value > 0.05:
        tag = "偏高"
    elif value >= -0.05:
        tag = "近趨勢"
    else:
        tag = "低於趨勢"
    return f"距200日均線 {_signed_pct(value)}（{tag}）"


def _pace_label(value: Any) -> str:
    parsed = _finite(value, non_negative=True)
    return "節奏未知" if parsed is None else f"節奏 {parsed * 100:.0f}%"


def _signal_tier_label(value: Any) -> str:
    return {
        "none": "未觸發",
        "pullback": "一般回檔",
        "deep": "深度回檔",
        "capitulation": "急跌",
        "unavailable": "資料不足",
    }.get(str(value), str(value))


def _rsi_zone(value: Any) -> str:
    parsed = _finite(value)
    if parsed is None:
        return "n/a"
    if parsed < 30:
        return f"{parsed:.1f} 超賣區"
    if parsed < 50:
        return f"{parsed:.1f} 弱／中性"
    if parsed <= 70:
        return f"{parsed:.1f} 偏強"
    return f"{parsed:.1f} 過熱"


def _primary_tldr(item: Mapping[str, Any]) -> str:
    indicator = item["indicator"]
    benchmark_note = (
        f"；節奏訊號看 {item['signal_benchmark']}"
        if item.get("price_symbol") != item.get("signal_benchmark")
        else ""
    )
    if item.get("price_status") != "observed":
        return (
            f"{_display_label(item)}；{item.get('price_symbol') or item['ticker']} "
            f"自身價格資料不足{benchmark_note}"
        )
    return (
        f"{_display_label(item)}；自身 RSI {_rsi_zone(indicator.get('rsi_14'))}；"
        f"{_moves(indicator)}；距高點 {_pct(indicator.get('drawdown_252'))}；"
        f"{_heat(indicator)}{benchmark_note}"
    )


def _relative_conclusion_label(item: Mapping[str, Any]) -> str:
    if _primary_action(item) == "PAUSE CONTRIBUTION":
        return "排除：資料或個別限制未通過"
    if _primary_action(item) != "CONTRIBUTE REVIEW":
        return "今日不比較（尚未到投入評估日）"
    incremental = _finite(
        (item.get("signal_add_on") or {}).get("incremental_pace"),
        non_negative=True,
    ) or 0.0
    if incremental > 0:
        return "回檔觀察優先；Signal 尚未驗證"
    return "例行候選；沒有相對加碼證據"


def _individual_exception_label(item: Mapping[str, Any], currency: str | None) -> str:
    capital = item.get("capital_constraints") or {}
    hard = [str(value) for value in capital.get("hard_blockers") or []]
    blockers = set(_primary_blockers(item))
    if hard:
        return "、".join(_constraint_label(value) for value in hard)
    if "overlapping_instrument_deferred" in blockers:
        return "同基準商品已優先配置，本檔後延"
    if _primary_action(item) == "CONTRIBUTE REVIEW":
        ceiling = _primary_supported_ceiling(item)
        return f"本檔人工評估上限 {_money(ceiling, currency)}"
    return "無；共用日期／現金／投組上限見表格上方"


def _constraint_label(value: Any) -> str:
    raw = str(value)
    labels = {
        "campaign_budget": "單輪預算",
        "deployable_cash": "可部署現金",
        "leveraged_nominal_capacity": "槓桿 ETF 資金上限",
        "leveraged_effective_capacity": "換算槓桿曝險上限",
        "routine_review_cooldown": "尚未到例行投入評估日",
        "overlapping_instrument_deferred": "同基準標的已優先評估",
        "technical_history_insufficient_252_sessions": "歷史不足 252 個交易日",
        "technical_observation_missing": "缺少技術資料",
        "technical_observation_stale": "技術資料過期",
        "technical_session_stale_vs_twse": "TWSE 官方行情較新，技術訊號暫停",
        "technical_twse_freshness_unavailable": "TWSE freshness 校驗不可用",
        "technical_signal_metric_missing": "技術指標不完整",
        "safe_capacity_exhausted": "本輪可用上限已用完",
    }
    return labels.get(raw, raw.replace("_", " "))


def _warning_label(value: Any) -> str:
    raw = str(value)
    if raw.startswith("issuer_concentration_warning:"):
        return f"{raw.partition(':')[2]} 集中曝險已進警戒"
    return {
        "issuer_lookthrough_partial": "ETF 成分穿透僅涵蓋已登記部分",
        "leveraged_effective_warning": "換算槓桿曝險已進警戒",
        "leveraged_nominal_warning": "槓桿 ETF 資金占比已進警戒",
        "unclassified_holdings_assumed_unlevered_direct_issuer": (
            "未分類持股暫按非槓桿直接曝險計算"
        ),
        "drawn_debt_present": "已有提款貸款",
        "credit_terms_incomplete": "貸款條件資料不完整",
        "twse_freshness_unavailable": "TWSE freshness 校驗不可用",
        "twse_reference_older_than_provider": "TWSE 參考列落後供應商列",
    }.get(raw, raw.replace("_", " "))


def _status_label(value: Any) -> str:
    return {
        "available": "可用",
        "incomplete": "資料不完整",
        "unavailable": "不可用",
        "complete": "完整",
        "unknown": "未知",
    }.get(str(value), str(value).replace("_", " "))


def _primary_action(item: Mapping[str, Any]) -> str:
    return str(item["action"])


def _primary_blockers(item: Mapping[str, Any]) -> list[str]:
    return [str(value) for value in item.get("blockers") or []]


def _primary_binding_constraints(item: Mapping[str, Any]) -> list[str]:
    return [str(value) for value in item.get("binding_constraints") or []]


def _primary_supported_ceiling(item: Mapping[str, Any]) -> Any:
    value = item.get("supported_order_range_base") or [0.0, 0.0]
    return value[1]


def _display_label(item: Mapping[str, Any]) -> str:
    action = _primary_action(item)
    if action == "CONTRIBUTE REVIEW":
        return "🟢 可評估"
    if item["technical_status"] != "observed":
        return "🔴 資料不足"
    blockers = set(_primary_blockers(item))
    if "routine_review_cooldown" in blockers or "overlapping_instrument_deferred" in blockers:
        return "🟡 冷卻／排序中"
    if action == "PAUSE CONTRIBUTION":
        return "🔴 暫停新增"
    return "⚪ 觀察"


def _compact_monitor_item(item: Mapping[str, Any]) -> str:
    twse = _twse_snapshot(item["indicator"]).rstrip("｜")
    return (
        f"{item['ticker']} {_display_label(item)}"
        f"（{_moves(item['indicator'])}，"
        f"{_signal_tier_label(item['signal_tier'])}/{_pace_label(item['signal_pace'])}"
        + (f"，{twse}" if twse else "")
        + (
            "，"
            + "、".join(
                _constraint_label(value)
                for value in _primary_blockers(item)
            )
            if _primary_blockers(item)
            else ""
        )
        + "）"
    )


def _risk_hint_summary(report: Mapping[str, Any]) -> str:
    changes = report.get("risk_changes") or []
    if not changes:
        return "今日沒有顯示門檻跨越或狀態翻轉"
    if any(item.get("kind") == "baseline_initialized" for item in changes):
        return "已建立第一筆風險 baseline；後續只回報門檻跨越或狀態翻轉"
    labels: list[str] = []
    for item in changes:
        metric = str(item.get("metric") or "")
        if metric.startswith("issuer_exposure:"):
            labels.append(f"{metric.partition(':')[2]} 集中曝險變動")
        elif metric == "alpha_total_weight":
            labels.append("alpha 總量變動")
        elif "leverage" in metric:
            labels.append("槓桿狀態變動")
        elif metric == "policy_version":
            labels.append("風控 policy 已換版")
    return "、".join(dict.fromkeys(labels)) or "風險狀態有變"


def _money(value: Any, currency: str | None) -> str:
    parsed = _finite(value, non_negative=True)
    return "未知" if parsed is None else f"{currency or ''} {parsed:,.0f}".strip()


def _issuer_exposure_label(value: Any, coverage_status: Any) -> str:
    exposure = _pct(value)
    return f"已知至少 {exposure}" if str(coverage_status) == "partial" else exposure


def _risk_snapshot_lines(report: Mapping[str, Any], *, full: bool) -> list[str]:
    snapshot = report["risk_snapshot"]
    changes = report.get("risk_changes") or []
    if not full and not changes:
        return []
    etf = snapshot["etf_leverage"]
    lines = ["", "## 投組風險變化" if not full else "## 投組風險完整快照"]
    # 總曝險永遠顯示：它是唯一同時涵蓋持股、槓桿 ETF 與借款的口徑，
    # 而借款在 2026-08-01 之前完全不受任何硬擋約束。歸零門檻與它並列，
    # 因為「1.5x」對人沒有感覺，「指數跌 67% 自有資本歸零」才有。
    total = _finite(snapshot.get("total_exposure_weight"), non_negative=True)
    if total is not None:
        wipeout = _finite(snapshot.get("wipeout_index_drawdown"), non_negative=True)
        cap = _finite(snapshot.get("total_exposure_cap"), non_negative=True)
        lines.append(
            f"- **總曝險 {total:.2f}x**"
            + (f"（上限 {cap:.2f}x）" if cap else "")
            + (f"；自有資本歸零門檻：指數跌 {wipeout:.0%}" if wipeout else "")
        )
    if full or any("leverage" in str(item.get("metric")) for item in changes):
        lines.append(
            f"- 槓桿 ETF 資金占比：{_pct(etf.get('nominal_weight'))}；"
            f"換算槓桿曝險：{_pct(etf.get('effective_weight'))}；"
            f"已提款貸款占 NAV：{_pct(snapshot.get('loan_leverage_weight'))}；"
            f"合計換算曝險：{_pct(snapshot.get('combined_leverage_weight'))}"
        )
    if full or any(item.get("metric") == "alpha_total_weight" for item in changes):
        lines.append(f"- Alpha 總量：{_pct(snapshot.get('alpha_total_weight'))}（警告、不阻擋）")
    changed_issuers = {
        str(item.get("metric")).partition(":")[2]
        for item in changes
        if str(item.get("metric") or "").startswith("issuer_exposure:")
    }
    coverage = snapshot["issuer_coverage"]
    for issuer, exposure in snapshot.get("issuer_exposures", {}).items():
        if full or issuer in changed_issuers:
            lines.append(
                f"- {issuer}：總曝險 "
                f"{_issuer_exposure_label(exposure.get('total_weight'), coverage.get('status'))}"
                f"（直接 {_pct(exposure.get('direct_weight'))}／間接 {_pct(exposure.get('indirect_weight'))}）"
            )
    if full:
        lines.append(
            f"- Issuer look-through coverage：{coverage['status']}；method={coverage['method']}；"
            f"未建模={','.join(coverage['unmodeled_lookthrough_instruments']) or 'none'}"
        )
    if changes:
        lines.append(
            "- 較前次："
            + "；".join(
                f"{item.get('metric')} {item.get('previous_state', '')}→{item.get('current_state', '')}"
                for item in changes
            )
        )
    return lines


def render_beta_monitor_markdown(
    report: Mapping[str, Any],
    *,
    risk_view: str = "changes",
) -> str:
    """Render one shared Alpha/Beta self-funded cash pool and separate loan view。"""

    portfolio = report["portfolio"]
    currency = portfolio.get("base_currency")
    capital_view = report["capital_view"]
    self_funded_cash = capital_view["self_funded_cash"]
    contingent = report["contingent_credit_available"]
    deployable_cash = self_funded_cash.get("deployable_cash_base")
    supported_ceiling = report["self_funded_supported_range"][1]
    reviews = [
        item
        for item in report["items"]
        if _primary_action(item) == "CONTRIBUTE REVIEW"
    ]
    review_names = "、".join(str(item["ticker"]) for item in reviews) or "無"
    routine = report.get("routine_reminder") or {}
    cadence_sessions = int(routine.get("cadence_sessions") or 5)
    if routine.get("due"):
        invest_today = "應啟動人工投入評估"
        routine_line = (
            f"- 例行提醒：每 {cadence_sessions} 個完整交易日一次的自有現金評估本期已到；"
            + (
                f"{review_names} 可進人工評估。"
                if reviews
                else "目前因資料／風控限制沒有可評估標的。"
            )
            + "貸款不在本提醒內。"
        )
    else:
        invest_today = "今天不用啟動投入評估"
        remaining = routine.get("sessions_until_next")
        routine_line = (
            f"- 例行提醒：每 {cadence_sessions} 個完整交易日一次；"
            + (
                f"距下一次約 {remaining} 個完整交易日。"
                if isinstance(remaining, int)
                else "下一次待有效行情恢復後計算。"
            )
            + "只涵蓋自有現金，貸款不在本提醒內。"
        )
    signal_candidates = [
        item
        for item in reviews
        if (
            _finite(
                (item.get("signal_add_on") or {}).get("incremental_pace"),
                non_negative=True,
            )
            or 0.0
        )
        > 0
    ]
    if not reviews:
        comparison_line = "今天不是投入評估日，因此不做標的排名。"
    elif signal_candidates:
        comparison_line = (
            "回檔觀察可先比較 "
            + "、".join(str(item["ticker"]) for item in signal_candidates)
            + "；但 Signal 加碼尚未通過驗證，不等於預期報酬較高。"
        )
    else:
        comparison_line = (
            "本輪可評估標的都只有例行 baseline，沒有相對加碼證據；"
            "系統不硬排一個沒有證據的首選。"
        )
    lines = [
        "# Beta Technical Monitor",
        "",
        "## TL;DR",
        "",
        "- 目標：最大化約 30 年後的退休淨終值；Beta 維持只累積、不因一般回檔自動賣出，技術訊號只決定新增的時點與節奏。",
        f"- **今天是否投入：{invest_today}。**",
        routine_line,
        f"- **相對比較：{comparison_line}**",
        f"- 今日候選：{review_names}；自有現金的本輪可評估上限 "
        f"{_money(supported_ceiling, currency)}，不是下單金額。",
        f"- 風控：{_risk_hint_summary(report)}；未動用貸款額度 "
        f"{_money(contingent.get('undrawn_amount_base'), currency)} 不算自有現金，也未納入本輪上限。",
        "",
        "## 資本與風控明細",
        "",
        f"- 自有現金可部署：{_money(deployable_cash, currency)}",
        f"- 本輪可評估上限：{_money(supported_ceiling, currency)}（今日燈號、單輪預算與風控上限後）",
        f"- 未動用貸款額度：{_money(contingent.get('undrawn_amount_base'), currency)}"
        f"（狀態：{_status_label(contingent.get('status', 'unknown'))}；"
        f"條件資料：{_status_label(contingent.get('terms_status', 'unknown'))}；"
        "不算自有現金）",
        f"- 已借款：{_money(contingent.get('drawn_amount_base'), currency)}；"
        f"估計月息：{_money(contingent.get('estimated_monthly_interest_base'), currency)}",
        "- 貸款投入：不在例行提醒內且尚未核准；提款時間表、金額、標的與批次留待另案人工核准，且月息不得依賴被迫賣出 beta",
        f"- 共同現金池計算：Portfolio CASH {_money(portfolio.get('cash_base'), currency)} − "
        f"cash floor {_money(self_funded_cash.get('cash_floor_base'), currency)}；"
        "cash floor 以上全部可供 Alpha 與 Beta 共用",
        "- Alpha／Beta 分配：由各自的 campaign budget、Decision sizing、單筆上限與風控另外決定；不預扣 alpha reserve。",
        "- 節奏說明：25% 代表使用該類資產完整單輪預算的四分之一，不是投入總資產的 25%。",
        "- 限制口徑：評估日期、可部署現金與投組 hard caps 是全局條件；商品資料 freshness、單輪預算、槓桿容量與重疊商品排序才會造成個別差異。",
    ]
    blockers = report.get("blockers") or []
    warnings = list(report.get("warnings") or [])
    if risk_view != "full":
        warnings = [
            item
            for item in warnings
            if item not in set(report["risk_snapshot"].get("warnings") or [])
        ]
    if blockers:
        lines.append(f"- Portfolio blockers：{'、'.join(str(item) for item in blockers)}")
    if warnings:
        lines.append(f"- 風險提醒：{'、'.join(_warning_label(item) for item in warnings)}")
    twse_freshness = report.get("twse_freshness") or {}
    if twse_freshness.get("status") not in {None, "not_required", "not_available"}:
        lines.append(
            f"- 台股行情 freshness：{twse_freshness.get('status')}；"
            "TWSE 官方列只作最新交易日校驗，不混入 adjusted-close 指標"
        )

    lines += _risk_snapshot_lines(report, full=risk_view == "full")
    requests = report.get("event_search_requests") or []
    if requests:
        lines += ["", "## 集中曝險事件搜尋請求（未經查證、不寫入 authority）"]
        coverage_status = (report["risk_snapshot"].get("issuer_coverage") or {}).get(
            "status"
        )
        for request in requests:
            lines.append(
                f"- {request['issuer']}｜1日 {_signed_pct(request['return_1d'])}｜"
                f"曝險 {_issuer_exposure_label(request['exposure_weight'], coverage_status)}"
                f"（直接 {_pct(request['direct_weight'])}／"
                f"間接 {_pct(request['indirect_weight'])}）｜WebSearch：{request['search_query']}"
            )

    lines += ["", "## 需要人工判斷"]
    if not reviews:
        lines.append("- NO ACTION")
    else:
        lines.append(
            "- 今日可人工評估："
            + "、".join(str(item["ticker"]) for item in reviews)
            + "；仍需逐筆核准，未產生 live permission。"
        )
    primary_rank = {ticker: index for index, ticker in enumerate(_PRIMARY_DISPLAY_ORDER)}
    primary_items = sorted(
        (item for item in report["items"] if item["ticker"] in primary_rank),
        key=lambda item: primary_rank[item["ticker"]],
    )
    secondary_items = [
        item for item in report["items"] if item["ticker"] not in primary_rank
    ]
    lines += ["", "## 主力 ETF／權值"]
    if primary_items:
        lines += [
            "| 標的 | 系統動作 | 每檔 TL;DR（自身價格） | 相對結論 | 個別例外／上限 |",
            "|---|---|---|---|---|",
        ]
        for item in primary_items:
            indicator = item["indicator"]
            twse = _twse_snapshot(indicator).rstrip("｜")
            tldr = _primary_tldr(item) + (f"；{twse}" if twse else "")
            lines.append(
                f"| {item['ticker']} | {_primary_action(item)} | {tldr} | "
                f"{_relative_conclusion_label(item)} | "
                f"{_individual_exception_label(item, currency)} |"
            )
    else:
        lines.append("- 無")
    lines += ["", "## 個股與其他（摘要）"]
    if secondary_items:
        other_etfs = [item for item in secondary_items if item["ticker"] in {"0050.TW", "006208.TW"}]
        individual_names = [item for item in secondary_items if item not in other_etfs]
        if other_etfs:
            lines.append(
                "- 其他 ETF："
                + "；".join(
                    _compact_monitor_item(item)
                    for item in other_etfs
                )
            )
        if individual_names:
            lines.append(
                "- 個股："
                + "；".join(
                    _compact_monitor_item(item)
                    for item in individual_names
                )
            )
    else:
        lines.append("- 無")
    lines += [
        "",
        "> 所有金額都只是人工評估上限；例行提醒只涵蓋自有現金。未動用貸款額度不計入投資資產或自有現金，也不代表已核准、已提款、已下單或已寫回 Google Sheet。",
    ]
    return "\n".join(lines)


__all__ = ["build_beta_monitor", "render_beta_monitor_markdown", "signal_state"]
