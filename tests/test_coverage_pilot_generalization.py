"""Coverage Pilot（2026-09-07）：整條 Evidence → … → Analyst View 是否只對 COHR 成立。

Pilot 標的挑成 heterogeneous（非 USD 報價／資料不完整／商業模式不同），目的不是「三檔都變綠」，
而是**對不同資料形態，系統要嘛產生可追溯的完整 view，要嘛在正確的層級 fail closed**。

⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：本檔原本 25 條，其中 16 條守的是估值鏈的判準——
報價單位 vs 結算幣別在 fair value gap 上的拒絕（`units_comparable`）、本益比法不套在虧損公司上
（`method_applicability`）、市場付的倍數不綁 fair value、內部 vs 共識的比較狀態表、換算殘差在兩桿
拆解上的雜訊註記——那些機制整組退役，測試跟著退役。**留下的九條守資料層的機械比對**：
共識的營收要與基期對得上帳（單體 vs 合併）、EPS 口徑靠去年實際值核實、容差不得吞掉最窄的
gaap↔non_gaap 間距；以及固定警語不得對本檔產業下斷言。
"""
from __future__ import annotations

from datetime import date

import pytest

from alpha.fundamental.compare import reconcile_consensus_base
from alpha.fundamental.contracts import FiscalPeriod, FiscalYearActuals
from tests.fixtures_fundamental import _actuals, _consensus


# ---------------------------------------------------------------------------
# 1. 共識與基期對帳（單體 vs 合併）
# ---------------------------------------------------------------------------

def test_revenue_consensus_whose_year_ago_actual_misses_the_base_is_flagged() -> None:
    """6324.T 的實際形狀：EPS 的 year_ago 是連結、營收的 year_ago 是單體。"""
    base = _actuals()
    parent_only = _consensus("revenue", 74_682_164_000.0, year_ago=base.revenue * 0.561)
    why = reconcile_consensus_base(parent_only, base)
    assert why is not None and "對不上" in why and "43.9%" in why


def test_revenue_consensus_that_reconciles_is_not_flagged() -> None:
    """守住非空跑：對得上帳的不報，這不是一道恆亮的牆（L14 的『不會滅』測試）。"""
    base = _actuals()
    good = _consensus("revenue", 10_618_193_080.0, year_ago=base.revenue)
    assert reconcile_consensus_base(good, base) is None


def test_reconciliation_is_scoped_to_revenue_because_eps_is_already_checked() -> None:
    """EPS 的同一件事在 `verify_consensus_basis` 裡做；不讓同一個問題有兩個名字（L12）。"""
    base = _actuals()
    assert reconcile_consensus_base(_consensus("eps", 9.4, year_ago=1.0), base) is None
    # 無從檢查（沒有基期／沒有 year_ago）≠ 檢查通過，但也不因此拒絕
    assert reconcile_consensus_base(_consensus("revenue", 1.0, year_ago=None), base) is None
    assert reconcile_consensus_base(_consensus("revenue", 1.0, year_ago=1.0), None) is None


# ---------------------------------------------------------------------------
# 2. 固定警語不得對「這一檔屬於哪個產業」下斷言
# ---------------------------------------------------------------------------

def test_correlation_warning_is_about_the_graph_not_about_this_company() -> None:
    """它無條件掛在每一檔的單檔 view 上，所以任何產業斷言都會對某些檔變成假話。

    Pilot 實測：LYC.AX（稀土）與 6324.T（機器人減速機）都被寫成「高度集中於 AI 光互連」。
    要條件化就得有一份「這檔屬於哪個群」的分類，而系統沒有那個 SSOT——在下游自己猜一份
    正是 L16 的形狀。所以修法是把主詞放回圖，不是加分類。
    """
    from briefing.alpha_view.builder import CORRELATION_WARNING

    assert "這份圖的組成" in CORRELATION_WARNING
    assert "不是對本檔所屬產業的斷言" in CORRELATION_WARNING


# ---------------------------------------------------------------------------
# 3. 口徑判定的容忍度不得隨 EPS 的尺度失效
# ---------------------------------------------------------------------------

def _pence_scale_base():
    """IQE.L FY2025 的實際形狀：GAAP 稀釋 EPS −0.0377、adjusted −0.0282，兩者只差 0.0095。"""
    from tests.fixtures_fundamental import ACT_REF

    return FiscalYearActuals(
        period=FiscalPeriod(end=date(2025, 12, 31)), currency="GBP", revenue=97_300_000.0,
        segment_revenue=None, gaap={"diluted_eps": -0.0377}, non_gaap={"diluted_eps": -0.0282},
        evidence=(ACT_REF,))


def test_basis_is_identified_at_pence_scale_where_an_absolute_tolerance_would_blur_it() -> None:
    """絕對容忍 0.011 會讓兩個候選一起命中 → `unverified`；而 −0.0282 精確等於 adjusted。

    這不是「無法判定」，是尺度把判準稀釋掉了（L15-1：gate 攔下的不是它想攔的東西）。
    """
    from alpha.fundamental.compare import verify_consensus_basis

    base = _pence_scale_base()
    estimate = _consensus("eps", -0.01158, period=FiscalPeriod(end=date(2026, 12, 31)),
                          year_ago=-0.0282, currency="GBP")
    assert verify_consensus_basis(estimate, base) == "non_gaap"


def test_a_year_ago_actual_matching_neither_candidate_is_still_unverified() -> None:
    """守住非空跑：拿掉絕對容忍不是把判準放寬成永遠命中。"""
    from alpha.fundamental.compare import verify_consensus_basis

    base = _pence_scale_base()
    estimate = _consensus("eps", -0.01158, period=FiscalPeriod(end=date(2026, 12, 31)),
                          year_ago=-0.0500, currency="GBP")
    assert verify_consensus_basis(estimate, base) == "unverified"


def test_dollar_scale_identification_is_unchanged() -> None:
    """COHR 的形狀（5.61 non-GAAP vs 4.12 GAAP）不因為拿掉絕對容忍而改變。"""
    from alpha.fundamental.compare import verify_consensus_basis

    base = _actuals()
    assert verify_consensus_basis(_consensus("eps", 9.41634, year_ago=5.61), base) == "non_gaap"
    assert verify_consensus_basis(_consensus("eps", 9.41634, year_ago=4.12), base) == "gaap"


# ---------------------------------------------------------------------------
# 換算匯率容差（2026-09-11）：把 `unverified` 的兩種語意拆開
# ---------------------------------------------------------------------------

def _single_candidate_base(diluted_eps: float = 10.43):
    """只有 gaap 區塊的基期——TSM 的形狀（20-F 沒印 adjusted EPS）。"""
    from tests.fixtures_fundamental import ACT_REF

    return FiscalYearActuals(
        period=FiscalPeriod(end=date(2025, 12, 31)), currency="USD", revenue=1.0e11,
        segment_revenue=None, gaap={"diluted_eps": diluted_eps}, non_gaap=None,
        evidence=(ACT_REF,))


def test_translation_difference_is_no_longer_the_same_signal_as_a_basis_difference() -> None:
    """TSM 2.11%（換算率）與 SOI.PA 46.84%（真的口徑不同）不得再共用一個訊號。

    2026-09-11 實測 13 檔樣本：11 檔逐字相等、TSM 2.11%、SOI.PA 46.84%——
    2.11% 與「最窄的 gaap↔non_gaap 間距 4.70%」之間沒有任何樣本，容差 3% 落在中間。
    """
    from alpha.fundamental.compare import fx_tolerated_delta, verify_consensus_basis

    base = _single_candidate_base()                       # 一手 10.43（年末 NT$31.37）
    tsm = _consensus("eps", 12.0, period=FiscalPeriod(end=date(2026, 12, 31)), year_ago=10.65)
    assert verify_consensus_basis(tsm, base) == "gaap_fx_tolerated"
    assert fx_tolerated_delta(tsm, base) == pytest.approx(0.0211, abs=5e-4)

    soi = _consensus("eps", 12.0, period=FiscalPeriod(end=date(2026, 12, 31)), year_ago=-3.28)
    assert verify_consensus_basis(soi, _single_candidate_base(-6.17)) == "unverified"
    assert fx_tolerated_delta(soi, _single_candidate_base(-6.17)) is None


def test_exact_match_always_beats_a_tolerated_one() -> None:
    """放寬的只有識別，判準反而更嚴（L15-4）。

    non_gaap 逐字相等、gaap 剛好落在 3% 內時，答案不得取決於字典序。
    """
    from alpha.fundamental.compare import verify_consensus_basis
    from tests.fixtures_fundamental import ACT_REF

    base = FiscalYearActuals(
        period=FiscalPeriod(end=date(2025, 12, 31)), currency="USD", revenue=1.0e10,
        segment_revenue=None, gaap={"diluted_eps": 5.75}, non_gaap={"diluted_eps": 5.61},
        evidence=(ACT_REF,))                              # 5.61 與 5.75 只差 2.5%
    est = _consensus("eps", 9.0, period=FiscalPeriod(end=date(2026, 12, 31)), year_ago=5.61)
    assert verify_consensus_basis(est, base) == "non_gaap", "逐字相等的那個必須贏"


def test_two_candidates_inside_the_tolerance_fail_closed() -> None:
    """容差內恰好一個才算數——0 個或 2 個都是 unverified。

    這是「寬容不會選錯」的唯一保證：放寬只可能讓答案退回不知道，不會讓它選錯一個。
    """
    from alpha.fundamental.compare import verify_consensus_basis
    from tests.fixtures_fundamental import ACT_REF

    base = FiscalYearActuals(
        period=FiscalPeriod(end=date(2025, 12, 31)), currency="USD", revenue=1.0e10,
        segment_revenue=None, gaap={"diluted_eps": 5.70}, non_gaap={"diluted_eps": 5.80},
        evidence=(ACT_REF,))
    est = _consensus("eps", 9.0, period=FiscalPeriod(end=date(2026, 12, 31)), year_ago=5.75)
    assert verify_consensus_basis(est, base) == "unverified"


def test_the_tolerance_stops_short_of_the_narrowest_observed_basis_gap() -> None:
    """3% 不是挑的，是量出來的：必須低於 002472.SZ 的 4.70%（最窄的 gaap↔non_gaap 間距）。

    這條會在有人把容差調到 4.7% 以上時變紅——那一刻 gaap 與 non_gaap 開始互相污染。
    """
    from alpha.fundamental.compare import _FX_TOLERATED_REL_TOL, _BASIS_MATCH_REL_TOL

    assert _BASIS_MATCH_REL_TOL < _FX_TOLERATED_REL_TOL < 0.047
