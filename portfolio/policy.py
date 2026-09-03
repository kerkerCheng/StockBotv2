"""Versioned beta-monitor policy loader and strict validator。"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping


DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "beta_policy.json"
DEFAULT_TARGET_ALLOCATION_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "target_allocation.json"
)
_SLEEVES = {
    "beta_core",
    "beta_tilt",
    "beta_tilt_active",
    "beta_leverage",
    "large_cap_tilt",
}
# 目標配置多出來的那一格：它在 beta_policy 裡沒有任何 instrument，實際佔比只能由
# 「非現金持股扣掉所有 beta instrument」的殘量導出。名字不寫死在計算裡，
# 由這兩份設定的 sleeve 集合相減得到（見 beta_monitor.build_allocation_gap）。
_TARGET_ONLY_SLEEVES = {"alpha"}


class BetaPolicyError(ValueError):
    """Policy malformed or internally inconsistent。"""


class TargetAllocationError(ValueError):
    """目標配置設定缺漏或內部不一致。"""


def _finite_fraction(value: Any, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BetaPolicyError(f"{field} must be numeric")
    parsed = float(value)
    lower_ok = parsed > 0 if positive else parsed >= 0
    if not math.isfinite(parsed) or not lower_ok or parsed > 1:
        raise BetaPolicyError(f"{field} must be a finite fraction")
    return parsed


def _finite_multiple(value: Any, field: str) -> float:
    """曝險倍數：可以大於 1（1.5x、1.75x），但必須有限且有界。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BetaPolicyError(f"{field} must be numeric")
    parsed = float(value)
    if not math.isfinite(parsed) or not 0 < parsed <= 5:
        raise BetaPolicyError(f"{field} must be a finite multiple within (0, 5]")
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
        "market_data",
        "risk",
        "instruments",
    }
    if set(source) != required:
        raise BetaPolicyError("beta policy top-level fields do not match schema")
    if source.get("schema_version") != "beta-policy-v3":
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

    # 行情鮮度是「這份價格還能不能拿來顯示」的資料品質門檻，與已於 2026-08-29
    # 移除的技術訊號無關，因此獨立成 market_data，不再寄生在 signal 區塊下。
    market_data = source.get("market_data")
    if not isinstance(market_data, Mapping) or set(market_data) != {"max_refresh_age_hours"}:
        raise BetaPolicyError("market_data policy fields do not match schema")
    max_age = market_data.get("max_refresh_age_hours")
    if isinstance(max_age, bool) or not isinstance(max_age, int) or not 24 <= max_age <= 168:
        raise BetaPolicyError("max_refresh_age_hours must be 24..168")

    risk = source.get("risk")
    risk_scalar_keys = {
        "leveraged_nominal_warning",
        "leveraged_nominal_cap",
        "leveraged_effective_warning",
        "leveraged_effective_cap",
        "issuer_concentration_warning",
        "alpha_total_warning",
        "callable_debt_cap",
    }
    multiple_keys = {"total_exposure_warning", "total_exposure_cap"}
    if not isinstance(risk, Mapping) or set(risk) != risk_scalar_keys | multiple_keys | {
        "daily_display_change",
        "event_monitor",
    }:
        raise BetaPolicyError("risk policy fields do not match schema")
    normalized_risk = {
        key: _finite_fraction(
            risk.get(key), key, positive=key != "callable_debt_cap"
        )
        for key in risk_scalar_keys
    }
    # 總曝險以 NAV 的倍數表示，可大於 1，故用另一個驗證器。
    normalized_risk.update(
        {key: _finite_multiple(risk.get(key), key) for key in multiple_keys}
    )
    if normalized_risk["total_exposure_warning"] >= normalized_risk["total_exposure_cap"]:
        raise BetaPolicyError("total_exposure warning must be below cap")
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
        "schema_version": "beta-policy-v3",
        "policy_version": str(source["policy_version"]),
        "mode": "paper_observation",
        "capital_scope": "shared_cash_pool",
        "capital": {
            "cash_bucket_aliases": normalized_cash_aliases,
            "authority_max_age_days": authority_age,
            "fx_max_age_hours": fx_age,
        },
        "market_data": {"max_refresh_age_hours": max_age},
        "risk": normalized_risk,
        "instruments": sorted(normalized_instruments, key=lambda item: item["priority"]),
    }


def load_beta_policy(path: str | Path = DEFAULT_POLICY_PATH) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BetaPolicyError("beta policy must be a JSON object")
    return validate_beta_policy(value)


def _public_keys(source: Mapping[str, Any]) -> set[str]:
    """忽略 `_` 開頭的說明欄位（設定檔裡的長註解），只驗真正的資料欄位。"""

    return {str(key) for key in source if not str(key).startswith("_")}


def validate_target_allocation(source: Mapping[str, Any]) -> dict[str, Any]:
    """驗證目標配置設定；缺格、比例不合 1.0 或缺相關性警告一律 fail closed。"""

    if _public_keys(source) != {
        "schema_version",
        "policy_version",
        "investor_profile",
        "basis",
        "sleeves",
        "correlation_warnings",
        "rebalancing",
    }:
        raise TargetAllocationError("target allocation top-level fields do not match schema")
    if source.get("schema_version") != "target-allocation-v1":
        raise TargetAllocationError("unsupported target allocation schema")
    if not isinstance(source.get("policy_version"), str) or not str(source["policy_version"]).strip():
        raise TargetAllocationError("policy_version must be non-empty text")
    # 分母只有一種：已投入的非現金部位。現金屬 cash floor authority，不佔比例。
    if source.get("basis") != "invested_non_cash":
        raise TargetAllocationError("target allocation basis must be invested_non_cash")
    if not isinstance(source.get("investor_profile"), Mapping):
        raise TargetAllocationError("investor_profile must be an object")

    sleeves = source.get("sleeves")
    if not isinstance(sleeves, Mapping):
        raise TargetAllocationError("sleeves must be an object")
    expected = _SLEEVES | _TARGET_ONLY_SLEEVES
    if _public_keys(sleeves) != expected:
        # 新增 beta sleeve 卻沒補目標比例時，這裡就會擋下來，而不是安靜地
        # 讓那一格永遠算成 0%（那正是會催人多買的方向）。
        raise TargetAllocationError("target allocation must cover each sleeve exactly")
    normalized_sleeves: dict[str, dict[str, Any]] = {}
    for name in sorted(expected):
        spec = sleeves.get(name)
        if not isinstance(spec, Mapping) or not {"target", "band", "role"} <= _public_keys(spec):
            raise TargetAllocationError(f"sleeve {name} fields do not match schema")
        target = _finite_fraction(spec.get("target"), f"sleeve_target:{name}")
        band = _finite_fraction(spec.get("band"), f"sleeve_band:{name}", positive=True)
        normalized_sleeves[name] = {
            "target": target,
            "band": band,
            "role": _text(spec.get("role"), f"sleeve_role:{name}"),
        }
    total = sum(item["target"] for item in normalized_sleeves.values())
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise TargetAllocationError("sleeve targets must sum to 1.0")

    warnings = source.get("correlation_warnings")
    if not isinstance(warnings, list) or not warnings:
        raise TargetAllocationError("correlation_warnings must be a non-empty list")
    normalized_warnings: list[dict[str, str]] = []
    for item in warnings:
        if not isinstance(item, Mapping) or _public_keys(item) != {"name", "detail", "surface_in"}:
            raise TargetAllocationError("correlation warning fields do not match schema")
        normalized_warnings.append(
            {
                "name": _text(item.get("name"), "correlation warning name"),
                "detail": _text(item.get("detail"), "correlation warning detail"),
                "surface_in": _text(item.get("surface_in"), "correlation warning surface_in"),
            }
        )

    rebalancing = source.get("rebalancing")
    if not isinstance(rebalancing, Mapping) or not {"method", "loan_tranche_excluded"} <= _public_keys(
        rebalancing
    ):
        raise TargetAllocationError("rebalancing fields do not match schema")
    if rebalancing.get("method") != "new_money_only":
        raise TargetAllocationError("rebalancing method must remain new_money_only")
    if rebalancing.get("loan_tranche_excluded") is not True:
        raise TargetAllocationError("loan tranches must stay outside automatic rebalancing")

    return {
        "schema_version": "target-allocation-v1",
        "policy_version": str(source["policy_version"]),
        # 只作記錄；本檔的計算不讀它，但保留以便驗證過的視圖可以再驗一次。
        "investor_profile": dict(source["investor_profile"]),
        "basis": "invested_non_cash",
        "sleeves": normalized_sleeves,
        "correlation_warnings": normalized_warnings,
        "rebalancing": {
            "method": "new_money_only",
            "loan_tranche_excluded": True,
        },
    }


def load_target_allocation(
    path: str | Path = DEFAULT_TARGET_ALLOCATION_PATH,
) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TargetAllocationError("target allocation must be a JSON object")
    return validate_target_allocation(value)


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


def instrument_price_key(instrument: Mapping[str, Any]) -> str:
    """回傳該標的「自身價格」在 Engine C 的序列 key。

    槓桿與重疊商品（TQQQ／00631L／006208）在設定裡共用一個 benchmark 分組，
    但它們的行情心跳與相對水位一律取自 provider_symbol 自己的序列，
    絕不冒用 QQQ／0050 的價格表現。
    """

    provider_symbol = str(instrument["provider_symbol"]).upper()
    benchmark_symbol = str(instrument["benchmark_symbol"]).upper()
    if provider_symbol == benchmark_symbol:
        return str(instrument["benchmark_key"])
    return f"price:{str(instrument['ticker']).casefold()}"


def unique_technical_targets(policy: Mapping[str, Any]) -> list[dict[str, str]]:
    """回傳 benchmark 分組序列，加上每檔自身價格序列（去重後的抓取清單）。"""

    result = {
        str(target["benchmark_key"]): dict(target)
        for target in unique_benchmarks(policy)
    }
    for instrument in policy.get("instruments") or []:
        key = instrument_price_key(instrument)
        result.setdefault(
            key,
            {
                "benchmark_key": key,
                "benchmark_symbol": str(instrument["provider_symbol"]),
            },
        )
    return [result[key] for key in sorted(result)]


__all__ = [
    "BetaPolicyError",
    "DEFAULT_POLICY_PATH",
    "DEFAULT_TARGET_ALLOCATION_PATH",
    "TargetAllocationError",
    "instrument_price_key",
    "load_beta_policy",
    "load_target_allocation",
    "unique_benchmarks",
    "unique_technical_targets",
    "validate_beta_policy",
    "validate_target_allocation",
]
