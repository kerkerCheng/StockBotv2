"""跨年的橋必須說出它跨幾年（2026-09-19，Phase 7 Step 7.2）。

⚠ 橋在算術上**一直**支援跨年：`revenue = base × (1 + growth)` 是一次乘法，
不管目標是明年還是五年後。危險就在這裡——`revenue_growth=0.5` 在 span 1 時是
「成長 50%」，在 span 5 時是「**五年累積**成長 50%」，而在今天之前**沒有任何地方
說出這件事**（L12：一個表示承載兩種語意）。

至今 63 檔的假設 span **全部是 1**（2026-09-19 實測：沒有任何一檔有兩個以上的目標年度），
所以這個兩義從來沒有現形過——而多年橋會讓它立刻變成一個每天都在誤導的數字。
**先分開再各自定規則**：橋自己算出 span 並在 > 1 時把語意寫進 warnings。
"""
from __future__ import annotations

from datetime import date

from alpha.fundamental.bridge import build_bridge
from alpha.fundamental.contracts import FiscalPeriod
from tests.test_reverse_bridge import _actuals, _full_set


def _bridge(target_year: int):
    return build_bridge(_actuals(), _full_set(growth=0.50),
                        FiscalPeriod(end=date(target_year, 6, 30)))


def test_one_year_span_is_silent() -> None:
    """基期 FY2026 → 目標 FY2027：span 1，**不加任何 warning**（這是至今唯一發生過的情況）。"""
    result = _bridge(2027)
    assert result.span_years == 1
    assert not [w for w in result.warnings if "累積值" in w]


def test_multi_year_span_says_the_growth_is_cumulative() -> None:
    result = _bridge(2030)
    assert result.span_years == 4
    warning = next((w for w in result.warnings if "累積值" in w), None)
    assert warning is not None, "跨年時必須說出成長率是累積值——否則 0.5 會被讀成「一年五成」"
    assert "4 年" in warning
    assert "不是年增率" in warning


def test_the_arithmetic_is_unchanged_because_that_is_the_point() -> None:
    """⚠ 橋**不該**替你把年化換算成累積——它只做一次乘法，而那是刻意的。

    換算等於替使用者決定「這個 0.5 是年化還是累積」，而那正是要他自己講清楚的那件事。
    """
    one = _bridge(2027).metrics["revenue"].value
    four = _bridge(2030).metrics["revenue"].value
    assert one == four, "同一組假設在不同 span 下算出同一個營收——差別只在它的意思"
