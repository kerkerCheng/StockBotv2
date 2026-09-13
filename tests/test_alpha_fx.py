"""報表幣別 → 報價幣別的可稽核換算路徑（`alpha/fx.py`，2026-09-13）。

守的是三件事：
1. **同幣別不同尺度用 registry 的 factor**（定義值，不需要任何觀測）——IQE.L 的 GBP／GBp。
2. **真的跨幣別一定要一筆帶日期的觀測**，而且日期要對得上現價的 bar_date——6680.HK 的 CNY／HKD。
3. **換不了就回理由，絕不猜**；而且 `fair_value.currency` 永遠不被改寫。
"""
from __future__ import annotations

from datetime import date

import pytest

from alpha.errors import ContractViolation
from alpha.fx import FX_AS_OF_TOLERANCE_DAYS, FxObservation, convert_to_quote_unit

BAR = date(2026, 9, 11)


def _obs(base="CNY", quote="HKD", rate=1.0972, as_of=BAR, source="HKMA 每日中間價"):
    return FxObservation(base=base, quote=quote, rate=rate, as_of=as_of, source=source)


def test_same_currency_different_scale_needs_no_observation() -> None:
    """GBP → GBp 是**定義**不是市場價：registry 已經握著精確的 factor。"""
    conv, reason = convert_to_quote_unit(1.25, from_currency="GBP", to_unit="GBp",
                                         bar_date=BAR, observations=())
    assert reason is None and conv is not None
    assert conv.kind == "same_currency_scale"
    assert conv.factor == pytest.approx(100.0)          # 1 英鎊 ＝ 100 便士
    assert conv.value == pytest.approx(125.0)
    assert "registry" in conv.formula and "定義值不是市場價" in conv.formula
    assert conv.evidence_refs == ()                     # 不需要觀測，所以沒有 evidence


def test_cross_currency_without_an_observation_refuses_and_says_what_is_missing() -> None:
    """換不了就回理由——而理由要說出**缺的是一筆 mechanical 觀測**，不是缺研究。"""
    conv, reason = convert_to_quote_unit(50.0, from_currency="CNY", to_unit="HKD",
                                         bar_date=BAR, observations=())
    assert conv is None
    assert "缺 CNY → HKD 的匯率觀測" in (reason or "")
    assert "fx_rate" in (reason or "") and "不是缺研究" in (reason or "")
    # 有觀測但幣別對不上 → 一樣拒絕，而且把 ledger 裡有什麼列出來。
    conv2, reason2 = convert_to_quote_unit(50.0, from_currency="CNY", to_unit="HKD",
                                           bar_date=BAR, observations=(_obs(base="EUR", quote="SEK"),))
    assert conv2 is None and "EUR/SEK@2026-09-11" in (reason2 or "")


def test_cross_currency_observation_must_be_near_the_price_bar_date() -> None:
    """容忍帶是**天數**不是幅度：用幅度容忍等於自己決定「這個變動不重要」。"""
    stale = _obs(as_of=date(2026, 8, 1))
    conv, reason = convert_to_quote_unit(50.0, from_currency="CNY", to_unit="HKD",
                                         bar_date=BAR, observations=(stale,))
    assert conv is None and f"±{FX_AS_OF_TOLERANCE_DAYS} 天" in (reason or "")
    # 週末內（3 天）可以，而且會選最接近的那一筆。
    near = _obs(as_of=date(2026, 9, 9), rate=1.09)
    nearer = _obs(as_of=date(2026, 9, 10), rate=1.0972)
    conv2, reason2 = convert_to_quote_unit(50.0, from_currency="CNY", to_unit="HKD",
                                          bar_date=BAR, observations=(near, nearer))
    assert reason2 is None and conv2 is not None
    assert conv2.factor == pytest.approx(1.0972)        # 選 2026-09-10 那一筆
    assert conv2.as_of == date(2026, 9, 10)
    assert "1 CNY = 1.0972 HKD" in conv2.formula and "HKMA" in conv2.formula


def test_cross_currency_into_a_minor_unit_applies_both_the_rate_and_the_scale() -> None:
    """報價單位是 minor unit 時：先換幣別，再換尺度。少做一步就差 100 倍。"""
    conv, reason = convert_to_quote_unit(
        2.0, from_currency="USD", to_unit="GBp", bar_date=BAR,
        observations=(FxObservation(base="USD", quote="GBP", rate=0.75, as_of=BAR),))
    assert reason is None and conv is not None
    assert conv.factor == pytest.approx(75.0)           # 0.75 × (1 ÷ 0.01)
    assert conv.value == pytest.approx(150.0)
    assert "尺度" in conv.formula


def test_direction_and_identity_are_enforced_by_the_type() -> None:
    """方向寫在型別裡：反了會差一個倒數，而那種錯不會報錯。"""
    with pytest.raises(ContractViolation, match="rate 必須為正"):
        FxObservation(base="CNY", quote="HKD", rate=0.0, as_of=BAR)
    with pytest.raises(ContractViolation, match="同幣別不需要匯率觀測"):
        FxObservation(base="GBP", quote="gbp", rate=1.0, as_of=BAR)
    # 未登記**且非 ISO 形式**的單位一律拒絕——不猜。
    # ⚠ 三個大寫字母（例 "ZZZ"）會被 registry 當成 ISO 形式接受，那是刻意的：
    # 新幣別不該每次都要先改 config。真正擋下的是**不像幣別的字串**。
    conv, reason = convert_to_quote_unit(1.0, from_currency="CNY", to_unit="dollars",
                                        bar_date=BAR, observations=(_obs(),))
    assert conv is None and "不在 quote unit registry" in (reason or "")


def test_no_bar_date_means_no_cross_currency_conversion() -> None:
    """跨幣別換算需要一個日期，而不得用 ETL 日冒充行情交易日（F-27）。"""
    conv, reason = convert_to_quote_unit(50.0, from_currency="CNY", to_unit="HKD",
                                        bar_date=None, observations=(_obs(),))
    assert conv is None and "沒有 bar_date" in (reason or "")
