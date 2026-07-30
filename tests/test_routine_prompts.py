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
    assert "self_funded_supported_range" in text
    assert "Portfolio CASH − cash floor" in text
    assert "Alpha／Beta 共用" in text
    assert "sheet_conservative_range" not in text
    assert "household_cash_supported_range" not in text
    assert "contingent_credit_available" in text
    assert "loan_funded_supported_range" in text
    assert "spreadsheets.readonly" in text
    assert "retirement_net_terminal_wealth" in text
    assert "failure_class" in text
    assert "access_blocked" in text
    assert "同一來源後續成功才算 recovered" in text
    assert "可互換" in text and "不認 agent 身分" in text
    assert "engine_b.todo complete-ra" in text
    assert "一般 `todo batch` 不得用 bare go" in text
    assert "--risk-view changes" in text
    assert "event_search_requests" in text
    assert "不註冊 lead" in text
    assert "自有現金可部署" in text
    assert "本輪可評估上限" in text
    assert "未動用貸款額度" in text
    assert "槓桿 ETF 資金占比" in text
    assert "換算槓桿曝險" in text
    assert "不得用未解釋的斜線" in text
    for light in ("🟢", "🟡", "⚪", "🔴"):
        assert light in text


def test_daily_prompt_requires_subject_complete_pq2_items() -> None:
    text = DAILY.read_text(encoding="utf-8")
    for token in (
        "每個 active pq2 item 不得只列短標題",
        "誰供應誰",
        "事件成熟度",
        "證據與反證邊界",
        "`go` 實際授權的 action type",
    ):
        assert token in text


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
    assert "--risk-view full --no-record-risk" in text
    assert "投組風險完整快照" in text
