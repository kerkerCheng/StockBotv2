"""daily-brief skill 契約：封閉動詞、operational commands、不硬編政策、閘門不放寬。"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "daily-brief" / "SKILL.md"


def _text() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_references_batch_verbs_and_operational_commands() -> None:
    text = _text()
    # v1.1 批次語法動詞
    for verb in ("go", "drop", "pending"):
        assert verb in text
    assert "parse_batch_reply" in text  # deterministic parser，不自由心證
    assert "1 3 7 go 4 drop 5 6 pending" in text  # 範例
    for command in (
        ".venv\\Scripts\\python.exe",
        "crons\\harvest_leads.py",
        "engine_c\\etl_yfinance.py",
        "scripts\\daily_beta_snapshot.py",
        "-m engine_b.cli",
        "-m engine_b.todo sync",
        "-m decision_lab today",
        "drain",  # pq1 priority drain
    ):
        assert command in text


def test_references_closed_loop_and_no_github() -> None:
    text = _text()
    assert "evidence-delta" in text or "evidence_delta" in text
    assert "自動建 Shadow" in text
    assert "GitHub" in text  # 明文說不用 GitHub UI
    assert "record_lead_decision" in text  # 遠端 fallback 仍走 MCP
    assert "scripts\\publish_daily_state.py" in text


def test_does_not_hardcode_probe_policy_numbers() -> None:
    text = _text()
    for forbidden in ("0.5%", "axis_ceilings", "probe_book_nav_cap",
                      "single_probe_nav_cap", "paper_nav ="):
        assert forbidden not in text


def test_states_gates_and_human_boundaries() -> None:
    text = _text()
    # 三道閘門與人工邊界必須明文。
    assert "graph admission" in text
    assert "不連 broker" in text
    assert "recommendation 推定 choice" in text
    # 決策寫入只在本機、遠端 fallback 用唯讀 get_decision_brief。
    assert "get_decision_brief" in text
    assert "只在本機" in text
    assert "不推定 choice／fill" in text
    assert "self_funded_supported_range" in text
    assert "Portfolio CASH − cash floor" in text
    assert "Alpha 與 Beta" in text
    assert "sheet_conservative_range" not in text
    assert "household_cash_supported_range" not in text
    assert "contingent_credit_available" in text
    assert "loan_funded_supported_range=manual_review_required" in text
    assert "spreadsheets.readonly" in text
    assert "retirement_net_terminal_wealth" in text
    assert "technical 只決定新增 timing／pace" in text
    assert "自有現金可部署" in text
    assert "本輪可評估上限" in text
    assert "未動用貸款額度" in text
    assert "槓桿 ETF 資金占比" in text
    assert "換算槓桿曝險" in text
    assert "節奏 25%" in text
    for light in ("🟢", "🟡", "⚪", "🔴"):
        assert light in text


def test_requires_subject_complete_pq2_explanations() -> None:
    text = _text()
    for token in (
        "待核准項目的內容密度",
        "誰、對誰、做了什麼",
        "完整公司名與 ticker",
        "事件成熟度",
        "證據來源、反證",
        "`go` 實際授權的 action type",
    ):
        assert token in text


def test_codex_scheduled_run_does_not_depend_on_task_rename_app() -> None:
    text = _text()
    assert "codex_app__set_thread_title" not in text
    assert "title_update_failed" not in text


def test_access_blocked_is_retried_and_never_presented_as_no_result() -> None:
    text = _text()
    assert "harvest-health" in text
    assert "failure_class" in text
    assert "access_blocked" in text
    assert "首次呼叫就直接使用" in text
    assert "`require_escalated`" in text
    assert "窄 prefix rule" in text
    assert "不得先在 sandbox 製造可預期的失敗再重跑" in text
    assert "把整個 PowerShell、Python 或 working tree 設成 unrestricted" in text
    assert "同一來源後續成功才標 recovered" in text
    assert "不得改寫成「零筆」或 `no_result`" in text


def test_scheduled_run_auto_drains_pq1_but_keeps_admission_gate() -> None:
    text = _text()
    assert "依每輪 limit 自動跑" in text
    assert "Triage PASS 只授權研究、不授權入圖" in text
    assert "prepared RA 進 pq2 後才等待使用者 `go`" in text
    assert "不為了讓每個 PASS 都進 pq2而製造空 Research Action".replace("pq2而", "pq2 而") in text
    assert "## pq1 研究進度（無 pq2 編號）" in text


def test_lead_status_never_claims_evidence_tier() -> None:
    text = _text()
    assert "不是" in text and "evidence tier" in text


def test_uses_persistent_todo_numbers_and_does_not_blindly_dispatch_batch() -> None:
    text = _text()
    assert "todo_pool.json" in text
    assert "不得依當日排序" in text
    assert "todo batch" in text and "不會代做" in text
    assert "engine_b.todo complete-ra" in text
    assert "action:<id>;digest:<sha256>;commit:<sha|not_required>;cohort:<dc_id>" in text
    assert "權限與完成狀態綁 action type＋receipt，不綁 provider" in text


def test_decision_review_go_dispatches_gap_pq1_before_reassess() -> None:
    text = _text()
    assert "engine_b.todo dispatch" in text
    assert "不得立刻拿舊" in text and "bare reassess" in text
    assert "--to awaiting_approval" in text or "awaiting_approval" in text
    assert "decision:<new_decision_id>" in text
