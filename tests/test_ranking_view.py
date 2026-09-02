"""瓶頸排序輸出——系統的終點。

以股票為單位，不給額度。兩份排序回答不同問題且不可互換：
  actionable → 現在能投什麼（證據夠強才可行動）
  structural → 該去補誰的證據（結構很卡但證據沒跟上的，研究 ROI 最高）
"""
from __future__ import annotations

from decision_lab.ranking_view import build_ranking_view


def _row(company_id, ticker, bottleneck, *, sub=5, evidence="externally_corroborated",
         sole_source=True, anchor="tech:ai_switch", hops=2):
    return {
        "company_id": company_id,
        "ticker": ticker,
        "relation": "supplies_to",
        "bottleneck": bottleneck,
        "substitutability": sub,
        "sole_source": sole_source,
        "qualification_status": "designed_in",
        "evidence": evidence,
        "confidence": 0.9,
        "documents": 5,
        "chain": [anchor, bottleneck] if anchor else [],
        "demand_anchor": anchor,
        "demand_hops": hops,
    }


RANKING = {
    "rows": [
        _row("co:coherent", "COHR", "co:nvidia"),
        _row("co:broadcom", "AVGO", "tech:cpo", evidence="needs_review"),
        _row("co:lumentum", "LITE", "tech:uhp_laser", evidence="self_reported"),
    ],
    "structural_rows": [
        _row("co:broadcom", "AVGO", "tech:cpo", evidence="needs_review", hops=1),
        _row("co:coherent", "COHR", "co:nvidia"),
        _row("co:lumentum", "LITE", "tech:uhp_laser", evidence="self_reported"),
    ],
    "coverage": {
        "canonical_edges": 413,
        "edges_with_substitutability": 60,
        "substitutability_coverage": 0.145,
        "edges_with_lead_time": 1,
        "self_reported_share": 0.48,
    },
}


def test_outputs_are_stock_level_with_rank() -> None:
    view = build_ranking_view(RANKING)

    first = view["actionable"][0]
    assert first["ticker"] == "COHR"
    assert first["rank"] == 1
    assert first["bottleneck"] == "co:nvidia"


def test_both_orderings_are_present_and_distinct() -> None:
    """R3：兩份排序用途不同，不可互換——所以必須同時在，且各自有說明。"""
    view = build_ranking_view(RANKING)

    assert [r["ticker"] for r in view["actionable"]] == ["COHR", "AVGO", "LITE"]
    assert [r["ticker"] for r in view["structural"]] == ["AVGO", "COHR", "LITE"]
    assert view["actionable_purpose"] != view["structural_purpose"]
    assert "能投" in view["actionable_purpose"]
    assert "補" in view["structural_purpose"]


def test_weakest_axis_is_attached_per_company() -> None:
    """最弱軸是「該補什麼」的指標——它要跟著標的走，不然使用者得自己去別處查。"""
    view = build_ranking_view(
        RANKING, weakest_axes={"co:coherent": "technical_causal_link"}
    )

    by_ticker = {r["ticker"]: r for r in view["actionable"]}
    assert by_ticker["COHR"]["weakest_axis"] == "technical_causal_link"
    assert by_ticker["AVGO"]["weakest_axis"] is None


def test_disproof_travels_with_each_candidate() -> None:
    """R4：排序是研究判斷，判斷必須附可證偽條件，否則它只是意見。"""
    view = build_ranking_view(
        RANKING, disproofs={"co:coherent": "毛利率跌破 40.2% 即失效"}
    )

    by_ticker = {r["ticker"]: r for r in view["actionable"]}
    assert "40.2%" in by_ticker["COHR"]["disproof"]


def test_carries_the_judgment_and_coverage_caveats() -> None:
    """R4：必須明說這不是回測；且沿用排序表既有的限制聲明，不重寫。"""
    view = build_ranking_view(RANKING)

    assert "回測" in view["judgment_note"]
    joined = " ".join(view["caveats"])
    assert "15%" in joined or "0.145" in joined or "覆蓋" in joined
    assert "lead time" in joined.lower() or "換掉" in joined


def test_limit_truncates_but_reports_total() -> None:
    """截斷不得靜默——使用者要知道自己只看到前幾名。"""
    view = build_ranking_view(RANKING, limit=2)

    assert len(view["actionable"]) == 2
    assert view["actionable_total"] == 3


def test_missing_demand_anchor_is_flagged_not_dropped() -> None:
    """無需求錨點者依 alpha 判準不是候選，但要現形而非消失。"""
    ranking = {
        "rows": [_row("co:globalfoundries", "GFS", "mat:silicon_wafer", anchor=None, hops=None)],
        "structural_rows": [],
        "coverage": {},
    }
    view = build_ranking_view(ranking)

    assert view["actionable"][0]["demand_anchor"] is None
    assert view["actionable"][0]["no_demand_anchor"] is True


def test_output_carries_no_position_sizing() -> None:
    """R5 零額度：排序是終點，它不說買多少。"""
    view = build_ranking_view(
        RANKING,
        weakest_axes={"co:coherent": "technical_causal_link"},
        disproofs={"co:coherent": "毛利率跌破 40.2%"},
    )

    rendered = repr(view).lower()
    for forbidden in (
        "supported_range", "axis_ceiling", "paper_target", "nav_pct",
        "probe", "cap", "position_size",
    ):
        assert forbidden not in rendered


def test_sector_grouping_segments_full_list_with_global_rank() -> None:
    """族群分段（2026-09-02 使用者定案）：對截斷前完整列表分組、各段有自己的
    第一名、rank 保留全域名次；sector_anchors 新增族群時自動長出新段。"""
    sector_map = {"tech:ai_switch": "AI 光互連／CPO", "mat:rare_earth_magnets": "稀土磁材"}
    ranking = {
        "rows": [
            _row("co:coherent", "COHR", "co:nvidia"),
            _row("co:lumentum", "LITE", "tech:uhp_laser"),
            _row("co:mp_materials", "MP", "mat:rare_earth_magnets",
                 anchor="mat:rare_earth_magnets", sub=4),
            _row("co:globalfoundries", "GFS", "mat:silicon_wafer",
                 anchor=None, hops=None),
        ],
        "structural_rows": [],
        "coverage": {},
    }
    view = build_ranking_view(ranking, sector_map=sector_map, limit=2)

    segs = {s["sector"]: s for s in view["actionable_by_sector"]}
    # 全域 limit=2 截斷不影響分組——稀土段仍要出現（對完整列表分組）
    assert "稀土磁材" in segs
    assert segs["稀土磁材"]["entries"][0]["company_id"] == "co:mp_materials"
    # rank 是全域名次：MP 全域第 3
    assert segs["稀土磁材"]["entries"][0]["rank"] == 3
    # 各段有自己的第一名
    assert segs["AI 光互連／CPO"]["entries"][0]["rank"] == 1
    # 無錨者集中在未歸組段現形，不消失
    from decision_lab.ranking_view import UNGROUPED_SECTOR
    assert segs[UNGROUPED_SECTOR]["entries"][0]["company_id"] == "co:globalfoundries"
    # 新族群 = 改 map 就長新段
    sector_map["mat:silicon_wafer"] = "矽晶圓"
    view2 = build_ranking_view(ranking, sector_map=sector_map)
    assert any(s["sector"] == "AI 光互連／CPO" for s in view2["actionable_by_sector"])
