"""today 首屏：瓶頸排序在前、NAV 比例在後。

系統終點是「哪些標的值得看」，不是「今天要不要動作」——首屏順序要反映這件事。
"""
from __future__ import annotations

from decision_lab.brief import _evidence_gap_order, _render_nav_exposure, _render_ranking

RANKING = {
    "actionable": [
        {
            "rank": 1, "ticker": "COHR", "company_id": "co:coherent",
            "bottleneck": "co:nvidia", "substitutability": 5, "sole_source": True,
            "evidence": "externally_corroborated", "weakest_axis": "technical_causal_link",
            "no_demand_anchor": False,
        }
    ],
    "actionable_total": 27,
    "actionable_purpose": "現在能投什麼",
    "structural": [
        {
            "rank": 1, "ticker": "AVGO", "company_id": "co:broadcom",
            "bottleneck": "tech:cpo", "substitutability": 5, "sole_source": True,
            "evidence": "needs_review", "weakest_axis": None,
            "no_demand_anchor": False,
        }
    ],
    "structural_total": 27,
    "structural_purpose": "該去補誰的證據",
    "judgment_note": "這是研究判斷，不是回測結果",
    "caveats": ["substitutability 覆蓋 60/413"],
}

NAV = {
    "status": "available",
    "positions": [{"ticker": "VWRA", "bucket": "大盤", "nav_pct": 0.217}],
    "cash_pct": 0.072,
    "buckets": {"大盤": 0.549, "CORE": 0.237},
    "groups": {"AI 光互連": 0.30},
}


def test_ranking_renders_both_orderings_with_their_purposes() -> None:
    text = "\n".join(_render_ranking(RANKING))

    assert "現在能投什麼" in text
    assert "該去補誰的證據" in text
    assert "COHR" in text and "AVGO" in text
    assert text.index("現在能投什麼") < text.index("該去補誰的證據")


def test_ranking_shows_total_when_truncated() -> None:
    """截斷要現形——使用者要知道自己只看到前幾名。"""
    text = "\n".join(_render_ranking(RANKING))

    assert "共 27 個候選" in text


def test_ranking_carries_judgment_note_and_caveats() -> None:
    text = "\n".join(_render_ranking(RANKING))

    assert "不是回測" in text
    assert "60/413" in text


def test_absent_ranking_says_so_instead_of_vanishing() -> None:
    """排序缺席時仍渲染區塊並說明原因——整段消失會被讀成「沒有候選」。"""
    text = "\n".join(_render_ranking(None))

    assert "瓶頸排序" in text
    assert "不是" in text and "沒有候選" in text


def test_nav_renders_positions_and_distribution() -> None:
    text = "\n".join(_render_nav_exposure(NAV))

    assert "VWRA" in text
    assert "大盤" in text
    assert "AI 光互連" in text


def test_nav_unavailable_is_not_zero_exposure() -> None:
    text = "\n".join(
        _render_nav_exposure(
            {"status": "unavailable", "failure": "TimeoutError", "positions": []}
        )
    )

    assert "讀不到" in text
    assert "TimeoutError" in text
    assert "零曝險" in text


def test_absent_nav_says_so_instead_of_vanishing() -> None:
    """NAV 未注入時仍渲染區塊並說明原因——與排序區同一個處置。

    先前 `_render_nav_exposure(None)` 回空 list，於是「呼叫端沒給持股」與「這個人
    沒有持股」在畫面上完全同形，整區靜默消失。排序區早就有這條斷言
    （`test_absent_ranking_says_so_instead_of_vanishing`），NAV 沒有——**那個不對稱
    就是缺陷本身**，所以這條測試刻意寫成它的鏡像。
    """
    text = "\n".join(_render_nav_exposure(None))

    assert "持股 NAV 比例" in text
    assert "未提供" in text
    assert "沒有持股" in text


def test_first_screen_order_is_ranking_then_nav() -> None:
    """R1：排序在前、NAV 在後。"""
    combined = "\n".join(_render_ranking(RANKING) + _render_nav_exposure(NAV))

    assert combined.index("瓶頸排序") < combined.index("持股 NAV 比例")


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
