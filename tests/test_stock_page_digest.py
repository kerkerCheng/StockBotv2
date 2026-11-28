"""個股頁消化成句（2026-10-29 使用者三輪手機截圖回饋；ROADMAP 旁支「個股頁：故事層與依據層」A 段）。

前端沒有 JS 測試環境（本機無 node）；JS 這半邊鎖住「哪一塊印什麼、字從哪裡來」不該悄悄變的事，畫得對不對由 headless Edge 驗。
「APP 是給人看的」：給查核的出處（可知日、watch 編號、代表公司宣告理由）不上首屏，照舊在 artifact 與 API。
"""
from __future__ import annotations

import re
from pathlib import Path

from engine_b.disproof import confirm_summary

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")


def _body(name: str) -> str:
    start = SOURCE.index(f"function {name}(")
    nxt = re.search(r"\n(?:async )?function |\nconst [A-Z_]+ =", SOURCE[start + 10:])
    return SOURCE[start: start + 10 + (nxt.start() if nxt else len(SOURCE))]


def test_will_it_die_is_one_line_that_copies_the_lamps_and_never_judges_a_colour() -> None:
    """「會不會死我不知道灰字這麼多要幹嘛 燈號跟訊息也不直覺」：一行＝最差那盞的詞＋不是綠的那幾盞的短句（`alpha.wipeout`
    給的 `short`）；沒量到的寫名字（灰不是綠）。前端不從輸入重判顏色。2026-11-28 舊版個股頁刪除：一行在兩版「系統裡的它」
    都印；四盞的全句只在沒做深的檔那一版（做過故事頁的，不是綠的燈寫進故事——stock-story skill）。"""
    assert "lampLine(view)" in _body("systemBlock") and "lampLine(view)" in _body("storySystemBlock")
    line = _body("lampLine")
    for copied in ("value.colour", "value.short", "沒查到", "jumpToNumbers('will_it_die')", "LAMP_WORDS[worst]"):
        assert copied in line, f"會不會死那一行少了 {copied}"
    for judged in ("inputs", "runway", "free_cash_flow", "months"):
        assert judged not in line, f"前端不得自己判燈：{judged}"
    assert "lampsBlock(view, true)" in _body("systemBlock") and "lampsBlock(" not in _body("storySystemBlock")


def test_disproof_and_confirm_print_only_what_needs_you_and_count_the_rest() -> None:
    """「1815.TWO 真的太長了」：反證與加碼條件在首屏只逐條印要你看的（觸及／醒來／到期／未盯），在盯的只數；
    每一條的全文在「錯了怎麼知道」的展開裡（`downsideDetail`）。加碼條件的字只住 `engine_b/disproof.py`（app.js 禁字）。"""
    disproof = _body("disproofBrief")
    assert "r.state !== 'active'" in disproof and "都在盯" in disproof
    brief = _body("confirmBrief")
    assert "row.confirm_summary" in brief and "confirmLines(" in brief
    assert "加碼" not in SOURCE
    assert confirm_summary([]) is None
    rows = [{"state": "active"}, {"state": "active"}]
    assert confirm_summary(rows) == "加碼條件 2 條在等，還沒有一條觸及"
    assert confirm_summary(rows + [{"state": "touched"}]) == "其餘加碼條件 2 條在等"
    assert confirm_summary([{"state": "touched"}]) is None


def test_rewrite_reasons_are_words_on_the_card_and_the_page_with_the_sentence_in_the_title() -> None:
    """「該重寫為啥沒寫…可以五字一目瞭然嗎」：卡片的 chip 與個股頁那一行印 `rewrite_words`；原句放 title、不丟。"""
    card = _body("cardStateLine")
    assert "c.rewrite_words" in card and "該重寫：" in card
    line = _body("candidateLine")
    assert "row.rewrite_words" in line and "why.title = (row.rewrite || []).join" in line


def test_absence_sentences_stay_off_the_first_screen() -> None:
    """「營收哪裡來 事件與影響多大…只看到一堆斜體字」：缺席句（`ss-pending`）不上首屏。2026-11-28 舊版個股頁（十三塊）刪除後：
    事件那一塊只有缺席句時整塊不印（`eventBlock`）；需求錨與「吃到多少」的缺席句只在「數字與出處」那個展開裡（`systemNumbers`）。"""
    events = _body("eventBlock")
    assert "ss-pending" in events and "return null" in events
    numbers = _body("systemNumbers")
    assert "anchorFigures(payload)" in numbers and "captureFigure(payload)" in numbers and "drill('數字與出處'" in numbers
    for name in ("systemBlock", "storySystemBlock", "stockPage"):
        assert "anchorFigures(" not in _body(name) and "captureFigure(" not in _body(name), name


def test_a_not_edge_page_says_no_narrative_is_by_rule_and_names_its_seats() -> None:
    """非邊緣＝規定不寫敘事（2026-10-28），不是還沒寫：短故事那一格印首頁分組字彙那一句；它坐在哪幾層照印（層名中文、可點）。
    2026-11-28 舊版個股頁（`briefCard` 的非邊緣分支）刪除——這兩件改由新版個股頁的短故事與「系統裡的它」負責。"""
    story = _body("shortStory")
    assert "edge_state === 'not_edge'" in story and "listGroupLabel('not_edge_no_narrative')" in story
    assert "seatsSentence(payload, view)" in _body("systemBlock")
    seats = _body("seatsSentence")
    assert "nodeLabel(node, names[node])" in seats and "'#/graph/'" in seats and "split('｜')[0]" in seats


def test_node_names_have_one_reading_point() -> None:
    """層中文名的讀取點只有 `alpha.node_labels`：候選列（是不是新賭注）與 materialize 都從那裡拿（L16）；前端從 `.meta.json`。"""
    from alpha.node_labels import node_labels_zh
    import webapp.materialize as mat

    assert mat.node_labels_zh is node_labels_zh
    assert "VOCAB.node_labels_zh" in _body("nodeLabel")
    provider = (ROOT / "alpha" / "providers" / "candidates.py").read_text(encoding="utf-8")
    assert "from alpha.node_labels import node_labels_zh" in provider and "結構表逐列錨）" not in provider
