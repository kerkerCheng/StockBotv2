"""內部估計 vs 共識——**只在 apples-to-apples 時給數字**。

五個不可比的情形各自有名字，不合併成一個 `unavailable`：期間不同（`incompatible_period`）、
口徑不同或未核實（`incompatible_basis`）、單位／幣別不同（`incompatible_unit`）、
共識與基期對不上帳（`unreconciled_base`）、任一邊沒值（`internal_missing`／`consensus_missing`）。
**不合就不減。**

## 共識口徑的核實（L11：自己要引用的事實套同一套追源紀律）

yfinance 不宣告 EPS 共識是 GAAP 還是 non-GAAP。這裡不用「業界慣例」代替核實：
provider 給的 `year_ago_actual`（去年實際值）與一手財報的 GAAP／non-GAAP 稀釋 EPS
機械比對，剛好命中其中一個才判定口徑；兩個都不中、或兩個都中，就是 `unverified`，
而 `unverified` 不得與任何口徑相減。COHR 實測：5.61 ＝ non-GAAP（8-K Table 8），≠ GAAP 4.12。

## 營收也要對帳（2026-09-07 Coverage Pilot 補）

`year_ago_actual` 對 EPS 是「口徑是哪一種」的判準，順帶也把「這串共識量的是不是同一家公司」
對了帳。**營收沒有口徑之分，於是原本什麼都沒對**——`verify_consensus_basis` 直接回
`not_applicable`，比較就照減。

實測（6324.T ハーモニック・ドライブ）：同一批 yfinance 共識紀錄裡，EPS 的 `year_ago_actual`
16.99 是**連結**（決算短信第 1 頁），營收的 `year_ago_actual` 33,438,000,000 卻是**單體**
（第 2 頁「(参考) 個別業績の概要」），而連結營收是 59,557,877 千円——**同一組紀錄混用兩種
合併範圍，差 −43.9%**。而那一年的營收估計值 74,682M 又高於公司自家的連結指引 68,000M，
所以估計值本身看起來是連結的：紀錄內部就不自洽。

`year_ago_actual` 是我們唯一能機械檢查「共識與基期是不是同一個量」的把手。對不上就
`unreconciled_base`——**不是口徑問題，也不是缺料**，是這串共識量的東西和我們的基期不同（L12）。
"""
from __future__ import annotations

import math

from .contracts import ConsensusEstimate, ExpectationComparison, FiscalYearActuals, ModeledMetric

#: `year_ago_actual` 與一手數字的**相對**容忍（吸收印刷四捨五入）。
#: ⚠ **刻意沒有絕對容忍**（2026-09-07 Coverage Pilot 移除）。第一版是 `abs_tol=0.011`，
#: 那個數字是拿 COHR 校準的——美元級 EPS 印到分位，0.011 剛好蓋住一次進位。
#: 但絕對容忍在**便士級**的 EPS 上會把兩個候選一起放進來：IQE.L FY2025 的 GAAP 稀釋 EPS
#: −0.0377 與 adjusted −0.0282 只差 **0.0095 < 0.011**，於是兩個都「命中」、函式回
#: `unverified`——而 provider 的 `year_ago_actual` −0.0282 其實**精確等於** adjusted。
#: 那不是「無法判定」，是尺度把判準稀釋掉了（L15-1：這個 gate 攔下的不是它想攔的東西）。
#: 相對容忍本身就與尺度無關，是正確的判準；`math.isclose` 對 0.0 vs 0.0 仍為真，
#: 對 0.0 vs 任何非零仍為偽——EPS 恰為零的邊界不需要靠絕對容忍撐。
_BASIS_MATCH_REL_TOL = 0.01
_BASIS_MATCH_ABS_TOL = 0.0

_METRIC_UNIT = {"eps": "currency_per_share", "revenue": "currency", "operating_margin": "ratio"}


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=_BASIS_MATCH_REL_TOL, abs_tol=_BASIS_MATCH_ABS_TOL)


def verify_consensus_basis(estimate: ConsensusEstimate, base: FiscalYearActuals | None) -> str:
    """判定一筆共識的會計口徑。營收 → `not_applicable`；EPS 靠去年實際值核對，否則 `unverified`。"""
    if estimate.metric != "eps":
        return "not_applicable"
    if base is None or estimate.year_ago_actual is None:
        return "unverified"
    if not base.period.same_as(estimate.period.shifted(-1)):
        return "unverified"                      # 去年實際值對應的不是我們手上的基期
    gaap_eps = base.gaap.get("diluted_eps") if base.gaap else None
    non_gaap_eps = base.non_gaap.get("diluted_eps") if base.non_gaap else None
    matches = [name for name, value in (("gaap", gaap_eps), ("non_gaap", non_gaap_eps))
               if value is not None and _close(float(value), float(estimate.year_ago_actual))]
    return matches[0] if len(matches) == 1 else "unverified"


def reconcile_consensus_base(
    estimate: ConsensusEstimate, base: FiscalYearActuals | None
) -> str | None:
    """共識的 `year_ago_actual` 與我們的基期實際值對得上嗎？對得上（或無從檢查）回 `None`。

    只管**營收**：EPS 的同一件事已經在 `verify_consensus_basis` 裡做掉了（對不上就是
    `unverified` → `incompatible_basis`），在這裡再做一次會讓同一個問題有兩個名字。
    刻意不猜倍數關係、不換算合併範圍——只回報「對不上」與差多少，怎麼修是研究的事。
    """
    if estimate.metric != "revenue":
        return None
    if base is None or estimate.year_ago_actual is None:
        return None                                   # 無從檢查 ≠ 檢查通過；但也不因此拒絕
    if not base.period.same_as(estimate.period.shifted(-1)):
        return None                                   # 去年實際值對應的不是我們手上的基期
    reported = float(base.revenue)
    provider = float(estimate.year_ago_actual)
    if _close(reported, provider):
        return None
    delta = (provider / reported - 1.0) if reported else None
    return (f"共識的去年實際營收 {provider:,.0f} 與一手財報的 {base.period.label} 營收 "
            f"{reported:,.0f} 對不上"
            + (f"（差 {delta:+.1%}）" if delta is not None else "")
            + "——provider 的這串共識量的不是我們基期量的那個東西（常見成因：單體 vs 合併、"
              "重編、幣別或口徑不同）。不猜、不換算，本期營收不比較")


def compare_metric(
    metric: str,
    internal: ModeledMetric | None,
    consensus: ConsensusEstimate | None,
    *,
    consensus_basis: str,
    internal_currency: str | None,
    base_reconciliation: str | None = None,
) -> ExpectationComparison:
    """一個指標的比較。回傳物件的 `status != comparable` 時**沒有任何 gap 數字**。"""
    unit = _METRIC_UNIT.get(metric)
    common = dict(
        metric=metric, unit=unit,
        internal_period=internal.period if internal else None,
        consensus_period=consensus.period if consensus else None,
        internal=internal.value if internal else None,
        consensus=consensus.value if consensus else None,
        accounting_basis_internal=internal.accounting_basis if internal else None,
        accounting_basis_consensus=(consensus_basis if consensus else None),
        analyst_count=consensus.analyst_count if consensus else None,
        consensus_captured_at=consensus.captured_at if consensus else None,
        assumption_ids=tuple(internal.assumption_ids) if internal else (),
        observation_refs=tuple(internal.observation_refs) if internal else (),
        consensus_refs=consensus.refs if consensus else (),
    )

    def _no(status: str, reason: str) -> ExpectationComparison:
        return ExpectationComparison(status=status, absolute_gap=None, relative_gap=None,
                                     reason=reason, **common)

    if internal is None or internal.value is None:
        return _no("internal_missing",
                   (internal.reason if internal and internal.reason else "內部估計不存在") + "（不是 0）")
    if consensus is None or consensus.value is None:
        return _no("consensus_missing", "Engine C 無這個指標的同期共識（不是 0）")
    if not internal.period.same_as(consensus.period):
        return _no("incompatible_period",
                   f"內部 {internal.period.label}（至 {internal.period.end}）vs 共識 "
                   f"{consensus.period.label}（至 {consensus.period.end}）——不同會計期間不得相減")
    if base_reconciliation is not None:
        return _no("unreconciled_base", base_reconciliation)
    if metric == "eps":
        if consensus_basis not in ("gaap", "non_gaap"):
            return _no("incompatible_basis",
                       f"共識口徑 {consensus_basis}：provider 未宣告且無法用去年實際值核實，不得與內部 {internal.accounting_basis} 相減")
        if internal.accounting_basis != consensus_basis:
            return _no("incompatible_basis",
                       f"內部 {internal.accounting_basis} vs 共識 {consensus_basis}——口徑不同不得相減")
    if consensus.currency and internal_currency and consensus.currency.upper() != internal_currency.upper():
        return _no("incompatible_unit",
                   f"幣別不同：內部 {internal_currency} vs 共識 {consensus.currency}")
    absolute = internal.value - consensus.value
    relative = (internal.value / consensus.value - 1.0) if consensus.value > 0 else None
    reason = None if relative is not None else "共識非正，相對 gap 無定義（只給絕對 gap）"
    return ExpectationComparison(status="comparable", absolute_gap=absolute, relative_gap=relative,
                                 reason=reason, **common)


__all__ = ["compare_metric", "reconcile_consensus_base", "verify_consensus_basis"]
