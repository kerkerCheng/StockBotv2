"""daily-brief skill 契約：封閉動詞、operational commands、不硬編政策、閘門不放寬。"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "daily-brief" / "SKILL.md"


def _text() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_references_closed_verbs_and_operational_commands() -> None:
    text = _text()
    for verb in ("research", "apply", "park", "skip"):
        assert verb in text
    for command in (
        "python crons/harvest_leads.py",
        "python -m engine_b.cli",
        "python -m decision_lab today",
    ):
        assert command in text


def test_does_not_hardcode_probe_policy_numbers() -> None:
    text = _text()
    for forbidden in ("0.5%", "axis_ceilings", "probe_book_nav_cap",
                      "single_probe_nav_cap", "paper_nav ="):
        assert forbidden not in text


def test_states_gates_and_human_boundaries() -> None:
    text = _text()
    # 三道閘門與人工邊界必須明文。
    assert "graph admission" in text
    assert "不連 broker" in text
    assert "recommendation 推定 choice" in text
    # 決策寫入只在本機、雲端用唯讀 get_decision_brief。
    assert "get_decision_brief" in text
    assert "只在本機" in text


def test_lead_status_never_claims_evidence_tier() -> None:
    text = _text()
    assert "不是" in text and "evidence tier" in text
