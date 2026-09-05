"""內部估計 vs 共識——**只在 apples-to-apples 時給數字**。

四個不可比的情形各自有名字，不合併成一個 `unavailable`：期間不同（`incompatible_period`）、
口徑不同或未核實（`incompatible_basis`）、單位／幣別不同（`incompatible_unit`）、
任一邊沒值（`internal_missing`／`consensus_missing`）。**不合就不減。**

## 共識口徑的核實（L11：自己要引用的事實套同一套追源紀律）

yfinance 不宣告 EPS 共識是 GAAP 還是 non-GAAP。這裡不用「業界慣例」代替核實：
provider 給的 `year_ago_actual`（去年實際值）與一手財報的 GAAP／non-GAAP 稀釋 EPS
機械比對，剛好命中其中一個才判定口徑；兩個都不中、或兩個都中，就是 `unverified`，
而 `unverified` 不得與任何口徑相減。COHR 實測：5.61 ＝ non-GAAP（8-K Table 8），≠ GAAP 4.12。
"""
from __future__ import annotations

import math

from .contracts import ConsensusEstimate, ExpectationComparison, FiscalYearActuals, ModeledMetric

#: year_ago_actual 與一手數字的相對容忍（新聞稿四捨五入到 0.01）。
_BASIS_MATCH_REL_TOL = 0.01
_BASIS_MATCH_ABS_TOL = 0.011

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


def compare_metric(
    metric: str,
    internal: ModeledMetric | None,
    consensus: ConsensusEstimate | None,
    *,
    consensus_basis: str,
    internal_currency: str | None,
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


__all__ = ["compare_metric", "verify_consensus_basis"]
