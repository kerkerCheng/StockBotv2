"""Coverage Pilot（2026-09-07）：整條 Evidence → … → Analyst View 是否只對 COHR 成立。

Pilot 標的挑成 heterogeneous（非 USD 報價／資料不完整／商業模式不同），目的不是「三檔都變綠」，
而是**對不同資料形態，系統要嘛產生可追溯的完整 view，要嘛在正確的層級 fail closed**。

本檔守兩個在 Pilot 中被實測揪出的 generic 缺陷（兩個都不是 COHR 會遇到的，所以既有測試全綠）：

1. **報價單位 ≠ 結算幣別的判準自己折疊了大小寫。** `units_comparable` 原本寫
   `a.upper() != b.upper()`，於是 `GBp`（便士）與 `GBP`（英鎊）被判為同尺度——而**那正是這道
   gate 唯一要擋的 case**（`GBX`／`ILA`／`ZAc` 只是因為字母剛好不同才被偶然攔下）。
   修法是走 `identity/currency.py` 這個唯一 registry（L16：分類已有 SSOT 就不要在下游重造）。

2. **本益比法被套在虧損公司身上。** 負的內部 EPS × 目標倍數 ＝ 負的 fair value，gap 判
   `comparable`、relative_gap −100.8%，並以〔確定性規則〕呈現成隱含報酬。做多部位不可能跌超過
   100%——這不是缺料，是 method 不適用，必須在 valuation 層 fail closed（L12：缺料與不適用
   是兩種語意，不得共用一個表示）。
"""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from alpha.fundamental.compare import reconcile_consensus_base
from alpha.fundamental.contracts import (
    COMPARISON_STATUSES,
    FiscalPeriod,
    FiscalYearActuals,
    ModeledMetric,
)
from alpha.valuation.contracts import METHOD_FORWARD_EARNINGS_MULTIPLE, method_applicability
from alpha.valuation.model import units_comparable
from tests.test_fundamental_model import _actuals, _consensus, _run
from tests.test_implied_return import TODAY, _horizon, _return, _valued
from tests.test_valuation_model import PRICE, _index, _valuation

ROOT = Path(__file__).resolve().parents[1]
MINOR_UNITS = json.loads((ROOT / "config" / "currency_units.json").read_text(encoding="utf-8"))["quote_units"]


# ---------------------------------------------------------------------------
# 1. 報價單位 ≠ 結算幣別
# ---------------------------------------------------------------------------

def test_pence_quote_against_pound_reporting_currency_is_not_comparable() -> None:
    """IQE.L 的實際形狀：報表幣別 GBP、報價單位 GBp。差 100 倍，不得相減。"""
    status, why = units_comparable("GBP", "GBp")
    assert status == "incompatible_unit"
    assert "100" in why and "GBp" in why


@pytest.mark.parametrize("unit", MINOR_UNITS, ids=lambda u: u["quote_code"])
def test_every_registered_minor_unit_is_incompatible_with_its_settlement_currency(unit) -> None:
    """判準綁 registry 而不是綁字串：日後在 `config/currency_units.json` 新增一列即自動受測。"""
    assert units_comparable(unit["currency"], unit["quote_code"])[0] == "incompatible_unit"
    assert units_comparable(unit["quote_code"], unit["currency"])[0] == "incompatible_unit"
    # 同一個 minor unit 對自己仍然可比——修法不是「一律拒絕」。
    assert units_comparable(unit["quote_code"], unit["quote_code"])[0] == "comparable"


def test_iso_currencies_still_compare_and_unknown_codes_fail_open_to_unverified() -> None:
    assert units_comparable("AUD", "AUD")[0] == "comparable"      # LYC.AX
    assert units_comparable("JPY", "JPY")[0] == "comparable"      # 6324.T
    assert units_comparable("TWD", "TWD")[0] == "comparable"      # 3081.TWO
    assert units_comparable("usd", "USD")[0] == "comparable"      # 大小寫不敏感只適用於 ISO code
    assert units_comparable("USD", "JPY")[0] == "incompatible_unit"
    assert units_comparable("XX", "USD")[0] == "unverified_unit"  # 未登記且非 ISO 形式 → 不猜
    assert units_comparable(None, "USD")[0] == "unverified_unit"


def test_gap_and_return_both_refuse_when_the_price_is_quoted_in_a_minor_unit() -> None:
    """fair value 照算（它不依賴 price），但 gap 與隱含報酬都必須拒絕。"""
    pence = replace(PRICE, unit="GBp")
    valuation = _valued(price=pence)
    assert valuation.status == "available" and valuation.fair_value is not None
    assert valuation.gap.status == "incompatible_unit"
    assert valuation.gap.absolute_gap is None and valuation.gap.relative_gap is None
    result = _return(valuation, price=pence)
    assert result.status == "missing"
    assert "incompatible_unit" in (result.reason or "")


# ---------------------------------------------------------------------------
# 2. 估值方法適用性（虧損公司）
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("eps", [-0.02, -1.0, 0.0])
def test_forward_pe_is_declared_not_applicable_for_non_positive_earnings(eps: float) -> None:
    reason = method_applicability(METHOD_FORWARD_EARNINGS_MULTIPLE, eps)
    assert reason is not None and "不適用" in reason


def test_positive_earnings_remain_applicable_so_the_guard_is_not_a_blanket_refusal() -> None:
    assert method_applicability(METHOD_FORWARD_EARNINGS_MULTIPLE, 8.94) is None
    assert method_applicability(METHOD_FORWARD_EARNINGS_MULTIPLE, None) is None   # 缺料走 missing 路徑


def _model_with_eps(value: float | None):
    """把跑出來的 COHR 模型的內部 EPS 換成 Pilot 想測的值，其餘一格不動。"""
    model = _run(index=_index())
    metric = model.metrics["eps"]
    swapped = (replace(metric, value=value) if value is not None
               else replace(metric, value=None, input_dependency=None, reason="內部 eps 缺席（測試）"))
    return replace(model, metrics={**model.metrics, "eps": swapped})


def test_negative_internal_eps_fails_closed_at_the_valuation_layer() -> None:
    """SIVE.ST／IQE.L 的形狀：期間對、口徑對、資料齊全——method 本身不適用。"""
    result = _valuation(model=_model_with_eps(-0.02))
    assert result.status == "missing" and result.fair_value is None
    assert "不適用" in (result.reason or "")
    assert "valuation_method_not_applicable:forward_earnings_multiple" in [
        w.replace("：", ":") for w in result.warnings]
    # gap 也不得留下任何數字——包含 implied_multiple_at_price：盈餘為負時 price/eps 是
    # 負的本益比（−14,093x），那和負的 fair value 一樣沒有意義。
    assert result.gap.status == "fair_value_missing"
    assert result.gap.absolute_gap is None and result.gap.implied_multiple_at_price is None
    assert not [s for s in result.steps if s.key == "implied_multiple_at_price"]


def test_the_refusal_says_not_applicable_not_missing_data() -> None:
    """L12：`缺料` 與 `方法不適用` 是兩種語意，訊息必須分得開。"""
    not_applicable = _valuation(model=_model_with_eps(-0.02)).reason or ""
    missing = _valuation(model=_model_with_eps(None)).reason or ""
    assert "不適用" in not_applicable and "缺席" not in not_applicable
    assert "缺席" in missing and "不適用" not in missing


def test_implied_return_is_missing_when_the_method_does_not_apply() -> None:
    valuation = _valuation([_valued().assumptions[0]], model=_model_with_eps(-0.02))
    result = _return(valuation)
    assert result.status == "missing" and result.price_return is None


# ---------------------------------------------------------------------------
# 3. 共識與基期對帳（單體 vs 合併）
# ---------------------------------------------------------------------------

def test_revenue_consensus_whose_year_ago_actual_misses_the_base_is_not_subtracted() -> None:
    """6324.T 的實際形狀：EPS 的 year_ago 是連結、營收的 year_ago 是單體。"""
    base = _actuals()
    parent_only = _consensus("revenue", 74_682_164_000.0, year_ago=base.revenue * 0.561)
    assert reconcile_consensus_base(parent_only, base) is not None
    model = _run(consensus=(parent_only,), index=_index())
    revenue_cmp = model.comparisons["revenue"]
    assert revenue_cmp.status == "unreconciled_base"
    assert revenue_cmp.absolute_gap is None and revenue_cmp.relative_gap is None
    assert "對不上" in (revenue_cmp.reason or "")


def test_revenue_consensus_that_reconciles_is_still_subtracted() -> None:
    """守住非空跑：對得上帳的照比，這不是一道恆亮的牆（L14 的『不會滅』測試）。"""
    base = _actuals()
    good = _consensus("revenue", 10_618_193_080.0, year_ago=base.revenue)
    assert reconcile_consensus_base(good, base) is None
    assert _run(consensus=(good,), index=_index()).comparisons["revenue"].status == "comparable"


def test_reconciliation_is_scoped_to_revenue_because_eps_is_already_checked() -> None:
    """EPS 的同一件事在 `verify_consensus_basis` 裡做；不讓同一個問題有兩個名字（L12）。"""
    base = _actuals()
    assert reconcile_consensus_base(_consensus("eps", 9.4, year_ago=1.0), base) is None
    # 無從檢查（沒有基期／沒有 year_ago）≠ 檢查通過，但也不因此拒絕
    assert reconcile_consensus_base(_consensus("revenue", 1.0, year_ago=None), base) is None
    assert reconcile_consensus_base(_consensus("revenue", 1.0, year_ago=1.0), None) is None


def test_read_model_covers_every_comparison_status() -> None:
    """`_COMPARISON_STATUS_TO_DATUM` 是直接索引，漏一個就是整個 section 爆掉（L16）。"""
    from briefing.alpha_view.builder import _COMPARISON_STATUS_TO_DATUM

    assert set(COMPARISON_STATUSES) <= set(_COMPARISON_STATUS_TO_DATUM)


# ---------------------------------------------------------------------------
# 4. implied_multiple_at_price 不該綁在 fair value 上
# ---------------------------------------------------------------------------

def test_market_multiple_on_internal_eps_is_available_without_a_target_multiple() -> None:
    """6324.T 的實際形狀：刻意不寫目標倍數，但『市場為我們的 EPS 付幾倍』照樣要看得到。"""
    result = _valuation([])                                   # ledger 空 → 沒有 fair value
    assert result.status == "missing" and result.fair_value is None
    eps = _run(index=_index()).metrics["eps"].value
    assert result.gap.implied_multiple_at_price == pytest.approx(PRICE.value / eps)
    step = next(s for s in result.steps if s.key == "implied_multiple_at_price")
    assert step.value == pytest.approx(PRICE.value / eps) and step.basis == "deterministic"


def test_market_multiple_is_withheld_when_the_units_do_not_match() -> None:
    """它是 price ÷ EPS——尺度不同時算出來的數字沒有意義，寧可沒有。"""
    result = _valuation([], price=replace(PRICE, unit="GBp"))
    assert result.gap.implied_multiple_at_price is None
    assert not [s for s in result.steps if s.key == "implied_multiple_at_price"]


# ---------------------------------------------------------------------------
# 5. 固定警語不得對「這一檔屬於哪個產業」下斷言
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
# 6. 口徑判定的容忍度不得隨 EPS 的尺度失效
# ---------------------------------------------------------------------------

def _pence_scale_base():
    """IQE.L FY2025 的實際形狀：GAAP 稀釋 EPS −0.0377、adjusted −0.0282，兩者只差 0.0095。"""
    from alpha.fundamental.contracts import FiscalPeriod, FiscalYearActuals
    from tests.test_fundamental_model import ACT_REF

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
    from tests.test_fundamental_model import _actuals

    base = _actuals()
    assert verify_consensus_basis(_consensus("eps", 9.41634, year_ago=5.61), base) == "non_gaap"
    assert verify_consensus_basis(_consensus("eps", 9.41634, year_ago=4.12), base) == "gaap"


# ---------------------------------------------------------------------------
# 換算匯率容差（2026-09-11）：把 `unverified` 的兩種語意拆開
# ---------------------------------------------------------------------------

def _single_candidate_base(diluted_eps: float = 10.43):
    """只有 gaap 區塊的基期——TSM 的形狀（20-F 沒印 adjusted EPS）。"""
    from tests.test_fundamental_model import ACT_REF

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
    from tests.test_fundamental_model import ACT_REF

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
    from tests.test_fundamental_model import ACT_REF

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


def test_a_tolerated_comparison_carries_its_residual_as_a_number_not_only_prose() -> None:
    """殘差是結構化欄位——下游要拿它比大小，不得 parse 理由句（L16）。"""
    from alpha.fundamental.compare import compare_metric

    internal = ModeledMetric(
        metric="eps", period=FiscalPeriod(end=date(2026, 12, 31)), value=12.5,
        unit="currency_per_share", accounting_basis="gaap", input_dependency="session_judgment")
    est = _consensus("eps", 12.0, period=FiscalPeriod(end=date(2026, 12, 31)), year_ago=10.65)
    cmp_ = compare_metric("eps", internal, est, consensus_basis="gaap_fx_tolerated",
                          internal_currency="USD", fx_delta=0.0211)
    assert cmp_.status == "comparable"
    assert cmp_.fx_translation_delta == pytest.approx(0.0211)
    assert "換算容差" in (cmp_.reason or "")


def test_a_lever_smaller_than_the_residual_says_so_instead_of_looking_like_a_finding() -> None:
    """TSM 實測：倍數桿 +1.71% 配 +2.11% 殘差——**它在雜訊裡**，畫面必須講出來。

    這條守的是「放寬識別」不得變成「拿精度換覆蓋率而不說」。
    """
    from alpha.implied_return.attribution import noise_floor_note

    note = noise_floor_note(fx_delta=0.0211, eps_contribution=-0.0000005, multiple_contribution=0.01715)
    assert note is not None and "雜訊裡" in note and "EPS 桿" in note and "倍數桿" in note
    # 殘差不存在（逐字相等）或桿明顯大於殘差時不得亂講話
    assert noise_floor_note(fx_delta=None, eps_contribution=0.3, multiple_contribution=0.4) is None
    assert noise_floor_note(fx_delta=0.0211, eps_contribution=0.30, multiple_contribution=0.25) is None
