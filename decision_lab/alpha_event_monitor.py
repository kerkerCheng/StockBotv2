"""Alpha live 部位的事件監控。

Beta lane 的 `portfolio_risk.event_search_requests()` 走 `config/beta_policy.json`
的 `instruments`，要求 `leverage_multiple == 1.0`、`issuer_loads[issuer] == 1.0`
與 issuer 曝險 >= 20%。那組判準對 beta 合理（少數大權重 ETF），對 alpha 則
**結構上永遠不會觸發**：alpha 標的根本不在 `instruments` 裡，連 monitor 都建不
出來；就算建得出來，單筆 5% 上限也永遠碰不到 20% 門檻。

2026-08-18 開出系統第一筆真實 alpha 部位（COHR 10 股 @ US$316.23，約 0.732% NAV）
之後，08-18 單日 -12.75%、08-19 -6.19%、08-24 -4.85%，系統全程沒有任何路徑會發現。
依 L14（未經量測的機制不得享有默認信任，gate 也不例外）第 4 點的三個免 outcome
測試，那是「恆滅」——觸發率恆為 0，鑑別力與恆亮的閘門同樣是零。

本模組把觸發條件 keyed 在「**這個 cohort 有沒有 live fill**」，不是曝險占比。
其餘語意刻意與 beta 對齊，維持單一心智模型：單日報酬**首次**跨越門檻才發一次
packet；packet 是 ephemeral 的 WebSearch 提示，`persistence=none`、
`authority_effect=none`——不建 lead、不進 pq1/pq2、不寫 Engine A、不寫 Engine C、
不改任何資本閘門。使用者要深挖仍走 `skills/lead-intake`。

⚠ **行情不取自 Engine C `technical_observations`。** 2026-08-25 查證：該表只涵蓋
`config/beta_policy.json` 的 14 個 benchmark（QQQ／SOXX／TSMC／NVDA…），alpha 標的
一筆都沒有，COHR 亦然。因此這裡比照 `scripts/outcome_if_settled_today.py` 直接取
provider 已收盤序列，唯讀、不寫 Engine C——與 packet 本身 `persistence=none` 的
定位一致。序列由呼叫端注入（`series_by_ticker`），純函式好測；抓取放
`fetch_close_series()`，失敗只降級不阻斷 brief。
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any, Iterable, Mapping, Sequence

__all__ = [
    "alpha_event_search_requests",
    "fetch_close_series",
]


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _returns(series: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """把 {session_date, close} 序列轉成帶 return_1d 的清單，最新在前。

    只用**相鄰兩個已收盤 session** 算報酬，缺值直接跳過該日而不內插——內插會造出
    一個市場上不存在的價格，然後拿它去比門檻。
    """

    ordered = sorted(
        (
            {"session_date": str(row["session_date"]), "close": close}
            for row in series
            if (close := _finite(row.get("close"))) is not None and close > 0
        ),
        key=lambda row: row["session_date"],
    )
    out: list[dict[str, Any]] = []
    for index in range(1, len(ordered)):
        previous = ordered[index - 1]["close"]
        current = ordered[index]["close"]
        out.append(
            {
                "session_date": ordered[index]["session_date"],
                "close": current,
                "return_1d": current / previous - 1.0,
            }
        )
    out.reverse()
    return out


def alpha_event_search_requests(
    positions: Iterable[Mapping[str, Any]],
    *,
    series_by_ticker: Mapping[str, Sequence[Mapping[str, Any]]],
    policy: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """對每個開著的 alpha live 部位，在單日報酬首次跌破門檻時產生一筆 packet。

    「首次」的定義與 beta 相同：**前一個 session 也在門檻以下就不重發**，避免一段
    連續下跌每天都問一次。回補的是「這件事發生了」，不是每日行情播報——逐日行情
    已由 Beta 呈現契約的主力逐檔表負責。
    """

    monitor = policy.get("live_position_monitor")
    if not isinstance(monitor, Mapping):
        # 沒登記門檻就不監控，而不是自己挑一個數字：一個沒人決定過的門檻
        # 會安靜地決定使用者看不看得到部位出事。
        return []
    floor = _finite(monitor.get("return_1d_at_most"))
    if floor is None:
        return []

    requests: list[dict[str, Any]] = []
    for position in positions:
        ticker = str(position.get("ticker") or "").strip()
        if not ticker:
            # 未上市／未登記 ticker（如 co:agility_robotics）沒有行情可監控。
            continue
        history = _returns(series_by_ticker.get(ticker) or ())
        if len(history) < 2:
            continue
        current, previous = history[0], history[1]
        current_return = _finite(current.get("return_1d"))
        previous_return = _finite(previous.get("return_1d"))
        if current_return is None or current_return > floor:
            continue
        if previous_return is not None and previous_return <= floor:
            continue

        entry_price = _finite(position.get("entry_price"))
        latest_close = _finite(current.get("close"))
        since_entry = (
            latest_close / entry_price - 1.0
            if entry_price and latest_close and entry_price > 0
            else None
        )
        session_date = str(current.get("session_date") or "")
        requests.append(
            {
                "schema_version": "alpha-live-position-event-search-v1",
                "lane": "alpha",
                "cohort_id": position.get("cohort_id"),
                "company_id": position.get("company_id"),
                "ticker": ticker,
                "session_date": session_date or None,
                "return_1d": current_return,
                "trigger": f"return_1d<={floor}",
                "trigger_basis": "live_fill_exists",
                "position_weight": position.get("selected_weight"),
                "shares": position.get("shares"),
                "entry_price": entry_price,
                "entry_currency": position.get("currency"),
                "latest_close": latest_close,
                "return_since_entry": since_entry,
                "search_query": (
                    f"{ticker} stock price drop {session_date} reason "
                    "official filing company announcement"
                ).strip(),
                "verification_status": "unverified",
                "persistence": "none",
                "authority_effect": "none",
            }
        )
    return requests


def fetch_close_series(
    tickers: Iterable[str],
    *,
    sessions: int,
    today: date | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """取 provider 已收盤日線 {ticker: [{session_date, close}]}。

    ⚠ 只取**已收盤**的交易日。盤中價與收盤價混在同一條序列會讓單日報酬時而是
    「昨收到現價」、時而是「昨收到今收」——一個欄位兩種語意（L12），而門檻比較
    無從分辨。yfinance 的日線在盤中會回一根未結算的當日 bar，因此丟掉最後一根
    session_date == 今天的資料。

    任何 ticker 抓取失敗只是該 ticker 沒有序列（呼叫端會因 `len(history) < 2`
    自然跳過），不拋例外——事件監控是加值訊號，不該讓整份 brief 失敗。
    """

    symbols = [str(ticker).strip() for ticker in tickers if str(ticker).strip()]
    if not symbols:
        return {}
    try:
        import yfinance as yf
    except ImportError:
        return {}

    # 交易日約占日曆日的 7 成，抓寬一點再截尾，免得遇到連假拿不滿 sessions 根。
    period_days = max(int(sessions) * 2 + 10, 20)
    cutoff = today or date.today()
    out: dict[str, list[dict[str, Any]]] = {}
    for symbol in symbols:
        try:
            history = yf.Ticker(symbol).history(period=f"{period_days}d")["Close"]
        except Exception:  # noqa: BLE001 — provider 失敗只降級成「沒有序列」
            continue
        rows = [
            {"session_date": timestamp.date().isoformat(), "close": float(close)}
            for timestamp, close in history.items()
            if close == close  # NaN guard
        ]
        rows = [row for row in rows if row["session_date"] < cutoff.isoformat()]
        if rows:
            out[symbol] = rows[-int(sessions) :]
    return out
