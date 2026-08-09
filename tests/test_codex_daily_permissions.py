"""Daily Brief scheduled task 只使用窄 fixed-entry rules。"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".codex" / "config.toml"
RULES = ROOT / ".codex" / "rules" / "stockbot-automations.rules"


def test_project_does_not_define_an_ignored_permission_profile() -> None:
    assert not CONFIG.exists()


def test_only_daily_fixed_entries_have_outside_sandbox_rules() -> None:
    rules = RULES.read_text(encoding="utf-8")
    assert rules.count("prefix_rule(") == 7
    for fixed_entry in (
        "crons\\\\harvest_leads.py",
        "engine_c\\\\etl_yfinance.py",
        "scripts\\\\daily_beta_snapshot.py",
        '"-m", "decision_lab", "today"',
        '"-m", "engine_b.todo", "sync"',
        "scripts\\\\publish_daily_state.py",
        "scripts\\\\publish_daily_brief.py",
    ):
        assert fixed_entry in rules
    for broad_entry in (
        'pattern=["python"',
        'pattern=[".venv\\\\Scripts\\\\python.exe"]',
        'pattern=["powershell"',
        'pattern=["git"',
    ):
        assert broad_entry not in rules
    assert "stockbot-daily" not in rules
