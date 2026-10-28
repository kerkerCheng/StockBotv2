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


def test_the_prompt_is_built_from_the_page_and_fetches_nothing() -> None:
    prompt = _function("askClaudePrompt")
    for token in ("getJSON", "fetch(", "XMLHttpRequest", "${API}"):
        assert token not in prompt, token
    for field in ("payload.ticker", "payload.company_label", "what_it_does", "candidate:state", "row.reason", "row.watch"):
        assert field in prompt, field


def test_the_prompt_says_read_only() -> None:
    prompt = _function("askClaudePrompt")
    assert "只讀" in prompt and "不寫任何 authority" in prompt
    assert "缺 X" in prompt and "向你要文件" in prompt        # 讀到邊、向使用者要文件照 AGENTS 那兩條


def test_a_blocked_clipboard_shows_the_text_instead_of_pretending() -> None:
    button = _function("askClaudeButton")
    assert "navigator.clipboard.writeText" in button
    assert "catch" in button and "textarea" in button and "剪貼簿不給用" in button
    assert "ask-preview" in button                              # ?ask=1 讓 headless 驗得到提示本身
