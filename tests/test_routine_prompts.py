"""Daily／weekly Codex 本機 routine prompt 的 v1.2 契約。"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DAILY = ROOT / "crons" / "daily_brief_prompt.md"
WEEKLY = ROOT / "crons" / "weekly_scan_prompt.md"


def test_daily_prompt_uses_local_authorities_and_repo_venv() -> None:
    text = DAILY.read_text(encoding="utf-8")
    for token in (
        "$daily-brief",
        ".venv\\Scripts\\python.exe",
        "crons\\harvest_leads.py",
        "engine_b.cli harvest-health",
        "engine_c\\etl_yfinance.py",
        "scripts\\daily_beta_snapshot.py",
        "decision_lab today",
        "engine_b.todo sync",
        "scripts\\publish_daily_state.py",
    ):
        assert token in text
    assert "master" in text
    assert "不要建立 branch" in text


def test_daily_prompt_keeps_human_gates_and_batch_contract() -> None:
    text = DAILY.read_text(encoding="utf-8")
    assert "engine_b.cli drain" in text
    assert "config/daily_routine.json" in text
    assert "drain --limit 2" not in text
    assert "只有 prepared RA 才進 pq2" in text
    assert "Graph admission" in text
    assert "record-choice" in text and "record-fill" in text
    assert "go" in text and "drop" in text and "pending" in text
    assert "todo_pool.json" in text and "不得依 section" in text
    assert "engine_b.todo dispatch" in text
    assert "bare reassess" in text
    assert "新 decision receipt" in text
    assert "beta technical" in text
    assert "supported range 歸零" in text
    assert "sheet_conservative_range" in text
    assert "household_cash_supported_range" in text
    assert "contingent_credit_available" in text
    assert "loan_funded_supported_range" in text
    assert "spreadsheets.readonly" in text
    assert "retirement_net_terminal_wealth" in text
    assert "failure_class" in text
    assert "access_blocked" in text
    assert "同一來源後續成功才算 recovered" in text


def test_daily_brief_title_carries_taipei_date() -> None:
    for path in (DAILY, ROOT / "skills" / "daily-brief" / "SKILL.md"):
        text = path.read_text(encoding="utf-8")
        assert "# Daily Brief <YYYY-MM-DD> (Asia/Taipei)" in text


def test_daily_prompt_is_not_the_retired_cloud_runner() -> None:
    text = DAILY.read_text(encoding="utf-8")
    assert "Codex 本機排程" in text
    assert "不要使用 Claude cloud clone" in text
    assert "MCP 降級路徑" in text


def test_weekly_is_local_health_discovery_and_read_only_lifecycle() -> None:
    text = WEEKLY.read_text(encoding="utf-8")
    for token in (
        "query\\health_audit.py --local",
        "發現未知",
        "Topic discovery",
        "不追源",
        "不抽取",
        "不改 lifecycle",
        "engine_b.todo sync",
        "穩定編號",
    ):
        assert token in text
    assert "健康 finding 與 pq2 是正交" in text
    assert "Codex 本機" in text
