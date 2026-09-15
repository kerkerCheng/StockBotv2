"""V2 gap closure（`alpha/gap_closure.py`＋read model 兩格，2026-09-15）——不需要 Neo4j／Engine C。

守的是三件事：
1. **量測不是訊號**：比例只是 (現值−起點)÷(我們的值−起點)；起點等於我們的值時無定義（None，不是 0）。
2. **起點是判斷日之後第一筆**：判斷日之後沒有抓取就是 missing，不拿最後一筆冒充「沒動」。
3. **目標價比較是機械的且措辭中性**：「高於」同時涵蓋市場比我們樂觀與該收割，不是賣出指令。
"""
from __future__ import annotations

from datetime import date

import pytest

from alpha.gap_closure import consensus_progress, target_reached
from alpha.narrative import FORBIDDEN_TERMS
from alpha.narrative.argument import closure_phrase, timeline_paragraph

P = [(date(2026, 9, 4), 9.0), (date(2026, 9, 8), 9.2), (date(2026, 9, 14), 9.4)]


def test_progress_is_a_fraction_of_the_distance_toward_our_value() -> None:
    out = consensus_progress(P, since=date(2026, 9, 7), our_value=10.0)
    assert out["status"] == "available" and out["start_date"] == date(2026, 9, 8) and out["now_value"] == 9.4
    assert out["closed_fraction"] == pytest.approx((9.4 - 9.2) / (10.0 - 9.2))
    assert out["n_points"] == 2
    # 反向移動是負數，不是 0；起點等於我們的值時無定義
    assert consensus_progress(P, since=None, our_value=8.0)["closed_fraction"] == pytest.approx((9.4 - 9.0) / (8.0 - 9.0))
    assert consensus_progress([(date(2026, 9, 4), 9.0), (date(2026, 9, 5), 9.5)], since=None, our_value=9.0)["closed_fraction"] is None


def test_no_capture_after_judgment_is_missing_not_zero() -> None:
    out = consensus_progress(P, since=date(2026, 9, 20), our_value=10.0)
    assert out["status"] == "missing" and "尚無共識抓取" in out["reason"]
    assert consensus_progress([], since=None, our_value=10.0)["status"] == "missing"


def test_target_reached_is_mechanical_and_neutral() -> None:
    out = target_reached(price=266.5, base_target=223.6, bet_target=243.97)
    assert out["base_reached"] and out["bet_reached"] and out["any_reached"]
    assert "不是賣出指令" in out["rule"]
    assert target_reached(price=200.0, base_target=223.6, bet_target=None)["any_reached"] is False
    assert target_reached(price=None, base_target=1.0, bet_target=None)["status"] == "missing"


def test_phrases_are_plain_and_say_when_consensus_did_not_move() -> None:
    still = {"base": {"status": "available", "start_date": date(2026, 9, 8), "start_value": 9.42, "now_value": 9.42,
                      "moved": 0.0, "closed_fraction": -0.0, "n_points": 5}, "variant": None}
    text = closure_phrase(still)
    assert text and "沒有動" in text and "5 次抓取" in text
    moved = {"base": {"status": "available", "start_date": date(2026, 9, 8), "start_value": 9.2, "now_value": 9.4,
                      "moved": 0.2, "closed_fraction": 0.25, "n_points": 3},
             "variant": {"status": "available", "closed_fraction": 0.4}}
    text2 = closure_phrase(moved)
    assert "朝我們的看法移了 25%" in text2 and "對賭注而言是 +40%" in text2
    for term in FORBIDDEN_TERMS:
        assert term.lower() not in (text + text2).lower()
    assert closure_phrase(None) is None and closure_phrase({"base": {"status": "missing"}}) is None
    tl = timeline_paragraph(checkpoints=[], catalysts=[], value_date=None, horizon_end=None, thesis_next_check=None,
                            reached={"any_reached": True, "bet_reached": False})
    assert "現價已高於沒賭對的目標價" in tl and "不是自動賣出" in tl


def test_read_model_carries_gap_closure_and_target_reached_datums() -> None:
    from tests.test_analyst_view import _full_view

    view = _full_view(with_criterion=False)
    eg = view.expectation_gap
    assert eg.gap_closure is not None and eg.consensus_series is not None
    assert eg.gap_closure.status == "missing"            # fixture 沒有共識時序 → missing，不是 0
    assert view.implied_return.target_reached is not None
