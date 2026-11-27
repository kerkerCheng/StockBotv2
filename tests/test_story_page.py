"""個股故事頁的純規則（Phase 8 plan 2026-11-26-001 Step 8.1；`alpha.narrative.story_page`）。

守四件事：
1. **研究 session 寫的 HTML 只有白名單內的東西才收**：行內程式、事件屬性、行內樣式、外部資源、javascript:／data:／http:// 網址
   各自被拒（注入）；而且**拿掉那一道檢查，同一筆注入就會被收**（變異）——證明測試真的靠那一道，不是碰巧紅。
2. 節序、頁首、`#system` 空位、私有字串、宣告形狀（E2–E6）。
3. W 類寫法檢查各自會亮、範例頁不亂亮。
4. 看得到的字：摺疊只算 summary、SVG 的 title 不算、`viewBox` 大小寫照收。
全部用合成的範例頁（`tests/fixtures/story_page/ZZZZ`，虛構公司）；不讀真實的帳。
"""
from __future__ import annotations

import copy
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from alpha.narrative import story_page as sp

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "story_page" / "ZZZZ"
HTML = (FIXTURE / "page.html").read_text(encoding="utf-8")
DECL = json.loads((FIXTURE / "page.json").read_text(encoding="utf-8"))
CORPUS = sp.normalize_for_match((FIXTURE / "source_excerpt.txt").read_text(encoding="utf-8"))
NAMES = {"co:zzzz_example": ["範例精密"], "co:pkg_a": ["封裝廠甲"], "co:pkg_b": ["封裝廠乙"]}


def _check(html: str = HTML, decl: dict | None = None, **kw) -> sp.PageCheck:
    return sp.check_page(html, DECL if decl is None else decl, company_names=kw.pop("names", NAMES),
                         quote_corpus=kw.pop("corpus", CORPUS), **kw)


def _codes(result: sp.PageCheck) -> list[str]:
    return [f.code for f in result.findings]


def _messages(result: sp.PageCheck, code: str) -> str:
    return "\n".join(f.message for f in result.findings if f.code == code)


def _inject(snippet: str, *, where: str = "<section id=\"q4\">\n<h2>先賺錢的是低階機台，長期要拼的是高階機台</h2>") -> str:
    assert where in HTML
    return HTML.replace(where, where + "\n" + snippet, 1)

# ---------------------------------------------------------------- 範例頁

def test_example_page_has_no_error_and_only_the_short_page_warning() -> None:
    result = _check()
    assert result.errors == [], [f.line() for f in result.errors]
    assert _codes(result) == ["W1"]                      # 範例頁本來就短；其餘寫法檢查都不該亮
    assert result.wait_keys == frozenset({"w1", "w2"})
    assert result.visible_chars == 1_259                  # 穩定（plan 8.1 驗收）：改了範例頁就照新數改這裡
    assert _check().text == result.text


def test_fragment_check_alone_passes_the_example_page() -> None:
    """物化時的第二道（E1–E4，不需要宣告）。"""
    assert sp.fragment_problems(HTML) == []


def test_visible_text_counts_summary_but_not_the_folded_sources_or_svg_title() -> None:
    html = HTML.replace("<title>誰賣給誰</title>", "<title>只給螢幕閱讀器的標題字</title>")
    root, _problems = sp.parse_fragment(html)
    text = sp.visible_text(root)
    assert "出處" in text                                # summary 看得到
    assert "範例精密年報（虛構）" not in text              # 摺疊裡的不算
    assert "範例精密年報（虛構）" in sp.all_text(root)      # 核引號用的全文要有
    assert "只給螢幕閱讀器的標題字" not in text
    assert "晶片設計公司（最終買家）" in text               # SVG 上的字看得到
    assert "（買方）" in text                              # 來源等級在文字版寫成括號


def test_cold_read_prompt_is_read_only_offline_and_asks_for_six_things() -> None:
    """冷讀的派工提示唯一一份在程式裡（plan §2.8）：讀者只拿到看得到的字；不對外、不寫任何檔、不給投資建議；回六樣。"""
    prompt = sp.cold_read_prompt("C:/x/coldread/PAGE.txt")
    assert prompt.splitlines()[0] == "對外請求不帶 email、不帶個人資訊；本任務不需要對外。"   # AGENTS 的派工第一行
    assert "C:/x/coldread/PAGE.txt" in prompt
    for rule in ("不對外", "不寫任何檔", "不給投資建議", "只讀這一個檔"):
        assert rule in prompt, rule
    headings = [line for line in prompt.splitlines() if line.startswith("### ")]
    assert headings == [f"### {i}. {title}" for i, title in enumerate(sp.COLD_READ_SECTIONS, 1)]
    assert len(sp.COLD_READ_SECTIONS) == 6 and "{" not in prompt          # 沒有沒填到的佔位字


def test_svg_attribute_case_is_accepted() -> None:
    root, _problems = sp.parse_fragment(HTML)
    svg = next(n for n in root.iter() if n.tag == "svg")
    assert svg.attr("viewbox") == "0 0 360 160"          # html.parser 轉小寫；白名單用小寫比對
    assert "viewbox" in sp.SVG_ATTRS
    assert "viewbox" in sp.whitelist_payload()["svg_attrs"]

# ---------------------------------------------------------------- E1：注入

INJECTIONS = {
    "script": "<script>alert(1)</script>",
    "event": "<p onclick=\"alert(1)\">點我</p>",
    "style": "<p style=\"color:red\">紅字</p>",
    "javascript_href": "<p><a href=\"javascript:alert(1)\">連結</a></p>",
    "tab_javascript_href": "<p><a href=\"java&#9;script:alert(1)\">連結</a></p>",
    "img": "<p><img src=\"https://example.com/x.png\"></p>",
    "svg_use_http": "<svg viewBox=\"0 0 10 10\"><use href=\"http://example.com/s.svg#a\"></use></svg>",
    "data_href": "<p><a href=\"data:text/html;base64,PHNjcmlwdD4=\">連結</a></p>",
    "svg_fill_remote_url": "<svg viewBox=\"0 0 10 10\"><rect fill=\"url(https://example.com/p.svg#g)\"></rect></svg>",
    "foreign_object": "<svg viewBox=\"0 0 10 10\"><foreignObject><p>字</p></foreignObject></svg>",
    "comment": "<!-- 註解 -->",
    "iframe": "<iframe src=\"https://example.com\"></iframe>",
    "svg_tag_outside_svg": "<path d=\"M0 0\"></path>",
    "unknown_source_level": "<p>一句<span class=\"src\" data-src=\"券商\">券商</span></p>",
    "data_slot_elsewhere": "<p data-slot=\"system\">字</p>",
    # svg 的 title／desc 是瀏覽器的 HTML 整合點（2026-11-26 R2：Python 3.14 把 title 當 RCDATA，前三筆兩道檢查都放行過）
    "svg_title_javascript_link": f"<svg xmlns=\"{sp.SVG_NAMESPACE}\" viewBox=\"0 0 10 10\"><title>"
                                 "<a href=\"javascript:alert(1)\">x</a></title></svg>",
    "svg_title_script": "<svg viewBox=\"0 0 10 10\"><title><script>alert(1)</script></title></svg>",
    "svg_title_nested_svg": "<svg viewBox=\"0 0 10 10\"><title><svg><rect x=\"1\"></rect></svg></title></svg>",
    "svg_desc_whitelisted_tag": "<svg viewBox=\"0 0 10 10\"><desc><g></g></desc></svg>",
    # CSS 跳脫拼出 url(…)（2026-11-27 結案 R2 C1：三道都放行過、只剩 CSP 擋；Edge 把三種寫法都解成 url(…) 並發出請求）
    "svg_fill_css_escaped_url": "<svg viewBox=\"0 0 10 10\"><rect fill=\"\\75 rl(https://example.com/p.svg#g)\"></rect></svg>",
    "svg_stroke_css_escaped_url": "<svg viewBox=\"0 0 10 10\"><line stroke=\"u\\72 l(/p.svg#g)\"></line></svg>",
    "svg_marker_css_escaped_url": "<svg viewBox=\"0 0 10 10\"><line marker-end=\"\\000075rl(/p.svg#m)\"></line></svg>",
    "svg_fill_src_function": "<svg viewBox=\"0 0 10 10\"><rect fill=\"src(https://example.com/p.svg#g)\"></rect></svg>",
}


@pytest.mark.parametrize("name", sorted(INJECTIONS))
def test_each_injection_is_rejected_by_the_whitelist(name: str) -> None:
    result = _check(_inject(INJECTIONS[name]))
    assert "E1" in _codes(result), (name, [f.line() for f in result.findings])
    assert sp.fragment_problems(_inject(INJECTIONS[name])), name      # 物化時的第二道同樣擋


def test_xmlns_is_only_the_svg_namespace() -> None:
    ok = _inject(f"<svg xmlns=\"{sp.SVG_NAMESPACE}\" viewBox=\"0 0 10 10\"><rect x=\"1\"></rect></svg>")
    assert "E1" not in _codes(_check(ok))
    bad = _inject("<svg xmlns=\"http://example.com/ns\" viewBox=\"0 0 10 10\"></svg>")
    assert "xmlns" in _messages(_check(bad), "E1")


def test_text_attributes_may_say_data_colon_without_being_treated_as_a_url() -> None:
    ok = _inject("<p title=\"data: 2026 年報\">字<span class=\"src\" data-src=\"自述\">自述</span></p>")
    assert "E1" not in _codes(_check(ok))

# ---------------------------------------------------------------- E1：變異（拿掉那一道，同一筆注入就被收）

def test_mutation_tag_whitelist_is_what_rejects_script(monkeypatch) -> None:
    monkeypatch.setattr(sp, "HTML_TAGS", sp.HTML_TAGS | {"script"})
    assert "E1" not in _codes(_check(_inject(INJECTIONS["script"])))


def test_mutation_tag_and_attribute_whitelists_are_what_reject_img(monkeypatch) -> None:
    monkeypatch.setattr(sp, "HTML_TAGS", sp.HTML_TAGS | {"img"})
    assert "E1" in _codes(_check(_inject(INJECTIONS["img"])))           # 標籤放行了，src 屬性還擋著
    monkeypatch.setattr(sp, "GLOBAL_ATTRS", sp.GLOBAL_ATTRS | {"src"})
    assert "E1" not in _codes(_check(_inject(INJECTIONS["img"])))


@pytest.mark.parametrize("name, attr", [("event", "onclick"), ("style", "style")])
def test_mutation_event_and_style_attributes_are_caught_by_two_layers(monkeypatch, name: str, attr: str) -> None:
    """事件屬性與行內樣式各有兩道：一律拒收的那一道、白名單沒有它。拿掉任一道都還擋，兩道都拿掉才收。"""
    whitelist_only = _check(_inject(INJECTIONS[name]))
    assert "E1" in _codes(whitelist_only)
    monkeypatch.setattr(sp, "_forbidden_attribute", lambda _name: None)
    assert "E1" in _codes(_check(_inject(INJECTIONS[name])))            # 白名單還擋著
    monkeypatch.setattr(sp, "GLOBAL_ATTRS", sp.GLOBAL_ATTRS | {attr})
    assert "E1" not in _codes(_check(_inject(INJECTIONS[name])))
    monkeypatch.undo()
    monkeypatch.setattr(sp, "GLOBAL_ATTRS", sp.GLOBAL_ATTRS | {attr})
    assert "E1" in _codes(_check(_inject(INJECTIONS[name])))            # 只放寬白名單：一律拒收那一道還擋著


def test_mutation_javascript_href_is_caught_by_two_layers(monkeypatch) -> None:
    monkeypatch.setattr(sp, "_BAD_SCHEME", re.compile(r"(?!x)x"))       # 永遠不中
    assert "E1" in _codes(_check(_inject(INJECTIONS["javascript_href"])))   # href 只准 https:// 或 # 還擋著
    monkeypatch.setattr(sp, "_SAFE_HREF", re.compile(r".*", re.S))
    assert "E1" not in _codes(_check(_inject(INJECTIONS["javascript_href"])))


def test_mutation_backslash_rule_is_what_rejects_css_escaped_urls(monkeypatch) -> None:
    """跳脫寫法躲得過「url(」的字面比對——擋它的是反斜線那一條；退回沒有反斜線的舊規則，三筆都被收（R2 C1 的原狀）。"""
    escaped = ("svg_fill_css_escaped_url", "svg_stroke_css_escaped_url", "svg_marker_css_escaped_url")
    for name in escaped:
        assert "E1" in _codes(_check(_inject(INJECTIONS[name]))), name
    monkeypatch.setattr(sp, "_BAD_SCHEME", re.compile(r"(?:javascript|vbscript|data|file|blob):|http://"))
    for name in escaped:
        assert "E1" not in _codes(_check(_inject(INJECTIONS[name]))), name
        assert not sp.fragment_problems(_inject(INJECTIONS[name])), name


def test_the_backslash_rule_reaches_the_front_end_unchanged() -> None:
    """前端照 `.meta.json` 的 patterns.bad_scheme 建規則（不另寫一份）；JavaScript 的 RegExp 讀同一段原文要同樣抓到反斜線。"""
    pattern = sp.whitelist_payload()["patterns"]["bad_scheme"]
    assert pattern == sp._BAD_SCHEME.pattern and pattern.endswith("|\\\\")


def test_mutation_url_reference_rule_is_what_rejects_remote_fill(monkeypatch) -> None:
    monkeypatch.setattr(sp, "_LOCAL_URL_REF", re.compile(r".*", re.S))
    monkeypatch.setattr(sp, "_BAD_SCHEME", re.compile(r"(?!x)x"))
    assert "E1" not in _codes(_check(_inject(INJECTIONS["svg_fill_remote_url"])))


def test_svg_title_content_is_parsed_the_way_the_browser_parses_it() -> None:
    """瀏覽器把 svg 的 title 當 HTML 整合點：裡面的 `<script>` 是元素。檢查器要看到同一棵樹。"""
    root, _problems = sp.parse_fragment(INJECTIONS["svg_title_script"])
    title = next(n for n in root.iter() if n.tag == "title")
    assert [e.tag for e in title.elements] == ["script"]


def test_svg_title_with_plain_words_and_an_escaped_less_than_sign_passes() -> None:
    ok = _inject("<svg viewBox=\"0 0 10 10\"><title>營收 &lt; 成本</title><rect x=\"1\"></rect></svg>")
    assert "E1" not in _codes(_check(ok))


def test_mutation_svg_title_markup_is_caught_by_two_layers(monkeypatch) -> None:
    """svg title 裡的標記有兩道：檢查器照瀏覽器讀（標記變成元素、白名單與只放字擋）、字裡像標記的也擋。
    拿掉任一道都還擋，兩道都拿掉才收——那就是 R2 找到時的樣子。"""
    if not hasattr(HTMLParser, "RCDATA_CONTENT_ELEMENTS"):
        pytest.skip("這一版 html.parser 不把 title 當 RCDATA：洞本來就不在")
    snippet = _inject(INJECTIONS["svg_title_script"])
    monkeypatch.setattr(sp._Builder, "RCDATA_CONTENT_ELEMENTS", ("textarea", "title"))   # 回到 3.14 的預設
    assert "E1" in _codes(_check(snippet))                               # 字裡像標記那一道還擋著
    monkeypatch.setattr(sp, "_MARKUP_IN_TEXT", re.compile(r"(?!x)x"))
    assert "E1" not in _codes(_check(snippet))                           # 兩道都拿掉：R2 找到的洞
    monkeypatch.undo()
    monkeypatch.setattr(sp, "_MARKUP_IN_TEXT", re.compile(r"(?!x)x"))
    assert "E1" in _codes(_check(snippet))                               # 只拿掉字那一道：照瀏覽器讀還擋著


def test_mutation_text_only_rule_is_what_rejects_whitelisted_tags_inside_desc(monkeypatch) -> None:
    monkeypatch.setattr(sp, "SVG_TEXT_ONLY", frozenset())
    assert "E1" not in _codes(_check(_inject(INJECTIONS["svg_desc_whitelisted_tag"])))
    assert "svg_text_only" in sp.whitelist_payload()                     # 前端照同一份


def test_every_source_level_has_a_plain_note_for_the_legend() -> None:
    """頁首圖例（app.js storyLegend）照 `source_levels` 的順序印 `source_level_notes`：少一個等級的白話，那個標記在 APP
    就沒有說明而且不報錯（Step 8.5 三份冷讀都抓到「標籤沒有說明」）。"""
    payload = sp.whitelist_payload()
    assert set(payload["source_level_notes"]) == set(payload["source_levels"]) == set(sp.SOURCE_LEVELS)
    assert all(note.strip() for note in payload["source_level_notes"].values())

# ---------------------------------------------------------------- E2：結構

def _swap(a: str, b: str) -> str:
    sections = re.findall(r"<section id=\"(q\d+)\">.*?</section>", HTML, flags=re.S)
    assert a in sections and b in sections
    blocks = {m.group(1): m.group(0) for m in re.finditer(r"<section id=\"(q\d+)\">.*?</section>", HTML, flags=re.S)}
    return HTML.replace(blocks[a], "\0A\0").replace(blocks[b], blocks[a]).replace("\0A\0", blocks[b])


def test_section_order_is_a_contract() -> None:
    assert "順序不對" in _messages(_check(_swap("q2", "q3")), "E2")
    q7 = re.search(r"<section id=\"q7\">.*?</section>\n", HTML, flags=re.S).group(0)
    assert "少了 q7" in _messages(_check(HTML.replace(q7, "")), "E2")
    extra = HTML.replace("<section id=\"bet-kind\">", "<section id=\"q13\"><h2>多的</h2></section>\n<section id=\"bet-kind\">")
    assert "多了 q13" in _messages(_check(extra), "E2")


def test_optional_system_gap_may_be_absent() -> None:
    gap = re.search(r"<section id=\"system-gap\">.*?</section>\n", HTML, flags=re.S).group(0)
    assert "E2" not in _codes(_check(HTML.replace(gap, "")))


def test_hero_is_one_h1_plus_three_or_four_paragraphs() -> None:
    hero_p = re.findall(r"<p>[^<]*</p>", HTML.split("</header>")[0])
    two = HTML.replace(hero_p[2], "").replace(hero_p[3], "")
    assert "頁首只放一個 <h1>" in _messages(_check(two), "E2")
    with_table = HTML.replace("</header>", "<table><tr><td>表</td></tr></table>\n</header>", 1)
    assert "頁首只放一個 <h1>" in _messages(_check(with_table), "E2")
    two_h1 = HTML.replace("<h2>這一層有兩種機台", "<h1>第二個標題</h1><h2>這一層有兩種機台")
    assert "剛好一個 <h1>" in _messages(_check(two_h1), "E2")


@pytest.mark.parametrize("html, needle", [
    (HTML.replace("<h2>缺不缺：", "<p>先寫一段</p><h2>缺不缺："), "#q7 的第一個元素要是 <h2>"),
    (HTML.replace("<h2>合作對象：兩家封裝廠，都不是獨家</h2>",
                  "<h2>合作對象：兩家封裝廠，都不是獨家</h2><p id=\"w1-note\"></p>"), None),   # 只要不撞 id 就沒事
    (HTML.replace("<p>樣板不畫股價圖", "<p id=\"q10\">樣板不畫股價圖"), "id 重複"),
    (_inject("<p/>"), "自閉合"),
    (_inject("<p><strong>沒閉合</p>"), "沒閉合"),
    (_inject("</div>"), "多出來的"),
    ("<div>" + HTML + "</div>", "根元素"),
    (HTML.replace("<article class=\"story-page\">", "<article class=\"other\">"), "根元素"),
])
def test_structure_problems(html: str, needle: str | None) -> None:
    messages = _messages(_check(html), "E2")
    if needle is None:
        assert messages == ""
    else:
        assert needle in messages, messages


def test_sources_must_start_with_summary() -> None:
    assert "#sources" in _messages(_check(HTML.replace("<summary>出處</summary>", "")), "E2")

# ---------------------------------------------------------------- E3、E4

def test_system_slot_must_stay_empty() -> None:
    filled = HTML.replace("<section id=\"system\" data-slot=\"system\"></section>",
                          "<section id=\"system\" data-slot=\"system\"><p>候選狀態：可開</p></section>")
    assert "E3" in _codes(_check(filled))
    unmarked = HTML.replace("<section id=\"system\" data-slot=\"system\">", "<section id=\"system\">")
    assert "data-slot" in _messages(_check(unmarked), "E3")


@pytest.mark.parametrize("snippet", [
    "<p>私有頁在 https://claude.ai/artifact/abc 這裡</p>",
    "<p title=\"library/private/story_pages/x\">字</p>",
    "<p>檔在 C:\\Users\\someone\\x.html</p>",
    "<p><a href=\"https://claude.ai/artifact/abc\">連結</a></p>",
])
def test_private_strings_never_reach_the_page(snippet: str) -> None:
    assert "E4" in _codes(_check(_inject(snippet)))


def test_https_urls_are_not_mistaken_for_drive_letters() -> None:
    assert "E4" not in _codes(_check(_inject("<p>出處 https://example.com/a/b 與 http 字樣<span class=\"src\" "
                                             "data-src=\"網路\">網路</span></p>")))

# ---------------------------------------------------------------- E5、E6：宣告

def _decl(**over) -> dict:
    decl = copy.deepcopy(DECL)
    for key, value in over.items():
        if value is ...:
            decl.pop(key, None)
        else:
            decl[key] = value
    return decl


@pytest.mark.parametrize("over, needle", [
    ({"self_eval": ...}, "宣告少了 self_eval"),
    ({"self_evals": {}}, "不認得的欄位 self_evals"),
    ({"brief_id": "bf_1"}, "brief_id 要是敘事 id"),
    ({"written_on": "2026/11/26"}, "written_on"),
    ({"self_eval": {"1": "full"}}, "self_eval 要有"),
    ({"key_question": 13}, "key_question"),
    ({"key_question": True}, "key_question"),
    ({"prices_seen": ["ZZZZ"], "price_as_of": None}, "price_as_of"),
    ({"quote_sources": ["../secret.txt"]}, "quote_sources"),
    ({"graph_gaps": [{"text": "缺一層", "lead_ids": ["L1"]}]}, "graph_gaps"),
    ({"waits": [{"key": "w1", "kind": "confirm", "watch_id": "ew_1"},
                {"key": "w1", "kind": "date", "watch_id": None}]}, "key 重複"),
    ({"waits": [{"key": "w1", "kind": "hope", "watch_id": None},
                {"key": "w2", "kind": "disproof", "watch_id": None}]}, "kind 要是"),
    ({"waits": [{"key": "w1", "kind": "confirm", "watch_id": "1452"},
                {"key": "w2", "kind": "disproof", "watch_id": None}]}, "ew_"),
    ({"waits": [{"key": "w1", "kind": "confirm", "watch_id": None}]}, "頁上有、宣告沒有：w2"),
    ({"waits": [*DECL["waits"], {"key": "w3", "kind": "date", "watch_id": None}]}, "宣告有、頁上沒有：w3"),
])
def test_declaration_shape(over: dict, needle: str) -> None:
    assert needle in _messages(_check(decl=_decl(**over)), "E5")


@pytest.mark.parametrize("cold, needle", [
    (..., "沒有 cold_read"),
    ({"skipped": "  "}, "理由不能空"),
    ({"skipped": "來不及", "asked": 1}, "只寫"),
    ({"report": "coldread/REPORT.md", "restated_ok": True, "asked": 1, "asked_outside": 2}, "asked_outside"),
    ({"report": "../REPORT.md", "restated_ok": True, "asked": 1, "asked_outside": 0}, "相對路徑"),
    ({"report": "coldread/REPORT.md", "restated_ok": "yes", "asked": 1, "asked_outside": 0}, "restated_ok"),
])
def test_cold_read_record(cold, needle: str) -> None:
    assert needle in _messages(_check(decl=_decl(cold_read=cold)), "E6")


def test_skipped_cold_read_with_a_reason_passes() -> None:
    assert "E6" not in _codes(_check(decl=_decl(cold_read={"skipped": "讀取私有頁面的工具關著"})))


def test_not_a_mapping_declaration() -> None:
    assert "JSON object" in _messages(_check(decl=[]), "E5")   # type: ignore[arg-type]

# ---------------------------------------------------------------- W 類

def test_w2_hero_must_not_point_forward() -> None:
    html = HTML.replace("什麼會讓夢醒：買方延後擴產，或改用另一種檢測方式。", "什麼會讓夢醒見第 12 題。")
    assert "W2" in _codes(_check(html))


def test_w3_the_same_number_four_times() -> None:
    line = "<p>營收 3,300 萬美元<span class=\"src\" data-src=\"自述\">自述</span></p>"
    html = _inject(line * 4)
    w3 = [f for f in _check(html).findings if f.code == "W3"]
    assert w3 and "3300萬美元 ×4" in w3[0].samples
    assert "W3" not in _codes(_check(_inject(line * 3)))
    years = _inject("<p>2026 年、2026 年、2026 年、2026 年<span class=\"src\" data-src=\"自述\">自述</span></p>")
    assert "W3" not in _codes(_check(years))                         # 年份重複是正常的


def test_w4_two_companies_and_it_in_one_sentence() -> None:
    html = _inject("<p>封裝廠甲向範例精密下單，它也向別家買<span class=\"src\" data-src=\"買方\">買方</span>。</p>")
    assert "W4" in _codes(_check(html))
    assert "W4" not in _codes(_check(html, names={}))


def test_w5_system_words_only_allowed_in_the_gap_section() -> None:
    assert "W5" not in _codes(_check())                               # 範例頁的 system-gap 用了「缺 X」「起始門」
    html = _inject("<p>這一檔還沒過起始門，敘事 ib_abcdef 寫它缺 X<span class=\"src\" data-src=\"推一步\">推一步</span></p>")
    samples = [s for f in _check(html).findings if f.code == "W5" for s in f.samples]
    assert any("起始門" in s for s in samples) and any("ib_abcdef" in s for s in samples)
    assert any("缺 X" in s for s in samples)


def test_w6_quotes_must_be_found_in_the_sources() -> None:
    assert "W6" not in _codes(_check())
    html = HTML.replace("「我們明年的封裝產能要比今年多一倍以上」", "「我們明年的封裝產能要比今年多三倍以上」")
    assert "W6" in _codes(_check(html))
    assert "沒核引號" in _messages(_check(corpus=None), "W6")
    english = _inject("<p>\"we will double our packaging capacity next year\"<span class=\"src\" data-src=\"買方\">買方</span></p>")
    assert "W6" in _codes(_check(english))


def test_w6_ellipsis_means_each_part_is_checked() -> None:
    html = HTML.replace("「我們明年的封裝產能要比今年多一倍以上」", "「我們明年的封裝產能…多一倍以上，設備的訂單已經陸續下出去」")
    assert "W6" not in _codes(_check(html))


def test_w7_w8_w9() -> None:
    bare = HTML.replace("<span class=\"src\" data-src=\"自述\">自述</span>。維修與耗材", "。維修與耗材")
    assert "q2" in _messages(_check(bare), "W7")
    assert "W8" in _codes(_check(decl=_decl(key_question=5)))       # 第 5 題自評是 half
    assert "W8" not in _codes(_check())
    assert "W9" in _codes(_check(_inject("<p>這一條已登記<span class=\"src\" data-src=\"推一步\">推一步</span></p>")))


def test_findings_line_for_the_ledger() -> None:
    finding = sp.Finding("W3", "同一個數字出現 4 次以上", ("3300萬美元 ×4",))
    assert finding.line() == "W3 同一個數字出現 4 次以上（1 處）"
    assert not finding.is_error and sp.Finding("E1", "x").is_error
