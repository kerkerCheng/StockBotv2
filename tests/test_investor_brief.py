"""投資人短評（`alpha/narrative`，2026-09-15）——不需要 Neo4j／Engine C。

守的是四件事：
1. **文字由 session 寫、數字由 authority 填**：placeholder 字彙封閉、未知的 `{…}` 拒收、缺值印「（尚無）」不補 0。
2. **禁字表**：內部名詞出現在任何一格就拒收；七格缺一不可；每格必帶引用。
3. **append-only 語意**：as-of 選取、最新者勝出、撤回就沒有。
4. **消費端**：沒寫短評 → section missing＋not_yet_recorded。⚠ 2026-09-23（Phase 0 Step 0b.1）：
   brief panel 由 optional **升為核心**（ROADMAP「首屏的單位是句不是格」），所以沒寫短評**會**讓
   readiness 變差——那是刻意的：新方向下沒寫短評的檔就是沒有產出。實測 70/73 檔還沒寫。
   APP 首屏只有短評卡，其餘收進「為什麼這樣算」。
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from alpha.errors import ContractViolation
from alpha.narrative import (
    ABSENT, FORBIDDEN_TERMS, PLACEHOLDERS, SLOT_KEYS, brief_record, fill_brief, format_value,
    parse_brief_record, select_brief,
)

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[1]
REF = "graph://edge/co:coherent/supplies_to/co:nvidia"


def _slots(**over):
    base = {
        "demand": {"text": "NVIDIA 對 Coherent 投資 20 億美元，把產能綁給自己。", "evidence_refs": [REF]},
        "supply": {"text": "Coherent 供 CPO 用的外部雷射光源。", "evidence_refs": [REF]},
        "bottleneck": {"text": "目前只有它一家被設計進去。", "evidence_refs": [REF]},
        "market_view": {"text": "{analyst_count} 位分析師平均目標價 {sell_side_target}。", "evidence_refs": [REF]},
        "our_bet": {"text": "營益率增幅取 {bet_assumption:operating_margin_delta[mix_and_utilization]}。", "evidence_refs": [REF]},
        "if_right_if_wrong": {"text": "賭對值 {bet_target}，現價 {price}，差 {payoff}。", "evidence_refs": [REF]},
        "when": {"text": "{next_checkpoint_date} 看產能。", "evidence_refs": [REF]},
    }
    base.update(over)
    return base


def _record(created="2026-09-15T08:00:00+00:00", **over):
    return parse_brief_record(brief_record(company_id="co:coherent", ticker="COHR", slots=_slots(**over),
                                           created_at=datetime.fromisoformat(created)))


# ---------------------------------------------------------------------------
# 1. placeholder：字彙封閉、缺值不補 0
# ---------------------------------------------------------------------------

def test_placeholder_vocabulary_is_closed() -> None:
    with pytest.raises(ContractViolation, match="未登記的 placeholder"):
        _record(when={"text": "{next_earnings} 看產能。", "evidence_refs": [REF]})
    with pytest.raises(ContractViolation, match="大括號"):
        _record(when={"text": "{next_checkpoint_date 看產能。", "evidence_refs": [REF]})


def test_fill_uses_authority_values_and_marks_missing_instead_of_zero() -> None:
    brief = _record()
    filled, missing = fill_brief(brief, {"analyst_count": "22", "sell_side_target": "415 USD",
                                         "bet_target": "244 USD", "price": "266.5 USD", "payoff": "−8.5%",
                                         "{bet_assumption:operating_margin_delta[mix_and_utilization]}": "+4.5%"})
    assert filled["market_view"] == "22 位分析師平均目標價 415 USD。"
    assert filled["if_right_if_wrong"] == "賭對值 244 USD，現價 266.5 USD，差 −8.5%。"
    assert filled["our_bet"] == "營益率增幅取 +4.5%。"
    assert filled["when"] == f"{ABSENT} 看產能。" and missing == {"when": ["{next_checkpoint_date}"]}


def test_format_is_presentation_not_arithmetic() -> None:
    assert format_value("ratio", -0.0845) == "−8.5%" and format_value("ratio", 0.036) == "+3.6%"
    assert format_value("multiple", 28.34) == "28.3 倍" and format_value("count", 22.0) == "22"
    assert format_value("price", 243.968, unit="USD") == "243.97 USD" and format_value("price", 1234.6) == "1,235"
    assert format_value("date", date(2026, 12, 1)) == "2026-12-01" and format_value("ratio", None) is None


# ---------------------------------------------------------------------------
# 2. 禁字、七格、引用
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("term", ["session_judgment", "sole_source", "隱含報酬", "non-GAAP", "tech:inp_6inch_fab"])
def test_forbidden_terms_are_rejected(term: str) -> None:
    assert any(t.lower() in term.lower() for t in FORBIDDEN_TERMS)
    with pytest.raises(ContractViolation, match="禁字"):
        _record(supply={"text": f"它是 {term} 供應商。", "evidence_refs": [REF]})


def test_all_seven_slots_are_required_and_each_needs_evidence() -> None:
    slots = _slots(); slots.pop("when")
    with pytest.raises(ContractViolation, match="七格缺一不可"):
        brief_record(company_id="co:coherent", ticker="COHR", slots=slots, created_at=datetime.now(UTC))
    with pytest.raises(ContractViolation, match="引用"):
        _record(when={"text": "{next_checkpoint_date} 看產能。", "evidence_refs": []})
    assert tuple(s.key for s in _record().slots) == SLOT_KEYS


# ---------------------------------------------------------------------------
# 3. append-only：as-of、最新者、撤回
# ---------------------------------------------------------------------------

def test_select_is_point_in_time_and_retraction_leaves_nothing() -> None:
    first = _record("2026-09-10T08:00:00+00:00")
    second = _record("2026-09-15T08:00:00+00:00", when={"text": "{next_checkpoint_date} 看財報。", "evidence_refs": [REF]})
    assert select_brief([first, second], as_of=None, today=date(2026, 9, 16)) is second
    assert select_brief([first, second], as_of=date(2026, 9, 12), today=date(2026, 9, 16)) is first
    assert select_brief([first, second], as_of=date(2026, 9, 1), today=date(2026, 9, 16)) is None
    retract = parse_brief_record(brief_record(company_id="co:coherent", ticker="COHR", slots=_slots(),
                                              retracted=True, supersedes_id=second.brief_id,
                                              created_at=datetime(2026, 9, 16, 9, tzinfo=UTC)))
    assert select_brief([first, second, retract], as_of=None, today=date(2026, 9, 17)) is None


# ---------------------------------------------------------------------------
# 4. 消費端：缺席現形、optional、首屏只有短評
# ---------------------------------------------------------------------------

def test_read_model_without_brief_is_missing_and_blocks_readiness() -> None:
    from briefing.analyst_view import build_analyst_view
    from tests.test_analyst_view import _full_view

    view = _full_view(with_criterion=False)
    ib = view.investor_brief
    assert ib.meta.status == "missing" and ib.meta.effective_absence_kind == "not_yet_recorded"
    assert ib.brief_id is None and len(ib.slots) == 7 and all(d.value is None for d in ib.slots)
    assert ib.status_light.value["label"], "沒短評也要有燈"
    analyst = build_analyst_view(view)
    # ⚠ 2026-09-23 Step 0b.1：brief 升核心。缺席語意仍是 `not_yet_recorded`（不是 settled），
    # 所以它會一直出現在 blockers 裡直到有人寫——這正是那個「會自己出現的計數器」（L14）。
    assert analyst.brief.optional is False and analyst.brief.status == "missing"
    assert any(b.startswith("brief：missing") for b in analyst.readiness.blockers)
    assert analyst.brief.absence_kind == "not_yet_recorded"
    assert "brief" not in "｜".join(analyst.readiness.optional_unavailable)
    # ⚠ 這條斷言的用途是「**brief panel 不得憑空多出不屬於 read model 的行**」，
    # 2026-09-20 加 `multiple_question` 時它正確地抓到了改動。多的那一格仍然必須
    # 來自同一個 read model（不是前端自己算的），所以加進 allowed 而不是放寬斷言。
    # ⚠ 這個 fixture 沒有 `multiple_horizon`，所以 `multiple_question` 應該是 None
    # ——「沒寫倍率射程就不印那一句」是刻意的（71/73 檔都沒寫，逐檔印是噪音）。
    assert ib.multiple_question is None, "沒寫倍率射程時首屏不該多一行"
    allowed = {id(d) for d in ib.slots} | {id(ib.scale), id(ib.status_light)}
    if ib.multiple_question is not None:
        allowed.add(id(ib.multiple_question))
    assert all(id(line.datum) in allowed for line in analyst.brief.lines)


def test_packet_carries_the_brief_frame_for_the_session() -> None:
    from alpha.models.session_assessor import _brief_frame

    frame = _brief_frame()
    assert [s["key"] for s in frame["slots"]] == list(SLOT_KEYS)
    assert set(frame["placeholders"]) == set(PLACEHOLDERS) and "session_judgment" in frame["forbidden_terms"]
    assert "alpha brief" in frame["_how_to_use"]


def test_first_screen_is_the_brief_and_everything_else_is_behind_one_click() -> None:
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    block = source.split("async function renderDetail", 1)[1]
    block = re.split(r"\n(?:async )?function ", block, maxsplit=1)[0]
    assert block.index("briefCard(") < block.index("argumentCard(") < block.index("drill(")
    # 首屏卡片不得自己算報酬；尺的三個數與兩個報酬都來自 materialize 端
    card = source.split("function briefCard", 1)[1].split("\nasync function renderDetail", 1)[0]
    for token in ("fair_value /", "/ price", "value - ", "value / ", "Math.pow"):
        assert token not in card, token
