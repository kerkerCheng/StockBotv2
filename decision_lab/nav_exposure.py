"""持股 NAV 比例呈現——純數字，零門檻。

系統終點是瓶頸度排序，不給額度（見 `docs/plans/2026-08-28-001-refactor-bottleneck-
ranking-terminus-plan.md`）。這個模組是反向的那一半：只回答「我現在持有什麼、各佔多少」，
失衡與否由使用者看數字自己判斷。

⚠ 本模組刻意**不產生任何門檻、警示或建議**（R13）。那正是這次重構要從系統終點移除的
東西；若 NAV 呈現偷偷長出 cap 或 warning，等於讓資本語意從另一個門回來（KTD5）。
`tests/test_nav_exposure.py` 有一條斷言直接掃輸出裡的禁用字。

資料來源用 `fetchers.gsheets.fetch_portfolio(strict_operational=True)` 的 **raw 層**，
不是 `engine_d_runtime.adapters.current_holdings` 的正規化層——後者只拿 `bucket` 判斷
是否為現金列，判完就丟掉，而 bucket 分布正是 R12 要的東西。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

# 現金 bucket 的判定沿用 adapters 的同一份字彙，不另寫一份：同一個分類在兩處各自
# 維護，遲早會在某一邊漏掉一個標籤，而那會讓現金被算成標的曝險（L16）。
from engine_d_runtime.adapters import _CASH_BUCKET_LABELS

UNCLASSIFIED_BUCKET = "未分類"
UNGROUPED = "未分組"


def _is_cash(row: Mapping[str, Any]) -> bool:
    bucket = row.get("bucket")
    if isinstance(bucket, str) and bucket.strip().lower() in _CASH_BUCKET_LABELS:
        return True
    return bool(row.get("is_cash"))


def _bucket_label(row: Mapping[str, Any]) -> str:
    bucket = row.get("bucket")
    if isinstance(bucket, str) and bucket.strip():
        return bucket.strip()
    return UNCLASSIFIED_BUCKET


def _value(row: Mapping[str, Any]) -> float:
    raw = row.get("market_value_base")
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _nav_base(rows: Sequence[Mapping[str, Any]]) -> float | None:
    for row in rows:
        raw = row.get("nav_base")
        if raw in (None, ""):
            continue
        try:
            nav = float(raw)
        except (TypeError, ValueError):
            continue
        if nav > 0:
            return nav
    return None


def build_nav_exposure(
    rows: Sequence[Mapping[str, Any]] | None,
    *,
    upstream: Mapping[str, Any] | None = None,
    groups: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """把持股列轉成 NAV 佔比、bucket 分布與相關性分組。

    `upstream` 是持股取得端的狀態（`adapters.current_holdings` 的回傳）。取得失敗時
    把 `failure` 與 `blockers` 原樣帶出來——否則使用者看到的是「你什麼都沒持有」，
    而不是「持股讀不到」，那正是 2026-08-28 讓一次 Sheet 瞬時失敗被讀成研究不足的形狀。

    `groups` 是 ticker → 分組名的對照；未列出的非現金部位歸「未分組」，不猜測。
    """
    if upstream is not None and upstream.get("status") not in (None, "available", "confirmed", "confirmed_empty"):
        result: dict[str, Any] = {
            "status": str(upstream.get("status")),
            "positions": [],
            "cash_pct": 0.0,
            "buckets": {},
            "groups": {},
            "blockers": list(upstream.get("blockers") or []),
        }
        failure = upstream.get("failure")
        if isinstance(failure, str) and failure:
            result["failure"] = failure
        return result

    rows = list(rows or [])
    nav = _nav_base(rows)
    if not rows or nav is None:
        return {
            "status": "unavailable",
            "positions": [],
            "cash_pct": 0.0,
            "buckets": {},
            "groups": {},
            "blockers": ["holdings_nav_missing"] if rows else ["holdings_unavailable"],
        }

    positions: list[dict[str, Any]] = []
    cash_value = 0.0
    buckets: defaultdict[str, float] = defaultdict(float)
    grouped: defaultdict[str, float] = defaultdict(float)
    group_map = dict(groups or {})

    for row in rows:
        value = _value(row)
        buckets[_bucket_label(row)] += value / nav
        if _is_cash(row):
            cash_value += value
            continue
        ticker = str(row.get("ticker") or row.get("symbol") or "").strip()
        pct = value / nav
        positions.append(
            {
                "ticker": ticker,
                "bucket": _bucket_label(row),
                "market_value_base": value,
                "nav_pct": pct,
            }
        )
        grouped[group_map.get(ticker, UNGROUPED)] += pct

    positions.sort(key=lambda p: p["nav_pct"], reverse=True)

    return {
        "status": "available",
        "nav_base": nav,
        "base_currency": next(
            (str(r["base_currency"]) for r in rows if r.get("base_currency")), None
        ),
        "positions": positions,
        "cash_pct": cash_value / nav,
        "buckets": dict(buckets),
        "groups": dict(grouped),
        "blockers": [],
    }


# ⚠ 取數不在這一層。`decision_lab` 不得 import `fetchers`／`engine_c`／`neo4j`
# （`tests/test_engine_d_runtime.py::test_decision_lab_does_not_import_concrete_
# current_state_authorities` 守這條線）：這一層只做純轉換，持股列由呼叫端注入。
# 實際從 Google Sheet 取數的入口在 `engine_d_runtime.adapters.fetch_nav_exposure`。
