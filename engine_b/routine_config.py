"""Daily routine 的 deterministic budget 與 tracked-universe 設定。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "daily_routine.json"
DEFAULT_LIFECYCLE = ROOT / "thesis" / "lifecycle.json"


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1":
        raise ValueError("daily routine config schema_version 必須是 1")
    pq1 = payload.get("pq1")
    if not isinstance(pq1, dict):
        raise ValueError("daily routine config 缺少 pq1")
    limit = pq1.get("drain_limit_per_run")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
        raise ValueError("pq1.drain_limit_per_run 必須是 1..20 的整數")
    sources = pq1.get("tracked_ticker_sources")
    if not isinstance(sources, dict):
        raise ValueError("pq1.tracked_ticker_sources 必須是 object")
    for key in ("thesis_lifecycle", "decision_cohorts"):
        if not isinstance(sources.get(key), bool):
            raise ValueError(f"tracked_ticker_sources.{key} 必須是 boolean")
    return payload


def lifecycle_tickers(path: Path = DEFAULT_LIFECYCLE) -> frozenset[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return frozenset()
    tickers: set[str] = set()
    for entry in payload.values() if isinstance(payload, dict) else ():
        if not isinstance(entry, Mapping) or entry.get("status") == "retired":
            continue
        ticker = str(entry.get("ticker") or "").strip().upper()
        if ticker:
            tickers.add(ticker)
    return frozenset(tickers)


def cohort_tickers(rows: Iterable[Mapping[str, Any]]) -> frozenset[str]:
    terminal = {"promoted", "rejected", "expired"}
    return frozenset(
        ticker
        for row in rows
        if str(row.get("lifecycle_status") or "") not in terminal
        if (ticker := str(row.get("research_ticker") or "").strip().upper())
    )


def discover_tracked_tickers(
    config: Mapping[str, Any],
    *,
    lifecycle_path: Path = DEFAULT_LIFECYCLE,
) -> frozenset[str]:
    sources = config["pq1"]["tracked_ticker_sources"]
    tickers: set[str] = set()
    if sources["thesis_lifecycle"]:
        tickers.update(lifecycle_tickers(lifecycle_path))
    if sources["decision_cohorts"]:
        try:
            from decision_lab.bootstrap import open_default_store

            store = open_default_store()
            try:
                rows = store.list_operational_cohorts(
                    as_of=datetime.now(timezone.utc).isoformat()
                )
            finally:
                store.close()
            tickers.update(cohort_tickers(rows))
        except Exception:
            # Private store 尚未建立或暫時不可讀時，lifecycle 仍可提供安全降級。
            pass
    return frozenset(tickers)
