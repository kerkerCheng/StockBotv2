"""Daily／weekly Codex 本機 routine prompt 的 v1.2 契約。"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"
DAILY = ROOT / "crons" / "daily_brief_prompt.md"
WEEKLY = ROOT / "crons" / "weekly_scan_prompt.md"


def test_daily_prompt_uses_local_authorities_and_repo_venv() -> None:
    text = DAILY.read_text(encoding="utf-8")
    for token in (
        "$daily-brief",
        "$alpha-status",
        ".venv\\Scripts\\python.exe",
        "crons\\harvest_leads.py",
        "engine_b.cli harvest-health",
        "engine_c\\etl_yfinance.py",
        "scripts\\daily_beta_snapshot.py",
        "scripts\\alpha_purity_snapshot.py",
        "fetchers\\edgar.py",
        "engine_b.cli list",
        "engine_b.cli drain",
        "scripts\\catalyst_watch.py",
        "scripts\\outcome_if_settled_today.py",
        "scripts\\prepare_research_action.py",
        "decision_lab today",
        "engine_b.todo sync",
        "engine_b.todo work",
        "scripts\\publish_daily_state.py",
        "query.coverage_gaps",
    ):
        assert token in text
    assert "master" in text
    assert "不要建立 branch" in text


def test_daily_prompt_uses_fixed_entries_on_first_call_and_never_replays_permission_failures() -> None:
    text = DAILY.read_text(encoding="utf-8")
    assert "Daily 的唯一權限來源" in text
    assert "第一次呼叫就用" in text and "`require_escalated` 命中 exact" in text
    assert "不得先在 sandbox 製造可預期失敗再升權重重跑" in text
    assert "bounded、idempotent retry 跑完作最後一步" in text
    assert "不得在 routine" in text and "整份 Daily Brief" in text
    assert "不得改用更寬 rule 或手動重跑" in text
    assert "已有 `dispatch_ref`" in text
    assert "不得用它代替 `dispatch`／`resolve`／`reassess`" in text


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
    assert "beta 行情" in text
    # 2026-08-29：已無逐檔 supported range，單檔行情降級不得再被寫成「該商品 range 歸零」。
    assert "單檔行情降級**不歸零**共用 supported range" in text
    assert "self_funded_supported_range" in text
    assert "Portfolio CASH − cash floor" in text
    assert "Alpha／Beta 共用" in text
    assert "sheet_conservative_range" not in text
    assert "household_cash_supported_range" not in text
    assert "contingent_credit_available" in text
    assert "loan_funded_supported_range" in text
    assert "spreadsheets.readonly" in text
    # ⚠ 2026-09-08：beta 呈現搬 APP，目標句跟著資料走進 artifact（見 test_daily_brief_skill 同一條）。
    assert "retirement_net_terminal_wealth" in (ROOT / "webapp" / "materialize.py").read_text(encoding="utf-8")
    assert "#/beta" in text and "APP 未更新" in text
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
    # 2026-08-29 訊號拔除：beta 不再回答「今天該不該投」，只回答距目標多遠與在什麼水位。
    assert "目標配置差距" in text
    # ⚠ 2026-09-08：beta 呈現搬 APP，契約句跟著搬進 artifact（見 test_daily_brief_skill 同一條）。
    beta_home = (ROOT / "webapp" / "materialize.py").read_text(encoding="utf-8")
    for clause in ("config/target_allocation.json", "band 是容忍區間不是 gate",
                   "只呈現、不參與排序、不換算金額", "不得用 RSI／MACD 等動能指標表達水位",
                   "不是該等回檔的訊號", "貸款 tranche 不適用配置建議"):
        assert clause in beta_home, f"beta artifact 少了契約句：{clause}"
    for banned in ("本輪可評估上限", "CONTRIBUTE REVIEW", "PAUSE CONTRIBUTION",
                   "baseline_pace", "campaign budget", "節奏"):
        assert banned not in text, f"daily prompt 不得再描述已拔除的訊號機制：{banned}"
    app_js = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    for clause in ("未動用貸款額度", "槓桿 ETF 資金占比", "換算槓桿曝險"):
        assert clause in text or clause in beta_home or clause in app_js, (
            f"資本欄位標籤消失了：{clause}"
        )
    assert "不得用未解釋的斜線" in AGENTS.read_text(encoding="utf-8") or "不得用未解釋的斜線" in text
    # 燈號只表達行情資料狀態；🟡 與舊語意已於 2026-08-29 廢止，該廢止必須留著當剎車——
    # 只是刪掉舊燈號不會阻止下一個 session 把它加回來。
    # ⚠ 2026-09-08：燈號隨 beta 呈現搬到 APP，所以**文字的產生端**才是該驗的地方；
    #    prompt 只需保留「只表達資料狀態」這條判準與廢止紀錄。
    allocation = (ROOT / "portfolio" / "allocation.py").read_text(encoding="utf-8")
    for light in ("🟢 行情正常", "🔴 資料不足", "⚪ 歷史不足"):
        assert light in allocation, f"燈號文字的產生端少了 {light}"
    assert "燈號只表達行情資料狀態，不表達投入建議" in AGENTS.read_text(encoding="utf-8"), (
        "燈號判準的家是 AGENTS.md 的 Beta 呈現契約"
    )
    assert "已於 2026-08-29 明文**廢止**" in AGENTS.read_text(encoding="utf-8")


def test_daily_prompt_requires_subject_complete_pq2_items() -> None:
    text = DAILY.read_text(encoding="utf-8")
    for token in (
        # 決策行（2026-08-29）：第一行就要能決定要不要展開。
        "第一行必須是決策行",
        "不含 <最相鄰但未授權的動作>",
        # 密度欄位一項都不減——決策行改的是閱讀順序，不是刪內容。
        "不得只列短標題",
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
        assert "codex_app__set_thread_title" not in text
        assert "title_update_failed" not in text


def test_daily_brief_preserves_beta_market_heartbeat_and_canonical_output() -> None:
    """⚠ 2026-09-04（Phase 3.9）分家：**判準留 `AGENTS.md`，欄位細節搬
    `docs/ARCHITECTURE.md`**。這條測試因此改成兩組各驗自己該有的，
    **每個 token 仍然被斷言存在**——搬移當下它就是這樣被抓到的（本檔第三次）。
    """
    architecture = ROOT / "docs" / "ARCHITECTURE.md"
    # ① 判準：不得省略心跳、舊語意必須明文廢止、canonical brief 只有一份
    materialize = (ROOT / "webapp" / "materialize.py").read_text(encoding="utf-8")
    for path in (AGENTS, DAILY, ROOT / "skills" / "daily-brief" / "SKILL.md"):
        text = path.read_text(encoding="utf-8")
        # ⚠ 禁的是「當成現行欄位使用」，不是提到這個詞——文件刻意留著移除紀錄，
        # 那正是防止它被重新加回來的剎車（見 AGENTS.md「技術訊號的地位」移除清單）。
        assert "本輪可評估上限：" not in text
        assert "canonical Markdown" in text or "Canonical Brief" in text
    # ① 舊燈號語意必須被明文廢止，而不是安靜消失——安靜消失擋不住下次回填。
    #    2026-09-08 Daily 不再印 beta 逐檔表，這份紀錄因此跟著搬到「呈現的新家」。
    for path in (AGENTS, architecture, ROOT / "skills" / "daily-brief" / "SKILL.md"):
        text = path.read_text(encoding="utf-8")
        assert "廢止" in text and "2026-08-29" in text, f"{path.name} 少了明文廢止紀錄"
    # ⚠ APP 端的防回填**不是**把廢止清單印給使用者看（那會讓那些字重新出現在畫面上），
    #    而是機械斷言：producer 一個字都不准吐。散文記錄留在 AGENTS／ARCHITECTURE／skill。
    for retired in ("可評估", "冷卻", "暫停新增", "本輪上限", "熱度"):
        assert retired not in materialize, f"beta artifact producer 不得吐出已廢止字彙：{retired}"
    # ② 心跳欄位規格：跟著 artifact 走（Daily 已不印逐檔表）
    for path_text in (architecture, materialize):
        text = path_text if isinstance(path_text, str) else path_text.read_text(encoding="utf-8")
        assert "最新完整交易日" in text
        assert "52 週區間位置" in text or "52週區間位置" in text
        assert "本輪可評估上限：" not in text
    daily = DAILY.read_text(encoding="utf-8")
    skill = (ROOT / "skills" / "daily-brief" / "SKILL.md").read_text(encoding="utf-8")
    # ③ 「不得省略」換成新的保險：APP 沒更新時 Daily 必須說出來（看不到 ≠ 沒發生）
    assert "APP 未更新" in daily and "APP 未更新" in skill
    assert "逐檔表永遠看得到" in materialize
    assert "task 最終回覆必須原樣輸出" in daily
    assert "不得在取得 delivery receipt 後另產生" in skill


def test_daily_prompt_points_at_where_the_panes_live_now() -> None:
    """Daily 不再印四 pane，但**每一段都要指得出新家**；還沒有 APP 畫面的不得先砍。

    ⚠ 2026-09-08 由「必須印完整四 pane」改寫。合法前提只有一個：內容在別處已經讀得到（L13）。
    """
    text = DAILY.read_text(encoding="utf-8")
    for pointer in ("#/ranking", "#/beta", "#/coverage", "#/watches"):
        assert pointer in text, f"prompt 沒有指出 {pointer}"
    # 部位與問責 2026-09-08 也搬進 APP，Daily 只印變動；兩種報酬的錨點語意必須標明
    assert "#/positions" in text
    assert "live（成交價為錨）還是 shadow（入圖日為錨）" in text
    assert "outcome_if_settled_today.py" in text
    # APP 當天沒更新時必須現形，否則「看不到」與「沒發生」同形（L12）
    assert "APP 未更新" in text
    # 已移出的四支命令不得又悄悄回到 daily 命令清單
    assert "不再跑" in text and "query.coverage_gaps" in text


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
