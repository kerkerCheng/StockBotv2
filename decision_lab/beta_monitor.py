"""Deterministic Engine D beta signal and conservative contribution monitor。"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .beta_policy import load_beta_policy
from .capital_authority import build_household_capital_view
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
    components = build_portfolio_components(holdings_rows, policy)
    blockers = list(components["blockers"])
    nav_base = float(components["nav_base"])
    cash = float(components["cash_base"])
    if holdings_rows is not None and cash <= 0:
        blockers.append("cash_bucket_missing")
    reserve = nav_base * (
        float(policy["capital"]["operating_reserve_nav_fraction"])
        + float(policy["capital"]["alpha_reserve_nav_fraction"])
    )
    deployable = max(cash - reserve, 0.0) if not blockers else 0.0
    return dict(components) | {
        "status": "available" if not blockers else "malformed",
        "blockers": sorted(set(blockers)),
        "reserve_base": reserve,
        "deployable_cash_base": deployable,
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
    risk_snapshot = compose_risk_snapshot(
        portfolio,
        capital_view,
        resolved_policy,
        as_of=evaluation_at,
    )
    sheet_allocations, remaining_cash = _allocate_ranges(
        prepared=prepared,
        portfolio=portfolio,
        policy=resolved_policy,
        deployable_cash=float(portfolio["deployable_cash_base"]),
        capital_available=portfolio["status"] == "available",
        capital_blockers=portfolio["blockers"],
        global_risk_blocks=risk_snapshot["hard_blocks"],
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
        global_risk_blocks=risk_snapshot["hard_blocks"],
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
        "schema_version": "engine-d-beta-monitor-v3",
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
                "household_cash",
                "fx",
                "blockers",
                "warnings",
                "drawn_debt_base",
            )
        },
        "sheet_conservative_range": [0.0, sheet_allocated],
        "household_cash_supported_range": [0.0, household_allocated],
        "contingent_credit_available": capital_view["contingent_credit_available"],
        "loan_funded_supported_range": capital_view["loan_funded_supported_range"],
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


def _risk_snapshot_lines(report: Mapping[str, Any], *, full: bool) -> list[str]:
    snapshot = report["risk_snapshot"]
    changes = report.get("risk_changes") or []
    if not full and not changes:
        return []
    etf = snapshot["etf_leverage"]
    lines = ["", "## 投組風險變化" if not full else "## 投組風險完整快照"]
    if full or any("leverage" in str(item.get("metric")) for item in changes):
        lines.append(
            f"- ETF 槓桿名目／effective：{_pct(etf.get('nominal_weight'))}／"
            f"{_pct(etf.get('effective_weight'))}；貸款 {_pct(snapshot.get('loan_leverage_weight'))}；"
            f"合計 {_pct(snapshot.get('combined_leverage_weight'))}"
        )
    if full or any(item.get("metric") == "alpha_total_weight" for item in changes):
        lines.append(f"- Alpha 總量：{_pct(snapshot.get('alpha_total_weight'))}（警告、不阻擋）")
    changed_issuers = {
        str(item.get("metric")).partition(":")[2]
        for item in changes
        if str(item.get("metric") or "").startswith("issuer_exposure:")
    }
    for issuer, exposure in snapshot.get("issuer_exposures", {}).items():
        if full or issuer in changed_issuers:
            lines.append(
                f"- {issuer}：總曝險 {_pct(exposure.get('total_weight'))}"
                f"（直接 {_pct(exposure.get('direct_weight'))}／間接 {_pct(exposure.get('indirect_weight'))}）"
            )
    coverage = snapshot["issuer_coverage"]
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
    """Render safe aggregates, dual cash ranges and the manual loan boundary。"""

    portfolio = report["portfolio"]
    currency = portfolio.get("base_currency")
    capital_view = report["capital_view"]
    household_cash = capital_view["household_cash"]
    contingent = report["contingent_credit_available"]
    loan_range = report["loan_funded_supported_range"]
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
    review_names = "、".join(str(item["ticker"]) for item in reviews) or "無"
    lines = [
        "# Beta Technical Monitor",
        "",
        "## TL;DR",
        "",
        "- 目標：最大化約 30 年後的退休淨終值；Beta 維持 accumulation-only，technical signal 只決定新增的 timing／pace，不因一般回檔自動賣出。",
        f"- 今日：{review_names} 可進人工評估；Sheet／household 本輪合計上限 "
        f"{_money(report['sheet_conservative_range'][1], currency)}／"
        f"{_money(report['household_cash_supported_range'][1], currency)}，不是下單金額。",
        f"- 風控：{_risk_hint_summary(report)}；未動用額度 {_money(contingent.get('undrawn_amount_base'), currency)} "
        "不算資本，貸款必須另做 exact draw／instrument／tranche 人工 review，扣除利息與到期本金，且月息不得依賴被迫賣出 beta。",
        "",
        "## 資本與風控明細",
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
        lines.append(f"- Warnings：{'、'.join(str(item) for item in warnings)}")

    lines += _risk_snapshot_lines(report, full=risk_view == "full")
    requests = report.get("event_search_requests") or []
    if requests:
        lines += ["", "## 集中曝險事件搜尋請求（未經查證、不寫入 authority）"]
        for request in requests:
            lines.append(
                f"- {request['issuer']}｜1日 {_signed_pct(request['return_1d'])}｜"
                f"曝險 {_pct(request['exposure_weight'])}（直接 {_pct(request['direct_weight'])}／"
                f"間接 {_pct(request['indirect_weight'])}）｜WebSearch：{request['search_query']}"
            )

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
