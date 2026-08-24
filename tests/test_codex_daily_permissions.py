"""Daily Brief scheduled task 只使用窄 fixed-entry rules。"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".codex" / "config.toml"
RULES = ROOT / ".codex" / "rules" / "stockbot-automations.rules"
AGENTS = ROOT / "AGENTS.md"
OPERATIONS = ROOT / "docs" / "OPERATIONS.md"


def test_project_does_not_define_an_ignored_permission_profile() -> None:
    assert not CONFIG.exists()


def test_all_privileged_daily_entries_have_narrow_outside_sandbox_rules() -> None:
    rules = RULES.read_text(encoding="utf-8")
    assert rules.count("prefix_rule(") == 15
    for fixed_entry in (
        "crons\\\\harvest_leads.py",
        "engine_c\\\\etl_yfinance.py",
        "scripts\\\\alpha_purity_snapshot.py",
        "fetchers\\\\edgar.py",
        "scripts\\\\daily_beta_snapshot.py",
        '"-m", "engine_b.cli", "list"',
        '"-m", "engine_b.cli", "drain"',
        "scripts\\\\catalyst_watch.py",
        "scripts\\\\outcome_if_settled_today.py",
        "scripts\\\\prepare_research_action.py",
        '"-m", "decision_lab", "today"',
        '"-m", "engine_b.todo", "sync"',
        '"-m", "engine_b.todo", "work"',
        "scripts\\\\publish_daily_state.py",
        "scripts\\\\publish_daily_brief.py",
    ):
        assert fixed_entry in rules
    assert '"scripts\\\\prepare_research_action.py", "--action-file"' in rules
    assert 'pattern=[".venv\\\\Scripts\\\\python.exe", "-m", "engine_b.todo"]' not in rules
    assert '"engine_b.todo", "dispatch"' not in rules
    assert '"engine_b.todo", "resolve"' not in rules
    for broad_entry in (
        'pattern=["python"',
        'pattern=[".venv\\\\Scripts\\\\python.exe"]',
        'pattern=["powershell"',
        'pattern=["git"',
    ):
        assert broad_entry not in rules
    assert "stockbot-daily" not in rules


def test_project_memory_defines_common_sandbox_impact_review() -> None:
    agents = AGENTS.read_text(encoding="utf-8")
    operations = OPERATIONS.read_text(encoding="utf-8")
    for token in (
        "`workspace-write` 是路徑邊界",
        "Windows identity／ACL",
        "任何 unattended routine 的 executable surface 變更",
        "更新 permission contract test",
        "端到端 smoke test",
        "重啟只會重新載入**已存在**的 rule",
        "不得用 broad permission",
    ):
        assert token in agents
    for token in (
        "Sandbox／private authority 排錯",
        "verification.status=unavailable",
        "skill 有命令而 rules 沒有",
        "相鄰高權限動詞仍未放行",
        "只有 rule 已存在但載入版本仍舊時才需要重啟",
    ):
        assert token in operations
