"""Codex 無人值守 allowlist 已清為 0 條（Phase 1 Step 1.3；C1／C4／C6）。

守的機制：**Codex 不在任何無人值守步驟裡**。無人值守只剩 Windows daily（`crons/daily_task.py` 的封閉清單，
由 `tests/test_daily_task.py` 守）；這份 rules 檔留著只為了寫明歷史，**一條 allow 都不得有**。

⚠ 驗的是「Codex 自己的 parser 認不認」，不是「rules 檔裡有沒有那串字」——2026-09-10 事故：文字檢查全綠，
整份 allowlist 卻因語法錯誤根本沒載入（OPERATIONS「文字存在不等於 rule 生效」）。所以舊 12 條逐條丟給
`codex execpolicy check`，而且 parser 找不到時**不 skip 成綠**：恆 skip 的測試與恆綠同形。

原本掛在 rules 上、判準本身沒有退役的斷言（materialize 不含 serve、XBRL 只寫一個欄位、scorecard 的網路上限、
重訊 watcher 的主機、月營收留在互動、機械段不放行 dispatch／resolve）**改主詞**搬到 `tests/test_daily_task.py`。
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".codex" / "config.toml"
RULES = ROOT / ".codex" / "rules" / "stockbot-automations.rules"
AGENTS = ROOT / "AGENTS.md"
OPERATIONS = ROOT / "docs" / "OPERATIONS.md"


#: 退役前的 12 條 exact prefix（2026-09-24 之前的 `ALLOWED_PREFIXES`）。**現在每一條都必須不是 allow。**
RETIRED_PREFIXES = (
    (r".venv\Scripts\python.exe", r"crons\harvest_leads.py"),
    (r".venv\Scripts\python.exe", r"engine_c\etl_yfinance.py"),
    (r".venv\Scripts\python.exe", r"scripts\alpha_purity_snapshot.py"),
    (r".venv\Scripts\python.exe", r"scripts\daily_beta_snapshot.py"),
    (r".venv\Scripts\python.exe", "-m", "engine_b.cli", "list"),
    (r".venv\Scripts\python.exe", r"scripts\catalyst_watch.py"),
    (r".venv\Scripts\python.exe", r"scripts\outcome_if_settled_today.py"),
    (r".venv\Scripts\python.exe", "-m", "engine_b.todo", "sync"),
    (r".venv\Scripts\python.exe", "-m", "engine_b.todo", "standing-go"),
    (r".venv\Scripts\python.exe", "-m", "webapp", "materialize"),
    (r".venv\Scripts\python.exe", r"scripts\publish_daily_brief.py"),
    (r".venv\Scripts\python.exe", r"scripts\backfill_fiscal_year_results.py"),
)


def _codex_binary() -> str | None:
    """Codex CLI 的位置——PATH 找不到時再問已知安裝點。

    2026-09-11 實測：只靠 `shutil.which("codex")` 時，本機 execpolicy 測試**永遠 skip**（Codex 以 app bundle
    安裝，可執行檔不在 PATH 上）。恆 skip 的測試與恆綠的測試同形（L13）。
    """
    found = shutil.which("codex")
    if found:
        return found
    bundled = Path.home() / ".codex" / ".sandbox-bin" / "codex.exe"
    return str(bundled) if bundled.exists() else None


CODEX = _codex_binary()


def _execpolicy_check(*command: str) -> dict[str, object]:
    assert CODEX is not None
    proc = subprocess.run(
        [CODEX, "execpolicy", "check", "--rules", str(RULES), "--", *command],
        cwd=ROOT, capture_output=True, text=True, timeout=30, shell=False,
    )
    assert proc.returncode == 0, f"parser 載入不了 rules 檔：{proc.stderr}"
    return json.loads(proc.stdout)


def test_rules_file_has_zero_prefix_rules() -> None:
    rules = RULES.read_text(encoding="utf-8")
    # 只數真的 rule（行首的 `prefix_rule(`），不數檔頭散文——散文刻意寫出歷史
    assert len(re.findall(r"(?m)^\s*prefix_rule\(", rules)) == 0
    assert "0 條" in rules and "Codex 不在任何無人值守步驟裡" in rules


@pytest.mark.skipif(CODEX is None, reason="Codex CLI 未安裝（本機應找得到 app bundle；CI 才會 skip）")
@pytest.mark.parametrize("prefix", RETIRED_PREFIXES)
def test_every_retired_prefix_is_no_longer_allowed_by_the_parser(prefix: tuple[str, ...]) -> None:
    assert _execpolicy_check(*prefix).get("decision") != "allow", prefix


@pytest.mark.skipif(CODEX is None, reason="Codex CLI 未安裝")
@pytest.mark.parametrize(
    "command",
    (
        (r".venv\Scripts\python.exe", r"crons\daily_task.py"),
        (r".venv\Scripts\python.exe", r"scripts\record_mechanical_observation.py"),
        (r".venv\Scripts\python.exe", "-m", "webapp", "serve"),
        ("git", "push", "origin", "master"),
        (r".venv\Scripts\python.exe", r"fetchers\edgar.py"),
        (r".venv\Scripts\python.exe", "-m", "engine_b.cli", "triage-apply"),
    ),
)
def test_adjacent_commands_are_not_allowed_either(command: tuple[str, ...]) -> None:
    """新的無人值守入口（daily_task、triage-apply）同樣不得透過 Codex 放行——它們不經 Codex。"""
    assert _execpolicy_check(*command).get("decision") != "allow"


def test_retired_list_matches_the_history_written_in_the_rules_header() -> None:
    """退役清單與 rules 檔頭寫的歷史是同一份（寫錯任何一條，parser 測試驗的就不是真正退役的那條）。"""
    rules = RULES.read_text(encoding="utf-8")
    for prefix in RETIRED_PREFIXES:
        tail = " ".join(prefix[1:])
        assert tail in rules, f"rules 檔頭沒記下退役的 {tail}"


def test_project_does_not_define_an_ignored_permission_profile() -> None:
    assert not CONFIG.exists()


def test_project_memory_defines_common_sandbox_impact_review() -> None:
    """sandbox impact review 的**判準與程序**都必須被寫下來（判準留 AGENTS、程序住 OPERATIONS）。"""
    agents = AGENTS.read_text(encoding="utf-8")
    operations = OPERATIONS.read_text(encoding="utf-8")
    for token in (
        "任何 unattended routine 的 executable surface 變更",
        "不得用 broad permission",
    ):
        assert token in agents, f"AGENTS.md 缺少 sandbox 判準：{token}"
    for token in (
        "`workspace-write` 是路徑邊界",
        "Windows identity／ACL",
        "更新 permission contract test",
        "端到端 smoke test",
        "重啟只會重新載入**已存在**的 rule",
        "Sandbox／private authority 排錯",
        "verification.status=unavailable",
        "skill 有命令而 rules 沒有",
        "相鄰高權限動詞仍未放行",
        "只有 rule 已存在但載入版本仍舊時才需要重啟",
        "Triage classification surface impact",
        "不新增 unattended rule",
        # 2026-09-24：Codex 退出無人值守的那一次 review
        "Phase 1 Step 1.3：triage 併進 daily、Codex 退出無人值守",
    ):
        assert token in operations, token


def test_heartbeat_monthly_revenue_line_reads_no_network() -> None:
    """心跳第 1 段的月營收行必須維持心跳的零網路契約（`sync`／`backfill` 會連 MOPS，不得出現在心跳）。"""
    heartbeat = (ROOT / "crons" / "heartbeat.py").read_text(encoding="utf-8")
    assert "_monthly_revenue_line" in heartbeat
    for network_entry in ("sync_current", "backfill(", "fetch_monthly_revenue"):
        assert network_entry not in heartbeat, network_entry
