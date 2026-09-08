"""前端沒有建置步驟，所以這裡就是它唯一的編譯器。

`webapp/static/app.js` 是手寫、直接被瀏覽器載入的——**沒有 bundler、沒有 linter、
沒有型別檢查**。少一個括號的後果不是某一格顯示錯誤，是整頁空白；而 pytest 全綠、
`webapp status` 全綠、API 也全綠，因為壞掉的東西在瀏覽器裡。這正是 L13 講的
「成功與失敗在同一個訊號上同形」——所以要驗的是那個**會因為真的壞掉而改變**的東西。

本機沒有 node（`validate_palette.js` 也因此跑不了），所以這裡自己做兩件機械檢查：

1. **括號平衡**——把字串／樣板字串／正則／註解都吃掉之後，`(){}[]` 必須收乾淨。
2. **死函式**——定義了但沒有任何地方呼叫的頂層函式。2026-09-08 就踩過：單檔頁改版後
   `renderHeadline` 與 `renderReadiness` 沒人叫了，內容（算術 vs 判斷的分解、readiness
   判準原文）等於安靜消失，而沒有任何東西會紅。

⚠ 這**不是** JS parser，別把它當成型別檢查。它只擋這兩類「不會有東西報錯」的失敗。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "webapp" / "static" / "app.js"

#: 一個 `/` 若前一個有意義字元是這些，就是正則的開頭而不是除號（標準啟發式）。
_REGEX_PRECEDERS = set("(,=:[!&|?{};+-*%~^<>")


def _strip_literals(source: str) -> str:
    """把註解／字串／樣板字串／正則替換成等長空白，只留結構符號。

    樣板字串裡的 `${...}` 是**真的程式碼**，必須留著——否則 `` `${a(} ` `` 這種錯誤會被吃掉。
    """
    out: list[str] = []
    i, n = 0, len(source)
    template_depth: list[int] = []          # 每一層樣板字串在 `${` 裡的大括號深度（-1 = 字面文字）
    last_significant = ""
    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        # ⚠ 樣板字串的字面文字必須**最先**判斷：裡面的 `//`、引號、斜線都只是字，
        #   先問「這是不是註解」會把 `` `${a}` `` 的收尾反引號讀成下一個樣板字串的開頭。
        if template_depth and template_depth[-1] == -1:
            if ch == "\\":
                out.append("  ")
                i += 2
                continue
            if ch == "`":
                template_depth.pop()
                out.append(" ")
                i += 1
                continue
            if ch == "$" and nxt == "{":
                template_depth[-1] = 0
                out.append(" {")            # `${` 之後是真的程式碼，大括號要算
                i += 2
                continue
            out.append(ch if ch == "\n" else " ")
            i += 1
            continue
        if ch == "/" and nxt == "/":
            j = source.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
            continue
        if ch == "/" and nxt == "*":
            j = source.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join(c if c == "\n" else " " for c in source[i:j]))
            i = j
            continue
        if ch in "'\"":
            j = i + 1
            while j < n and source[j] != ch:
                j += 2 if source[j] == "\\" else 1
            j = min(j + 1, n)
            out.append("".join(c if c == "\n" else " " for c in source[i:j]))
            last_significant = "'"
            i = j
            continue
        if ch == "`":
            template_depth.append(-1)
            out.append(" ")
            i += 1
            continue
        if template_depth:                  # 在 `${...}` 內：大括號要自己數，數到 0 就回字面文字
            if ch == "{":
                template_depth[-1] += 1
            elif ch == "}":
                if template_depth[-1] == 0:
                    template_depth[-1] = -1
                    out.append("}")
                    i += 1
                    continue
                template_depth[-1] -= 1
        if ch == "/" and last_significant in _REGEX_PRECEDERS:
            j = i + 1
            while j < n and source[j] != "/":
                j += 2 if source[j] == "\\" else 1
            j = min(j + 1, n)
            while j < n and source[j].isalpha():
                j += 1
            out.append(" " * (j - i))
            i = j
            continue
        out.append(ch)
        if not ch.isspace():
            last_significant = ch
        i += 1
    return "".join(out)


def test_app_js_brackets_are_balanced() -> None:
    """少一個括號 → 整頁空白，而後端每一項檢查都是綠的。這裡是唯一會紅的地方。

    空跑檢查：在 app.js 尾端加一個 `}` → 這條會紅。
    """
    stripped = _strip_literals(APP_JS.read_text(encoding="utf-8"))
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: list[tuple[str, int]] = []
    line = 1
    for ch in stripped:
        if ch == "\n":
            line += 1
        elif ch in "([{":
            stack.append((ch, line))
        elif ch in ")]}":
            assert stack, f"第 {line} 行多出一個 `{ch}`"
            opener, opened_at = stack.pop()
            assert opener == pairs[ch], (
                f"第 {line} 行的 `{ch}` 對不上第 {opened_at} 行的 `{opener}`"
            )
    assert not stack, f"沒有關閉的括號：{[(c, ln) for c, ln in stack]}"


def test_app_js_has_no_dead_function() -> None:
    """定義了卻沒人呼叫的函式＝內容安靜消失，而沒有任何東西會紅。

    事發 2026-09-08：單檔頁改版後 `renderHeadline`／`renderReadiness` 成了孤兒，
    「算術 vs 判斷的分解」與「readiness 判準原文」整段從畫面上不見了。
    """
    source = APP_JS.read_text(encoding="utf-8")
    defined = set(re.findall(r"^(?:async )?function (\w+)\(", source, flags=re.M))
    assert len(defined) > 40, "抓不到函式定義，這條守衛等於沒作用"
    entrypoints = {"boot", "route"}          # 由 index.html／hashchange 呼叫
    orphans = sorted(
        name for name in defined - entrypoints
        if len(re.findall(rf"\b{re.escape(name)}\b", source)) < 2
    )
    assert not orphans, (
        f"這些函式定義了但沒人呼叫：{orphans}——若是刻意保留，請改成有人消費它"
    )


@pytest.mark.parametrize("broken", ["function f() { return 1;", "const a = [1, 2;"])
def test_the_bracket_checker_actually_catches_things(broken: str) -> None:
    """守衛自己也要被驗（INV-5：未量測的機制不得享有默認信任）。"""
    stripped = _strip_literals(broken)
    assert stripped.count("{") + stripped.count("[") > stripped.count("}") + stripped.count("]")


def test_the_checker_does_not_trip_on_templates_or_regex() -> None:
    """樣板字串與正則裡的括號不算數——會誤報的守衛比沒有守衛更糟（L16 第 4 點）。"""
    sample = "const x = `a${fn({k: 1})}b`; const re = /^#\\/?[(]/; const s = '((';"
    stripped = _strip_literals(sample)
    assert stripped.count("(") == stripped.count(")")
    assert stripped.count("{") == stripped.count("}")
