"""today 首屏：NAV 比例區與 Engine D 的證據缺口排序鍵。

⚠ 2026-09-23（Phase 0 Step 0b.3）：本檔原本守「瓶頸排序在前、NAV 在後」；瓶頸排序 pane
（`alpha.brief.render_ranking`）隨跨檔排序退役（G1／L19），5 條排序測試跟著退役，
NAV 的三條（含「未注入不得靜默消失」的鏡像）與 Engine D 排序鍵的兩條留下。
"""
from __future__ import annotations

from decision_lab.brief import _evidence_gap_order
from portfolio.brief import render_nav_exposure

NAV = {
    "status": "available",
    "positions": [{"ticker": "VWRA", "bucket": "大盤", "nav_pct": 0.217}],
    "cash_pct": 0.072,
    "buckets": {"大盤": 0.549, "CORE": 0.237},
    "groups": {"AI 光互連": 0.30},
}


def test_nav_renders_positions_and_distribution() -> None:
    text = "\n".join(render_nav_exposure(NAV))

    assert "VWRA" in text
    assert "大盤" in text
    assert "AI 光互連" in text


def test_nav_unavailable_is_not_zero_exposure() -> None:
    text = "\n".join(
        render_nav_exposure(
            {"status": "unavailable", "failure": "TimeoutError", "positions": []}
        )
    )

    assert "讀不到" in text
    assert "TimeoutError" in text
    assert "零曝險" in text


def test_absent_nav_says_so_instead_of_vanishing() -> None:
    """NAV 未注入時仍渲染區塊並說明原因。

    先前 `render_nav_exposure(None)` 回空 list，於是「呼叫端沒給持股」與「這個人
    沒有持股」在畫面上完全同形，整區靜默消失。（已退役的）排序區早就有這條斷言，
    NAV 沒有——**那個不對稱就是缺陷本身**，所以這條測試刻意寫成它的鏡像。
    """
    text = "\n".join(render_nav_exposure(None))

    assert "持股 NAV 比例" in text
    assert "未提供" in text
    assert "沒有持股" in text


def test_evidence_gap_order_reads_effective_level_not_declared_level() -> None:
    """排序讀實質等級。宣告 corroborated 但引用不成立的軸最該先看，不是最後看。

    `weakest_axis_of` 的 docstring 明文記過這個坑：`_validate_assessment` 在
    fatal_axis_blocker 時讓該軸失效卻不動宣告 `level`。首屏排序原本讀 `level`，
    等於在同一個坑上再踩一次。
    """
    items = [
        {
            "weakest_level": "corroborated",
            "weakest_effective_level": "unknown",
            "weakest_axis": "source_reliability",
            "company_id": "co:broken_ref",
        },
        {
            "weakest_level": "bounded_hypothesis",
            "weakest_effective_level": "bounded_hypothesis",
            "weakest_axis": "source_reliability",
            "company_id": "co:honest",
        },
    ]

    ordered = sorted(items, key=_evidence_gap_order)

    assert [i["company_id"] for i in ordered] == ["co:broken_ref", "co:honest"]


def test_items_sort_by_evidence_gap_not_capital_action() -> None:
    """排序鍵改為「誰最需要補證據」，不再是四動作的資本語意。"""
    items = [
        {"weakest_level": "corroborated", "weakest_axis": "source_reliability", "company_id": "co:b"},
        {"weakest_level": "unknown", "weakest_axis": "valuation_payoff", "company_id": "co:a"},
        {"weakest_level": "bounded_hypothesis", "weakest_axis": "source_reliability", "company_id": "co:c"},
    ]

    ordered = sorted(items, key=_evidence_gap_order)

    assert [i["company_id"] for i in ordered] == ["co:a", "co:c", "co:b"]


def test_unknown_level_sorts_first_not_last() -> None:
    """算不出等級的項目排最前——寧可多看一眼，也不要讓它沉到底部。"""
    items = [
        {"weakest_level": "unknown", "weakest_axis": "source_reliability", "company_id": "co:b"},
        {"weakest_level": None, "weakest_axis": None, "company_id": "co:a"},
    ]

    ordered = sorted(items, key=_evidence_gap_order)

    assert ordered[0]["company_id"] == "co:a"
