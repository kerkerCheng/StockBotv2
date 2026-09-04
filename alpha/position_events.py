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
定位一致。序列由呼叫端注入（`series_by_ticker`），純函式好測。

## B6：為什麼從 `decision_lab/` 搬到這裡

原本住 `decision_lab/alpha_event_monitor.py`，是因為唯一的消費端是 `brief.py`。
B6 把 alpha pane 搬到 `alpha/brief.py` 之後那個理由就消失了——若留在原處，
`alpha/brief.py` 就得 import `decision_lab`，正是 `test_upstream_layers_do_not_
import_engine_d` 擋的方向。**它一直都是 alpha 的東西**（`engine-d-decomposition.md`
逐檔判定就標 **A**），只是被最短路徑留在了 Engine D。

抓取（yfinance）已分出去到 `alpha/providers/close_series.py`：本檔必須維持零外部
相依才能離線測試（`FORBIDDEN_IN_ALPHA` 含 `yfinance`）。
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence

__all__ = ["alpha_event_search_requests"]


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
