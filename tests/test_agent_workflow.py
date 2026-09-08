"""Agent Development Flow 的防腐測試。

這套流程沒有 runtime 產出可以驗——它的載體是三份 Markdown 與一個 agent 的行為。
所以**它的剎車必須是「文件說謊會變紅」**，而不是「跑得起來」。

三件會靜默腐爛的事，各對應一組斷言：

1. **文件複雜度失控。** agent workflow 最典型的失敗是長成一堆 `worker.md`／`reviewer.md`／
   `orchestrator.md` 碎檔，每份都聲稱自己是權威。這裡用 `<!-- agent-workflow-canonical -->`
   標記做硬上限（4），並直接擋住那些檔名重生。

2. **字彙漂移。** Zoom Level 與 Review Level 分別寫在模型檔（`docs/AGENT_WORKFLOW.md`）與
   執行檔（`skills/development-flow/SKILL.md`）。兩份各寫一套等級名稱時，agent 會照著手上
   那份跑，而使用者以為看的是另一份——L16 記過的形狀。

3. **判準被搬走後沒人守。** 「GO 只關閉本 Step」是本流程唯一的 hard invariant。它被刪掉時
   不會有任何東西壞掉，系統只會安靜地開始自己往下一個 Step 跑。

⚠ 依 Phase 3.9 定下的分家慣例：**判準驗 `AGENTS.md`，程序驗 `docs/`／`skills/`**，
兩份各驗自己該有的，不是把同一段字串在兩個地方各斷言一次。
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MARKER = "<!-- agent-workflow-canonical -->"
CANONICAL_BUDGET = 4

WORKFLOW = ROOT / "docs" / "AGENT_WORKFLOW.md"
DEV_FLOW = ROOT / "skills" / "development-flow" / "SKILL.md"
BLIND_SPOT = ROOT / "skills" / "blind-spot-audit" / "SKILL.md"
AGENTS = ROOT / "AGENTS.md"

# 掃描時跳過：虛擬環境、版控內部、逐字封存的歷史、私有資料與抓下來的原文。
_SKIP_PREFIXES = (
    ".venv",
    ".git",
    ".pytest_cache",
    ".pytest_tmp",
    "docs/archive",
    "library",
    "node_modules",
)


def _markdown_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*.md"):
        rel = path.relative_to(ROOT).as_posix()
        if any(rel == p or rel.startswith(f"{p}/") for p in _SKIP_PREFIXES):
            continue
        files.append(path)
    return files


def _marker_holders() -> set[str]:
    return {
        path.relative_to(ROOT).as_posix()
        for path in _markdown_files()
        if MARKER in path.read_text(encoding="utf-8")
    }


def _declared_canonical() -> list[str]:
    """`AGENT_WORKFLOW.md` §11 自己宣告的 canonical 清單。"""
    text = WORKFLOW.read_text(encoding="utf-8")
    section = text.split("## 11.", 1)[1].split("\n## ", 1)[0]
    return re.findall(r"^\d+\.\s+`([^`]+)`", section, flags=re.MULTILINE)


def test_canonical_workflow_docs_stay_within_the_budget() -> None:
    """帶 canonical 標記的檔案不得超過 4 份，且必須與文件自己宣告的清單逐字相同。

    空跑檢查：從 `skills/development-flow/SKILL.md` 拿掉標記 → 這條會紅
    （宣告 3 份、實際只找到 2 份）。
    """
    holders = _marker_holders()
    assert len(holders) <= CANONICAL_BUDGET, (
        f"canonical agent-workflow 檔超出預算（{len(holders)} > {CANONICAL_BUDGET}）："
        f"{sorted(holders)}。要新增第五份必須先退役一份。"
    )
    declared = _declared_canonical()
    assert declared, "AGENT_WORKFLOW.md §11 應列出 canonical 清單"
    assert set(declared) == holders, (
        "宣告的 canonical 清單與實際帶標記的檔案不一致——"
        f"宣告 {sorted(declared)}／實際 {sorted(holders)}"
    )


def test_splinter_agent_docs_do_not_come_back() -> None:
    """`worker.md`／`reviewer.md`／`orchestrator.md` 這類碎檔不得出現。

    這是 bootstrap 當時明確列出的反面清單。它們一旦出現，「哪一份是權威」就要靠記憶回答。
    """
    forbidden = {
        "worker.md",
        "reviewer.md",
        "architect.md",
        "planner.md",
        "orchestrator.md",
        "delivery.md",
        "verdict.md",
        "zoom.md",
    }
    found = sorted(
        path.relative_to(ROOT).as_posix()
        for path in _markdown_files()
        if path.name.lower() in forbidden
    )
    assert not found, f"agent workflow 碎檔重生了：{found}"


def test_zoom_and_review_vocabularies_do_not_drift() -> None:
    """模型檔與執行檔必須用同一組等級名稱，且不得自創新等級。"""
    model = WORKFLOW.read_text(encoding="utf-8")
    runner = DEV_FLOW.read_text(encoding="utf-8")

    for level in ("Z0", "Z1", "Z2", "Z3", "R0", "R1", "R2"):
        assert level in model, f"AGENT_WORKFLOW.md 缺少等級 {level}"
        assert level in runner, f"development-flow SKILL.md 缺少等級 {level}"

    for invented in ("Z4", "R3", "Z-1"):
        assert invented not in model, f"AGENT_WORKFLOW.md 自創了等級 {invented}"
        assert invented not in runner, f"development-flow SKILL.md 自創了等級 {invented}"


def test_verdict_vocabulary_is_closed_and_shared() -> None:
    """四個 verdict 是封閉字彙，兩份文件都必須列全。"""
    model = WORKFLOW.read_text(encoding="utf-8")
    runner = DEV_FLOW.read_text(encoding="utf-8")
    for verdict in ("GO", "CONDITIONAL_GO", "NO_GO", "HUMAN_REQUIRED"):
        assert verdict in model, f"AGENT_WORKFLOW.md 缺少 verdict {verdict}"
        assert verdict in runner, f"development-flow SKILL.md 缺少 verdict {verdict}"


def test_the_message_protocol_stays_at_seven_words() -> None:
    """七種 message 是刻意封閉的。多一種就代表有人在蓋 workflow engine。"""
    model = WORKFLOW.read_text(encoding="utf-8")
    for word in (
        "IDEA",
        "PLAN_PROPOSAL",
        "WORK_REQUEST",
        "DELIVERY",
        "REVIEW",
        "SCOPE_ESCALATION",
        "HUMAN_DECISION",
    ):
        assert word in model, f"message protocol 缺少 {word}"
    for forbidden in ("message queue", "workflow database", "autonomous merge bot"):
        assert forbidden in model, (
            f"「不做什麼」的清單缺少 {forbidden}——那份清單是這個 Phase 的 scope 界線"
        )


def test_go_does_not_open_the_next_step() -> None:
    """本流程唯一的 hard invariant：**判準寫在 `AGENTS.md`**。

    這條被刪掉時不會有任何東西壞掉——系統只會安靜地開始自己往下一個 Step 跑，
    而那正是 bootstrap 要防的第一件事。
    """
    agents = AGENTS.read_text(encoding="utf-8")
    assert "只關閉本 Step，不開啟下一個 Step" in agents, (
        "AGENTS.md 缺少『GO 只關閉本 Step，不開啟下一個 Step』這條判準"
    )
    assert "AGENT_WORKFLOW.md" in agents, "AGENTS.md 應指得到流程檔"


STEP_RESULT_FIELDS = (
    "Current Phase",
    "Current Step",
    "Zoom / Review",
    "Verdict",
    "Acceptance status",
    "Blocking findings",
    "Non-blocking debt",
    "Suggested next Step",
)


def test_step_result_keeps_all_eight_fields() -> None:
    """八欄缺一不可；少一欄，使用者就得回頭讀 transcript 才知道發生了什麼。"""
    runner = DEV_FLOW.read_text(encoding="utf-8")
    model = WORKFLOW.read_text(encoding="utf-8")
    for field in STEP_RESULT_FIELDS:
        assert field in runner, f"STEP_RESULT 少了 `{field}`（執行檔）"
        assert field in model, f"STEP_RESULT 少了 `{field}`（模型檔）"


def test_the_declared_step_result_count_matches_the_actual_block() -> None:
    """文件寫「八欄」時，那個區塊裡真的要有八欄。

    ⚠ 這條是第一版漏掉的檢查，而漏掉的代價當場發生：第一版把八個欄位寫成「七欄」，
    因為那個數字是**手寫的標籤，沒有任何東西去數它**。這正是 L14 的形狀——
    一個沒被量測的宣稱，看起來完全正常。修法不是把標籤改對就好，是讓它被數。
    """
    runner = DEV_FLOW.read_text(encoding="utf-8")
    block = runner.split("## Step 5｜STEP_RESULT", 1)[1].split("```", 2)[1]
    rows = [
        line for line in block.splitlines()
        if re.match(r"^[A-Za-z][^:]*:", line)
    ]
    assert len(rows) == len(STEP_RESULT_FIELDS), (
        f"STEP_RESULT 區塊實際有 {len(rows)} 欄，宣告是 {len(STEP_RESULT_FIELDS)} 欄：{rows}"
    )
    heading = runner.split("## Step 5｜STEP_RESULT", 1)[1].split("\n", 1)[0]
    assert "八欄" in heading, f"標題宣告的欄數與實際不符：{heading!r}"


HUMAN_SUMMARY_LINES = ("做了什麼", "為什麼重要", "現在在哪", "下一步")
NEXT_STEP_SEGMENTS = ("What", "Why now", "After this")


def test_human_summary_is_specified_in_both_canonical_files() -> None:
    """人話那幾行也要被數。

    ⚠ 同 `八欄` 那條的教訓：一個手寫的宣稱若沒有東西去數它，它會安靜地少一行
    （L14）。這裡數的是「四行問句」與「下一步的三段」，因為少任何一個，
    使用者就得回頭問「所以這對我的目標做了什麼／為什麼現在做」。
    """
    runner = DEV_FLOW.read_text(encoding="utf-8")
    model = WORKFLOW.read_text(encoding="utf-8")
    for name, text in (("執行檔", runner), ("模型檔", model)):
        assert "HUMAN SUMMARY" in text, f"{name} 少了 HUMAN SUMMARY 規格"
        for line in HUMAN_SUMMARY_LINES:
            assert line in text, f"{name} 的 HUMAN SUMMARY 少了「{line}」"
        for segment in NEXT_STEP_SEGMENTS:
            assert segment in text, f"{name} 的「下一步」少了 {segment} 段"


def test_human_summary_never_replaces_the_eight_fields() -> None:
    """它是**另一個問題**的答案，不是八欄的摘要——兩份文件都要寫明這件事，
    否則下一個 agent 會把八欄壓縮一遍交差，而那等於什麼都沒加。"""
    runner = DEV_FLOW.read_text(encoding="utf-8")
    model = WORKFLOW.read_text(encoding="utf-8")
    assert "不是摘要與被摘要的關係" in runner
    assert "不是八欄的摘要" in model
    for text in (runner, model):
        assert "HUMAN SUMMARY 在前" in text or "在 `STEP_RESULT` 之前" in text, (
            "必須寫明輸出順序：人話在前、證據在後"
        )


def test_r2_has_exactly_six_auto_triggers() -> None:
    """R2 是唯一會花第二份 token 的路徑，trigger 清單必須維持六條且可數。

    ⚠ 這條刻意數數量：trigger 一旦悄悄長出第七條、第八條，R2 就會從「例外」變成「預設」，
    而 token 成本是這個 Phase 的一級設計約束。
    """
    model = WORKFLOW.read_text(encoding="utf-8")
    section = model.split("### R2 的自動 trigger", 1)[1].split("\n## ", 1)[0]
    numbered = re.findall(r"^\d+\.\s+\S", section, flags=re.MULTILINE)
    assert len(numbered) == 6, f"R2 的自動 trigger 應為 6 條，實際 {len(numbered)} 條"
    assert "自動 spawn" in model, (
        "必須寫明「自動 trigger ＝自動提出，不是自動 spawn」——"
        "否則它會與 AGENTS.md『subagent 委派預設關閉、每次明確 opt-in』直接衝突"
    )


def test_no_auto_repair_loop() -> None:
    """NO_GO 之後預設停下來給人看，不進入修復迴圈。"""
    model = WORKFLOW.read_text(encoding="utf-8")
    runner = DEV_FLOW.read_text(encoding="utf-8")
    assert "auto-repair" in model
    assert "AWAITING_HUMAN" in model and "AWAITING_HUMAN" in runner
    assert "不自動 repair loop" in runner or "不自動進入修復迴圈" in runner


def test_blind_spot_audit_is_research_only_and_carries_no_retired_framing() -> None:
    """blind-spot-audit 已收斂成 research profile，退役的字彙不得回來。

    `AGENTS.md`「技術訊號的地位」明訂這些字彙不得以任何名義回到文件或輸出；
    `supported_range`／`axis_ceiling` 這一組則隨 U7 移除。舊版 blind-spot-audit 的 B8／B9／
    C10 三個 lens 整段建立在它們之上——留著會讓 reviewer 對著已不存在的機制開火。

    空跑檢查：把 `supported_range` 寫回 blind-spot-audit → 這條會紅。
    """
    text = BLIND_SPOT.read_text(encoding="utf-8")
    for retired in (
        "supported_range",
        "axis_ceiling",
        "paper_target",
        "single_probe_nav_cap",
        "probe_book_nav_cap",
        "campaign_budget_fraction",
        "RSI",
        "MACD",
    ):
        assert retired not in text, (
            f"blind-spot-audit 出現已退役字彙 `{retired}`——"
            "它會讓 reviewer 對著不存在的機制開火"
        )

    assert "Convergence without differentiated evidence is healthy" in text, (
        "research reviewer 必須接受『與共識一致但沒有差異化證據是健康的』——"
        "否則它會逼內部預測人為偏離共識"
    )
    assert "development-flow" in text, "blind-spot-audit 應指出開發／維運 profile 在哪裡"


def test_review_profiles_have_exactly_one_home_each() -> None:
    """三個 profile 各只有一個 owner——development／operational 在執行檔，research 在 blind-spot。

    這是 L16 的直接應用：分類已經有 SSOT 時，不要在第二個地方重造一份。
    """
    runner = DEV_FLOW.read_text(encoding="utf-8")
    blind = BLIND_SPOT.read_text(encoding="utf-8")

    for item in ("dead mechanism", "fix efficacy", "fail closed", "Missing != Zero"):
        assert item in runner, f"development profile 缺少 `{item}`"
    for item in ("queue liveness", "unattended mutation", "silent degradation"):
        assert item in runner, f"operational profile 缺少 `{item}`"

    # research profile 的內容不得同時出現在執行檔裡（重造 = 立刻開始漂移）
    assert "Convergence without differentiated evidence is healthy" not in runner


def test_agent_skill_adapters_are_in_sync() -> None:
    """canonical skill 改了就必須重生轉接層，否則 Codex 與 Claude Code 兩端會開始漂移。

    ⚠ 轉接層不是 SSOT。這條測試存在的理由是：手改 `.claude/skills/` 不會有任何東西壞掉，
    它只會讓兩個 harness 讀到不同的 skill。
    """
    result = subprocess.run(
        [sys.executable, "scripts/sync_agent_skills.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"轉接層有漂移，請跑 `python scripts/sync_agent_skills.py`：\n"
        f"{result.stdout}\n{result.stderr}"
    )
