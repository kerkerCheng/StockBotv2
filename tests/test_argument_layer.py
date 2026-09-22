"""論證層（`alpha/narrative/argument.py`＋read model `argument` section，2026-09-15）。

守的是四件事：
1. **句型輸出不含內部名詞**（與短評同一張禁字表），且不算數：輸入什麼值就印什麼值。
2. **鏈的段落**：有印證的逐條講、只有公司自己說的合成一句並點名為最薄處；節點印人話名字。
3. **缺料就說缺料**：沒有基期就一句話，不硬寫；沒有賭注就說還沒寫。
4. **consumer**：每一行是 read model 的同一個 Datum；APP 三層順序。
   ⚠ 2026-09-23（Phase 0 Step 0b.1）：argument panel 由 optional **升為核心**——它是在答
   「憑什麼」的面板（73/73 檔都有內容），原本站核心位的 `why` 答的是「估值怎麼算」，已退役。
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from alpha.narrative import FORBIDDEN_TERMS, format_value
from alpha.narrative.argument import (
    EVIDENCE_CLASS_PLAIN, bet_paragraph, chain_paragraph, market_paragraph, numbers_paragraph, timeline_paragraph,
)

ROOT = Path(__file__).resolve().parents[1]
NAMES = {"tech:ai_switch": "Data-center switch", "co:nvidia": "NVIDIA", "tech:inp_6inch_fab": "6-inch InP Fab",
         "tech:cpo": "Co-Packaged Optics"}
LABELS = {"revenue_growth": "營收成長", "operating_margin_delta": "營益率變化"}


def _clean(text: str) -> None:
    for term in FORBIDDEN_TERMS:
        assert term.lower() not in text.lower(), f"論證層句子出現內部名詞 {term!r}：{text}"


def test_evidence_class_vocabulary_matches_the_ranking_authority() -> None:
    from query.bottleneck import EVIDENCE_LABEL

    assert set(EVIDENCE_CLASS_PLAIN) == set(EVIDENCE_LABEL)


def test_chain_paragraph_names_nodes_and_isolates_the_thin_links() -> None:
    edges = [
        {"relation": "supplies_to", "target": "co:nvidia", "evidence_class": "externally_corroborated",
         "sole_source": True, "qualification_status": "designed_in"},
        {"relation": "depends_on", "target": "tech:inp_6inch_fab", "evidence_class": "externally_corroborated",
         "sole_source": False, "qualification_status": "qualified"},
        {"relation": "supplies_to", "target": "tech:cpo", "evidence_class": "self_reported",
         "sole_source": False, "qualification_status": "designed_in"},
    ]
    text = chain_paragraph(company="Coherent", anchor_id="tech:ai_switch", edges=edges, names=NAMES)
    _clean(text)
    assert text.startswith("需求端是「Data-center switch」。")
    assert "Coherent供應「NVIDIA」；目前是唯一來源；已被設計進客戶產品；有客戶或第三方印證。" in text
    assert "另外 1 條連結（「Co-Packaged Optics」）只有公司自己在講" in text and "最薄" in text
    assert "tech:" not in text and "sub=" not in text
    assert chain_paragraph(company="X", anchor_id=None, edges=[], names={}) == "圖裡還沒有 X 的供應鏈連結，所以說不出它在哪條鏈上。"


def test_numbers_paragraph_prints_the_given_values_in_human_units() -> None:
    text = numbers_paragraph(
        base_period="FY2026", target_period="FY2027", currency="USD", base_revenue=7_118_200_000.0, base_margin=0.2047,
        growth=[("Datacenter & Communications", 0.6), ("Industrial", -0.03)], margin_delta=0.025,
        internal_revenue=10_227_652_000.0, internal_margin=0.2297, internal_eps=8.944, consensus_eps=9.416,
        top_sensitivity={"driver": "operating_margin_delta", "delta_fair_value": 10.18, "fair_value_relative": 0.0456,
                         "bump_unit": "absolute_ratio"}, driver_labels=LABELS)
    _clean(text)
    assert "71.2 億 USD" in text and "20.5%" in text and "「Industrial」業務成長 −3.0%" in text
    assert "每股盈餘 8.94；市場共識 9.42" in text
    assert "最敏感的是營益率變化：每差 1 個百分點，目標價差約 10.18 USD（4.6%）" in text
    assert numbers_paragraph(base_period=None, target_period=None, currency=None, base_revenue=None, base_margin=None,
                             growth=[], margin_delta=None, internal_revenue=None, internal_margin=None, internal_eps=None,
                             consensus_eps=None, top_sensitivity=None, driver_labels=LABELS) == "還沒有上一個年度的實際數字，所以算不出明年的獲利。"


def test_market_and_bet_paragraphs_speak_in_percentage_points_not_driver_names() -> None:
    market = market_paragraph(
        comparisons=[{"label": "每股盈餘", "relative_gap": -0.05}], market_multiple=28.3, our_multiple=25.0,
        multiple_rationale=None,
        reverse={"solutions": [{"driver": "operating_margin_delta", "scope": "mix_and_utilization", "implied_value": 0.067, "status": "solved"}]},
        driver_labels=LABELS)
    _clean(market)
    assert "每股盈餘我們比市場低 5.0%" in market and "市場對明年獲利付 28.3 倍，我們給 25.0 倍" in market
    assert "營益率要多提高 6.7 個百分點" in market and "mix_and_utilization" not in market
    bet = bet_paragraph(has_bet=True, overrides=[{"driver": "operating_margin_delta", "scope": "mix_and_utilization",
                                                  "base_value": 0.025, "value": 0.045, "unit": "ratio"}],
                        bet_target=243.97, price=266.5, payoff=-0.0845, eps_part=0.036, multiple_part=-0.117,
                        currency="USD", driver_labels=LABELS)
    _clean(bet)
    assert "從 2.5 個百分點 改成 4.5 個百分點" in bet and "是 −8.5%" in bet and "獲利面貢獻 +3.6%" in bet
    assert bet_paragraph(has_bet=False, overrides=[], bet_target=None, price=None, payoff=None, eps_part=None,
                         multiple_part=None, currency=None, driver_labels=LABELS).startswith("還沒寫下賭注")


def test_timeline_paragraph_sorts_by_date_and_states_the_value_date() -> None:
    text = timeline_paragraph(
        checkpoints=[{"date": date(2026, 12, 1), "what": "六吋產能檢核", "decides": "倍增是否如期"}],
        catalysts=[{"expected_at": date(2026, 11, 18), "description": "Q3 財報"}],
        value_date=date(2027, 6, 30), horizon_end=date(2027, 6, 30), thesis_next_check=date(2026, 10, 15))
    _clean(text)
    assert text.index("2026-11-18") < text.index("2026-12-01")
    assert "目標價指的是 2027-06-30 那一天的值" in text and "下次例行核查是 2026-10-15" in text


def test_money_formatting_is_presentation_only() -> None:
    assert format_value("money", 7_118_200_000.0, unit="USD") == "71.2 億 USD"
    assert format_value("money", 18_100_000.0) == "18 百萬"
    assert format_value("money", 950.0) == "950"


def test_argument_section_is_built_from_the_fixture_and_panel_is_core() -> None:
    from briefing.analyst_view import build_analyst_view
    from tests.test_analyst_view import _full_view

    view = _full_view(with_criterion=False)
    ag = view.argument
    # ⚠ 2026-09-23（Phase 0 Step 0b.1b）：E 組（賭注四價 overlay）退役。 論證層的「賭注」段（四個價格組句）退役，六段變五段。
    # 「數字」「和市場差在哪」兩段讀的是估值鏈，隨 C／H 組退役（尚未執行）。
    assert len(ag.paragraphs) == 5 and [p.key for p in ag.paragraphs] == [
        "argument:chain", "argument:numbers", "argument:market", "argument:risks", "argument:timeline"]
    for p in ag.paragraphs:
        if p.is_known:
            _clean(str(p.value))
    analyst = build_analyst_view(view)
    # ⚠ 2026-09-23 Step 0b.1：由 optional 升核心（使用者定案 A）。
    assert analyst.argument.optional is False
    assert not any(b.startswith("argument") for b in analyst.readiness.blockers)
    allowed = {id(p) for p in ag.paragraphs}
    assert all(id(line.datum) in allowed for line in analyst.argument.lines)


def test_provider_narrative_context_is_optional_and_failures_only_warn() -> None:
    """假 provider 沒有 `get_narrative_context` → 論證層照常、只是沒名字沒引文；有但會炸 → warnings 現形，不讓 view 失敗。"""
    from briefing.alpha_view.builder import _citations

    assert _citations({}, ["co:x"]) == []
    claims = {"claims": [
        {"claim_id": "a", "statement": "about anchor", "about": ["tech:ai_switch"], "origin": "X", "published_at": date(2026, 9, 1)},
        {"claim_id": "b", "statement": "about company", "about": ["co:coherent"], "origin": "Y", "published_at": date(2026, 8, 1)},
    ]}
    out = _citations(claims, ["tech:ai_switch", "co:coherent"])
    assert [c["claim_id"] for c in out] == ["b", "a"], "關於公司本身的 claim 先排"


def test_app_has_three_tiers_in_order() -> None:
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    block = source.split("async function renderDetail", 1)[1]
    block = re.split(r"\n(?:async )?function ", block, maxsplit=1)[0]
    assert block.index("briefCard(") < block.index("argumentCard(") < block.index("drill(")
    card = source.split("function argumentCard", 1)[1].split("\nasync function renderDetail", 1)[0]
    for token in ("fair_value /", "/ price", "value - ", "value / ", "Math.pow"):
        assert token not in card, token
