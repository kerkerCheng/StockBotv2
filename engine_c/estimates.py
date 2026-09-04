"""分析師預估的**導出**序列：forward EPS 與它的修正幅度。

## 為什麼是導出而不是新欄位（2026-09-04 實測後定案）

Phase 4 原本的第一項交付是「Engine C 欄位擴充：forwardEps」，前提是那個數字
Engine C 沒有。**實測後那個前提是錯的**：yfinance 的 `forwardPE` 就是
`price / forwardEps`，兩邊在同一份 `info` dict 內恆等（COHR／NVDA／2330.TW／
6324.T／SIVE.ST 相對差 <1e-7）。而 `price` 與 `pe_forward` 我們**每天存**，
`financial_snapshots` 1,931 筆有 1,836 筆（95%）兩者皆有值，最早回到 2026-07-08。

差別很大：新增欄位今天開始才有資料，導出**立刻有兩個月歷史**。

## 這個序列真正解決的問題

`ConsensusSnapshot.estimate_revision_30d` 原本取 `pe_forward` 的 30 日變化，而
倍數同時被「分析師改估計」與「股價漲跌」推動——**一個表示兩種語意**（L12），
下游無從分辨。導出 EPS 之後兩者分離，實測 2026-07-08→09-03：

| 標的 | forward EPS | 股價 | 讀法 |
|---|---:|---:|---|
| COHR | **+69.9%** | −17.5% | 估計大幅上修而股價下跌——expectation gap 的原型 |
| AXTI | **+186.1%** | +22.5% | 估計跑在股價前面 |
| NVDA | +20.1% | +12.6% | 大致同步，落差小 |

## ⚠ 單位：只能當比值用，不得跨標的比大小

導出值的單位跟著 `price` 的**報價單位**走，不是結算幣別。實測 IQE.L：報價
`GBp`（便士），yfinance 的 `forwardEps` 卻是英鎊，`price/forwardPE` 與它差
**100 倍**。這正是 AGENTS.md「報價單位 ≠ 結算幣別」記過的坑。

因此本模組只回**同一標的的時間序列比值**（`eps_t1/eps_t0 - 1`），單位在比值中
消掉，恆正確。**不提供跨標的可比的絕對 EPS**——要那個必須先過
`identity/currency.py` 正規化，而那是另一件事。
"""
from __future__ import annotations

import math
from typing import Any, Sequence

__all__ = ["forward_eps_from", "forward_eps_series", "revision_over"]


def forward_eps_from(price: Any, pe_forward: Any) -> float | None:
    """`price / pe_forward`，即 yfinance 的 `forwardEps`（**以報價單位計**）。

    `pe_forward` 為 0、負值以外的任何有限值都可用——負的 forward PE 代表虧損預估，
    導出的負 EPS 是正確資訊，不得丟掉（SIVE.ST 與 IQE.L 都是這種情形）。
    """
    if isinstance(price, bool) or isinstance(pe_forward, bool):
        return None
    if not isinstance(price, (int, float)) or not isinstance(pe_forward, (int, float)):
        return None
    if not math.isfinite(price) or not math.isfinite(pe_forward) or pe_forward == 0:
        return None
    value = float(price) / float(pe_forward)
    return value if math.isfinite(value) else None


def forward_eps_series(
    conn, ticker: str, *, as_of: str | None = None, limit: int | None = None
) -> list[dict[str, Any]]:
    """`[{as_of, forward_eps, price}]`，由舊到新。缺任一輸入的列直接略過。

    略過而不內插：內插會造出一個分析師從未給過的估計值，然後拿它去算修正幅度。
    """
    sql = (
        "SELECT COALESCE(bar_date, snapshot_date) AS d, price, pe_forward "
        "FROM financial_snapshots "
        "WHERE ticker = ? AND price IS NOT NULL AND pe_forward IS NOT NULL "
    )
    params: list[Any] = [ticker]
    if as_of is not None:
        sql += "AND COALESCE(bar_date, snapshot_date) <= ? "
        params.append(str(as_of)[:10])
    sql += "ORDER BY d ASC"
    rows = conn.execute(sql, params).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        eps = forward_eps_from(row["price"], row["pe_forward"])
        if eps is None:
            continue
        out.append({"as_of": str(row["d"]), "forward_eps": eps, "price": float(row["price"])})
    return out[-limit:] if limit else out


def revision_over(
    series: Sequence[dict[str, Any]], *, sessions: int
) -> dict[str, float | int | str | None] | None:
    """最近 `sessions` 個觀測內，forward EPS 與股價各自變動多少。

    回 `None` 的三種情形都不是「沒有修正」：序列太短、起點為 0、起點與終點跨越
    正負號（虧損轉盈利時比值沒有意義——`-0.2 → +0.1` 算不出「成長 150%」）。
    **不用 0 冒充**，那會把「算不出來」讀成「估計沒動」（L12）。
    """
    if len(series) < 2:
        return None
    window = series[-(sessions + 1):] if sessions > 0 else series
    if len(window) < 2:
        return None
    start, end = window[0], window[-1]
    e0, e1 = start["forward_eps"], end["forward_eps"]
    p0, p1 = start["price"], end["price"]
    if e0 == 0 or p0 == 0:
        return None
    if (e0 > 0) != (e1 > 0):
        return None
    return {
        "from": start["as_of"],
        "to": end["as_of"],
        "observations": len(window),
        "eps_change": e1 / e0 - 1.0,
        "price_change": p1 / p0 - 1.0,
        # 兩者的差就是「估計修正沒有被股價反映的部分」——Q4 的原料。
        # 正值＝估計跑在股價前面（可能是 gap），負值＝股價跑在估計前面。
        "estimate_vs_price": (e1 / e0) / (p1 / p0) - 1.0,
    }
