"""研究缺口項目的標題必須指名「補哪一檔的哪一軸」。

先前是 `REVIEW — co:coherent`——說了狀態卻沒說成因。最弱軸是排序的瓶頸，也是提高
排序的唯一路徑，所以它才是這一列該講的事（R14）。
"""
from __future__ import annotations

from decision_lab.sizing import AXES, AXIS_RESEARCH_PROMPT
from engine_b.todo import _decision_review_title


def test_every_axis_has_a_research_prompt() -> None:
    """新增一軸就必須決定它的研究動作，否則項目會退回沒有成因的舊格式。"""
    assert set(AXIS_RESEARCH_PROMPT) == set(AXES)
    assert all(prompt.strip() for prompt in AXIS_RESEARCH_PROMPT.values())


def test_title_names_the_company_and_the_axis_action() -> None:
    title = _decision_review_title(
        "REVIEW", "co:coherent", weakest_axis="technical_causal_link"
    )

    assert title.startswith("co:coherent：")
    assert "counter-path" in title
    assert "REVIEW" not in title


def test_each_axis_produces_a_distinct_action() -> None:
    titles = {
        axis: _decision_review_title("REVIEW", "co:x", weakest_axis=axis)
        for axis in AXES
    }

    assert len(set(titles.values())) == len(AXES)
    assert "獨立來源" in titles["source_reliability"]
    assert "Engine C" in titles["financial_resilience"]


def test_missing_axis_falls_back_to_the_old_shape() -> None:
    """軸缺失時不硬套研究措辭——那會讓非研究缺口看起來需要補證據。"""
    assert _decision_review_title("REVIEW", "co:x", weakest_axis=None) == "REVIEW — co:x"


def test_sheet_only_items_keep_the_old_shape() -> None:
    """Sheet-only 持股不是研究缺口。"""
    title = _decision_review_title(
        "REVIEW", "ticker:ABC", weakest_axis="source_reliability", sheet_only=True
    )

    assert title == "REVIEW — ticker:ABC"


def test_unregistered_axis_is_still_named() -> None:
    """未登記的軸不猜措辭，但仍要指名——沉默會讓新軸悄悄退回舊格式。"""
    title = _decision_review_title("REVIEW", "co:x", weakest_axis="future_axis")

    assert "future_axis" in title
    assert title != "REVIEW — co:x"
