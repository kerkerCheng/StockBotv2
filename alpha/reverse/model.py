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


def _metric_with(
    actuals: FiscalYearActuals, assumptions: Sequence[OperatingAssumption],
    target: FiscalPeriod, assumption_id: str, value: float, *, metric: str = "eps",
) -> float | None:
    """把某一條假設換成 `value`，走一次**真正的** bridge，回目標指標（算不出來就 None）。

    `metric` 由估值方法決定（2026-09-20）：本益比法問 `eps`，EV／Sales 問 `revenue`。
    ⚠ **兩者共用同一條 `build_bridge`**——所以任何一步的缺席與口徑衝突仍然用跟正向
    完全一樣的規則現形，沒有「只有反解才有的第二套算術」。
    """
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
    datum = result.metrics.get(metric)
    return datum.value if datum is not None and datum.is_known else None


#: 端點往自己的值收斂時最多試幾次（每次砍一半）。10 次已經把區間縮到千分之一以下。
_ENDPOINT_RETRIES = 10


def _feasible_endpoint(actuals, assumptions, target, assumption, endpoint: float,
                       *, metric: str = "eps"):
    """從 `endpoint` 往 `assumption.value` 收斂，找第一個橋算得出 EPS 的點。

    回傳 `(找到的點, 該點的 EPS)`；找不到就 `(endpoint, None)`。
    ⚠ 這不是「放寬」：它只縮小搜尋區間，所以若真解落在被縮掉的那一段，
    下游會看到 `no_sign_change`（＝這個 driver 撐不起現價），而那是正確的結論。
    """
    x = float(endpoint)
    anchor = float(assumption.value)
    for _ in range(_ENDPOINT_RETRIES):
        value = _metric_with(actuals, assumptions, target, assumption.assumption_id, x,
                             metric=metric)
        if value is not None:
            return x, value
        x = (x + anchor) / 2.0
    return float(endpoint), None


def _bounds(driver: str) -> tuple[float, float]:
    spec = ASSUMPTION_DRIVERS[driver]
    lower = spec.lower if spec.lower is not None else -_FALLBACK_SPAN
    upper = spec.upper if spec.upper is not None else _FALLBACK_SPAN
    return float(lower), float(upper)


def solve_driver(
    actuals: FiscalYearActuals, assumptions: Sequence[OperatingAssumption], target: FiscalPeriod,
    *, assumption: OperatingAssumption, target_eps: float, metric: str = "eps",
) -> DriverSolution:
    """單一 driver 的反解。**其餘假設固定**，所以這是條件解不是唯一解。

    `metric`（2026-09-20）＝要命中的指標：本益比法是 `eps`，EV／Sales 是 `revenue`。
    `target_eps` 的名字沿用（改名要動所有呼叫端），但它裝的是**那個 metric 的目標值**。
    """
    spec = ASSUMPTION_DRIVERS[assumption.driver]
    lower, upper = _bounds(assumption.driver)
    label = "營收" if metric == "revenue" else "EPS"
    common = dict(driver=assumption.driver, scope=assumption.scope,
                  assumption_id=assumption.assumption_id, unit=spec.unit,
                  our_value=assumption.value, lower_bound=spec.lower, upper_bound=spec.upper)

    at_our = _metric_with(actuals, assumptions, target, assumption.assumption_id,
                          assumption.value, metric=metric)
    if at_our is None:
        return DriverSolution(implied_value=None, status="bridge_failed", **common,
                              reason=f"用我們自己的值都算不出{label}——缺其他假設或口徑衝突，"
                                     "反解不會比正向多知道什麼")
    if math.isclose(at_our, target_eps, rel_tol=EQUAL_REL_TOL, abs_tol=0.0):
        return DriverSolution(implied_value=assumption.value, status="already_equal", **common,
                              reason="我們的假設已經等於市場隱含——**這是答案不是失敗**："
                                     "它表示我們對這個 driver 的預測就是市場的預測")

    # 端點：往兩邊各縮一點點，避開剛好落在邊界上時 `replace` 被 contract 拒絕。
    edge = (upper - lower) * 1e-9
    lo, hi = lower + edge, upper - edge
    # ⚠ **driver 的合法界 ≠ 橋的可行域**（2026-09-13）。`operating_margin_delta` 的界在同日
    # 放寬到 ±10（AEVA 的 +143pp 是真的），而橋另外擋「結果營益率超過 100%」——
    # 於是 upper 端點本身可能算不出 EPS。這裡把端點**往我們自己的值收斂**直到橋算得出來，
    # 而不是直接回 `bridge_failed`：界是契約，可行域是算術，兩者本來就不必相同。
    lo, f_lo = _feasible_endpoint(actuals, assumptions, target, assumption, lo, metric=metric)
    hi, f_hi = _feasible_endpoint(actuals, assumptions, target, assumption, hi, metric=metric)
    if f_lo is None or f_hi is None:
        return DriverSolution(implied_value=None, status="bridge_failed", **common,
                              reason=f"區間端點的橋算不出{label}（已往我們自己的值收斂仍無解），"
                                     "無法確定解在不在範圍內")
    # ⚠ 兩端**完全相同**＝這個 driver 對這個指標在結構上無關，不是「撐不起」（L12）。
    # 2026-09-20 起 EV／Sales 會大量走到這裡：營益率、稅率、利息、股數對 `revenue` 的
    # 影響是零。若併進 `no_sign_change`，輸出會變成「連營益率拉到極限都撐不起營收目標」
    # ——那句話沒有意義，而且它對每一檔都會亮（L14-4：恆亮＝零鑑別力）。
    if math.isclose(f_lo, f_hi, rel_tol=EQUAL_REL_TOL, abs_tol=0.0):
        return DriverSolution(
            implied_value=None, status="driver_does_not_affect_metric", **common,
            reason=(f"把它推到合法範圍 [{lower:g}, {upper:g}] 的兩端，{label}一動也不動"
                    f"（都是 {f_lo:g}）——**這個 driver 對{label}在結構上無關**，"
                    f"不是「撐不起」。用 EV／Sales 估值時營益率／稅率／利息都會落在這一格"))
    if (f_lo - target_eps) * (f_hi - target_eps) > 0:
        return DriverSolution(
            implied_value=None, status="no_sign_change", **common,
            reason=(f"在合法範圍 [{lower:g}, {upper:g}] 的兩端，{label}是 {f_lo:g} 與 {f_hi:g}，"
                    f"都在目標 {target_eps:g} 的同一側——**光靠這一個 driver 撐不起現價**"
                    "（其他假設固定時）。這是結論，不是缺料"))

    for _ in range(_MAX_ITERATIONS):
        mid = (lo + hi) / 2.0
        f_mid = _metric_with(actuals, assumptions, target, assumption.assumption_id, mid,
                             metric=metric)
        if f_mid is None:
            return DriverSolution(implied_value=None, status="bridge_failed", **common,
                                  reason=f"二分到 {mid:g} 時橋算不出{label}（區間內有不連續）")
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
    target_return_multiple: float = 1.0,
    basis: str = "forward_earnings_multiple",
    net_debt: float | None = None,
    diluted_shares: float | None = None,
) -> ReverseBridgeResult:
    """一次反解。任何一段缺料都以 `missing`＋理由現形，不補預設值。

    `target_return_multiple`（2026-09-19，Phase 7 Step 7.1）＝**這次問的是幾倍**。
    `1.0` 是原本的問法（「市場隱含的假設是多少」）；`5.0` 問的是「**五倍要什麼為真**」。
    兩者共用同一條橋、同一套二分法、同一組合法上下限——**差別只有起點價格**。

    ⚠ 之所以能這麼小：`build_reverse_bridge` 本來就走一次真正的 `build_bridge`，
    所以任何一步的缺席與口徑衝突會用跟正向完全一樣的規則現形；不單調時回 `no_sign_change`
    而不是猜一個值。**問五倍時那個 `no_sign_change` 正是我們要的答案**——
    「即使把這個 driver 拉到極限也撐不起五倍」是結論，不是缺料。
    """
    if basis not in ("forward_earnings_multiple", "ev_to_sales"):
        raise ContractViolation(
            f"basis 未登記：{basis!r}——估值方法的權威是 alpha/valuation/contracts.py 的 "
            "METHOD_PARAMETERS，反解不得自己發明第三種")
    if not target_return_multiple or target_return_multiple <= 0:
        raise ContractViolation(
            f"target_return_multiple 必須是正數（收到 {target_return_multiple!r}）——"
            "「零倍」與「負倍」沒有定義，不得靠預設值把它變成 1")
    common = dict(company_id=company_id, ticker=ticker, as_of=as_of, target_period=target_period,
                  current_price=current_price, target_multiple=target_multiple,
                  our_eps=our_eps, consensus_eps=consensus_eps,
                  target_return_multiple=float(target_return_multiple),
                  basis=basis, net_debt=net_debt, diluted_shares=diluted_shares)
    metric = "revenue" if basis == "ev_to_sales" else "eps"

    def _no(reason: str) -> ReverseBridgeResult:
        return ReverseBridgeResult(status="missing", market_implied_eps=None, required_eps=None,
                                   reason=reason, **common)

    if current_price is None:
        return _no("沒有現價——反解的起點就是價格（不是 0）")
    if target_multiple is None:
        return _no("沒有目標倍數：反解問的是「在我們的倍數下，EPS 要多少」，"
                   "沒有倍數就沒有那個問題（不補市場倍數——那會讓答案恆等於共識）")
    if target_multiple == 0:
        return _no("目標倍數為 0，市場隱含 EPS 無定義")
    if actuals is None or target_period is None:
        return _no("沒有基期觀測或目標期間——沒有橋就無從反解")

    if basis == "ev_to_sales":
        # 照抄 alpha/valuation/model.py 的同一條公式，**反過來解**，不另立一套算術：
        #   fair_value/share = (revenue × target_ev_to_sales − net_debt) / diluted_shares
        # 要 fair_value/share ＝ 現價 × 倍率：
        #   required_revenue = (現價 × 倍率 × diluted_shares + net_debt) / target_ev_to_sales
        if diluted_shares is None or not diluted_shares:
            return _no("EV／Sales 反解需要稀釋股數才能把每股換成總量"
                       "（照抄估值層同一條公式；**不補一個猜的股數**）")
        if net_debt is None:
            return _no("EV／Sales 反解需要淨負債（Engine C 的 total_debt 與 cash_and_equivalents）："
                       "**不補 0**——把「沒讀到負債」當成「零負債」會讓所需營收憑空少掉整個負債")
        market_implied_eps = (current_price * diluted_shares + net_debt) / target_multiple
        required_eps = (current_price * target_return_multiple * diluted_shares
                        + net_debt) / target_multiple
    else:
        market_implied_eps = current_price / target_multiple        # 永遠是倍率 1 的那個問題
        required_eps = current_price * target_return_multiple / target_multiple
    live = [a for a in assumptions
            if a.driver in OPINION_BEARING_DRIVERS and not a.retracted]
    if not live:
        return ReverseBridgeResult(
            status="missing", market_implied_eps=market_implied_eps, required_eps=required_eps,
            reason="沒有任何營收／營益率假設可以反解——這一檔還沒開始做", **common)

    solutions = tuple(
        solve_driver(actuals, list(assumptions), target_period,
                     assumption=item, target_eps=required_eps, metric=metric)
        for item in live
    )
    solved = [s for s in solutions if s.status in ("solved", "already_equal")]
    # 對這個指標結構上無關的 driver **不算進分母**——否則 EV／Sales 永遠是 partial
    # （營益率等必然落在那一格），而那個 partial 講的不是這一檔的事（L14-4 恆亮）。
    relevant = [s for s in solutions if s.status != "driver_does_not_affect_metric"]
    if not relevant:
        status, reason = "partial", (
            f"{len(solutions)} 個 driver 全部對{'營收' if metric == 'revenue' else 'EPS'}"
            "在結構上無關——這一檔還沒有任何會動到這個指標的假設")
    elif not solved:
        status, reason = "partial", "每個 driver 都解不出來——逐項理由見 solutions"
    elif len(solved) == len(relevant):
        status, reason = "available", None
    else:
        status, reason = "partial", (
            f"{len(relevant) - len(solved)}／{len(relevant)} 個 driver 解不出來，逐項有理由")
    return ReverseBridgeResult(status=status, market_implied_eps=market_implied_eps,
                               required_eps=required_eps,
                               solutions=solutions, reason=reason, **common)


__all__ = ["build_reverse_bridge", "solve_driver"]
