"""唯讀輸出 Alpha 候選的市值與分析師覆蓋，供 Daily／alpha-status 消費。

本入口只讀 active Engine C SQLite authority，不寫 schema、不刷新資料，也不輸出
private path。市值先依公司 registry 把交易所報價單位（例如 GBp）換回結算幣別，
再乘流通股數；不同幣別仍分開標示，不假裝已做 FX 換算。
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable, Iterable, TextIO

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine_c.db import DB_TYPE, sqlite_path  # noqa: E402
from identity.currency import resolve_quote_unit  # noqa: E402
from identity.registry import IdentityRegistry, get_registry  # noqa: E402
from storage.relational import (  # noqa: E402
    PrivateStorageError,
    PrivateStorageVerificationUnavailable,
)

SCHEMA_VERSION = "alpha-purity-snapshot.v1"


def _decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _latest_financial(conn: sqlite3.Connection, ticker: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT ticker, snapshot_date, price, shares_outstanding,
               analyst_target_count, fetched_at
        FROM financial_snapshots
        WHERE ticker = ?
        ORDER BY snapshot_date DESC, fetched_at DESC, id DESC
        LIMIT 1
        """,
        (ticker,),
    ).fetchone()


def _latest_coverage(conn: sqlite3.Connection, ticker: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT ticker, observation_date, analyst_count, source, data_status, fetched_at
        FROM consensus_coverage_observations
        WHERE ticker = ?
        ORDER BY observation_date DESC, fetched_at DESC, id DESC
        LIMIT 1
        """,
        (ticker,),
    ).fetchone()


def _registered_tickers(registry: IdentityRegistry) -> list[str]:
    return sorted(
        {
            company.research_ticker.upper()
            for company in registry.companies
            if company.research_ticker
        }
    )


def build_snapshot(
    conn: sqlite3.Connection,
    tickers: Iterable[str],
    *,
    registry: IdentityRegistry,
) -> dict:
    """從既有 Engine C rows 組成 deterministic、無副作用的 purity snapshot。"""

    rows: list[dict] = []
    for raw_ticker in tickers:
        ticker = str(raw_ticker).strip().upper()
        if not ticker:
            continue
        financial = _latest_financial(conn, ticker)
        coverage = _latest_coverage(conn, ticker)
        company_id = registry.company_id_for_ticker(ticker)
        company = registry.company(company_id) if company_id else None
        quote_unit = resolve_quote_unit(
            company.market_quote_unit if company is not None else None
        )

        blockers: list[str] = []
        warnings: list[str] = []
        price = _decimal(financial["price"]) if financial is not None else None
        shares = (
            int(financial["shares_outstanding"])
            if financial is not None and financial["shares_outstanding"] is not None
            else None
        )
        settlement_price: Decimal | None = None
        market_cap: Decimal | None = None
        if financial is None:
            blockers.append("financial_snapshot_missing")
        else:
            if price is None:
                blockers.append("price_missing")
            if shares is None:
                blockers.append("shares_outstanding_missing")
            if quote_unit is None:
                blockers.append("quote_unit_unregistered")
            if price is not None and shares is not None and quote_unit is not None:
                factor = Decimal(str(quote_unit.factor))
                settlement_price = price * factor
                market_cap = settlement_price * shares

        analyst_status = "missing"
        analyst_count: int | None = None
        if coverage is None:
            blockers.append("analyst_coverage_missing")
        else:
            analyst_status = str(coverage["data_status"])
            if analyst_status == "observed":
                analyst_count = int(coverage["analyst_count"])
            else:
                blockers.append("analyst_count_manual_required")

        projected_count = (
            int(financial["analyst_target_count"])
            if financial is not None and financial["analyst_target_count"] is not None
            else None
        )
        if (
            analyst_count is not None
            and projected_count is not None
            and analyst_count != projected_count
        ):
            warnings.append("analyst_count_projection_mismatch")

        rows.append(
            {
                "ticker": ticker,
                "company_id": company_id,
                "snapshot_date": financial["snapshot_date"] if financial else None,
                "price_quote": str(price) if price is not None else None,
                "quote_unit": quote_unit.quote_code if quote_unit else None,
                "settlement_price": (
                    str(settlement_price) if settlement_price is not None else None
                ),
                "settlement_currency": quote_unit.currency if quote_unit else None,
                "shares_outstanding": shares,
                "market_cap": (
                    {
                        "amount": str(market_cap),
                        "currency": quote_unit.currency,
                    }
                    if market_cap is not None and quote_unit is not None
                    else None
                ),
                "analyst_count": analyst_count,
                "analyst_status": analyst_status,
                "analyst_observation_date": (
                    coverage["observation_date"] if coverage else None
                ),
                "analyst_source": coverage["source"] if coverage else None,
                "projection_analyst_target_count": projected_count,
                "status": "ok" if not blockers and not warnings else "degraded",
                "blockers": blockers,
                "warnings": warnings,
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok" if all(row["status"] == "ok" for row in rows) else "degraded",
        "rows": rows,
    }


def _format_decimal(amount: str) -> str:
    value = Decimal(amount)
    absolute = abs(value)
    for divisor, suffix in (
        (Decimal("1000000000000"), "T"),
        (Decimal("1000000000"), "B"),
        (Decimal("1000000"), "M"),
    ):
        if absolute >= divisor:
            return f"{value / divisor:,.2f}{suffix}"
    return f"{value:,.0f}"


def render_markdown(payload: dict) -> str:
    lines = [
        "### Alpha 標的純度（Engine C 唯讀）",
        "",
        "| 標的 | 財務日期 | 市值（結算幣別） | 分析師覆蓋 | 狀態 |",
        "|---|---:|---:|---:|---|",
    ]
    for row in payload["rows"]:
        market_cap = row["market_cap"]
        cap_text = (
            f"{market_cap['currency']} {_format_decimal(market_cap['amount'])}"
            if market_cap
            else "不可用"
        )
        if row["analyst_status"] == "observed":
            analyst_text = str(row["analyst_count"])
        elif row["analyst_status"] == "manual_required":
            analyst_text = "需人工補值（不是 0）"
        else:
            analyst_text = "不可用"
        issues = [*row["blockers"], *row["warnings"]]
        status_text = "正常" if not issues else "降級：" + "、".join(issues)
        lines.append(
            f"| {row['ticker']} | {row['snapshot_date'] or '—'} | "
            f"{cap_text} | {analyst_text} | {status_text} |"
        )
    lines.extend(
        [
            "",
            "市值已把 GBp 等 minor quote unit 換回結算幣別；未做 FX，"
            "不同幣別不得直接當成同一尺度排序。",
        ]
    )
    return "\n".join(lines)


def _failure_payload(failure_class: str, message: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "access_blocked",
        "failure_class": failure_class,
        "message": message,
        "rows": [],
    }


def _render_failure(payload: dict, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(payload, ensure_ascii=False, indent=2)
    return (
        "### Alpha 標的純度（Engine C 唯讀）\n\n"
        f"- `access_blocked`／`{payload['failure_class']}`：{payload['message']}"
    )


def run(
    argv: list[str] | None = None,
    *,
    stdout: TextIO = sys.stdout,
    path_resolver: Callable[[], Path] = sqlite_path,
    registry_resolver: Callable[[], IdentityRegistry] = get_registry,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--tickers", nargs="*", help="只輸出指定 research tickers")
    args = parser.parse_args(argv)

    if DB_TYPE != "sqlite":
        payload = _failure_payload(
            "unsupported_backend",
            "目前固定唯讀入口只支援 SQLite Engine C authority。",
        )
        print(_render_failure(payload, args.format), file=stdout)
        return 2

    try:
        registry = registry_resolver()
        tickers = args.tickers or _registered_tickers(registry)
        authority = path_resolver()
        conn = sqlite3.connect(f"file:{authority.as_posix()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            payload = build_snapshot(conn, tickers, registry=registry)
        finally:
            conn.close()
    except PrivateStorageVerificationUnavailable:
        payload = _failure_payload(
            "private_acl_verification_unavailable",
            "目前執行環境無法檢查 owner-only ACL；已 fail closed，未判定 ACL 不合格。",
        )
        print(_render_failure(payload, args.format), file=stdout)
        return 2
    except PrivateStorageError:
        payload = _failure_payload(
            "private_storage_boundary_rejected",
            "Engine C private storage boundary 拒絕存取。",
        )
        print(_render_failure(payload, args.format), file=stdout)
        return 2
    except (OSError, RuntimeError, sqlite3.Error, ValueError):
        payload = _failure_payload(
            "engine_c_read_failed",
            "Engine C 唯讀 snapshot 產生失敗；未以空值冒充成功。",
        )
        print(_render_failure(payload, args.format), file=stdout)
        return 2

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=stdout)
    else:
        print(render_markdown(payload), file=stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
