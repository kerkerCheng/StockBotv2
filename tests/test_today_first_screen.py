"""NAV 比例區的 renderer（`portfolio.brief.render_nav_exposure`）。

⚠ 2026-09-23（Phase 0 Step 0b.3）：本檔原本守「瓶頸排序在前、NAV 在後」；瓶頸排序 pane
隨跨檔排序退役（G1／L19），5 條排序測試跟著退役。
⚠ 2026-09-23（Step 0b.4）：Engine D 證據缺口排序鍵（`decision_lab.brief._evidence_gap_order`）的 3 條
隨 decision_lab 研究側退役；today brief 本身也退役，NAV renderer 目前沒有組裝端消費，
留下的三條守的是 renderer 自己的「未注入不得靜默消失」判準。
"""
from __future__ import annotations

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


