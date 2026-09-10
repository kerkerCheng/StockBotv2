"""Daily Brief scheduled task 只使用窄 fixed-entry rules。"""
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


ALLOWED_PREFIXES = (
    (r".venv\Scripts\python.exe", r"crons\harvest_leads.py"),
    (r".venv\Scripts\python.exe", r"engine_c\etl_yfinance.py"),
    (r".venv\Scripts\python.exe", r"scripts\alpha_purity_snapshot.py"),
    (r".venv\Scripts\python.exe", r"fetchers\edgar.py"),
    (r".venv\Scripts\python.exe", r"fetchers\mops.py"),
    (r".venv\Scripts\python.exe", r"scripts\daily_beta_snapshot.py"),
    (r".venv\Scripts\python.exe", "-m", "engine_b.cli", "list"),
    (r".venv\Scripts\python.exe", "-m", "engine_b.cli", "drain"),
    (r".venv\Scripts\python.exe", r"scripts\catalyst_watch.py"),
    (r".venv\Scripts\python.exe", r"scripts\outcome_if_settled_today.py"),
    (
        r".venv\Scripts\python.exe",
        r"scripts\prepare_research_action.py",
        "--action-file",
    ),
    (r".venv\Scripts\python.exe", r"scripts\publish_daily_state.py"),
    (r".venv\Scripts\python.exe", "-m", "decision_lab", "today"),
    (r".venv\Scripts\python.exe", "-m", "engine_b.todo", "sync"),
    (r".venv\Scripts\python.exe", "-m", "engine_b.todo", "work"),
    (r".venv\Scripts\python.exe", "-m", "engine_b.todo", "reassess-stale"),
    (r".venv\Scripts\python.exe", "-m", "engine_b.todo", "standing-go"),
    (r".venv\Scripts\python.exe", "-m", "webapp", "materialize"),
    (r".venv\Scripts\python.exe", r"scripts\publish_daily_brief.py"),
    (r".venv\Scripts\python.exe", r"scripts\backfill_fiscal_year_results.py"),
)


def _codex_binary() -> str | None:
    """Codex CLI 的位置——PATH 找不到時再問已知安裝點。

    2026-09-11 實測：只靠 `shutil.which("codex")` 時，本機六個 execpolicy 測試
    **永遠 skip**（Codex 以 app bundle 安裝，可執行檔不在 PATH 上）。而它們存在的
    全部理由就是驗「rules 真的載入得起來」——恆 skip 的測試與恆綠的測試同形，
    兩者都不會因為 rules 壞掉而變紅（L13：要驗的是那個會因為真的成功而改變的東西）。
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
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        shell=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.skipif(CODEX is None, reason="Codex CLI 未安裝")
def test_all_twenty_rules_parse_and_allow_their_existing_prefixes() -> None:
    """文字存在不代表 rule 能載入；用產品自己的 parser 驗完整檔與每條 prefix。

    2026-09-10 實際事故：permission contract test 全綠，但一段 Python 式隱式
    字串串接不是合法 Starlark，導致整份 allowlist 未載入，所有 fixed entry
    落入 Auto-review。這裡刻意不自製 parser，直接使用官方排錯入口。
    """
    assert len(ALLOWED_PREFIXES) == 20
    for prefix in ALLOWED_PREFIXES:
        result = _execpolicy_check(*prefix)
        assert result.get("decision") == "allow", prefix


@pytest.mark.skipif(CODEX is None, reason="Codex CLI 未安裝")
@pytest.mark.parametrize(
    "command",
    (
        (r".venv\Scripts\python.exe", r"scripts\publish_daily_state_backup.py"),
        (r".venv\Scripts\python.exe", r"scripts\publish_daily_brief_backup.py"),
        (r".venv\Scripts\python.exe", r"scripts\record_mechanical_observation.py"),
        (r".venv\Scripts\python.exe", "-m", "webapp", "serve"),
        ("git", "push", "origin", "master"),
    ),
)
def test_adjacent_privileged_commands_remain_outside_the_allowlist(
    command: tuple[str, ...],
) -> None:
    assert _execpolicy_check(*command).get("decision") != "allow"


def test_project_does_not_define_an_ignored_permission_profile() -> None:
    assert not CONFIG.exists()


def test_all_privileged_daily_entries_have_narrow_outside_sandbox_rules() -> None:
    rules = RULES.read_text(encoding="utf-8")
    assert rules.count("prefix_rule(") == 20
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
        '"-m", "engine_b.todo", "reassess-stale"',
        '"-m", "engine_b.todo", "standing-go"',
        "scripts\\\\publish_daily_state.py",
        "scripts\\\\publish_daily_brief.py",
        '"-m", "webapp", "materialize"',
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


def test_webapp_serve_is_not_allowed_alongside_materialize() -> None:
    """`webapp` 模組只放行 materialize，**不放行 serve**。

    兩者的 side effect 不同級：materialize 只寫 ignored derived cache，serve 會**綁定本機 port**
    ——那是新增 listener surface，且外部認證邊界在 Cloudflare Access 而不是程式本身。
    放行整個 `-m webapp` 會把 serve 一併帶進去，那正是 AGENTS.md 說的「用 broad permission
    掩蓋整合缺口」。serve 由開機自啟的 vbs 長駐，不需要、也不該由排程啟動。
    """
    rules = RULES.read_text(encoding="utf-8")

    assert '"-m", "webapp", "materialize"' in rules
    for adjacent_but_forbidden in (
        '"-m", "webapp", "serve"',
        'pattern=[".venv\\\\Scripts\\\\python.exe", "-m", "webapp"]',
        '"-m", "webapp", "verify"',
    ):
        assert adjacent_but_forbidden not in rules, adjacent_but_forbidden


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
    """sandbox impact review 的**判準與程序**都必須被寫下來。

    ⚠ 2026-09-04（Phase 3.9）分家：**判準留 `AGENTS.md`，程序搬 `OPERATIONS.md`**
    （「OPERATIONS 被改壞 → 跑不起來；AGENTS 被改壞 → 跑起來了，但做錯事」）。
    這條測試因此**改成兩份各驗自己該有的**，而不是放寬——
    每一個 token 仍然被斷言存在，只是換了檔案。搬移當下它就是這樣被抓到的。
    """
    agents = AGENTS.read_text(encoding="utf-8")
    operations = OPERATIONS.read_text(encoding="utf-8")
    for token in (
        # 判準：改壞了會讓人在無人值守路徑上加危險命令
        "任何 unattended routine 的 executable surface 變更",
        "不得用 broad permission",
    ):
        assert token in agents, f"AGENTS.md 缺少 sandbox 判準：{token}"
    for token in (
        # 程序：改壞了只會讓人排錯排錯方向
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
    ):
        assert token in operations


def test_mechanical_queue_segments_are_split_by_capability_not_by_convenience() -> None:
    """研究閉環 P5（2026-09-09）：daily 吃機械段，三支命令按 side effect 分兩邊。

    - `engine_b.cli consume-fired` 只讀寫 repo 內 `pending_leads.json`／`event_watches.json`（同目錄 tempfile
      原子替換），無網路無憑證——**留在 workspace-write sandbox，不得出現在 rule pattern**（與 event_watch
      sweep 同一條先例；放進去就是 broad permission 掩蓋整合缺口）。
    - `engine_b.todo reassess-stale`／`standing-go` 會跑 reassess（Neo4j／Engine C／Sheet readonly），
      需要 exact rule；**相鄰的 dispatch／resolve 仍不放行**——使用者的 go／drop 動詞不進無人值守。
    - daily prompt 必須帶這三步與 `--registry-listed`（APP 73 檔每天更新），否則 rule 放了沒人用（L13）。
    """
    rules = RULES.read_text(encoding="utf-8")
    patterns = re.findall(r"pattern=\[(.*?)\]", rules, re.S)
    assert not [p for p in patterns if "consume-fired" in p], "consume-fired 不需要 escalation"
    assert '"engine_b.todo", "reassess-stale"' in rules and '"engine_b.todo", "standing-go"' in rules
    assert '"engine_b.todo", "dispatch"' not in rules and '"engine_b.todo", "resolve"' not in rules

    prompt = (ROOT / "crons" / "daily_brief_prompt.md").read_text(encoding="utf-8")
    for token in (
        "engine_b.cli consume-fired",
        "engine_b.todo reassess-stale --run",
        "engine_b.todo standing-go --run",
        "--registry-listed",
        "今日自動清了",
    ):
        assert token in prompt, f"daily prompt 缺 {token}"
    skill = (ROOT / "skills" / "daily-brief" / "SKILL.md").read_text(encoding="utf-8")
    for token in ("consume-fired", "reassess-stale --run", "standing-go --run", "--registry-listed"):
        assert token in skill, f"daily-brief skill 缺 {token}"


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

    ⚠ **①要問的是「有沒有這樣一條 rule」，不是「檔案裡有沒有這串字」。**
    第一版寫成 `"event_watch" not in rules`，2026-09-04 被 publisher 的
    justification 誤觸——那段文字只是提到檔名 `event_watches.json`，
    不是一條 permission。gate 攔到的是散文不是權限（L15），
    修法一樣是**改它問問題的方式**：只掃 `pattern=[...]`。
    """
    rules = RULES.read_text(encoding="utf-8")
    patterns = re.findall(r"pattern=\[(.*?)\]", rules, re.S)
    assert patterns, "rules 檔解析不出任何 pattern——這條檢查會變成恆真"
    offenders = [p for p in patterns if "event_watch" in p]
    assert not offenders, f"event_watch 不需要 escalation，卻出現在 rule pattern：{offenders}"

    prompt = (ROOT / "crons" / "daily_brief_prompt.md").read_text(encoding="utf-8")
    for token in (
        "event_watch sweep",
        "sweep_budget_per_run",
        "--mark-checked",
    ):
        assert token in prompt


def test_xbrl_backfill_is_allowed_but_the_generic_observation_writer_is_not() -> None:
    """研究閉環 P7-a：放行的必須是**只寫得了一個 mechanical 欄位**的那一支。

    `scripts/record_mechanical_observation.py` 接受任意 `--field`，雖然它自己會擋
    judgment 欄位，但它的 surface 是「registry 裡所有 mechanical 欄位」而不是一個。
    無人值守只放行能由既有 gate 約束的**最窄** prefix（`AGENTS.md` 協作與邊界）。
    """
    rules = RULES.read_text(encoding="utf-8")
    assert 'scripts\\\\backfill_fiscal_year_results.py' in rules

    for adjacent_but_forbidden in (
        'scripts\\record_mechanical_observation.py',   # 任意 --field
        '"-m", "engine_c"',                                  # 整個 package
        '"engine_b.todo", "complete"',                       # pq2 核准後的 Engine C 判讀寫入
    ):
        assert adjacent_but_forbidden not in rules, adjacent_but_forbidden


def test_xbrl_backfill_can_only_write_one_mechanical_field() -> None:
    """腳本自己就是那道閘門：欄位是常數、非 mechanical 直接 exit 3。

    `append_manual_observation` **不擋** judgment 欄位（它只在 mechanical 時多驗數值），
    所以這道收緊必須在腳本裡，不能靠「FIELD 常數沒被改過」（L15：放行與收緊同時發生）。
    """
    from engine_c.observation_fields import validate_field_name

    source = (ROOT / "scripts" / "backfill_fiscal_year_results.py").read_text(encoding="utf-8")
    assert 'FIELD = "fiscal_year_results"' in source
    assert 'spec.verifiability != "mechanical"' in source
    # 沒有任何 CLI 參數可以換掉欄位
    assert "--field" not in source
    assert validate_field_name("fiscal_year_results").verifiability == "mechanical"
