"""Daily／weekly cloud routine prompt 的契約與分工不漂移。"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DAILY = ROOT / "crons" / "daily_brief_prompt.md"
WEEKLY = ROOT / "crons" / "weekly_scan_prompt.md"


def test_daily_prompt_references_mcp_and_clone_sources() -> None:
    text = DAILY.read_text(encoding="utf-8")
    for token in (
        "get_decision_brief",
        "get_research_action_status",
        "harvest_config.json",
        "pending_leads.json",
        "thesis/lifecycle.json",
    ):
        assert token in text


def test_daily_prompt_is_cloud_read_only_with_heartbeat_and_verbs() -> None:
    text = DAILY.read_text(encoding="utf-8")
    # cloud 只讀不寫（不回寫 leads／lifecycle、不 commit／push）。
    assert "只讀不寫" in text
    assert "不 commit" in text and "push" in text
    # 日期心跳＋carry-over。
    assert "Daily Brief <YYYY-MM-DD>" in text
    assert "Carry-over" in text
    assert "心跳" in text
    # 封閉動詞 legend。
    for verb in ("research", "apply", "park", "skip"):
        assert verb in text


def test_daily_prompt_defers_state_writes_to_local() -> None:
    text = DAILY.read_text(encoding="utf-8")
    # 決策寫入永遠只在本機；lifecycle 正式更新不在 daily。
    assert "record-choice" in text or "record-fill" in text
    assert "不改" in text and "lifecycle.json" in text


def test_weekly_prompt_points_to_daily_and_keeps_formal_lifecycle_update() -> None:
    text = WEEKLY.read_text(encoding="utf-8")
    # weekly 引用 daily 分工，且保留 lifecycle 的正式狀態更新端。
    assert "crons/daily_brief_prompt.md" in text
    assert "正式狀態更新" in text
    assert "lifecycle.json" in text
