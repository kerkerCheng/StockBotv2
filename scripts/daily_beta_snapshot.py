"""Fixed local Daily entry: refresh Engine C technicals and render Engine D beta monitor。"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence, TextIO


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from decision_lab.beta_monitor import build_beta_monitor, render_beta_monitor_markdown
from decision_lab.beta_policy import load_beta_policy, unique_benchmarks
from decision_lab.portfolio_risk import append_risk_snapshot, read_latest_risk_snapshot
from engine_c.db import get_conn
from engine_c.etl_technical import refresh_technical_observations
from engine_c.market_data import get_fx_snapshot
from engine_c.technical import latest_technical_status, recent_technical_observations
from fetchers.gsheets import fetch_capital_authority, fetch_portfolio


DEFAULT_RISK_HISTORY_PATH = (
    REPO_ROOT / "library" / "private" / "decision_lab" / "portfolio_risk_snapshots.jsonl"
)


def _portfolio() -> Sequence[Mapping[str, Any]]:
    return fetch_portfolio(strict_operational=True)


def _capital_authority() -> Sequence[Mapping[str, Any]]:
    return fetch_capital_authority()


def run(
    argv: list[str] | None = None,
    *,
    stdout: TextIO | None = None,
    policy: Mapping[str, Any] | None = None,
    conn_factory: Callable[[], Any] = get_conn,
    holdings_fetcher: Callable[[], Sequence[Mapping[str, Any]]] = _portfolio,
    capital_fetcher: Callable[[], Sequence[Mapping[str, Any]]] = _capital_authority,
    fx_fetcher=get_fx_snapshot,
    refresh_fn=refresh_technical_observations,
    risk_history_path: Path | None = None,
) -> int:
    parser = argparse.ArgumentParser(description="Daily beta technical refresh and monitor")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--as-of")
    parser.add_argument("--no-refresh", action="store_true")
    parser.add_argument("--risk-view", choices=("changes", "full"), default="changes")
    parser.add_argument("--no-record-risk", action="store_true")
    args = parser.parse_args(argv)
    output = stdout or sys.stdout
    as_of = args.as_of or datetime.now(timezone.utc).isoformat()
    connection = None
    try:
        resolved_policy = dict(policy or load_beta_policy())
        connection = conn_factory()
        if args.no_refresh:
            refresh = {
                "schema_version": "engine-c-technical-refresh-v1",
                "policy_version": resolved_policy["policy_version"],
                "status": "skipped",
                "observed_count": 0,
                "total_count": len(unique_benchmarks(resolved_policy)),
                "items": [],
            }
        else:
            try:
                refresh = dict(refresh_fn(policy=resolved_policy, conn=connection))
            except Exception:
                refresh = {
                    "schema_version": "engine-c-technical-refresh-v1",
                    "policy_version": resolved_policy["policy_version"],
                    "status": "fatal",
                    "observed_count": 0,
                    "total_count": len(unique_benchmarks(resolved_policy)),
                    "items": [],
                    "blockers": ["technical_refresh_fatal"],
                }
        observations: dict[str, Mapping[str, Any] | None] = {}
        histories: dict[str, Sequence[Mapping[str, Any]]] = {}
        failed_in_memory = {
            str(item["benchmark_key"]): item
            for item in refresh.get("items") or []
            if item.get("observation_id") is None
        }
        for target in unique_benchmarks(resolved_policy):
            key = target["benchmark_key"]
            if refresh.get("status") == "fatal" or key in failed_in_memory:
                observations[key] = {
                    "data_status": "unavailable",
                    "fetched_at": as_of,
                    "blockers": ["technical_refresh_failed"],
                }
                histories[key] = []
                continue
            observations[key] = latest_technical_status(connection, key)
            histories[key] = recent_technical_observations(connection, key, limit=20)
        try:
            holdings = list(holdings_fetcher())
        except Exception:
            holdings = None
        try:
            capital_authority = list(capital_fetcher())
        except Exception:
            capital_authority = None
        history_path = risk_history_path or DEFAULT_RISK_HISTORY_PATH
        previous_risk = read_latest_risk_snapshot(history_path)
        report = build_beta_monitor(
            observations_by_benchmark=observations,
            history_by_benchmark=histories,
            holdings_rows=holdings,
            capital_authority_rows=capital_authority,
            fx_fetcher=fx_fetcher,
            as_of=as_of,
            policy=resolved_policy,
            previous_risk_snapshot=previous_risk,
        )
        recorded = False
        if not args.no_record_risk:
            try:
                recorded = append_risk_snapshot(history_path, report["risk_snapshot"])
            except OSError:
                report["warnings"] = sorted(
                    set(report.get("warnings") or []) | {"risk_history_write_failed"}
                )
        report["risk_history_recorded"] = recorded
        report["refresh"] = {
            key: refresh.get(key)
            for key in ("status", "observed_count", "total_count", "blockers")
            if key in refresh
        }
        if args.format == "json":
            json.dump(
                report,
                output,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            output.write("\n")
        else:
            output.write(
                render_beta_monitor_markdown(report, risk_view=args.risk_view) + "\n"
            )
        return 0
    except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        json.dump(
            {"status": "error", "code": "DAILY_BETA_SNAPSHOT_FATAL"},
            output,
            separators=(",", ":"),
        )
        output.write("\n")
        return 2
    finally:
        if connection is not None:
            connection.close()


def main(argv: list[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
