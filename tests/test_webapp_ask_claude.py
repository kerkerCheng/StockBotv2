"""個股頁「問 Claude」（2026-10-28 使用者照推薦；brainstorm 2026-10-28 定案 8）。

守三件事：
1. **APP 不跑 LLM、不連外**：提示只用這一頁已經讀到的 payload 組，不另抓任何東西（request path 規則不動）。
2. **提示只讀**：貼進對話的那一段明講「只讀、不寫任何 authority」——按鈕不得變成繞過四個人工 gate 的捷徑。
3. **複製不了就說**：剪貼簿不給用時攤開那一段讓人自己複製，不假裝成功（L13：產出要到消費者手上）。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")


def _function(name: str) -> str:
    block = SOURCE.split(f"function {name}(", 1)[1]
    return block.split("\nfunction ", 1)[0].split("\r\nfunction ", 1)[0]


def test_the_stock_page_head_carries_the_button() -> None:
    detail = _function("renderDetail")
    assert "askClaudeButton(payload, view)" in detail
    assert "deepDiveButton(payload, view)" in detail              # 2026-11-26 Phase 8 Step 8.4a：兩顆都在頁首


#: 組提示的函式（兩段提示＋共用的現況）——每一個都只能用 payload 組（2026-11-26 起現況住 pageStatusLines，改主詞不刪判準）
PROMPT_PARTS = ("askClaudePrompt", "deepDivePrompt", "pageStatusLines", "storyPageStatus", "pageName", "storyStaleText")


def test_the_prompt_is_built_from_the_page_and_fetches_nothing() -> None:
    for name in PROMPT_PARTS:
        body = _function(name)
        for token in ("getJSON", "fetch(", "XMLHttpRequest", "${API}"):
            assert token not in body, (name, token)
    status = _function("pageStatusLines") + _function("pageName")
    for field in ("payload.company_label", "what_it_does", "candidate:state", "row.reason", "row.watch", "payload.story_page"):
        assert field in status, field
    for name in ("askClaudePrompt", "deepDivePrompt"):
        assert "pageStatusLines(payload, view)" in _function(name), name   # 兩段的現況是同一份字（L16）
        assert "payload.ticker" in _function(name), name


def test_the_prompt_says_read_only() -> None:
    prompt = _function("askClaudePrompt")
    assert "只讀" in prompt and "不寫任何 authority" in prompt
    assert "缺 X" in prompt and "向你要文件" in prompt        # 讀到邊、向使用者要文件照 AGENTS 那兩條


def test_the_prompt_points_at_a_checklist_that_exists() -> None:
    # 2026-11-09：提示點名研究 skill 的「完整重讀」五項；那一段被改名或刪掉，提示就指向空處（L13）
    prompt = _function("askClaudePrompt")
    assert "skills/research-drain/SKILL.md" in prompt and "「完整重讀」" in prompt
    skill = (ROOT / "skills" / "research-drain" / "SKILL.md").read_text(encoding="utf-8")
    assert "**完整重讀＝清單之外的五項回掃**" in skill


def test_the_prompt_offers_the_detective_as_the_deeper_entry() -> None:
    # 2026-11-19 使用者：按鈕是第一層、偵探是第二層的固定入口；提示點名的 skill 與觸發詞不存在，那一行就指向空處（L13）
    prompt = _function("askClaudePrompt")
    assert "偵探 ${payload.ticker}" in prompt and "skills/detective/SKILL.md" in prompt
    skill = (ROOT / "skills" / "detective" / "SKILL.md").read_text(encoding="utf-8")
    assert "觸發詞：偵探" in skill
    assert "不改候選狀態" in skill                               # 提示說「不改候選狀態」，skill 得真的這樣寫


def test_a_blocked_clipboard_shows_the_text_instead_of_pretending() -> None:
    # 2026-11-26 起複製與攤開住兩顆按鈕共用的 copyPromptButton（plan 8.4a：不抄兩份）
    button = _function("copyPromptButton")
    assert "navigator.clipboard.writeText" in button
    assert "catch" in button and "textarea" in button and "剪貼簿不給用" in button
    assert "preview.id = previewId" in button and "ask=1" in button     # ?ask=1 讓 headless 驗得到提示本身
    assert "copyPromptButton(" in _function("askClaudeButton") and "'ask-preview'" in _function("askClaudeButton")
    assert "copyPromptButton(" in _function("deepDiveButton") and "'deep-preview'" in _function("deepDiveButton")
    assert SOURCE.count("navigator.clipboard.writeText") == 1             # 只有一份


def test_the_deep_dive_prompt_names_both_skills_and_the_boundary() -> None:
    """「做深這一檔」（plan Step 8.4a）：第一行是 skill 認得的那一句；蒐證在偵探、寫故事頁在 stock-story；最後一行是邊界——
    按鈕不得變成繞過四個人工 gate 的捷徑。提示點名的 skill 段落不存在，那一行就指向空處（L13）。"""
    prompt = _function("deepDivePrompt")
    assert "`做深 ${payload.ticker}${name}`" in prompt
    assert "skills/detective/SKILL.md" in prompt and "「做深」" in prompt and "不看股價" in prompt
    assert "skills/stock-story/SKILL.md" in prompt and "冷讀" in prompt
    for rule in ("入圖等我 go", "不改候選狀態", "不給目標價與排序", "付費來源先問我金額"):
        assert rule in prompt, rule
    detective = (ROOT / "skills" / "detective" / "SKILL.md").read_text(encoding="utf-8")
    assert "「做深 <代號>」（個股頁上的按鈕複製的就是這一句）" in detective
    story = (ROOT / "skills" / "stock-story" / "SKILL.md").read_text(encoding="utf-8")
    assert "## 冷讀" in story and "「做深 <代號>」先走 skills/detective" in story
