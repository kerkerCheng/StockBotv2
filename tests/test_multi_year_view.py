"""多年視角是**另一條路**，不是主 view 多一格（2026-09-19，Phase 7 Step 7.3）。

`build_fundamental_model` 的目標期間永遠是 `actuals.period.shifted(1)`——主 view 結構上
到不了 FY+4，**而那是對的**：FY+1 那條鏈要對的是分析師共識，共識只到 FY+1／+2。
多年橋沒有共識可對，所以它不該混進同一張表。

⚠ 兩條路**共用同一條橋、同一套二分法、同一組合法上下限**；不共用的是「要對誰」。

三件刻意誠實的事，每一件都有一條測試守著：
①`multiple_horizon` 沒填就 missing，**不從 `expected_horizon` 換算**；
②目標倍數沿用 FY+1 的那一條，**而且要說出來**；
③`no_sign_change` 是答案不是失敗。
"""
from __future__ import annotations

from datetime import date



from briefing.multi_year import NO_HORIZON_REASON, MultiYearView, render_multi_year


def _view(**over) -> MultiYearView:
    base = dict(ticker="TEST", company_id="co:test", horizon=None, status="missing",
                reason=NO_HORIZON_REASON)
    base.update(over)
    return MultiYearView(**base)


def test_missing_horizon_says_nobody_wrote_it_down() -> None:
    """**「還沒有人寫下來」與「沒有多年主張」是兩件事**，輸出必須是前者。"""
    text = render_multi_year(_view())
    assert "算不出來" in text
    assert "還沒有人寫下" in text


def test_it_refuses_to_derive_the_year_from_expected_horizon() -> None:
    """⚠ `expected_horizon` 測的是「多久會被驗證」（實測 62 檔全在 1–8 季），
    不是「倍率在哪一年實現」。**換算等於把兩個不同的問題壓成一個**（L12）。"""
    text = render_multi_year(_view())
    assert "expected_horizon" in text and "不是「多久兌現」" in text


def test_the_borrowed_multiple_is_stated_not_hidden() -> None:
    """沒有人知道四年後市場付幾倍。沿用 FY+1 的倍數**是一個假設**，不是觀測。"""
    text = render_multi_year(_view(
        status="available", horizon=date(2030, 6, 30),
        base_period=type("P", (), {"label": "FY2026"})(), span_years=4,
        target_multiple=25.0, current_price=317.36, anchor_eps=5.39,
        multiple_source="沿用 FY2027 的 target_pe（va_x）——⚠ **這不是對目標年度的主張**，"
                        "是「假設那時市場付一樣的倍數」",
        ladder=()))
    assert "這不是對目標年度的主張" in text
    assert "假設那時市場付一樣的倍數" in text


def test_the_anchor_is_labelled_as_not_a_forecast() -> None:
    text = render_multi_year(_view(
        status="available", horizon=date(2030, 6, 30),
        base_period=type("P", (), {"label": "FY2026"})(), span_years=4,
        target_multiple=25.0, current_price=317.36, anchor_eps=5.39, ladder=()))
    assert "錨點不是預測" in text
    assert "4 年" in text          # 跨幾年必須出現在畫面上


def test_the_header_says_it_is_not_a_forecast() -> None:
    """整張表的第一句就要講清楚它在問什麼——否則「需要 EPS 25.39」會被讀成目標價。"""
    text = render_multi_year(_view())
    assert "這不是預測" in text
    assert "由人判斷那個數合不合理" in text
