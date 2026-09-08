"""daily-brief skill 契約：封閉動詞、operational commands、不硬編政策、閘門不放寬。"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "daily-brief" / "SKILL.md"
ALPHA_STATUS = ROOT / "skills" / "alpha-status" / "SKILL.md"


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
        "scripts\\alpha_purity_snapshot.py",
        "-m engine_b.cli",
        "-m engine_b.todo sync",
        "-m engine_b.todo work",
        "-m decision_lab today",
        "drain",  # pq1 priority drain
        "classification-health",
        "--content-type",
        "--decision-impact",
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
    # ⚠ 2026-09-08：beta 的**呈現**搬到 APP，所以目標句與心跳欄位規格跟著資料走到 artifact
    # （L16）。invariant 沒有放寬，只是換了家——這裡改成驗新家，不是刪掉這條檢查。
    beta_home = (ROOT / "webapp" / "materialize.py").read_text(encoding="utf-8")
    assert "retirement_net_terminal_wealth" in beta_home
    assert "最新完整交易日" in beta_home
    assert "52 週區間位置" in beta_home
    assert "#/beta" in text, "skill 必須指得出 beta 現在住哪裡"
    assert "APP 未更新" in text, "APP 沒被 materialize 時 Daily 必須說出來（否則看不到＝沒發生）"
    # 2026-08-29 訊號拔除（commit 6aa31de）：舊契約是「technical 只決定新增 timing／pace」，
    # 新契約是水位只呈現、不參與排序，且 beta 不回答「今天該不該投」。
    # ⚠ 2026-09-08：這些契約句跟著呈現搬進 beta artifact——**呈現在哪裡，契約句就要在哪裡**，
    # 否則規則會留在一份沒有人再照著印的文件裡（L16：分類要跟著資料走到消費端）。
    for clause in ("beta 不回答「今天該不該投」",
                   "只呈現、不參與排序、不換算金額",
                   "不得用 RSI／MACD 等動能指標表達水位",
                   "不是該等回檔的訊號",
                   "config/target_allocation.json",
                   "band 是容忍區間不是 gate",
                   "貸款 tranche 不適用配置建議"):
        assert clause in beta_home, f"beta artifact 少了契約句：{clause}"
    assert "貸款 tranche 不適用配置建議" in text, "skill 仍須保留貸款不適用配置的判準"
    # ⚠ 禁的是「當成現行欄位／動作使用」，不是提到這些詞——skill 刻意留著一段移除紀錄，
    # 那段本身是防回填的剎車。
    for banned in ("本輪可評估上限：", "CONTRIBUTE REVIEW", "PAUSE CONTRIBUTION",
                   "節奏 25%", "🟢 `可評估`"):
        assert banned not in text, f"daily-brief skill 不得再描述已拔除的訊號機制：{banned}"
    assert "訊號整組已於 2026-08-29 移除" in text
    app_js = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    for clause in ("自有現金可部署", "未動用貸款額度", "槓桿 ETF 資金占比"):
        assert clause in text or clause in beta_home or clause in app_js, (
            f"資本欄位標籤消失了：{clause}"
        )
    assert "換算槓桿曝險" in text
    assert "已投入的非現金部位" in text
    # 燈號只表達行情資料狀態；🟡 與 `可評估／冷卻` 舊語意已廢止。
    for light in ("🟢 `行情正常`", "🔴 `資料不足`", "⚪ `歷史不足`"):
        assert light in text
    assert "🟡 與舊語意" in text


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


def test_first_call_uses_single_fixed_entry_path_and_retry_is_last_resort() -> None:
    text = _text()
    assert "harvest-health" in text
    assert "failure_class" in text
    assert "access_blocked" in text
    assert "legacy `workspace-write` sandbox" in text
    assert "Daily 的唯一權限來源" in text
    assert "第一次呼叫就用 `require_escalated` 命中 exact" in text
    assert "outside-sandbox rule" in text
    assert "不是先製造可預期的 `access_blocked` 再以升權重重跑" in text
    assert "bounded、idempotent retry 作最後一步" in text
    assert "不得在 routine 層重跑整份 fixed entry、整份 Daily Brief" in text
    assert "不得放行整個 PowerShell、Python、Git 或 working tree" in text
    assert "保留結構化 failure、讓受影響資料 fail closed" in text
    assert "不得改用第二條更寬 rule、手動重跑或改寫成「零筆」／`no_result`" in text


def test_scheduled_run_auto_drains_pq1_but_keeps_admission_gate() -> None:
    text = _text()
    assert "依每輪 limit 自動跑" in text
    assert "scripts\\prepare_research_action.py --action-file" in text
    assert "default store 的 Decision work orders" in text
    assert "持股靜默降成空集合" in text
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
    assert "只 checkpoint 已由使用者 exact `go`" in text
    assert "不授權 `dispatch`／`resolve`／`reassess`" in text


def test_every_alpha_pane_still_has_a_home_after_daily_stopped_embedding_them() -> None:
    """四個 pane **不得因為 Daily 不再嵌入就消失**——每一個都要指得出新家。

    ⚠ 這條在 2026-09-08 由「Daily 必須嵌入完整四 pane」改寫。改寫的合法前提只有一個：
    **內容在別處已經讀得到**（L13：要移走一段內容，先確認它有消費端）。所以這裡驗的不是
    「Daily 有沒有印」，而是「每一 pane 現在住哪、Daily 有沒有指得出來」。
    """
    text = _text()
    alpha = ALPHA_STATUS.read_text(encoding="utf-8")

    # ① alpha-status 仍是四 pane 的完整權威——判準只有一份，沒有被稀釋
    for pane in ("## Pane 1 — 現在要投哪一檔", "## Pane 2 — 該去補誰的證據",
                 "## Pane 3 — 哪裡還是空白", "## Pane 4 — 部位與問責"):
        assert pane in alpha, f"alpha-status 少了 {pane}"
    assert "本 skill 仍是「完整四 pane」的權威" in alpha

    # ② Daily 必須指得出前三個 pane 的新家（APP），而不是安靜不提
    for pointer in ("#/ranking", "#/coverage", "$alpha-status"):
        assert pointer in text, f"Daily 沒有指出 {pointer}"

    # ③ Pane 4 於 2026-09-08 也搬進 APP（`positions` kind）→ Daily 只印變動。
    #    **規則本身不變**：還沒有 APP 畫面的段落一律留在 Daily；判準改成機械的——
    #    `webapp status` 列得出那個 kind 才算搬完，不靠誰記得哪一段還沒搬。
    assert "#/positions" in text
    assert "只印變動" in text
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "還沒有 APP 畫面的段落一律留在 Daily" in agents
    assert "webapp status" in agents, "判準必須可機械查證"

    # ④ 移出的動作必須被寫出來，不是安靜消失
    assert "2026-09-08" in text and "不再由 Daily 印出" in text
    assert "daily-brief 目前嵌入本 skill 的完整四個 pane" not in alpha, (
        "alpha-status 不得繼續宣稱自己被 Daily 嵌入——那句話已經是假的"
    )
