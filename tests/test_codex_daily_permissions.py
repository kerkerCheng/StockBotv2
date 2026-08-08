"""Daily Brief 的 project permission profile 必須窄、完整且可預期。"""
from __future__ import annotations

from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".codex" / "config.toml"
RULES = ROOT / ".codex" / "rules" / "stockbot-automations.rules"


def test_daily_profile_allows_required_domains_without_global_network_wildcard() -> None:
    config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["default_permissions"] == "stockbot-daily"
    profile = config["permissions"]["stockbot-daily"]
    assert profile["extends"] == ":workspace"
    assert profile["filesystem"][":workspace_roots"][".env"] == "read"
    network = profile["network"]
    assert network["enabled"] is True
    assert network["allow_local_binding"] is True
    domains = network["domains"]
    assert "*" not in domains
    for required in (
        "api.x.com",
        "data.sec.gov",
        "www.sec.gov",
        "query1.finance.yahoo.com",
        "query2.finance.yahoo.com",
        "openapi.twse.com.tw",
        "oauth2.googleapis.com",
        "sheets.googleapis.com",
        "localhost",
        "github.com",
        "discord.com",
    ):
        assert domains[required] == "allow"


def test_every_network_or_git_fixed_entry_has_an_outside_sandbox_fallback() -> None:
    rules = RULES.read_text(encoding="utf-8")
    for command in (
        "crons\\\\harvest_leads.py",
        "engine_c\\\\etl_yfinance.py",
        "scripts\\\\daily_beta_snapshot.py",
        '"-m", "decision_lab", "today"',
        '"-m", "engine_b.todo", "sync"',
        "scripts\\\\publish_daily_state.py",
        "scripts\\\\publish_daily_brief.py",
    ):
        assert command in rules
