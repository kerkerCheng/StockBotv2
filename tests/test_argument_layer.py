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
from alpha.narrative.argument import EVIDENCE_CLASS_PLAIN, chain_paragraph, timeline_paragraph

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


# ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`test_numbers_paragraph_prints_the_given_values_in_human_units` 與
# `test_market_and_bet_paragraphs_speak_in_percentage_points_not_driver_names` 退役——三個句型
# （數字怎麼算出來／和市場差在哪／賭注）的輸入全是估值鏈，句型與測試一起退役。


def test_timeline_paragraph_sorts_by_date_and_states_the_next_check() -> None:
    text = timeline_paragraph(
        checkpoints=[{"date": date(2026, 12, 1), "what": "六吋產能檢核", "decides": "倍增是否如期"}],
        catalysts=[{"expected_at": date(2026, 11, 18), "description": "Q3 財報"}],
        thesis_next_check=date(2026, 10, 15))
    _clean(text)
    assert text.index("2026-11-18") < text.index("2026-12-01")
    assert "下次例行核查是 2026-10-15" in text and "目標價" not in text


def test_money_formatting_is_presentation_only() -> None:
    assert format_value("money", 7_118_200_000.0, unit="USD") == "71.2 億 USD"
    assert format_value("money", 18_100_000.0) == "18 百萬"
    assert format_value("money", 950.0) == "950"


def test_argument_section_is_built_from_the_fixture_and_panel_is_core() -> None:
    from briefing.analyst_view import build_analyst_view
    from tests.test_analyst_view import _full_view

    view = _full_view(with_criterion=False)
    ag = view.argument
    # ⚠ 2026-09-23（Phase 0 Step 0b.1b）：「賭注」段隨 E 組、「數字」「和市場差在哪」兩段隨 C／H 組退役。
    # 論證層剩三段：鏈、風險與認錯條件、時間表。
    assert len(ag.paragraphs) == 3 and [p.key for p in ag.paragraphs] == [
        "argument:chain", "argument:risks", "argument:timeline"]
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
