"""pq1 字典序排序。

2026-08-21 由加權總分改為字典序。舊測試裡從真實事故學到的行為意圖全部保留
（見各 test 的 docstring），並新增本架構的核心性質測試：**無補償性**。
"""

from __future__ import annotations

import pytest

from engine_b import priority


def _lead(
    lead_id: str,
    *,
    tier: int = 4,
    flags: dict | None = None,
    classification: dict | None = None,
    title: str = "",
    source: str = "x:test",
    tickers: list[str] | None = None,
    refs: dict | None = None,
) -> dict:
    triage: dict = {"tier": tier, "priority_flags": flags or {}}
    if classification:
        triage["classification"] = classification
    lead = {
        "lead_id": lead_id,
        "title": title,
        "source": source,
        "triage": triage,
        "refs": refs or {},
    }
    if tickers is not None:
        lead["entities"] = {"tickers": tickers, "company_ids": []}
    return lead


def _order(ranked) -> list[str]:
    return [lead["lead_id"] for _rank, lead in ranked]


def test_lead_ticker_parses_edgar_source_and_title_cashtag() -> None:
    assert priority.lead_ticker({"source": "edgar:COHR", "title": ""}) == "COHR"
    assert priority.lead_ticker({"source": "x:feed", "title": "why $AXTI matters"}) == "AXTI"
    assert priority.lead_ticker({"source": "x:feed", "title": "no tag here"}) is None


def test_vocabulary_is_fail_closed(monkeypatch) -> None:
    """字彙缺檔必須立刻現形，不得靜默退回預設值。

    `AGENTS.md` 記過同型事故：新增 `config/*.json` 忘了補 `.gitignore` 的
    `!config/<name>.json`，fresh clone 會缺檔而靜默失效。
    """

    priority.vocabulary.cache_clear()
    monkeypatch.setattr(priority, "CONFIG_PATH", priority.CONFIG_PATH.parent / "nope.json")
    with pytest.raises(priority.ClassificationVocabularyError):
        priority.vocabulary()
    priority.vocabulary.cache_clear()


def test_classification_validation_rejects_unknown_and_incomplete_capital() -> None:
    with pytest.raises(priority.ClassificationValidationError):
        priority.validate_classification({
            "content_type": "unknown",
            "decision_impact": "ranking",
        })
    with pytest.raises(priority.ClassificationValidationError):
        priority.validate_classification({
            "content_type": "capital_commitment",
            "decision_impact": "candidate_set",
        })
    with pytest.raises(priority.ClassificationValidationError):
        priority.validate_classification({
            "content_type": "structural_fact",
            "decision_impact": "ranking",
        }, require_receipt=True)


def test_user_requested_campaign_gets_pq1_scheduling_priority() -> None:
    """使用者明確指定的 campaign 是 pq1 排程 authority（但不授權 pq2）。"""

    user = _lead("user", flags={"user_requested": True})
    strong = _lead(
        "strong",
        tier=1,
        classification={"content_type": "capital_commitment", "decision_impact": "candidate_set"},
    )
    assert _order(priority.rank_leads([strong, user]))[0] == "user"


def test_primary_campaign_focus_ranks_with_user_authority() -> None:
    focus = _lead("focus", refs={"campaign_focus": "primary"})
    other = _lead("other", tier=1)
    assert _order(priority.rank_leads([other, focus]))[0] == "focus"


def test_contradiction_flag_maps_to_exit_condition_without_backfill() -> None:
    """舊 `contradiction` 旗標（權重曾最高 5.0）語意等同 `exit_condition`。

    未 backfill 的舊 lead 不必等分類就保有原本的急迫性——可能推翻 thesis 的事最急，
    且它保護的是已投入的資本。
    """

    contra = _lead("contra", tier=4, flags={"contradiction": True})
    fresh = _lead(
        "fresh", tier=1, classification={"content_type": "structural_fact", "decision_impact": "ranking"}
    )
    assert _order(priority.rank_leads([fresh, contra]))[0] == "contra"


def test_insider_transaction_sinks_below_unclassified() -> None:
    """2026-08-21 主要事故：每日 5 個 pq1 slot 有 3 個是 7 週前的 Micron 內部人 Form 4。

    分類為 `insider_transaction`＋`confidence_only` 後必須沉底，**即使它是 tier 1
    一手來源、又是持股標的**——那正是舊加權總分把它推上去的三個理由。
    """

    form4 = _lead(
        "form4",
        tier=1,
        source="edgar:MU",
        title="MU 4 filed 2026-07-02",
        tickers=["MU"],
        classification={
            "content_type": "insider_transaction",
            "decision_impact": "confidence_only",
        },
    )
    plain = _lead("plain", tier=4, source="x:feed", tickers=["ZZZ"])
    ranked = priority.rank_leads(
        [form4, plain], tracked_tickers=frozenset({"MU"}), held_tickers=frozenset({"MU"})
    )
    assert _order(ranked) == ["plain", "form4"]


def test_no_compensation_many_weak_signals_cannot_outrank_one_strong_one() -> None:
    """**本架構的核心性質。**

    舊加權總分的病叫補償性：`tier 4.0 + holdings 4.0 + thesis 4.0 = 12.0`，三個各自
    成立的弱理由相加就壓過真正的資本承諾事件。字典序沒有補償性——這是結構保證，
    不是參數調校，所以這裡刻意讓弱方**佔滿所有次要軸**。
    """

    many_weak = _lead(
        "weak",
        tier=1,
        flags={"independent_source": True, "novelty": True},
        tickers=["MU"],
        classification={"content_type": "financial_fact", "decision_impact": "ranking"},
    )
    one_strong = _lead(
        "strong",
        tier=4,
        tickers=["ZZZ"],
        classification={
            "content_type": "capital_commitment",
            "decision_impact": "candidate_set",
            "payment_direction": "customer_to_supplier",
        },
    )
    ranked = priority.rank_leads(
        [many_weak, one_strong],
        tracked_tickers=frozenset({"MU"}),
        held_tickers=frozenset({"MU"}),
        chokepoint_tickers=frozenset({"MU"}),
    )
    assert _order(ranked) == ["strong", "weak"]


def test_payment_direction_orders_customer_funding_above_supplier_funding() -> None:
    """客戶掏錢綁供應商＝真瓶頸；供應商給股權換訂單＝不是瓶頸（POET／Lumilens 形狀）。

    兩者都是 `capital_commitment`，靠 `payment_direction` 分開——任何以替代難度為主的
    排序都抓不到後者。
    """

    inbound = _lead(
        "inbound",
        classification={
            "content_type": "capital_commitment",
            "decision_impact": "candidate_set",
            "payment_direction": "customer_to_supplier",
        },
    )
    outbound = _lead(
        "outbound",
        classification={
            "content_type": "capital_commitment",
            "decision_impact": "candidate_set",
            "payment_direction": "supplier_to_customer",
        },
    )
    assert _order(priority.rank_leads([outbound, inbound])) == ["inbound", "outbound"]


def test_broad_macro_post_no_longer_outranks_focused_tier1_filing() -> None:
    """2026-08-12 事故：提到 12 檔的財報季總評（已兩度被判無可入圖內容）擠掉 tier-1 8-K。

    舊修法是稀釋係數（`FOCUS_TICKER_CAP`），只治標；新架構靠 `content_type` 直接分開
    ——總評是 `sentiment`，8-K 是 `structural_fact`。
    """

    macro = _lead(
        "macro",
        tier=1,
        tickers=[f"T{i}" for i in range(12)],
        classification={"content_type": "sentiment", "decision_impact": "confidence_only"},
    )
    filing = _lead(
        "filing",
        tier=1,
        source="edgar:LITE",
        tickers=["LITE"],
        classification={"content_type": "structural_fact", "decision_impact": "ranking"},
    )
    ranked = priority.rank_leads(
        [macro, filing], tracked_tickers=frozenset({f"T{i}" for i in range(12)} | {"LITE"})
    )
    assert _order(ranked) == ["filing", "macro"]


def test_chokepoint_impact_lifts_supply_chain_leads_over_generic_commentary() -> None:
    """位於已知瓶頸上的公司優先——系統整個定位就是找瓶頸（2026-08-20 加入）。

    但它排在 `decision_impact`／`content_type` 之後：結構上重要不代表這一則有內容。
    """

    choke = _lead("choke", tickers=["AXTI"])
    generic = _lead("generic", tickers=["ZZZ"])
    ranked = priority.rank_leads(
        [generic, choke], chokepoint_tickers=frozenset({"AXTI"})
    )
    assert _order(ranked) == ["choke", "generic"]


def test_held_outranks_merely_tracked() -> None:
    """實際有部位優先於「有在追但沒部位」。先前只有 tracked，導致持股零加權。"""

    held = _lead("held", tickers=["COHR"])
    tracked = _lead("tracked", tickers=["AXTI"])
    ranked = priority.rank_leads(
        [tracked, held],
        tracked_tickers=frozenset({"COHR", "AXTI"}),
        held_tickers=frozenset({"COHR"}),
    )
    assert _order(ranked) == ["held", "tracked"]


def test_missing_or_invalid_tier_defaults_to_weakest() -> None:
    weakest = priority.rank_lead({"lead_id": "a", "triage": {"tier": "bogus"}})
    assert weakest.tier == 4
    assert priority.rank_lead({"lead_id": "b"}).tier == 4


def test_unclassified_sorts_above_no_content_but_below_real_types() -> None:
    """未分類不等於沒價值——它排在 `sentiment` 之下、`no_content` 之上。

    這一格長期應為 0；排在 `no_content` 之後會讓舊 lead 餓死，排在前面會讓它插隊。
    """

    unknown = _lead("unknown")
    empty = _lead("empty", classification={"content_type": "no_content", "decision_impact": "confidence_only"})
    opinion = _lead("opinion", classification={"content_type": "sentiment", "decision_impact": "ranking"})
    assert _order(priority.rank_leads([empty, unknown, opinion])) == [
        "opinion",
        "unknown",
        "empty",
    ]


def test_rank_uses_all_mentioned_tickers_not_just_the_first() -> None:
    """2026-08-08 事故：一則同時點名五家的推文只用第一家判定重要性。"""

    lead = _lead("multi", title="$AAOI readthrough", tickers=["AAOI", "SIVE", "LITE"])
    ranked = priority.rank_leads([lead], held_tickers=frozenset({"SIVE"}))
    assert ranked[0][0].relevance == 0


def test_label_explains_why_it_ranked_there() -> None:
    """任何會改變輸出的輸入，都要出現在該輸出自己的證據欄位裡（L12 推論）。

    刻意不提供合併後的單一分數——那正是本次移除的東西。
    """

    rank = priority.rank_lead(
        _lead(
            "x",
            classification={
                "content_type": "capital_commitment",
                "decision_impact": "candidate_set",
            },
        ),
        chokepoint_impact=True,
    )
    assert "候選集合" in rank.label
    assert "客戶端資本承諾" in rank.label
    assert "瓶頸" in rank.label
    assert not hasattr(rank, "score")
