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
