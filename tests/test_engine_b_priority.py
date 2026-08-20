"""Lead priority 計分與排序（plan U1）。"""
from __future__ import annotations

from engine_b import leads, priority


def _triaged(source: str, *, tier: int, flags=None):
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source=source, url=f"https://x.io/{source}")
    leads.triage(store, lead_id, go=True, tier=tier, reason="x", priority_flags=flags or {})
    return store["leads"][lead_id]


def test_lead_ticker_parses_edgar_source_and_title_cashtag() -> None:
    assert priority.lead_ticker({"source": "edgar:COHR"}) == "COHR"
    assert priority.lead_ticker({"source": "aleabitoreddit_rss"}) is None
    assert priority.lead_ticker({"source": "x:serenity", "title": "$GOOGL capex"}) == "GOOGL"


def test_tier_base_score() -> None:
    # tier1（最強來源）分數應高於 tier4
    t1 = priority.score_lead(_triaged("edgar:COHR", tier=1))
    t4 = priority.score_lead(_triaged("edgar:COHR", tier=4))
    assert t1 > t4
    assert t1 == 4.0 and t4 == 1.0


def test_flags_and_thesis_impact_boost() -> None:
    base = priority.score_lead(_triaged("edgar:COHR", tier=3))
    contra = priority.score_lead(
        _triaged("edgar:COHR", tier=3, flags={"contradiction": True})
    )
    impact = priority.score_lead(_triaged("edgar:COHR", tier=3), thesis_impact=True)
    assert contra == base + priority.PRIORITY_WEIGHTS["contradiction"]
    assert impact == base + priority.PRIORITY_WEIGHTS["thesis_impact"]


def test_user_requested_campaign_gets_pq1_scheduling_priority() -> None:
    base = priority.score_lead(_triaged("x:test", tier=4))
    campaign = priority.score_lead(
        _triaged("x:test", tier=4, flags={"user_requested": True})
    )
    assert campaign - base == priority.PRIORITY_WEIGHTS["user_requested"]


def test_primary_campaign_focus_boosts_new_domain() -> None:
    lead = _triaged("x:test", tier=4, flags={"user_requested": True})
    base = priority.score_lead(lead)
    lead["refs"]["campaign_focus"] = "primary"
    assert priority.score_lead(lead) - base == priority.PRIORITY_WEIGHTS["campaign_focus"]


def test_rank_orders_by_score_and_derives_thesis_impact() -> None:
    low = _triaged("edgar:AAOI", tier=4)  # 弱、非追蹤
    high = _triaged("edgar:COHR", tier=1, flags={"contradiction": True})
    mid = _triaged("aleabitoreddit_rss", tier=2)  # RSS 無 ticker → 無 thesis_impact
    ranked = priority.rank_leads([low, high, mid], tracked_tickers=frozenset({"COHR"}))
    order = [l["source"] for _s, l in ranked]
    # COHR：tier1 + contradiction + thesis_impact(在 tracked) → 最高
    assert order[0] == "edgar:COHR"
    assert order[-1] == "edgar:AAOI"


def test_missing_or_invalid_tier_defaults_to_weakest() -> None:
    assert priority.score_lead({"triage": {"tier": None}}) == 1.0
    assert priority.score_lead({"triage": {}}) == 1.0
    assert priority.score_lead({}) == 1.0


def test_focus_factor_dilutes_impact_for_broad_ticker_mentions() -> None:
    # 3 檔以內不打折；越廣稀釋越重。
    assert priority.focus_factor(0) == 1.0
    assert priority.focus_factor(1) == 1.0
    assert priority.focus_factor(3) == 1.0
    assert priority.focus_factor(6) == 0.5
    assert priority.focus_factor(12) == 0.25


def test_broad_macro_post_no_longer_outranks_focused_tier1_filing() -> None:
    """2026-08-12 迴歸：提到 12 檔的總體評論曾以 12 分擠掉 tier-1 的 LITE 8-K（6 分）。

    impact 權重只要任一 ticker 命中就給滿分，於是「提到越多檔」＝越容易同時拿到
    thesis_impact 與 holdings_impact——而廣度正是低價值的特徵。
    """
    macro = _triaged("x:serenity", tier=4, flags={"novelty": True})
    macro["title"] = (
        "$BE $TER $LITE $SNDK $AMKR $GOOGL $CXMT $SIVE $AAOI $META $NBIS $MU 財報季總評"
    )
    filing = _triaged("edgar:LITE", tier=1)

    tracked = frozenset({"LITE", "AAOI", "META", "SIVE"})
    ranked = priority.rank_leads([macro, filing], tracked_tickers=tracked, held_tickers=tracked)
    order = [lead["source"] for _score, lead in ranked]
    assert order[0] == "edgar:LITE", "tier-1 單一標的 filing 應排在廣泛總體評論之前"

    scores = {lead["source"]: score for score, lead in ranked}
    assert scores["x:serenity"] < scores["edgar:LITE"]


def test_chokepoint_impact_lifts_supply_chain_leads_over_generic_commentary() -> None:
    """瓶頸性參與 pq1 排序——系統整個定位就是找瓶頸，排序卻曾經不看它。

    事發（2026-08-20）：使用者問「它們應該會因為瓶頸性排到 pq1 前面？」，實測答案是
    不會——PRIORITY_WEIGHTS 七項全部不含瓶頸性，於是「AXT 供應 COHR 的 InP」與
    「財報季總評」只由 tier 與 flags 區分。
    """

    from engine_b.priority import PRIORITY_WEIGHTS, rank_leads, score_lead

    supply_chain = {
        "lead_id": "a", "triage": {"tier": 2, "priority_flags": {}},
        "entities": {"tickers": ["AXTI"]},
    }
    base = score_lead(supply_chain, mentioned_tickers=1)
    lifted = score_lead(supply_chain, chokepoint_impact=True, mentioned_tickers=1)
    assert lifted - base == PRIORITY_WEIGHTS["chokepoint_impact"]

    # 注入後 rank_leads 應給出同樣的提升
    ranked = rank_leads([supply_chain], chokepoint_tickers=frozenset({"AXTI"}))
    assert ranked[0][0] == lifted

    # 排序仍低於 contradiction：結構重要 ≠ 比「可能推翻 thesis」更急
    assert PRIORITY_WEIGHTS["chokepoint_impact"] < PRIORITY_WEIGHTS["contradiction"]
    assert PRIORITY_WEIGHTS["chokepoint_impact"] < PRIORITY_WEIGHTS["holdings_impact"]


def test_chokepoint_impact_is_diluted_by_ticker_count() -> None:
    """提到十幾檔的總評不該因為碰巧掃到一家瓶頸公司就拿滿分（FOCUS_TICKER_CAP）。"""

    from engine_b.priority import PRIORITY_WEIGHTS, score_lead

    broad = {
        "lead_id": "b", "triage": {"tier": 2, "priority_flags": {}},
        "entities": {"tickers": [f"T{i}" for i in range(12)]},
    }
    base = score_lead(broad, mentioned_tickers=12)
    lifted = score_lead(broad, chokepoint_impact=True, mentioned_tickers=12)
    assert lifted - base < PRIORITY_WEIGHTS["chokepoint_impact"]
    assert abs((lifted - base) - PRIORITY_WEIGHTS["chokepoint_impact"] * 0.25) < 1e-9
