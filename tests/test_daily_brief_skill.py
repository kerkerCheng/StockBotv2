"""daily-brief skill 契約：封閉動詞、operational commands、不硬編政策、閘門不放寬。"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "daily-brief" / "SKILL.md"


def _text() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_references_batch_verbs_and_operational_commands() -> None:
    text = _text()
    # v1.1 批次語法動詞
    for verb in ("go", "drop", "pending"):
        assert verb in text
    assert "parse_batch_reply" in text  # deterministic parser，不自由心證
    assert "1 3 7 go 4 drop 5 6 pending" in text  # 範例
    for command in (
        "python crons/harvest_leads.py",
        "python -m engine_b.cli",
        "python -m engine_b.todo sync",
        "python -m decision_lab today",
        "drain",  # pq1 priority drain
    ):
        assert command in text


def test_references_closed_loop_and_no_github() -> None:
    text = _text()
    assert "evidence-delta" in text or "evidence_delta" in text
    assert "自動建 Shadow" in text
    assert "GitHub" in text  # 明文說不用 GitHub UI
    assert "record_lead_decision" in text  # 雲端改 leads 走 MCP


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


def test_uses_persistent_todo_numbers_and_does_not_blindly_dispatch_batch() -> None:
    text = _text()
    assert "todo_pool.json" in text
    assert "不得依當日排序" in text
    assert "todo batch" in text and "不會代做" in text
