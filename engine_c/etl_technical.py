"""Refresh fixed-universe TechnicalObservation rows in Engine C。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from portfolio.policy import load_beta_policy, unique_technical_targets
from engine_c.db import DB_TYPE, get_conn
from engine_c.technical import (
    append_technical_observation,
    fetch_technical_observation,
    reconcile_twse_freshness,
)
from engine_c.twse import fetch_twse_latest_rows, twse_code


TechnicalFetcher = Callable[[str, str], Mapping[str, Any]]
TwseFetcher = Callable[[], Mapping[str, Mapping[str, Any]]]


def refresh_technical_observations(
    *,
    policy: Mapping[str, Any] | None = None,
    fetcher: TechnicalFetcher = fetch_technical_observation,
    twse_fetcher: TwseFetcher | None = None,
    conn=None,
) -> dict[str, Any]:
    """Refresh every signal and instrument-price series; failures stay isolated。"""

    resolved_policy = dict(policy or load_beta_policy())
    targets = unique_technical_targets(resolved_policy)
    owns_connection = conn is None
    connection = conn or get_conn()
    items: list[dict[str, Any]] = []
    twse_symbols = [
        str(target["benchmark_symbol"])
        for target in targets
        if twse_code(str(target["benchmark_symbol"])) is not None
    ]
    twse_rows: Mapping[str, Mapping[str, Any]] = {}
    twse_status = "not_required"
    twse_error: str | None = None
    # Custom fetchers are used by deterministic tests and callers that already
    # own their transport.  The scheduled/default path owns the official check.
    if twse_symbols and (fetcher is fetch_technical_observation or twse_fetcher is not None):
        try:
            twse_rows = dict((twse_fetcher or fetch_twse_latest_rows)())
            twse_status = "ok"
        except Exception as exc:
            twse_status = "unavailable"
            twse_error = type(exc).__name__
    elif twse_symbols:
        twse_status = "skipped_custom_fetcher"
    try:
        for target in targets:
            key = target["benchmark_key"]
            symbol = target["benchmark_symbol"]
            try:
                observation = dict(fetcher(key, symbol))
                if twse_code(str(symbol)) is not None and twse_status != "skipped_custom_fetcher":
                    reference = twse_rows.get(twse_code(str(symbol)) or "")
                    observation = reconcile_twse_freshness(
                        observation,
                        reference=reference,
                        oracle_error=twse_error or (None if reference else "twse_symbol_missing"),
                        provider_symbol=str(symbol),
                    )
                twse_reference = observation.pop("_twse_reference", None)
                observation_id = append_technical_observation(
                    connection, observation, commit=False
                )
                connection.commit()
                items.append(
                    {
                        "benchmark_key": key,
                        "benchmark_symbol": symbol,
                        "observation_id": observation_id,
                        "data_status": observation["data_status"],
                        "session_date": observation.get("session_date"),
                        "blockers": list(observation.get("blockers") or []),
                        "warnings": list(observation.get("warnings") or []),
                        "twse_reference": twse_reference,
                    }
                )
            except Exception:
                connection.rollback()
                items.append(
                    {
                        "benchmark_key": key,
                        "benchmark_symbol": symbol,
                        "observation_id": None,
                        "data_status": "unavailable",
                        "session_date": None,
                        "blockers": ["technical_refresh_failed"],
                        "warnings": [],
                        "twse_reference": None,
                    }
                )
    finally:
        if owns_connection:
            connection.close()
    observed = sum(item["data_status"] == "observed" for item in items)
    statuses = {str(item["data_status"]) for item in items}
    run_status = (
        "ok"
        if observed == len(items)
        else "partial"
        if statuses <= {"observed", "insufficient_history"}
        else "degraded"
    )
    return {
        "schema_version": "engine-c-technical-refresh-v1",
        "policy_version": resolved_policy["policy_version"],
        "backend": DB_TYPE,
        "status": run_status,
        "observed_count": observed,
        "total_count": len(items),
        "items": items,
        "twse_freshness": {
            "status": twse_status,
            "source": "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
            "symbols": twse_symbols,
            "reference_count": len(twse_rows),
            "error": twse_error,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh Engine C beta technical observations")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args(argv)
    try:
        result = refresh_technical_observations()
    except Exception:
        print(json.dumps({"status": "error", "code": "TECHNICAL_REFRESH_FATAL"}))
        return 2
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    else:
        print(
            f"technical refresh {result['status']}: "
            f"{result['observed_count']}/{result['total_count']} observed"
        )
        for item in result["items"]:
            blockers = ",".join(item["blockers"]) or "none"
            print(
                f"- {item['benchmark_key']} {item['data_status']} "
                f"session={item['session_date'] or 'none'} blockers={blockers}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
