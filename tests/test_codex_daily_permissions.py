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
    assert rules.count("prefix_rule(") == 16
    for fixed_entry in (
        "crons\\\\harvest_leads.py",
        "engine_c\\\\etl_yfinance.py",
        "scripts\\\\alpha_purity_snapshot.py",
        "fetchers\\\\edgar.py",
        "fetchers\\\\mops.py",
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
    for sandbox_only_entry in (
        '"engine_b.cli", "triage"',
        '"engine_b.cli", "classification-health"',
        "scripts\\backfill_lead_classification.py",
    ):
        assert sandbox_only_entry not in rules
    for broad_entry in (
        'pattern=["python"',
        'pattern=[".venv\\\\Scripts\\\\python.exe"]',
        'pattern=["powershell"',
        'pattern=["git"',
    ):
        assert broad_entry not in rules
    assert "stockbot-daily" not in rules


def test_fetchers_directory_is_not_broadly_allowed() -> None:
    """fetchers/ 只放行兩支公開文件下載器，不是整包。

    edgar.py 與 mops.py 都是「從公開來源抓指定文件到本機 raw store」，無憑證、
    不碰 identity/ACL、不寫 private authority。同目錄的 gsheets.py 則使用 Google
    service account 憑證，屬 credential-bearing surface——放行整個 fetchers 目錄
    會把它一併帶進去，那正是 AGENTS.md 說的「用 broad permission 掩蓋整合缺口」。
    """
    rules = RULES.read_text(encoding="utf-8")

    assert "fetchers\\\\edgar.py" in rules
    assert "fetchers\\\\mops.py" in rules

    for credential_bearing in (
        "fetchers\\\\gsheets.py",
        'pattern=[".venv\\\\Scripts\\\\python.exe", "fetchers"]',
        'pattern=[".venv\\\\Scripts\\\\python.exe", "-m", "fetchers"]',
    ):
        assert credential_bearing not in rules


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
        "Triage classification surface impact",
        "不新增 unattended rule",
    ):
        assert token in operations


def test_event_watch_sweep_is_in_sandbox_not_escalated() -> None:
    """Event Watch T2 sweep 的 sandbox impact review 結論（2026-08-31）。

    `python -m engine_b.event_watch sweep [--mark-checked]` 只讀
    config/event_watch.json 與 library/leads/event_watches.json、寫後者
    （同目錄 tempfile 原子替換）——無網路、無憑證、無 identity/ACL、
    無 private authority，完全在 workspace-write sandbox 內，**不需**
    outside-sandbox rule。WebSearch 部分由 daily agent 既有能力執行
    （同事件監控先例），受 config `sweep_budget_per_run` cap 約束。

    本測試鎖兩件事：①rules 檔**不得**出現 event_watch 條目——它不需要
    escalation，未來有人順手放寬就是 broad permission 掩蓋整合缺口；
    ②daily prompt 必須帶 sweep 步驟與 cap 紀律。
    """
    rules = RULES.read_text(encoding="utf-8")
    assert "event_watch" not in rules

    prompt = (ROOT / "crons" / "daily_brief_prompt.md").read_text(encoding="utf-8")
    for token in (
        "event_watch sweep",
        "sweep_budget_per_run",
        "--mark-checked",
    ):
        assert token in prompt
