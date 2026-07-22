"""五軸 Confidence Envelope 與 paper/live 分離的 Probe sizing。"""
from __future__ import annotations

import math
from copy import deepcopy
from typing import Any, Mapping, Sequence

from identity.registry import IdentityRegistry, get_registry
from thesis.investment_policy import PolicyError, load_policy, validate_policy

from .models import ContextBundle, CoverageResult, ProbeSizingResult


AXES = (
    "source_reliability",
    "technical_causal_link",
    "commercial_maturity",
    "financial_resilience",
    "valuation_payoff",
)
LEVELS = ("unknown", "bounded_hypothesis", "corroborated")
AXIS_REFERENCE_AUTHORITIES = {
    "source_reliability": frozenset(
        {"graph_source_assertion", "source_trace"}
    ),
    "technical_causal_link": frozenset(
        {"graph_entity", "graph_causal", "graph_source_assertion"}
    ),
    "commercial_maturity": frozenset(
        {"graph_commercial", "engine_c_backlog", "engine_c_customer"}
    ),
    "financial_resilience": frozenset(
        {"engine_c_financial", "engine_c_manual"}
    ),
    "valuation_payoff": frozenset(
        {"engine_c_valuation", "market", "fx"}
    ),
}


class AssessmentError(ValueError):
    """Confidence assessment 或其凍結 context 不可安全計算。"""


def _finite(value: Any, *, non_negative: bool = False) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    if not math.isfinite(parsed) or (non_negative and parsed < 0):
        return None
    return parsed


def _string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise AssessmentError(f"{field} must be a list")
    result = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    if len(result) != len(value):
        raise AssessmentError(f"{field} must contain non-empty strings")
    return result


def _validate_assessment(
    assessment: Mapping[str, Any],
    ceilings: Mapping[str, float],
    reference_index: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], tuple[str, ...]]:
    if not isinstance(assessment, Mapping) or set(assessment) != set(AXES):
        raise AssessmentError("assessment must contain exactly the five confidence axes")
    normalized: dict[str, dict[str, Any]] = {}
    blockers: list[str] = []
    for axis in AXES:
        raw = assessment[axis]
        if not isinstance(raw, Mapping):
            raise AssessmentError(f"{axis} must be an object")
        missing_keys = {"level", "evidence_refs", "reason", "missing_data"} - set(raw)
        if missing_keys:
            raise AssessmentError(f"{axis} missing fields: {', '.join(sorted(missing_keys))}")
        level = raw["level"]
        if level not in LEVELS:
            raise AssessmentError(f"{axis}.level is invalid")
        refs = _string_list(raw["evidence_refs"], f"{axis}.evidence_refs")
        missing_data = _string_list(raw["missing_data"], f"{axis}.missing_data")
        reason = raw["reason"]
        if not isinstance(reason, str) or not reason.strip():
            blockers.append(f"{axis}_reason_missing")
        if level == "unknown":
            blockers.append(f"{axis}_unknown")
        elif not refs:
            blockers.append(f"{axis}_evidence_missing")
        elif any(
            not isinstance(reference_index.get(reference), Mapping)
            or not (
                set(reference_index[reference].get("authorities") or ())
                & AXIS_REFERENCE_AUTHORITIES[axis]
            )
            for reference in refs
        ):
            blockers.append(f"assessment_context_mismatch:{axis}")
        if level == "corroborated" and missing_data:
            blockers.append(f"{axis}_corroboration_incomplete")
        context_mismatch = f"assessment_context_mismatch:{axis}" in blockers
        effective_ceiling = 0.0 if (
            context_mismatch
            or any(blocker.startswith(f"{axis}_") for blocker in blockers)
        ) else ceilings[level]
        normalized[axis] = {
            "level": "unknown" if context_mismatch else level,
            "evidence_refs": refs,
            "reason": reason.strip() if isinstance(reason, str) else "",
            "missing_data": missing_data,
            "ceiling": effective_ceiling,
        }
    return normalized, tuple(sorted(set(blockers)))


def _constraint(
    lane: str,
    name: str,
    cap: float,
    authority: str,
    *,
    status: str = "available",
    detail: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "lane": lane,
        "constraint": name,
        "cap_weight": max(0.0, float(cap)),
        "authority": authority,
        "status": status,
        "binding": False,
    }
    if detail:
        item["detail"] = detail
    return item


def _mark_binding(
    trace: list[dict[str, Any]], lane: str, maximum: float
) -> tuple[Mapping[str, Any], ...]:
    for item in trace:
        if item["lane"] == lane and math.isclose(
            item["cap_weight"], maximum, rel_tol=1e-12, abs_tol=1e-12
        ):
            item["binding"] = True
    return tuple(deepcopy(trace))


def _lane_max(trace: Sequence[Mapping[str, Any]], lane: str) -> float:
    caps = [float(item["cap_weight"]) for item in trace if item["lane"] == lane]
    return min(caps) if caps else 0.0


def _level_floor(level: str, ceilings: Mapping[str, float]) -> float:
    index = LEVELS.index(level)
    return 0.0 if index == 0 else ceilings[LEVELS[index - 1]]


def _factor_caps(
    *,
    lane: str,
    current_company_weight: float,
    factor_weights: Mapping[str, Any],
    factor_tags: tuple[str, ...],
    policy_caps: Mapping[str, float],
    trace: list[dict[str, Any]],
    blockers: list[str],
) -> None:
    if not factor_tags:
        blockers.append("factor_mapping_unresolved")
        trace.append(_constraint(lane, "factor_mapping", 0.0, "identity_registry", status="missing"))
        return
    for factor in factor_tags:
        if factor not in policy_caps:
            blockers.append(f"factor_policy_missing:{factor}")
            trace.append(
                _constraint(
                    lane,
                    f"factor:{factor}",
                    0.0,
                    "investment_policy",
                    status="missing",
                )
            )
            continue
        existing = _finite(factor_weights.get(factor, 0.0), non_negative=True)
        if existing is None:
            blockers.append(f"factor_exposure_invalid:{factor}")
            trace.append(
                _constraint(
                    lane,
                    f"factor:{factor}",
                    0.0,
                    "portfolio_snapshot",
                    status="quarantined",
                )
            )
            continue
        total_position_cap = current_company_weight + max(0.0, policy_caps[factor] - existing)
        trace.append(
            _constraint(
                lane,
                f"factor:{factor}",
                total_position_cap,
                "portfolio_snapshot+investment_policy",
            )
        )


def _live_portfolio(
    payload: Mapping[str, Any],
    *,
    registry: IdentityRegistry,
    focus_company_id: str,
    execution_symbol: str,
    research_ticker: str,
    policy_caps: Mapping[str, float],
) -> tuple[float, dict[str, float], list[str], float]:
    holdings = payload["holdings"]
    nav = _finite(holdings.get("nav_base"), non_negative=True)
    if nav is None or nav <= 0:
        return 0.0, {}, ["live_nav_missing"], 0.0
    factor_values: dict[str, float] = {}
    company_values: dict[str, float] = {}
    blockers: list[str] = []
    for row in holdings.get("rows") or []:
        ticker = str(row.get("ticker") or "").upper()
        company_id = row.get("company_id")
        if company_id is None and ticker in {execution_symbol.upper(), research_ticker.upper()}:
            company_id = focus_company_id
        if company_id is None:
            company_id = registry.company_id_for_ticker(ticker)
        value = _finite(row.get("market_value_base"), non_negative=True)
        if company_id is None:
            blockers.append(f"holdings_company_mapping_unresolved:{ticker}")
            continue
        if value is None:
            blockers.append(f"holdings_market_value_missing:{ticker}")
            continue
        company_values[company_id] = company_values.get(company_id, 0.0) + value
        tags = registry.factor_tags(company_id)
        if not tags and value:
            blockers.append(f"holdings_factor_mapping_unresolved:{company_id}")
        for tag in tags:
            if tag not in policy_caps:
                blockers.append(f"factor_policy_missing:{tag}")
            factor_values[tag] = factor_values.get(tag, 0.0) + value
    factor_weights = {factor: value / nav for factor, value in factor_values.items()}
    current = company_values.get(focus_company_id, 0.0) / nav
    return nav, factor_weights, blockers, current


def calculate_probe_limits(
    bundle: ContextBundle,
    coverage: CoverageResult,
    assessment: Mapping[str, Any],
    *,
    policy: Mapping[str, Any] | None = None,
    registry: IdentityRegistry | None = None,
    paper_exposure_override: Mapping[str, Any] | None = None,
) -> ProbeSizingResult:
    """Pure calculation；不保存 decision，也不建立 paper event。"""

    if coverage.cohort_id != bundle.cohort_id or coverage.context_digest != bundle.digest:
        raise AssessmentError("coverage and context bundle do not match")
    current_policy = validate_policy(policy) if policy is not None else load_policy()
    probe = current_policy.get("probe_lane")
    if not isinstance(probe, Mapping):
        raise PolicyError("validated policy has no probe_lane")
    payload = bundle.payload
    if payload.get("policy_version") != current_policy["policy_version"]:
        raise AssessmentError("context policy version does not match calculator policy")
    registry = registry or get_registry()
    reference_index = payload.get("reference_index")
    if not isinstance(reference_index, Mapping):
        reference_index = {}
    axes, assessment_blockers = _validate_assessment(
        assessment,
        probe["axis_ceilings"],
        reference_index,
    )
    weakest_axis = min(AXES, key=lambda axis: (axes[axis]["ceiling"], AXES.index(axis)))
    weakest_level = str(axes[weakest_axis]["level"])
    axis_ceiling = float(axes[weakest_axis]["ceiling"])
    identity = payload["identity"]
    company_id = str(identity.get("company_id") or "")
    execution_symbol = str(identity.get("execution_symbol") or "")
    research_ticker = str(identity.get("research_ticker") or "")
    factor_tags = registry.factor_tags(company_id)
    trace: list[dict[str, Any]] = []

    coverage_cap = probe["single_probe_nav_cap"] if coverage.status == "analyzable" else 0.0
    for lane in ("paper", "live"):
        trace.extend(
            [
                _constraint(lane, "weakest_axis", axis_ceiling, probe["rubric_version"]),
                _constraint(
                    lane,
                    "single_probe_cap",
                    probe["single_probe_nav_cap"],
                    current_policy["policy_version"],
                ),
                _constraint(
                    lane,
                    "coverage_gate",
                    coverage_cap,
                    coverage.assessment_id,
                    status="available" if coverage_cap else "blocked",
                ),
            ]
        )

    paper = paper_exposure_override or payload["paper_exposure"]
    paper_blockers = list(coverage.paper_blockers)
    if identity.get("status") != "resolved" or not company_id:
        paper_blockers.append("identity_unresolved")
    if not coverage.paper_context_ready or paper.get("status") != "available":
        paper_blockers.extend(paper.get("blockers") or ["paper_context_not_ready"])
        trace.append(_constraint("paper", "paper_context", 0.0, bundle.digest, status="blocked"))
    else:
        trace.append(
            _constraint(
                "paper",
                "paper_context",
                probe["single_probe_nav_cap"],
                bundle.digest,
            )
        )
    paper_company_weights = paper.get("company_weights") or {}
    paper_current = _finite(paper_company_weights.get(company_id, 0.0), non_negative=True)
    paper_total = _finite(paper.get("total_weight"), non_negative=True)
    if paper_current is None or paper_total is None:
        paper_blockers.append("paper_exposure_invalid")
        paper_current = 0.0
        trace.append(_constraint("paper", "probe_book_remaining", 0.0, "paper_ledger", status="quarantined"))
    else:
        trace.append(
            _constraint(
                "paper",
                "probe_book_remaining",
                paper_current + max(0.0, probe["probe_book_nav_cap"] - paper_total),
                "paper_ledger+investment_policy",
            )
        )
    _factor_caps(
        lane="paper",
        current_company_weight=paper_current,
        factor_weights=paper.get("factor_weights") or {},
        factor_tags=factor_tags,
        policy_caps=current_policy["factor_exposure_caps"],
        trace=trace,
        blockers=paper_blockers,
    )
    paper_max = _lane_max(trace, "paper")
    if paper_blockers:
        trace.append(_constraint("paper", "paper_lane_blockers", 0.0, bundle.digest, status="blocked"))
        paper_max = 0.0
    paper_floor = min(_level_floor(weakest_level, probe["axis_ceilings"]), paper_max)
    paper_target = paper_max if paper_current > paper_max else (paper_floor + paper_max) / 2.0

    live_blockers = list(coverage.live_blockers)
    if identity.get("status") != "resolved" or not company_id:
        live_blockers.append("identity_unresolved")
    if not coverage.live_context_ready:
        live_blockers.append("live_context_not_ready")
    holdings = payload["holdings"]
    if holdings.get("status") not in {"confirmed", "confirmed_empty"}:
        live_blockers.extend(holdings.get("blockers") or ["holdings_not_confirmed"])
    live_nav, live_factor_weights, portfolio_blockers, live_current = _live_portfolio(
        payload,
        registry=registry,
        focus_company_id=company_id,
        execution_symbol=execution_symbol,
        research_ticker=research_ticker,
        policy_caps=current_policy["factor_exposure_caps"],
    )
    live_blockers.extend(portfolio_blockers)
    _factor_caps(
        lane="live",
        current_company_weight=live_current,
        factor_weights=live_factor_weights,
        factor_tags=factor_tags,
        policy_caps=current_policy["factor_exposure_caps"],
        trace=trace,
        blockers=live_blockers,
    )
    execution_market = payload.get("execution_market") or {}
    execution_fx = payload.get("execution_fx") or {}
    if execution_market.get("status") != "available":
        live_blockers.extend(execution_market.get("blockers") or ["execution_market_missing"])
    if execution_fx.get("status") != "available":
        live_blockers.extend(execution_fx.get("blockers") or ["execution_fx_missing"])
    adv = _finite(execution_market.get("adv20"), non_negative=True)
    price = _finite(execution_market.get("price"), non_negative=True)
    fx_rate = _finite(execution_fx.get("rate"), non_negative=True)
    if live_nav > 0 and adv is not None and price and fx_rate:
        additional_liquidity_weight = (
            adv * probe["live_adv_fraction_cap"] * price * fx_rate / live_nav
        )
        trace.append(
            _constraint(
                "live",
                "execution_adv_1pct",
                live_current + additional_liquidity_weight,
                "execution_market+execution_fx",
            )
        )
    else:
        trace.append(
            _constraint(
                "live",
                "execution_adv_1pct",
                0.0,
                "execution_market+execution_fx",
                status="missing",
            )
        )
    if live_blockers:
        trace.append(_constraint("live", "live_lane_blockers", 0.0, bundle.digest, status="blocked"))
    live_max = _lane_max(trace, "live")
    live_floor = min(_level_floor(weakest_level, probe["axis_ceilings"]), live_max)
    live_range = (live_floor, live_max) if not live_blockers else (0.0, 0.0)
    if live_range[1] > 0 and live_nav > 0 and price and fx_rate:
        live_shares = (
            live_range[0] * live_nav / (price * fx_rate),
            live_range[1] * live_nav / (price * fx_rate),
        )
    else:
        live_shares = None

    trace_tuple = _mark_binding(trace, "paper", paper_max)
    trace = [dict(item) for item in trace_tuple]
    trace_tuple = _mark_binding(trace, "live", live_range[1])
    if paper_blockers:
        paper_status = "DATA_NEEDED"
    elif paper_max <= 0:
        paper_status = "SHADOW_ONLY"
    else:
        paper_status = "ELIGIBLE"
    if live_blockers:
        live_status = "DATA_NEEDED"
    elif live_range[1] <= 0:
        live_status = "SHADOW_ONLY"
    else:
        live_status = "ELIGIBLE"
    if paper_status == "DATA_NEEDED":
        action = "DATA_NEEDED"
    elif paper_max <= 0:
        action = "SHADOW_ONLY"
    elif paper_current > paper_max:
        action = "REDUCE_PAPER"
    elif paper_target > paper_current:
        action = "FUND_PAPER"
    else:
        action = "HOLD_PAPER"
    return ProbeSizingResult(
        cohort_id=bundle.cohort_id,
        context_digest=bundle.digest,
        policy_version=current_policy["policy_version"],
        rubric_version=probe["rubric_version"],
        calculator_version=probe["calculator_version"],
        identity_registry_version=registry.version,
        weakest_axis=weakest_axis,
        axis_ceiling=axis_ceiling,
        axis_results=axes,
        assessment_blockers=assessment_blockers,
        paper_status=paper_status,
        paper_target=paper_target,
        paper_max_supported_position=paper_max,
        paper_current_position=paper_current,
        paper_blockers=tuple(sorted(set(paper_blockers))),
        live_status=live_status,
        live_supported_range=live_range,
        live_supported_shares=live_shares,
        live_current_position=live_current,
        live_blockers=tuple(sorted(set(live_blockers))),
        constraint_trace=trace_tuple,
        action=action,
    )
