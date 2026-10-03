"""已收盤日線序列的 provider（yfinance 唯讀），以及「最後一根 K 棒收盤了沒」的**唯一 owner**。

從 `alpha/position_events.py` 分出來的抓取段：那一支必須維持零外部相依才能離線
測試（`FORBIDDEN_IN_ALPHA` 含 `yfinance`），而 I/O 的家在 `alpha/providers/`。
純函式與抓取分開之後兩邊都變嚴格——判斷邏輯可以完全用注入序列測，抓取失敗
只降級成「這個 ticker 沒有序列」。

⚠ 2026-10-03（Phase 6 Step 6.7c；Phase 5 #12）：在台北白天互動跑追蹤表，歐股與台股會取到**盤中尚未收盤**的當日 K 棒
（yfinance 回進行中的值）；本檔原本只丟「日期＝台北今天」的那根，美股盤中（台北凌晨）的當日 K 棒日期是美東昨天、照樣混進來。
改成一個 owner（`bar_state`／`closed_points`）：日期＝**交易所當地**今天、且現在早於 yfinance
`history_metadata.currentTradingPeriod.regular.end` → 拿掉那一根並計數；拿不到交易時段 → 保留並計數「收盤狀態未知」（不靜默丟）。
追蹤表三支取價（`scripts/outcome_if_settled_today.py`）與帳號計分表（`engine_b/account_scorecard.py`）都走這裡。
daily 05:30 各市場都已收盤，輸出不變。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, MutableMapping

__all__ = ["BAR_STATE_LABELS", "bar_state", "closed_points", "closing_bars_line", "fetch_close_series",
           "summarize_bar_states"]

#: 最後一根 K 棒的收盤狀態（封閉字彙）。取價端每檔記一個，呼叫端計數——拿掉的與說不出的都要數得到（INV-3）。
BAR_STATE_LABELS: Mapping[str, str] = {
    "closed": "最後一根是已收盤的交易日",
    "dropped_unfinished": "最後一根是交易所當地今天、現在還沒到收盤——盤中未收盤，拿掉",
    "close_unknown": "最後一根是交易所當地今天（或時戳沒有時區）、但說不出收盤了沒——保留並計數",
}


def bar_state(last_stamp: Any, metadata: Mapping[str, Any] | None, *, now: datetime | None = None) -> str:
    """最後一根 K 棒收盤了沒（`BAR_STATE_LABELS` 三選一）。

    - 日期不是**交易所當地**今天 → `closed`（那個交易日已經過去；`last_stamp` 是 yfinance 日線時戳，帶交易所時區）。
    - 是今天：讀 `currentTradingPeriod.regular` 的 start／end（epoch 秒）。交易時段是同一天 → 現在早於 end 才是
      `dropped_unfinished`；交易時段已經是之後的交易日（Yahoo 滾到下一段）→ 今天那根已收（`closed`）；
      交易時段比那根還早、或拿不到 → `close_unknown`。時戳沒有時區（說不出交易所的今天）→ `close_unknown`。
    """
    moment = now or datetime.now(timezone.utc)
    tz = getattr(last_stamp, "tzinfo", None)
    if tz is None:
        return "close_unknown"
    bar_day = last_stamp.date()
    if bar_day != moment.astimezone(tz).date():
        return "closed"
    regular = ((metadata or {}).get("currentTradingPeriod") or {}).get("regular") or {}
    start, end = regular.get("start"), regular.get("end")
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
        return "close_unknown"
    period_day = datetime.fromtimestamp(start, tz).date()
    if period_day > bar_day:
        return "closed"
    if period_day < bar_day:
        return "close_unknown"
    return "dropped_unfinished" if moment.timestamp() < end else "closed"


def closed_points(points: Iterable[tuple[Any, Any]], metadata: Mapping[str, Any] | None, *,
                  now: datetime | None = None) -> tuple[list[tuple[Any, float]], str | None]:
    """(時戳, 收盤) 序列（時間遞增，yfinance 的 `history()["Close"].items()`）→ (只留已收盤的點, 最後一根的狀態)。

    NaN／非數值先不收（既有規則：未完成的歐股 K 棒會回 NaN——跳過它，端點退回前一根）；剩下的最後一根交給
    `bar_state`，`dropped_unfinished` 就拿掉。一個點都沒有 → 狀態 None（沒有東西可判，不是 closed）。
    """
    kept: list[tuple[Any, float]] = []
    for stamp, value in points:
        try:
            close = float(value)
        except (TypeError, ValueError):
            continue
        if close != close:  # NaN guard
            continue
        kept.append((stamp, close))
    if not kept:
        return kept, None
    state = bar_state(kept[-1][0], metadata, now=now)
    if state == "dropped_unfinished":
        kept = kept[:-1]
    return kept, state


def summarize_bar_states(states: Mapping[str, str | None]) -> dict[str, Any]:
    """每檔最後一根的狀態 → 計數。拿掉的與說不出的**各列出是哪幾檔**；沒有序列的（None）不算進 checked。"""
    return {
        "checked": sum(1 for state in states.values() if state is not None),
        "dropped_unfinished": sorted(s for s, state in states.items() if state == "dropped_unfinished"),
        "close_unknown": sorted(s for s, state in states.items() if state == "close_unknown"),
        "labels": dict(BAR_STATE_LABELS),
    }


def closing_bars_line(summary: Mapping[str, Any] | None) -> str | None:
    """`summarize_bar_states` 的結果 → 報告裡那一行（追蹤表與計分表共用）。都沒有就 None——盤中跑才會有東西，
    daily 05:30 各市場都已收盤；計數本身照樣留在 artifact（`checked` 說得出這一段真的跑過）。"""
    if not summary:
        return None
    dropped, unknown = list(summary.get("dropped_unfinished") or ()), list(summary.get("close_unknown") or ())
    if not dropped and not unknown:
        return None
    return (f"未收盤 K 棒：拿掉 {len(dropped)} 檔" + (f"（{'、'.join(dropped)}）" if dropped else "")
            + f"——那幾檔的現價是前一個收盤；收盤狀態未知 {len(unknown)} 檔"
            + (f"（{'、'.join(unknown)}，照用最後一根）" if unknown else ""))


def fetch_close_series(
    tickers: Iterable[str],
    *,
    sessions: int,
    now: datetime | None = None,
    states: MutableMapping[str, str | None] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """取 provider 已收盤日線 {ticker: [{session_date, close}]}。

    ⚠ 只取**已收盤**的交易日。盤中價與收盤價混在同一條序列會讓單日報酬時而是
    「昨收到現價」、時而是「昨收到今收」——一個欄位兩種語意（L12），而門檻比較
    無從分辨。哪一根算未收盤由 `closed_points` 判（交易所當地今天＋交易時段）；`states` 給了就逐檔記下
    最後一根的狀態（`summarize_bar_states` 計數）。

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
    out: dict[str, list[dict[str, Any]]] = {}
    for symbol in symbols:
        try:
            handle = yf.Ticker(symbol)
            history = handle.history(period=f"{period_days}d")["Close"]
            metadata = getattr(handle, "history_metadata", None)
        except Exception:  # noqa: BLE001 — provider 失敗只降級成「沒有序列」
            continue
        points, state = closed_points(history.items(), metadata, now=now)
        if states is not None:
            states[symbol] = state
        rows = [{"session_date": stamp.date().isoformat(), "close": close} for stamp, close in points]
        if rows:
            out[symbol] = rows[-int(sessions):]
    return out
