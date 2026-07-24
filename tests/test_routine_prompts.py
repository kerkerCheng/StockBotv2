"""Daily／weekly cloud routine prompt 的 v1.1 契約與分工不漂移。"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DAILY = ROOT / "crons" / "daily_brief_prompt.md"
WEEKLY = ROOT / "crons" / "weekly_scan_prompt.md"


def test_daily_prompt_references_mcp_and_clone_sources() -> None:
    text = DAILY.read_text(encoding="utf-8")
    for token in (
        "get_decision_brief",
        "get_pending_leads",
        "record_lead_decision",
        "get_research_action_status",
        "harvest_config.json",
        "pending_leads.json",
        "thesis/lifecycle.json",
    ):
        assert token in text


def test_daily_prompt_is_cloud_read_only_with_heartbeat_and_batch() -> None:
    text = DAILY.read_text(encoding="utf-8")
    assert "只讀不寫" in text
    assert "不使用 GitHub" in text  # v1.1：無 GitHub UI
    assert "Claude app" in text
    assert "心跳" in text
    # 批次語法核准
    assert "go" in text and "drop" in text and "pending" in text
    assert "pq1 drain" in text  # 心跳後 best-effort drain


def test_daily_prompt_defers_writes_to_local_and_leads_via_mcp() -> None:
    text = DAILY.read_text(encoding="utf-8")
    # 入圖/live 只在本機；leads 狀態只經 MCP record_lead_decision
    assert "record-choice" in text or "record-fill" in text
    assert "不改" in text and "lifecycle.json" in text
    assert "record_lead_decision" in text


def test_weekly_points_to_daily_and_no_longer_writes_lifecycle() -> None:
    text = WEEKLY.read_text(encoding="utf-8")
    assert "crons/daily_brief_prompt.md" in text
    # v1.1：weekly 不再寫 lifecycle（唯讀提醒）
    assert "不寫" in text and "lifecycle.json" in text
    assert "發現未知" in text  # weekly 保留 horizon discovery
    assert "唯讀" in text
