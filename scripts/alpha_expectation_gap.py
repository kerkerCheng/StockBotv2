"""唯讀輸出 Alpha 候選的「股價已經定價了什麼」，供 alpha-status／Daily 消費。

## 為什麼要有這一支（2026-09-04）

Phase 4（Expectation Gap）的 4a 把 `market_implied_growth`、
`revenue_estimate_next_fy_growth`、`estimate_revision_30d` 都算了出來——**但它們只流進
`alpha research --emit-packet` 產的研究包，那是給 session 讀的**。使用者實際會看的六個
surface（`query/bottleneck.py`、`scripts/alpha_purity_snapshot.py`、`decision_lab today`、
`briefing/*`、alpha-status 與 daily-brief 兩份 SKILL）對這三個欄位的引用次數是 **0**。

於是使用者的原話是：「我原本想看到的是我的消費端有所改變，像是未來定價空間等等，
那些在哪裡？我感覺我看到的東西還是跟以前一樣。」——他說得對，而且是可查證的對。
這是 L13（驗收條件是「產出出現在下游消費者手上」，不是「這一步回傳成功」）在
Phase 4 上的復發：當時驗的是「欄位算得出來、73/73 有覆蓋」。

本支就是那個缺掉的下游消費端。

## ⚠ 這支**不排序**，也不得被拿去排序

`AGENTS.md`：唯一排序權威是 `query/bottleneck.py::rank_bottlenecks()`。本支輸出的順序
**就是呼叫端傳進來的順序**（也就是瓶頸排序的順序），內部不做任何 sort。理由不是潔癖：
估值落差一旦參與排序，它就從「脈絡」變成「訊號」，而那正是 2026-08-01 三次實測後被
整組移除的那類機制。

## ⚠ 兩個成長率**不可相減**，這是刻意的

- `market_implied_eps_growth` 由 `pe_trailing / pe_forward - 1` 導出，是**每股盈餘**成長。
- `revenue_estimate_next_fy_growth` 是分析師的**營收**成長估計。

兩者分母不同（EPS 受利潤率與股數影響，營收不受），相減沒有意義。實例：COHR 的市場隱含
EPS 成長 +244.6%、分析師營收估成長 +38.2%——差值 206 個百分點不代表任何東西，它只反映
「市場預期利潤率大幅擴張」。所以本支**並排呈現、明確拒絕相減**，也不提供合併欄位。

## 不可算就寫不可算，不寫 0

虧損公司沒有 `pe_trailing`、預估仍虧損的 `pe_forward` 是負數——這些是「不知道／不適用」，
**不是「成長 0%」**。每一格都帶得出不可算的理由代碼。
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
from identity.registry import IdentityRegistry, get_registry  # noqa: E402
from storage.relational import (  # noqa: E402
    PrivateStorageError,
    PrivateStorageVerificationUnavailable,
)

SCHEMA_VERSION = "alpha-expectation-gap.v1"

#: 不可算的理由代碼。**封閉字彙**——新增一種不可算就在這裡登記，
#: 讓下游能區分「沒資料」與「這家公司在虧錢」，而不是都看到一個空格。
UNAVAILABLE_REASONS = {
    "financial_snapshot_missing": "Engine C 沒有這檔的財務快照",
    "pe_trailing_missing": "無 trailing PE——公司目前無正的 trailing EPS（多半在虧損）",
    "pe_forward_missing": "無 forward PE",
    "pe_forward_nonpositive": "forward PE 為負——分析師預估下一年度仍虧損，比值無意義",
    "revenue_estimate_missing": "分析師沒有下一年度營收估計",
    "price_missing": "無現價",
    "analyst_target_missing": "無分析師目標價",
}


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
        SELECT ticker, snapshot_date, price, pe_trailing, pe_forward, ev_revenue,
               revenue_estimate_next_fy_growth, revenue_estimate_next_fy_analysts,
               analyst_target_mean, fetched_at
        FROM financial_snapshots
        WHERE ticker = ?
        ORDER BY snapshot_date DESC, fetched_at DESC, id DESC
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


def _implied_eps_growth(
    pe_trailing: Decimal | None, pe_forward: Decimal | None
) -> tuple[Decimal | None, str | None]:
    """`pe_trailing / pe_forward - 1`＝股價已經定價的**每股盈餘**成長。

    直覺：同一個股價下，forward PE 比 trailing PE 低多少，就是市場認為 EPS 要漲多少。
    """
    if pe_trailing is None:
        return None, "pe_trailing_missing"
    if pe_forward is None:
        return None, "pe_forward_missing"
    if pe_forward <= 0:
        return None, "pe_forward_nonpositive"
    return pe_trailing / pe_forward - Decimal(1), None


def build_snapshot(
    conn: sqlite3.Connection,
    tickers: Iterable[str],
    *,
    registry: IdentityRegistry,
) -> dict:
    """組成 deterministic、無副作用的 expectation-gap snapshot。

    ⚠ **順序＝傳進來的順序**，本函式不 sort。見模組 docstring。
    """
    rows: list[dict] = []
    for raw_ticker in tickers:
        ticker = str(raw_ticker).strip().upper()
        if not ticker:
            continue
        financial = _latest_financial(conn, ticker)
        company_id = registry.company_id_for_ticker(ticker)

        unavailable: list[str] = []
        if financial is None:
            rows.append(
                {
                    "ticker": ticker,
                    "company_id": company_id,
                    "snapshot_date": None,
                    "market_implied_eps_growth": None,
                    "analyst_revenue_growth": None,
                    "analyst_revenue_growth_n": None,
                    "ev_revenue": None,
                    "target_vs_price": None,
                    "status": "degraded",
                    "unavailable": ["financial_snapshot_missing"],
                }
            )
            continue

        implied, implied_reason = _implied_eps_growth(
            _decimal(financial["pe_trailing"]), _decimal(financial["pe_forward"])
        )
        if implied_reason:
            unavailable.append(implied_reason)

        rev_growth = _decimal(financial["revenue_estimate_next_fy_growth"])
        if rev_growth is None:
            unavailable.append("revenue_estimate_missing")

        price = _decimal(financial["price"])
        target = _decimal(financial["analyst_target_mean"])
        target_vs_price: Decimal | None = None
        if price is None:
            unavailable.append("price_missing")
        elif target is None:
            unavailable.append("analyst_target_missing")
        elif price > 0:
            # 兩者同為交易所報價單位，比值本身無單位——不需 FX，也不需 quote-unit 換算。
            target_vs_price = target / price - Decimal(1)

        rows.append(
            {
                "ticker": ticker,
                "company_id": company_id,
                "snapshot_date": financial["snapshot_date"],
                "market_implied_eps_growth": (
                    str(implied) if implied is not None else None
                ),
                "analyst_revenue_growth": (
                    str(rev_growth) if rev_growth is not None else None
                ),
                "analyst_revenue_growth_n": financial["revenue_estimate_next_fy_analysts"],
                "ev_revenue": (
                    str(_decimal(financial["ev_revenue"]))
                    if financial["ev_revenue"] is not None
                    else None
                ),
                "target_vs_price": (
                    str(target_vs_price) if target_vs_price is not None else None
                ),
                "status": "ok" if not unavailable else "degraded",
                "unavailable": unavailable,
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok" if all(row["status"] == "ok" for row in rows) else "degraded",
        "note": (
            "market_implied_eps_growth 是**每股盈餘**成長，analyst_revenue_growth 是"
            "**營收**成長；兩者分母不同，**不得相減**，本 payload 也刻意不提供合併欄位。"
        ),
        "rows": rows,
    }


def _pct(raw: str | None) -> str:
    if raw is None:
        return "—"
    return f"{Decimal(raw) * 100:+.1f}%"


def render_markdown(payload: dict) -> str:
    if payload.get("status") == "access_blocked":
        return (
            "### 股價已經定價了什麼（Engine C 唯讀）\n\n"
            f"- `access_blocked`／`{payload['failure_class']}`：{payload['message']}"
        )
    lines = [
        "### 股價已經定價了什麼（Engine C 唯讀）",
        "",
        "| 標的 | 快照日 | 市場隱含 EPS 成長 | 分析師營收估成長 | EV/營收 | 目標價 vs 現價 | 不可算 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in payload["rows"]:
        reasons = "、".join(
            UNAVAILABLE_REASONS.get(code, code) for code in row["unavailable"]
        ) or "—"
        n = row["analyst_revenue_growth_n"]
        rev = _pct(row["analyst_revenue_growth"])
        if row["analyst_revenue_growth"] is not None and n is not None:
            rev = f"{rev}（{n} 位）"
        ev = row["ev_revenue"]
        ev_text = f"{Decimal(ev):.1f}x" if ev is not None else "—"
        lines.append(
            f"| {row['ticker']} | {row['snapshot_date'] or '—'} | "
            f"{_pct(row['market_implied_eps_growth'])} | {rev} | "
            f"{ev_text} | {_pct(row['target_vs_price'])} | {reasons} |"
        )
    lines.extend(
        [
            "",
            "⚠ **前兩欄不可相減。** 左邊是**每股盈餘**成長（由 trailing/forward PE 導出），"
            "右邊是**營收**成長估計；分母不同，差值不代表任何東西——只反映市場對利潤率的預期。",
            "⚠ **本表順序＝瓶頸排序的順序，不由估值重排。** 唯一排序權威是 "
            "`query/bottleneck.py::rank_bottlenecks()`；估值落差一旦參與排序就從脈絡變成訊號。",
            "⚠ **「目標價 vs 現價」是賣方目標價**，不是我們的判斷，也不是報酬預期。",
            "⚠ 「不可算」欄有字就代表那一格是**不知道**，不是 0。",
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
    return render_markdown(payload)


def run(
    argv: list[str] | None = None,
    *,
    stdout: TextIO = sys.stdout,
    path_resolver: Callable[[], Path] = sqlite_path,
    registry_resolver: Callable[[], IdentityRegistry] = get_registry,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument(
        "--tickers", nargs="*",
        help="只輸出指定 research tickers。**順序會被保留**——請照瓶頸排序傳入。",
    )
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
