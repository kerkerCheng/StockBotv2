"""Versioned beta-monitor policy loader and strict validator。"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping


DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "beta_policy.json"
_SLEEVES = {
    "beta_core",
    "beta_tilt",
    "beta_tilt_active",
    "beta_leverage",
    "large_cap_tilt",
}


class BetaPolicyError(ValueError):
    """Policy malformed or internally inconsistent。"""


def _finite_fraction(value: Any, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BetaPolicyError(f"{field} must be numeric")
    parsed = float(value)
    lower_ok = parsed > 0 if positive else parsed >= 0
    if not math.isfinite(parsed) or not lower_ok or parsed > 1:
        raise BetaPolicyError(f"{field} must be a finite fraction")
    return parsed


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BetaPolicyError(f"{field} must be non-empty text")
    return value.strip()


def validate_beta_policy(source: Mapping[str, Any]) -> dict[str, Any]:
    """Return a detached validated view; reject partial or ambiguous policy。"""

    required = {
        "schema_version",
        "policy_version",
        "mode",
        "capital_scope",
        "capital",
        "signal",
        "risk",
        "campaign_budget_fraction_by_sleeve",
        "instruments",
    }
    if set(source) != required:
        raise BetaPolicyError("beta policy top-level fields do not match schema")
    if source.get("schema_version") != "beta-policy-v2":
        raise BetaPolicyError("unsupported beta policy schema")
    if source.get("mode") != "paper_observation":
        raise BetaPolicyError("v1 beta policy must remain paper_observation")
    if source.get("capital_scope") != "shared_cash_pool":
        raise BetaPolicyError("beta capital scope must remain shared_cash_pool")
    _text(source.get("policy_version"), "policy_version")

    capital = source.get("capital")
    if not isinstance(capital, Mapping) or set(capital) != {
        "cash_bucket_aliases",
        "authority_max_age_days",
        "fx_max_age_hours",
    }:
        raise BetaPolicyError("capital policy fields do not match schema")
    aliases = capital.get("cash_bucket_aliases")
    if not isinstance(aliases, list) or not aliases:
        raise BetaPolicyError("cash_bucket_aliases must be a non-empty list")
    normalized_cash_aliases = sorted({_text(item, "cash bucket alias").casefold() for item in aliases})
    authority_age = capital.get("authority_max_age_days")
    fx_age = capital.get("fx_max_age_hours")
    if (
        isinstance(authority_age, bool)
        or not isinstance(authority_age, int)
        or not 1 <= authority_age <= 365
    ):
        raise BetaPolicyError("authority_max_age_days must be 1..365")
    if isinstance(fx_age, bool) or not isinstance(fx_age, int) or not 24 <= fx_age <= 168:
        raise BetaPolicyError("fx_max_age_hours must be 24..168")

    signal = source.get("signal")
    if not isinstance(signal, Mapping) or set(signal) != {
        "allowed_paces",
        "baseline_pace",
        "max_refresh_age_hours",
        "repeat_after_sessions",
        "stretched_above_sma200",
        "tiers",
    }:
        raise BetaPolicyError("signal policy fields do not match schema")
    # 距 200 日均線超過此值時降一級 pace。回撤 tier 只看「跌了多少」，看不出
    # 「跌之前漲了多少」——標的可能距高點 -23% 卻仍在長期趨勢上方 +26%。
    stretched = signal.get("stretched_above_sma200")
    if (
        isinstance(stretched, bool)
        or not isinstance(stretched, (int, float))
        or not 0.0 < float(stretched) <= 1.0
    ):
        raise BetaPolicyError("stretched_above_sma200 must be within (0, 1]")
    paces = signal.get("allowed_paces")
    if not isinstance(paces, list) or sorted(paces) != [0.0, 0.25, 0.5, 1.0]:
        raise BetaPolicyError("allowed_paces must be the closed v1 set")
    # 不受訊號影響的投入下限。2026-08-01 實測：以訊號 gate 自有現金投入，
    # 終值輸給無腦定投 8.5%（QQQ 91.5%、SOXX 91.9%）——市場多數時間在漲，
    # 等回檔等於在上漲期間抱現金。baseline 保證例行投入不被訊號擋掉。
    baseline = signal.get("baseline_pace")
    if isinstance(baseline, bool) or baseline not in set(paces):
        raise BetaPolicyError("baseline_pace must be one of allowed_paces")
    repeat = signal.get("repeat_after_sessions")
    if isinstance(repeat, bool) or not isinstance(repeat, int) or repeat < 1:
        raise BetaPolicyError("repeat_after_sessions must be a positive integer")
    max_age = signal.get("max_refresh_age_hours")
    if isinstance(max_age, bool) or not isinstance(max_age, int) or not 24 <= max_age <= 168:
        raise BetaPolicyError("max_refresh_age_hours must be 24..168")
    tiers = signal.get("tiers")
    if not isinstance(tiers, list) or [item.get("name") for item in tiers if isinstance(item, Mapping)] != [
        "pullback",
        "deep",
        "capitulation",
    ]:
        raise BetaPolicyError("signal tiers must be pullback/deep/capitulation")
    normalized_tiers: list[dict[str, Any]] = []
    for position, item in enumerate(tiers):
        if not isinstance(item, Mapping) or set(item) != {
            "name",
            "drawdown_at_most",
            "rsi_at_most",
            "base_pace",
            "turning_pace",
        }:
            raise BetaPolicyError("signal tier fields do not match schema")
        drawdown = item.get("drawdown_at_most")
        rsi = item.get("rsi_at_most")
        if (
            isinstance(drawdown, bool)
            or not isinstance(drawdown, (int, float))
            or not math.isfinite(float(drawdown))
            or not -1 < float(drawdown) < 0
            or isinstance(rsi, bool)
            or not isinstance(rsi, (int, float))
            or not math.isfinite(float(rsi))
            or not 0 < float(rsi) < 100
        ):
            raise BetaPolicyError("signal tier thresholds are invalid")
        base_pace = float(item.get("base_pace"))
        turning_pace = float(item.get("turning_pace"))
        if base_pace not in paces or turning_pace not in paces or turning_pace < base_pace:
            raise BetaPolicyError("signal tier pace is invalid")
        normalized_tiers.append(
            {
                "name": item["name"],
                "drawdown_at_most": float(drawdown),
                "rsi_at_most": float(rsi),
                "base_pace": base_pace,
                "turning_pace": turning_pace,
            }
        )
    if not (
        normalized_tiers[0]["drawdown_at_most"]
        > normalized_tiers[1]["drawdown_at_most"]
        > normalized_tiers[2]["drawdown_at_most"]
        and normalized_tiers[0]["rsi_at_most"]
        > normalized_tiers[1]["rsi_at_most"]
        > normalized_tiers[2]["rsi_at_most"]
    ):
        raise BetaPolicyError("signal tiers must become stricter with depth")

    risk = source.get("risk")
    risk_scalar_keys = {
        "leveraged_nominal_warning",
        "leveraged_nominal_cap",
        "leveraged_effective_warning",
        "leveraged_effective_cap",
        "issuer_concentration_warning",
        "alpha_total_warning",
    }
    if not isinstance(risk, Mapping) or set(risk) != risk_scalar_keys | {
        "daily_display_change",
        "event_monitor",
    }:
        raise BetaPolicyError("risk policy fields do not match schema")
    normalized_risk = {
        key: _finite_fraction(risk.get(key), key, positive=True)
        for key in risk_scalar_keys
    }
    for prefix in ("leveraged_nominal", "leveraged_effective"):
        if normalized_risk[f"{prefix}_warning"] >= normalized_risk[f"{prefix}_cap"]:
            raise BetaPolicyError(f"{prefix} warning must be below cap")
    display = risk.get("daily_display_change")
    display_keys = {"issuer_weight", "combined_leverage_weight", "alpha_total_weight"}
    if not isinstance(display, Mapping) or set(display) != display_keys:
        raise BetaPolicyError("daily display change fields do not match schema")
    normalized_risk["daily_display_change"] = {
        key: _finite_fraction(display.get(key), f"daily_display_change:{key}", positive=True)
        for key in display_keys
    }
    event_monitor = risk.get("event_monitor")
    if not isinstance(event_monitor, Mapping) or set(event_monitor) != {
        "concentrated_issuer_threshold",
        "return_1d_at_most",
    }:
        raise BetaPolicyError("event monitor fields do not match schema")
    return_floor = event_monitor.get("return_1d_at_most")
    if (
        isinstance(return_floor, bool)
        or not isinstance(return_floor, (int, float))
        or not math.isfinite(float(return_floor))
        or not -1 < float(return_floor) < 0
    ):
        raise BetaPolicyError("event return threshold must be in (-1, 0)")
    normalized_risk["event_monitor"] = {
        "concentrated_issuer_threshold": _finite_fraction(
            event_monitor.get("concentrated_issuer_threshold"),
            "concentrated_issuer_threshold",
            positive=True,
        ),
        "return_1d_at_most": float(return_floor),
    }

    campaign = source.get("campaign_budget_fraction_by_sleeve")
    if not isinstance(campaign, Mapping) or set(campaign) != _SLEEVES:
        raise BetaPolicyError("campaign budget must cover each v1 sleeve exactly")
    normalized_campaign = {
        key: _finite_fraction(value, f"campaign:{key}", positive=True)
        for key, value in campaign.items()
    }

    instruments = source.get("instruments")
    if not isinstance(instruments, list) or not instruments:
        raise BetaPolicyError("instruments must be a non-empty list")
    normalized_instruments: list[dict[str, Any]] = []
    tickers: set[str] = set()
    priorities: set[int] = set()
    alias_owner: dict[str, str] = {}
    benchmark_symbols: dict[str, str] = {}
    instrument_keys = {
        "ticker",
        "sheet_aliases",
        "provider_symbol",
        "benchmark_key",
        "benchmark_symbol",
        "sleeve",
        "allocation_group",
        "leverage_multiple",
        "issuer_loads",
        "priority",
    }
    for raw in instruments:
        if not isinstance(raw, Mapping) or set(raw) != instrument_keys:
            raise BetaPolicyError("instrument fields do not match schema")
        ticker = _text(raw.get("ticker"), "instrument ticker").upper()
        if ticker in tickers:
            raise BetaPolicyError("duplicate instrument ticker")
        tickers.add(ticker)
        sleeve = _text(raw.get("sleeve"), "instrument sleeve")
        if sleeve not in _SLEEVES:
            raise BetaPolicyError("unknown instrument sleeve")
        leverage = raw.get("leverage_multiple")
        if (
            isinstance(leverage, bool)
            or not isinstance(leverage, (int, float))
            or not math.isfinite(float(leverage))
            or not 1 <= float(leverage) <= 3
            or (sleeve == "beta_leverage") != (float(leverage) > 1)
        ):
            raise BetaPolicyError("instrument leverage/sleeve mismatch")
        priority = raw.get("priority")
        if isinstance(priority, bool) or not isinstance(priority, int) or priority <= 0 or priority in priorities:
            raise BetaPolicyError("instrument priority must be unique and positive")
        priorities.add(priority)
        raw_aliases = raw.get("sheet_aliases")
        if not isinstance(raw_aliases, list) or not raw_aliases:
            raise BetaPolicyError("sheet_aliases must be non-empty")
        sheet_aliases = sorted({_text(item, "sheet alias").upper() for item in raw_aliases})
        if ticker not in sheet_aliases:
            raise BetaPolicyError("canonical ticker must be one sheet alias")
        for alias in sheet_aliases:
            if alias in alias_owner and alias_owner[alias] != ticker:
                raise BetaPolicyError("sheet alias belongs to multiple instruments")
            alias_owner[alias] = ticker
        benchmark_key = _text(raw.get("benchmark_key"), "benchmark_key").casefold()
        benchmark_symbol = _text(raw.get("benchmark_symbol"), "benchmark_symbol").upper()
        existing_symbol = benchmark_symbols.setdefault(benchmark_key, benchmark_symbol)
        if existing_symbol != benchmark_symbol:
            raise BetaPolicyError("one benchmark_key maps to multiple symbols")
        issuer_loads = raw.get("issuer_loads")
        if not isinstance(issuer_loads, Mapping):
            raise BetaPolicyError("issuer_loads must be an object")
        normalized_loads = {
            _text(issuer, "issuer key").upper(): _finite_fraction(load, f"issuer_load:{issuer}")
            for issuer, load in issuer_loads.items()
        }
        normalized_instruments.append(
            {
                "ticker": ticker,
                "sheet_aliases": sheet_aliases,
                "provider_symbol": _text(raw.get("provider_symbol"), "provider_symbol").upper(),
                "benchmark_key": benchmark_key,
                "benchmark_symbol": benchmark_symbol,
                "sleeve": sleeve,
                "allocation_group": _text(raw.get("allocation_group"), "allocation_group").casefold(),
                "leverage_multiple": float(leverage),
                "issuer_loads": normalized_loads,
                "priority": priority,
            }
        )

    return {
        "schema_version": "beta-policy-v2",
        "policy_version": str(source["policy_version"]),
        "mode": "paper_observation",
        "capital_scope": "shared_cash_pool",
        "capital": {
            "cash_bucket_aliases": normalized_cash_aliases,
            "authority_max_age_days": authority_age,
            "fx_max_age_hours": fx_age,
        },
        "signal": {
            "allowed_paces": [0.0, 0.25, 0.5, 1.0],
            "max_refresh_age_hours": max_age,
            "repeat_after_sessions": repeat,
            "baseline_pace": float(baseline),
            "stretched_above_sma200": float(stretched),
            "tiers": normalized_tiers,
        },
        "risk": normalized_risk,
        "campaign_budget_fraction_by_sleeve": normalized_campaign,
        "instruments": sorted(normalized_instruments, key=lambda item: item["priority"]),
    }


def load_beta_policy(path: str | Path = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BetaPolicyError("beta policy must be a JSON object")
    return validate_beta_policy(value)


def unique_benchmarks(policy: Mapping[str, Any]) -> list[dict[str, str]]:
    """Return one stable fetch target per benchmark key。"""

    result: dict[str, dict[str, str]] = {}
    for instrument in policy.get("instruments") or []:
        key = str(instrument["benchmark_key"])
        result.setdefault(
            key,
            {
                "benchmark_key": key,
                "benchmark_symbol": str(instrument["benchmark_symbol"]),
            },
        )
    return [result[key] for key in sorted(result)]


__all__ = [
    "BetaPolicyError",
    "DEFAULT_POLICY_PATH",
    "load_beta_policy",
    "unique_benchmarks",
    "validate_beta_policy",
]
