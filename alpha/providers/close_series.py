"""已收盤日線序列的 provider（yfinance 唯讀）。

從 `alpha/position_events.py` 分出來的抓取段：那一支必須維持零外部相依才能離線
測試（`FORBIDDEN_IN_ALPHA` 含 `yfinance`），而 I/O 的家在 `alpha/providers/`。
純函式與抓取分開之後兩邊都變嚴格——判斷邏輯可以完全用注入序列測，抓取失敗
只降級成「這個 ticker 沒有序列」。
"""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable

__all__ = ["fetch_close_series"]


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
