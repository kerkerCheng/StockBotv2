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

from .contracts import (
    ConsensusEstimate,
    ExpectationComparison,
    FiscalYearActuals,
    ModeledMetric,
    consensus_basis_stem,
)

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

#: **換算匯率容差**（2026-09-11 使用者定案：「你給個推薦數字」）。
#: provider 的 `year_ago_actual` 與一手稀釋 EPS 差在 1%–3% 之間時，判定為
#: 「同一個會計口徑、不同 FX 換算慣例」而不是「口徑不同」。
#:
#: **3% 這個數字是量出來的，不是挑的**（2026-09-11 全庫 13 檔有基期觀測＋同期
#: `year_ago_actual` 的樣本）：
#: - 11 檔**逐字相等**（0.00%）
#: - TSM **2.11%**——20-F 印的 10.43 用年末 NT$31.37，provider 的 10.65 隱含約年均價
#: - SOI.PA **46.84%**——那不是匯率，是真的口徑不同（yfinance 剔了減損）
#: 而「最近候選 vs **次近**候選」最窄的一檔是 002472.SZ 的 **4.70%**——容差一旦到那裡，
#: gaap 與 non_gaap 會同時落進容差內。2.11% 與 4.70% 之間**沒有任何樣本**，3% 落在中間。
#:
#: ⚠ 這個數字會隨樣本增加而需要重驗：跑 `_BASIS_TOLERANCE_PROBE` 註記的量測。
#: ⚠ 放寬的**只有識別**，判準反而更嚴（L15-4）——見 `verify_consensus_basis` 的三條。
#: ⚠ 代價要講明白：容忍 3% 的指紋差，等於接受 forward 比較裡最多約 3% 的換算誤差。
#: EPS gap 常在 5% 量級，所以這個殘差**必須印出來**，不得靜默吸收（`*_fx_tolerated`
#: 這個字彙存在的全部理由）。
_FX_TOLERATED_REL_TOL = 0.03

_METRIC_UNIT = {"eps": "currency_per_share", "revenue": "currency", "operating_margin": "ratio"}


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=_BASIS_MATCH_REL_TOL, abs_tol=_BASIS_MATCH_ABS_TOL)


def verify_consensus_basis(estimate: ConsensusEstimate, base: FiscalYearActuals | None) -> str:
    """判定一筆共識的會計口徑，回 `CONSENSUS_BASES` 的一個值。

    營收 → `not_applicable`；EPS 靠去年實際值核對。

    **兩段判定，順序不可反**（L15-3：先解析身分，再判它算不算數）：
    1. **逐字相等**（≤1%）：回 `gaap`／`non_gaap`。
    2. 都不逐字相等時才看**換算容差**（≤3%）：回 `gaap_fx_tolerated`／`non_gaap_fx_tolerated`。
    其餘一律 `unverified`。

    **放寬的只有識別，判準反而更嚴**（L15-4）——三條缺一就退回 `unverified`：
    - **exact 永遠贏**：只要有任何一個候選逐字相等，就不考慮容差段（否則
      non_gaap 逐字對上、gaap 剛好落在 3% 內時，答案會取決於字典序）。
    - **唯一性**：該段內恰好一個候選命中；0 個或 2 個都是 `unverified`
      （容差放寬後這條更重要，它是「寬容不會選錯」的唯一保證）。
    - **同號**：`_close` 走相對比，異號時 |ratio−1| ≥ 1 > 3%，自動排除。

    ⚠ 回 `*_fx_tolerated` 的那一筆**帶著一個已知的換算誤差**，
    `compare_metric` 會把它寫進 reason，呈現層不得把它壓回 `gaap`／`non_gaap` 講。
    """
    if estimate.metric != "eps":
        return "not_applicable"
    if base is None or estimate.year_ago_actual is None:
        return "unverified"
    if not base.period.same_as(estimate.period.shifted(-1)):
        return "unverified"                      # 去年實際值對應的不是我們手上的基期
    gaap_eps = base.gaap.get("diluted_eps") if base.gaap else None
    non_gaap_eps = base.non_gaap.get("diluted_eps") if base.non_gaap else None
    provider = float(estimate.year_ago_actual)
    candidates = [(name, float(value))
                  for name, value in (("gaap", gaap_eps), ("non_gaap", non_gaap_eps))
                  if value is not None]

    exact = [name for name, value in candidates if _close(value, provider)]
    if exact:
        return exact[0] if len(exact) == 1 else "unverified"

    tolerated = [name for name, value in candidates
                 if value and abs(provider / value - 1.0) <= _FX_TOLERATED_REL_TOL]
    if len(tolerated) == 1:
        return f"{tolerated[0]}_fx_tolerated"
    return "unverified"


def fx_tolerated_delta(estimate: ConsensusEstimate, base: FiscalYearActuals | None) -> float | None:
    """`*_fx_tolerated` 那一筆的殘差：provider ÷ 一手 − 1。認不出來回 None。

    這個數字**必須被印出來**——容忍 3% 的指紋差等於接受同量級的換算誤差進到 forward
    比較，而 EPS gap 常在 5% 量級。靜默吸收就是把訊號的一半換成噪音。
    """
    basis = verify_consensus_basis(estimate, base)
    if not basis.endswith("_fx_tolerated") or base is None or estimate.year_ago_actual is None:
        return None
    block = base.gaap if consensus_basis_stem(basis) == "gaap" else base.non_gaap
    value = (block or {}).get("diluted_eps")
    if value is None or not float(value):
        return None
    return float(estimate.year_ago_actual) / float(value) - 1.0


def describe_basis_mismatch(
    estimate: ConsensusEstimate, base: FiscalYearActuals | None
) -> str | None:
    """`unverified` 時把**兩個數字**寫出來，讓讀者自己看得出差多少。

    事發（2026-09-09 SOI.PA）：理由句只說「provider 未宣告且無法用去年實際值核實」，
    於是「差 2%」與「差 40%」長得一模一樣。而那兩種差距的處置完全相反——前者多半是
    換算匯率（TSM 實測：provider 10.65 用年均價、20-F 印的 10.43 用年末 NT$31.37），
    後者才是真的會計口徑不同。

    ⚠ 本函式**只描述，不分類**：它不宣稱差距的成因是匯率還是口徑。把
    `incompatible_basis` 拆成兩個訊號是 ROADMAP「`incompatible_basis` 兩義」那一條的事，
    需要先決定「願意接受多少換算差」——那是使用者的判斷，不是這裡能猜的。
    """
    if estimate.metric != "eps" or base is None or estimate.year_ago_actual is None:
        return None
    if not base.period.same_as(estimate.period.shifted(-1)):
        return None
    provider = float(estimate.year_ago_actual)
    parts: list[str] = []
    for name, block in (("gaap", base.gaap), ("non_gaap", base.non_gaap)):
        value = (block or {}).get("diluted_eps")
        if value is None:
            continue
        delta = (provider / float(value) - 1.0) if float(value) else None
        parts.append(f"一手 {name} {float(value):,.4g}"
                     + (f"（差 {delta:+.1%}）" if delta is not None else ""))
    if not parts:
        return None
    return (f"provider 去年實際 {provider:,.4g} vs " + "／".join(parts)
            + "——差距大小自己看：換算匯率差通常在個位數 %，會計口徑差不會")


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
    basis_detail: str | None = None,
    fx_delta: float | None = None,
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
        fx_translation_delta=(
            fx_delta if (consensus is not None
                         and str(consensus_basis).endswith("_fx_tolerated")) else None),
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
    fx_note: str | None = None
    if metric == "eps":
        stem = consensus_basis_stem(consensus_basis)
        if stem not in ("gaap", "non_gaap"):
            return _no("incompatible_basis",
                       f"共識口徑 {consensus_basis}：provider 未宣告且無法用去年實際值核實，"
                       f"不得與內部 {internal.accounting_basis} 相減"
                       + (f"｜{basis_detail}" if basis_detail else ""))
        if internal.accounting_basis != stem:
            return _no("incompatible_basis",
                       f"內部 {internal.accounting_basis} vs 共識 {stem}——口徑不同不得相減")
        if consensus_basis != stem:
            # 口徑認出來了，但 provider 與一手的換算率不同。比較成立，**殘差必須跟著走**——
            # 它與 gap 同量級時，讀者要看得出這個 gap 有多少是匯率而不是預期差。
            fx_note = (
                f"⚠ 共識口徑經**換算容差**認定為 {stem}（不是逐字相等）"
                + (f"：provider 的去年實際值較一手高 {fx_delta:+.1%}" if fx_delta is not None else "")
                + f"，容差上限 {_FX_TOLERATED_REL_TOL:.0%}。"
                "同一個換算差會原樣進到下面的 gap——**gap 小於這個殘差時不具意義**。"
                "要消掉它得用同一條 FX 路徑重算共識，不是調容差。"
            )
    if consensus.currency and internal_currency and consensus.currency.upper() != internal_currency.upper():
        return _no("incompatible_unit",
                   f"幣別不同：內部 {internal_currency} vs 共識 {consensus.currency}")
    absolute = internal.value - consensus.value
    relative = (internal.value / consensus.value - 1.0) if consensus.value > 0 else None
    reason = None if relative is not None else "共識非正，相對 gap 無定義（只給絕對 gap）"
    if fx_note:
        reason = f"{reason}｜{fx_note}" if reason else fx_note
    return ExpectationComparison(status="comparable", absolute_gap=absolute, relative_gap=relative,
                                 reason=reason, **common)


__all__ = ["compare_metric", "describe_basis_mismatch", "fx_tolerated_delta",
           "reconcile_consensus_base", "verify_consensus_basis"]
