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
下游無從分辨。導出 EPS 把「估計動了多少」與「股價動了多少」分成兩個數字。

## ⚠ 第二個一表兩義：forward 是**相對標籤**，不是會計年度身分（2026-09-07 實測後補）

yfinance 的 `forwardPE` 指的是「下一個會計年度」——那是相對於抓取日的標籤，
**公司一報完年報它就換一個年度**，而序列本身完全看不出來。COHR 實測：

| 日期 | price | pe_forward | 導出 forward EPS | 相對前一觀測 |
|---|---:|---:|---:|---:|
| 2026-08-12 | ~327 | ~39 | 8.2 | — |
| 2026-08-13 | 327.23 | 24.08 | **13.59** | **+62.3%** |

FY2026 財報（8-K，2026-08-12）一出，forward year 由 FY2027 換成 FY2028，
**一天之內導出 EPS 跳 +62.3%——那不是分析師上修，是換了一把尺**。
被污染的舊結論（「COHR forward EPS +69.9% 而股價 −17.5%＝expectation gap 的原型」）
就是這樣來的：整段窗口跨過了 rollover。

因此 `revision_over` 現在要求窗口兩端的 **forward 會計年度身分相同**才回報修正幅度；
身分不明或不相同一律回 `comparable=False` 並說出原因——**不猜、不用幅度門檻硬猜
（「跳超過 30% 就算 rollover」本身就是未經量測的 gate，L14）**。
身分由當日 `consensus_estimates` 的逐年估計值**反查**（值相等，不是推論）；
`consensus_estimates` 沒有那天的列 → 身分不明 → fail closed。

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
from typing import Any, Mapping, Sequence

__all__ = [
    "FISCAL_IDENTITY_REL_TOL", "attach_forward_period", "forward_eps_from", "forward_eps_series",
    "forward_period_candidates", "resolve_forward_period", "revision_over",
]


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


#: 反查 forward 會計年度身分時的相對容差。導出值 `price / pe_forward` 與
#: `consensus_estimates.estimate_avg` 是同一份 yfinance `info` 的兩種寫法，實測相對差 <1e-5；
#: 1e-3 只吸收四捨五入，**不足以讓相鄰兩個年度的估計互相冒充**（COHR FY27 9.42 vs FY28 13.96
#: 差 48%，AXTI 兩年估計最近也差一個數量級）。
FISCAL_IDENTITY_REL_TOL = 1e-3


def forward_period_candidates(
    conn, ticker: str, *, as_of: str | None = None, metric: str = "eps"
) -> dict[str, list[tuple[str, float]]]:
    """觀測日 → `[(fiscal_period_end, estimate_avg)]`，取自 `consensus_estimates`。

    這是**身分表**：它回答「那一天，我們知道哪些會計年度、各自的共識是多少」。
    沒有那天的列 → 那天不在 dict 裡 → 身分不明（不是「沒有 rollover」）。
    """
    sql = ("SELECT COALESCE(bar_date, snapshot_date) AS d, fiscal_period_end, estimate_avg "
           "FROM consensus_estimates WHERE ticker = ? AND metric = ? "
           "AND fiscal_period_end IS NOT NULL AND estimate_avg IS NOT NULL ")
    params: list[Any] = [ticker, metric]
    if as_of is not None:
        sql += "AND COALESCE(bar_date, snapshot_date) <= ? "
        params.append(str(as_of)[:10])
    out: dict[str, list[tuple[str, float]]] = {}
    try:
        rows = conn.execute(sql, params).fetchall()
    except Exception:  # noqa: BLE001 — 表還沒建＝身分不明，不是「沒有 rollover」
        return {}
    for row in rows:
        day, end, avg = str(row[0])[:10], str(row[1])[:10], row[2]
        if not isinstance(avg, (int, float)) or isinstance(avg, bool):
            continue
        out.setdefault(day, []).append((end, float(avg)))
    return out


def resolve_forward_period(
    forward_eps: float | None, candidates: Sequence[tuple[str, float]] | None,
    *, rel_tol: float = FISCAL_IDENTITY_REL_TOL,
) -> str | None:
    """由**值**反查「這個 forward EPS 是哪一個會計年度的」。

    ⚠ 這是比對不是推論：導出值必須等於某一年的共識估計（相對容差 `rel_tol`）才算命中。
    對不上任何一年、或同時對上兩年（不該發生，但發生了就是分不出來）→ `None`（不知道）。
    """
    if forward_eps is None or not candidates:
        return None
    hits = [end for end, avg in candidates
            if avg not in (0, None) and abs(forward_eps / float(avg) - 1.0) <= rel_tol]
    return hits[0] if len(hits) == 1 else None


def attach_forward_period(
    series: Sequence[dict[str, Any]], identity: Mapping[str, Sequence[tuple[str, float]]],
) -> list[dict[str, Any]]:
    """把 `forward_period_end` 補到序列的每一筆上（查不到就留 `None`＝身分不明）。"""
    return [
        dict(obs, forward_period_end=resolve_forward_period(
            obs.get("forward_eps"), identity.get(str(obs.get("as_of"))[:10])))
        for obs in series
    ]


def forward_eps_series(
    conn, ticker: str, *, as_of: str | None = None, limit: int | None = None
) -> list[dict[str, Any]]:
    """`[{as_of, forward_eps, price, forward_period_end}]`，由舊到新。缺任一輸入的列直接略過。

    略過而不內插：內插會造出一個分析師從未給過的估計值，然後拿它去算修正幅度。
    `forward_period_end` 由 `consensus_estimates` 反查（查不到＝`None`＝身分不明）。
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
    out = attach_forward_period(out, forward_period_candidates(conn, ticker, as_of=as_of))
    return out[-limit:] if limit else out


def revision_over(
    series: Sequence[dict[str, Any]], *, sessions: int
) -> dict[str, float | int | str | None] | None:
    """最近 `sessions` 個觀測內，forward EPS 與股價各自變動多少。

    回 `None` 的三種情形都不是「沒有修正」：序列太短、起點為 0、起點與終點跨越
    正負號（虧損轉盈利時比值沒有意義——`-0.2 → +0.1` 算不出「成長 150%」）。
    **不用 0 冒充**，那會把「算不出來」讀成「估計沒動」（L12）。

    ⚠ **回傳 dict 一律帶 `comparable`。** `comparable=False` 時 `eps_change` 與
    `estimate_vs_price` 是 `None`（不是 0），並附 `not_comparable_reason`；
    `price_change` 仍然給——股價沒有會計年度身分問題。兩種不可比：
    窗口端點的 forward 年度身分不明、或兩端不是同一年（rollover）。
    身分由呼叫端先用 `attach_forward_period` 補在每筆觀測的 `forward_period_end` 上。
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
    id0, id1 = start.get("forward_period_end"), end.get("forward_period_end")
    base = {
        "from": start["as_of"],
        "to": end["as_of"],
        "observations": len(window),
        "forward_period_from": id0,
        "forward_period_to": id1,
        # 股價變動永遠可比——價格沒有會計年度身分問題。
        "price_change": p1 / p0 - 1.0,
    }
    if id0 is None or id1 is None:
        unknown = start["as_of"] if id0 is None else end["as_of"]
        return {**base, "comparable": False, "eps_change": None, "estimate_vs_price": None,
                "not_comparable_reason": (
                    f"窗口端點 {unknown} 的 forward 會計年度身分不明（consensus_estimates 沒有那天的列）"
                    "——無法區分「分析師修正」與「forward year rollover」，fail closed"
                    "（不是修正為 0）")}
    if id0 != id1:
        return {**base, "comparable": False, "eps_change": None, "estimate_vs_price": None,
                "not_comparable_reason": (
                    f"窗口跨越 forward year rollover（{id0} → {id1}）：兩端不是同一個會計年度的估計，"
                    "比值是換尺不是修正")}
    return {
        **base,
        "comparable": True,
        "eps_change": e1 / e0 - 1.0,
        # 兩者的差就是「估計修正沒有被股價反映的部分」——Q4 的原料。
        # 正值＝估計跑在股價前面（可能是 gap），負值＝股價跑在估計前面。
        "estimate_vs_price": (e1 / e0) / (p1 / p0) - 1.0,
    }
