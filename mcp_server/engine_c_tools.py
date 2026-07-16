"""Narrow read-only Engine C helpers for the remote MCP surface."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Mapping

from engine_c import db as engine_db
from engine_c.checklist import get_checklist
from thesis.investment_policy import coverage_policy_view, load_policy, validate_policy


_TICKER = re.compile(r"^[A-Z0-9.^_-]{1,20}$")


def get_financial_checklist_core(
    ticker: str,
    *,
    checklist_getter: Callable[[str], dict[str, Any]] | None = None,
    connection_factory: Callable[[], Any] | None = None,
    sqlite_path: str | Path | None = engine_db._SQLITE_PATH,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return five checklist items, raw coverage, and a query-time policy view."""

    normalized = ticker.strip().upper() if isinstance(ticker, str) else ""
    if not _TICKER.fullmatch(normalized):
        return {
            "ticker": normalized,
            "engine_c_available": False,
            "items": {},
            "gate_pass": False,
            "raw_coverage_observation": None,
            "policy_view": None,
            "note": "ticker 格式無效",
        }

    current_policy = validate_policy(policy) if policy is not None else load_policy()
    unknown_view = coverage_policy_view(None, policy=current_policy)
    if not engine_db._use_postgres() and sqlite_path is not None and not Path(sqlite_path).exists():
        return {
            "ticker": normalized,
            "engine_c_available": False,
            "items": {},
            "gate_pass": False,
            "raw_coverage_observation": None,
            "policy_view": unknown_view,
            "note": f"Engine C SQLite 檔案不存在：{Path(sqlite_path)}",
        }

    getter = checklist_getter or get_checklist
    try:
        checklist = getter(normalized)
    except Exception as exc:
        return {
            "ticker": normalized,
            "engine_c_available": False,
            "items": {},
            "gate_pass": False,
            "raw_coverage_observation": None,
            "policy_view": unknown_view,
            "note": f"財務清單查詢失敗：{type(exc).__name__}: {exc}",
        }

    if not checklist.get("engine_c_available", False):
        return {
            **checklist,
            "raw_coverage_observation": None,
            "policy_view": unknown_view,
        }

    factory = connection_factory or engine_db.get_conn
    conn = None
    try:
        conn = factory()
        observation = engine_db.get_latest_coverage_observation(conn, normalized)
    except Exception as exc:
        observation = None
        coverage_note = f"覆蓋觀測查詢失敗：{type(exc).__name__}: {exc}"
    else:
        coverage_note = None if observation else "尚無分析師覆蓋觀測；請重跑 Engine C ETL"
    finally:
        if conn is not None:
            conn.close()

    count = (
        observation.get("analyst_count")
        if observation and observation.get("data_status") == "observed"
        else None
    )
    result = {
        **checklist,
        "raw_coverage_observation": observation,
        "policy_view": coverage_policy_view(count, policy=current_policy),
    }
    if coverage_note:
        result["coverage_note"] = coverage_note
    return result
