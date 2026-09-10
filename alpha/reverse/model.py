"""`build_reverse_bridge()`——現價 ＋ 目標倍數 ＋ 我們的假設 → 「市場隱含的假設是多少」。

```
market_implied_eps ＝ 現價 ÷ 目標倍數
                          │
   對每個 opinion-bearing driver：固定其餘假設，二分求解 value 使 bridge 的 EPS 命中它
                          │
                    DriverSolution（我們的值 vs 市場隱含的值）
```

## 為什麼是二分法而不是解析解

橋是分段的（分部營收加總 → 營益率 → 利息 → 稅 → NCI → 股數），對 `revenue_growth` 這種
分部 driver 沒有乾淨的解析反函式；而且它**刻意**要走一次真正的 `build_bridge`，
這樣任何一步的缺席／口徑衝突都會用跟正向完全一樣的規則現形——不會出現「反解算得出來，
正向卻算不出來」這種只有反解才有的第二套算術。

## 不單調怎麼辦

虧損公司的 EPS 對 `revenue_growth` 可以是非單調的（營收增加但營益率為負 → EPS 更負）。
二分法要求端點異號；不異號時**不猜、不掃描**，回 `no_sign_change` 並說出兩端的值。
那本身就是有用的結論：「即使把這個 driver 拉到合法上限，也撐不起現價」。
"""
from __future__ import annotations

import math
from dataclasses import replace
from datetime import date
from typing import Sequence

from ..errors import ContractViolation
from ..fundamental.bridge import build_bridge
from ..fundamental.contracts import (
    ASSUMPTION_DRIVERS, OPINION_BEARING_DRIVERS, FiscalPeriod, FiscalYearActuals,
    OperatingAssumption,
)
from .contracts import EQUAL_REL_TOL, DriverSolution, ReverseBridgeResult

#: 二分法迭代次數。50 次把區間縮小 2^-50，遠超過任何財務數字的有效位數。
_MAX_ITERATIONS = 50

#: driver 沒有宣告上下限時的兜底區間（`interest_and_other_net` 這類金額型）。
#: ⚠ 只用於**沒有** contract 上下限的 driver；有宣告的一律照抄 contract，不另立一套。
_FALLBACK_SPAN = 1e12


def _eps_with(
    actuals: FiscalYearActuals, assumptions: Sequence[OperatingAssumption],
    target: FiscalPeriod, assumption_id: str, value: float,
) -> float | None:
    """把某一條假設換成 `value`，走一次**真正的** bridge，回 EPS（算不出來就 None）。"""
    perturbed = []
    for item in assumptions:
        if item.assumption_id == assumption_id:
            try:
                item = replace(item, value=value)
            except ContractViolation:
                return None                      # 超出該 driver 宣告的上下限
        perturbed.append(item)
    try:
        result = build_bridge(actuals, perturbed, target)
    except ContractViolation:
        return None
    metric = result.metrics.get("eps")
    return metric.value if metric is not None and metric.is_known else None


def _bounds(driver: str) -> tuple[float, float]:
    spec = ASSUMPTION_DRIVERS[driver]
    lower = spec.lower if spec.lower is not None else -_FALLBACK_SPAN
    upper = spec.upper if spec.upper is not None else _FALLBACK_SPAN
    return float(lower), float(upper)


def solve_driver(
    actuals: FiscalYearActuals, assumptions: Sequence[OperatingAssumption], target: FiscalPeriod,
    *, assumption: OperatingAssumption, target_eps: float,
) -> DriverSolution:
    """單一 driver 的反解。**其餘假設固定**，所以這是條件解不是唯一解。"""
    spec = ASSUMPTION_DRIVERS[assumption.driver]
    lower, upper = _bounds(assumption.driver)
    common = dict(driver=assumption.driver, scope=assumption.scope,
                  assumption_id=assumption.assumption_id, unit=spec.unit,
                  our_value=assumption.value, lower_bound=spec.lower, upper_bound=spec.upper)

    at_our = _eps_with(actuals, assumptions, target, assumption.assumption_id, assumption.value)
    if at_our is None:
        return DriverSolution(implied_value=None, status="bridge_failed", **common,
                              reason="用我們自己的值都算不出 EPS——缺其他假設或口徑衝突，"
                                     "反解不會比正向多知道什麼")
    if math.isclose(at_our, target_eps, rel_tol=EQUAL_REL_TOL, abs_tol=0.0):
        return DriverSolution(implied_value=assumption.value, status="already_equal", **common,
                              reason="我們的假設已經等於市場隱含——**這是答案不是失敗**："
                                     "它表示我們對這個 driver 的預測就是市場的預測")

    # 端點：往兩邊各縮一點點，避開剛好落在邊界上時 `replace` 被 contract 拒絕。
    edge = (upper - lower) * 1e-9
    lo, hi = lower + edge, upper - edge
    f_lo = _eps_with(actuals, assumptions, target, assumption.assumption_id, lo)
    f_hi = _eps_with(actuals, assumptions, target, assumption.assumption_id, hi)
    if f_lo is None or f_hi is None:
        return DriverSolution(implied_value=None, status="bridge_failed", **common,
                              reason="區間端點的橋算不出 EPS，無法確定解在不在範圍內")
    if (f_lo - target_eps) * (f_hi - target_eps) > 0:
        return DriverSolution(
            implied_value=None, status="no_sign_change", **common,
            reason=(f"在合法範圍 [{lower:g}, {upper:g}] 的兩端，EPS 是 {f_lo:g} 與 {f_hi:g}，"
                    f"都在目標 {target_eps:g} 的同一側——**光靠這一個 driver 撐不起現價**"
                    "（其他假設固定時）。這是結論，不是缺料"))

    for _ in range(_MAX_ITERATIONS):
        mid = (lo + hi) / 2.0
        f_mid = _eps_with(actuals, assumptions, target, assumption.assumption_id, mid)
        if f_mid is None:
            return DriverSolution(implied_value=None, status="bridge_failed", **common,
                                  reason=f"二分到 {mid:g} 時橋算不出 EPS（區間內有不連續）")
        if (f_lo - target_eps) * (f_mid - target_eps) <= 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return DriverSolution(implied_value=(lo + hi) / 2.0, status="solved", **common)


def build_reverse_bridge(
    *,
    company_id: str,
    ticker: str,
    as_of: date | None,
    target_period: FiscalPeriod | None,
    actuals: FiscalYearActuals | None,
    assumptions: Sequence[OperatingAssumption],
    current_price: float | None,
    target_multiple: float | None,
    our_eps: float | None,
    consensus_eps: float | None,
) -> ReverseBridgeResult:
    """一次反解。任何一段缺料都以 `missing`＋理由現形，不補預設值。"""
    common = dict(company_id=company_id, ticker=ticker, as_of=as_of, target_period=target_period,
                  current_price=current_price, target_multiple=target_multiple,
                  our_eps=our_eps, consensus_eps=consensus_eps)

    def _no(reason: str) -> ReverseBridgeResult:
        return ReverseBridgeResult(status="missing", market_implied_eps=None, reason=reason, **common)

    if current_price is None:
        return _no("沒有現價——反解的起點就是價格（不是 0）")
    if target_multiple is None:
        return _no("沒有目標倍數：反解問的是「在我們的倍數下，EPS 要多少」，"
                   "沒有倍數就沒有那個問題（不補市場倍數——那會讓答案恆等於共識）")
    if target_multiple == 0:
        return _no("目標倍數為 0，市場隱含 EPS 無定義")
    if actuals is None or target_period is None:
        return _no("沒有基期觀測或目標期間——沒有橋就無從反解")

    market_implied_eps = current_price / target_multiple
    live = [a for a in assumptions
            if a.driver in OPINION_BEARING_DRIVERS and not a.retracted]
    if not live:
        return ReverseBridgeResult(
            status="missing", market_implied_eps=market_implied_eps,
            reason="沒有任何營收／營益率假設可以反解——這一檔還沒開始做", **common)

    solutions = tuple(
        solve_driver(actuals, list(assumptions), target_period,
                     assumption=item, target_eps=market_implied_eps)
        for item in live
    )
    solved = [s for s in solutions if s.status in ("solved", "already_equal")]
    if not solved:
        status, reason = "partial", "每個 driver 都解不出來——逐項理由見 solutions"
    elif len(solved) == len(solutions):
        status, reason = "available", None
    else:
        status, reason = "partial", (
            f"{len(solutions) - len(solved)}／{len(solutions)} 個 driver 解不出來，逐項有理由")
    return ReverseBridgeResult(status=status, market_implied_eps=market_implied_eps,
                               solutions=solutions, reason=reason, **common)


__all__ = ["build_reverse_bridge", "solve_driver"]
