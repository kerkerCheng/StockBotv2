"""外部 market／FX payload 的 fail-closed normalization。"""
from __future__ import annotations

import math
import re
from datetime import datetime, timedelta
from typing import Any, Mapping


def sessions_between(earlier: datetime, later: datetime) -> int:
    """兩個時刻之間隔了幾個交易日（以工作日近似）。

    行情鮮度必須用交易日量測，不能用小時。日線 bar 的 ``as_of`` 是交易日**當地
    午夜**，代表的卻是當天收盤（美股約 20:00 UTC）；拿它當觀測時刻做小時級減法
    等於憑空多算約 20 小時的假過期，36 小時上限實際只剩約 16 小時真實鮮度。
    2026-08-08 實測：三筆 cohort 的決策在**凍結當下即已 stale**，而 stale 會直接
    封鎖 paper lane——等於資料一進來就被自己的鮮度規則廢掉。

    純計算路徑不去抓「最新完整交易日是哪天」，因此用工作日近似。假日會讓容忍度
    多出一天（偏寬鬆），但那遠比現況安全：現況是把每一筆行情都判成 stale。
    真正的交易日 authority 仍在 Engine C 的 TechnicalObservation。
    """

    start = earlier.date()
    end = later.date()
    if end <= start:
        return 0
    sessions = 0
    cursor = start
    while cursor < end:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:
            sessions += 1
    return sessions


def _time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    converted = float(value)
    return converted if math.isfinite(converted) else None


def _quarantined(*blockers: str) -> dict[str, Any]:
    return {"status": "quarantined", "blockers": sorted(set(blockers))}


def normalize_market_snapshot(
    payload: Mapping[str, Any],
    *,
    expected_ticker: str,
    expected_currency: str,
    evaluation_at: str,
    max_age_sessions: float = 2,
) -> dict[str, Any]:
    upstream = payload.get("status")
    if upstream in {"missing", "unavailable"}:
        blockers = list(payload.get("blockers") or [f"market_{upstream}"])
        failure_class = payload.get("failure_class")
        if failure_class == "access_blocked":
            blockers.append("market_access_blocked_retry_required")
        result = {"status": upstream, "blockers": sorted(set(blockers))}
        if isinstance(failure_class, str) and failure_class:
            result["failure_class"] = failure_class
        return result
    blockers: list[str] = []
    if payload.get("ticker") != expected_ticker:
        blockers.append("market_ticker_mismatch")
    if payload.get("currency") != expected_currency:
        blockers.append("market_currency_mismatch")
    price = _finite(payload.get("price"))
    if price is None or price <= 0:
        blockers.append("market_price_invalid")
    elif price > 10_000_000:
        blockers.append("market_price_anomaly")
    adv20 = _finite(payload.get("adv20"))
    if adv20 is None or adv20 < 0 or adv20 > 1e15:
        blockers.append("market_adv_invalid")
    if payload.get("unit_status") != "ok":
        blockers.append("market_unit_unverified")
    as_of = _time(payload.get("as_of"))
    fetched_at = _time(payload.get("fetched_at"))
    evaluation = _time(evaluation_at)
    if as_of is None or fetched_at is None or evaluation is None:
        blockers.append("market_timestamp_invalid")
    elif as_of > max(evaluation, fetched_at):
        # 只有「觀測時間」比 max(operation as-of, 抓取時刻) 還晚才算 future data。
        # fetched_at 幾乎必略晚於 evaluation（先設 as-of 再 fetch 的延遲），不該
        # 因此判 future；as_of 既已被我們抓到，晚於 evaluation、不晚於 fetched_at
        # 也是正常（當日資料）。genuinely future（隔日 as_of）仍會被擋。
        blockers.append("market_timestamp_future")
    if not payload.get("source"):
        blockers.append("market_source_missing")
    if blockers:
        return _quarantined(*blockers)
    assert as_of is not None and evaluation is not None and price is not None
    status = (
        "stale" if sessions_between(as_of, evaluation) > max_age_sessions else "available"
    )
    normalized = {
        "status": status,
        "ticker": expected_ticker,
        "price": price,
        "currency": expected_currency,
        "adv20": adv20,
        "as_of": payload["as_of"],
        "fetched_at": payload["fetched_at"],
        "source": payload["source"],
        "blockers": [] if status == "available" else ["market_stale"],
    }
    # 報價單位不是結算幣別時（LSE 的 GBp 等），保留原始報價供人工核對——
    # price 已是結算幣別金額，少了這三欄就無法回推 provider 實際回傳什麼。
    quote_currency = payload.get("quote_currency")
    quote_price = _finite(payload.get("quote_price"))
    quote_factor = _finite(payload.get("quote_factor"))
    if isinstance(quote_currency, str) and quote_price is not None and quote_factor:
        normalized["quote_currency"] = quote_currency
        normalized["quote_price"] = quote_price
        normalized["quote_factor"] = quote_factor
    return normalized


def normalize_fx_snapshot(
    payload: Mapping[str, Any],
    *,
    expected_pair: str,
    evaluation_at: str,
    max_age_sessions: float = 2,
) -> dict[str, Any]:
    upstream = payload.get("status")
    if upstream in {"missing", "unavailable"}:
        blockers = list(payload.get("blockers") or [f"fx_{upstream}"])
        failure_class = payload.get("failure_class")
        if failure_class == "access_blocked":
            blockers.append("fx_access_blocked_retry_required")
        result = {"status": upstream, "blockers": sorted(set(blockers))}
        if isinstance(failure_class, str) and failure_class:
            result["failure_class"] = failure_class
        return result
    blockers: list[str] = []
    if payload.get("pair") != expected_pair:
        blockers.append("fx_pair_mismatch")
    rate = _finite(payload.get("rate"))
    if rate is None or rate <= 0 or rate > 1e6:
        blockers.append("fx_rate_invalid")
    as_of = _time(payload.get("as_of"))
    fetched_at = _time(payload.get("fetched_at"))
    evaluation = _time(evaluation_at)
    if as_of is None or fetched_at is None or evaluation is None:
        blockers.append("fx_timestamp_invalid")
    elif as_of > max(evaluation, fetched_at):
        # 同 market：fetch 延遲不算 future，只有 observation 晚於 max(eval, fetched)
        # 才是真正的未來資料（見 normalize_market_snapshot 說明）。
        blockers.append("fx_timestamp_future")
    if not payload.get("source"):
        blockers.append("fx_source_missing")
    if blockers:
        return _quarantined(*blockers)
    assert as_of is not None and evaluation is not None and rate is not None
    # FX 與行情同源同語意：provider 回的是 yfinance 日線 bar（`fx/SEKUSD=X`），
    # as_of 標在當地午夜卻代表當日收盤。先前把 FX 留在小時制，理由是「FX 是連續
    # 報價」——那是按概念推理而沒查資料源實際回傳什麼，於是昨天的收盤在 37 小時後
    # 就被判 stale，與行情犯同一個錯（2026-08-08 由 Sivers live 實跑撞出）。
    status = (
        "stale" if sessions_between(as_of, evaluation) > max_age_sessions else "available"
    )
    return {
        "status": status,
        "pair": expected_pair,
        "rate": rate,
        "as_of": payload["as_of"],
        "fetched_at": payload["fetched_at"],
        "source": payload["source"],
        "blockers": [] if status == "available" else ["fx_stale"],
    }
