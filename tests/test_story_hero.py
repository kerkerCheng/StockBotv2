"""淺寫頁首（2026-11-27 使用者：沒做深的檔「我看不懂」、不知道要不要做深 → 「預設每一檔都寫一小部分的內容？再來做深？」→「走2」）。

- 住故事紀錄的選填鍵 `hero`（同賭注句：寫了才進紀錄、敘事換版就跟著故事過期）；標題一句＋三到四段，每句句尾帶來源標記；
- 只換頁首時故事其他格與賭注句一字不動（反過來也是）；改故事的字沒帶頁首＝悄悄拿掉，拒收；
- ⑤「頁首還沒寫」只數可開與已持有、有故事、沒有故事頁的列；讀不到是未讀到，不是 0；
- 個股頁：沒做深的檔最前面印頁首，句尾標記畫成標籤；逐句核對把頁首的句子也核。
全部用注入的輸入：tmp 目錄的 ledger、手做的敘事——不讀真實 ledger。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from alpha.errors import ContractViolation
from alpha.narrative.story import hero_plain, hero_problems
from alpha.providers.stories import (bet_only_spec, current_stories, hero_gaps, hero_only_spec, hero_state,
                                     write_story)
from tests.test_bet_line import BET, T, TODAY, _brief, _Registry, _spec

ROOT = Path(__file__).resolve().parents[1]

HERO = {
    "title": "替高階基板廠做含浸機的小廠，賭的是擴產的量",
    "paragraphs": [
        "它在台灣做電路板與載板用的含浸機，客戶是幾家高階基板廠〔自述〕。",
        "2026 年第三季營收年增一倍半，預收的設備款比一年前多〔自述〕。買方的申報裡寫著向它買機台〔買方〕。",
        "夢在高階基板一路擴產：預收貨款照排程交機、新單接得上，營收就能再翻一倍〔推一步〕。",
        "會讓夢醒的是買方停止擴產，或客戶的申報裡出現第二家供應商〔推一步〕。",
    ],
}


def _write(tmp_path, brief, spec):
    return write_story(brief.ticker, spec, path=tmp_path / "stories.jsonl", registry=_Registry(), today=TODAY,
                       brief_loader=lambda t: ([brief], []))


def _hero(**over) -> dict:
    return {**HERO, **over}


# ---------------------------------------------------------------------------
# 寫入規則
# ---------------------------------------------------------------------------

def test_a_plain_hero_with_a_source_on_every_sentence_passes() -> None:
    assert hero_problems(HERO) == []
    assert "〔" not in hero_plain(HERO["paragraphs"][1]) and "買方的申報" in hero_plain(HERO["paragraphs"][1])


@pytest.mark.parametrize("hero,needle", [
    (_hero(paragraphs=HERO["paragraphs"][:2]), "3 到 4 段"),
    (_hero(paragraphs=[*HERO["paragraphs"], "多一段〔自述〕。"]), "3 到 4 段"),
    (_hero(paragraphs=["它做含浸機。", *HERO["paragraphs"][1:]]), "句尾沒有來源標記"),
    (_hero(paragraphs=["它做含浸機〔自述〕。客戶是基板廠。", *HERO["paragraphs"][1:]]), "句尾沒有來源標記"),
    (_hero(paragraphs=["它做含浸機〔公司說〕。", *HERO["paragraphs"][1:]]), "不在字彙裡"),
    (_hero(title="賭擴產的量〔推一步〕"), "〕不帶來源標記"),
    (_hero(paragraphs=["它的市值 {market_cap}〔自述〕。", *HERO["paragraphs"][1:]]), "佔位字"),
    (_hero(paragraphs=["2026-11-27 公告擴產〔自述〕。", *HERO["paragraphs"][1:]]), "含日期"),
    (_hero(paragraphs=["今年營收翻倍〔自述〕。", *HERO["paragraphs"][1:]]), "相對年份"),
    (_hero(paragraphs=["它" + "很會做機台" * 40 + "〔自述〕。", *HERO["paragraphs"][1:]]), "上限"),
    ({**HERO, "extra": "x"}, "不認得的鍵"),
    ("一段話", "hero 必須是"),
])
def test_each_bad_hero_is_refused_with_a_reason(hero, needle) -> None:
    problems = hero_problems(hero)
    assert any(needle in p for p in problems), problems


def test_a_story_carries_the_hero_and_dropping_it_is_refused(tmp_path) -> None:
    brief = _brief()
    first = _write(tmp_path, brief, _spec(brief, hero=HERO))
    assert first["hero"] == HERO
    assert current_stories(path=tmp_path / "stories.jsonl")[0][brief.brief_id]["hero"]["title"] == HERO["title"]
    with pytest.raises(ContractViolation, match="一樣"):
        _write(tmp_path, brief, _spec(brief, hero=HERO))
    # 其他格一字不差、只少了頁首：不是「一樣」，是拿掉——要說清楚是哪一種
    with pytest.raises(ContractViolation, match="有淺寫頁首"):
        _write(tmp_path, brief, _spec(brief))
    changed = _spec(brief)
    changed["slots"]["events"] = "最近沒有新的事。"
    with pytest.raises(ContractViolation, match="有淺寫頁首"):
        _write(tmp_path, brief, changed)


def test_a_story_without_a_hero_keeps_its_old_id_rule() -> None:
    """沒寫頁首的故事 id 照舊算（選填鍵寫了才進 body）——舊紀錄不會因為多一個恆在的鍵而換 id。"""
    from alpha.providers.stories import story_id

    body = {"slots": {"a": "x"}, "evidence": {}, "candidate": {}}
    assert story_id("ib_a", "2026-11-27T00:00:00+00:00", body) == story_id("ib_a", "2026-11-27T00:00:00+00:00", dict(body))


def test_hero_only_and_bet_only_keep_each_other_word_for_word(tmp_path) -> None:
    brief = _brief()
    path = tmp_path / "stories.jsonl"
    load = {"path": path, "today": TODAY, "brief_loader": lambda t: ([brief], [])}
    with pytest.raises(ContractViolation, match="還沒有故事"):
        hero_only_spec(T, HERO, **load)
    first = _write(tmp_path, brief, _spec(brief, bet=BET))
    spec = hero_only_spec(T, HERO, **load)
    assert spec["slots"] == first["slots"] and spec["bet"] == BET and spec["hero"] == HERO
    second = _write(tmp_path, brief, spec)
    assert second["bet"] == BET and second["hero"] == HERO and second["supersedes_id"] == first["story_id"]
    # 換賭注句時頁首照帶（不帶就會被當成拿掉而拒收）
    new_bet = {**BET, "doubling": "單季營收到 15 億，最晚 2027 年第三季的季報看得到"}
    third = _write(tmp_path, brief, bet_only_spec(T, new_bet, **load))
    assert third["hero"] == HERO and third["bet"] == new_bet


# ---------------------------------------------------------------------------
# ⑤「頁首還沒寫」的判定
# ---------------------------------------------------------------------------

def _row(ticker, group, brief_id, company=None):
    return {"ticker": ticker, "group": group, "brief_id": brief_id, "company_id": company or f"co:{ticker.lower()}"}


def test_only_open_and_held_rows_with_a_story_and_no_page_are_owed() -> None:
    stories = {"ib_a": {"story_id": "st_a"}, "ib_b": {"story_id": "st_b", "hero": HERO},
               "ib_c": {"story_id": "st_c"}, "ib_e": {"story_id": "st_e"}}
    groups = {"open": [_row("AAA", "open", "ib_a"), _row("BBB", "open", "ib_b"), _row("CCC", "open", "ib_c", "co:paged"),
                       _row("DDD", "open", "ib_d")],
              "held": [_row("EEE", "held", "ib_e")],
              "missing": [_row("GGG", "missing", "ib_e")],
              "pass": [_row("FFF", "pass", "ib_a")]}
    pages = {"co:paged"}
    states = {r["ticker"]: hero_state(r, stories=stories, page_companies=pages) for g in groups.values() for r in g}
    assert states == {"AAA": "not_written", "BBB": "written", "CCC": "has_page", "DDD": "no_story",
                      "EEE": "not_written", "FFF": "not_written", "GGG": "not_written"}
    # 缺 X 與不要的檔也有故事、也沒寫頁首，但不欠（要不要做深只問可開與已持有）
    assert [g["ticker"] for g in hero_gaps(groups, stories=stories, page_companies=pages)] == ["AAA", "EEE"]


def test_the_todo_cell_counts_the_same_rows_and_says_when_it_could_not_read() -> None:
    from engine_b.todo_ledger import collect

    stories = {"ib_a": {"story_id": "st_a"}, "ib_b": {"story_id": "st_b", "hero": HERO}}
    board = {"holdings": {"status": "ok"},
             "groups": {"open": [_row("AAA", "open", "ib_a"), _row("BBB", "open", "ib_b")], "held": []}}
    loaders = {"current_stories": lambda: stories, "story_page_companies": lambda: set()}

    def cell(candidates):
        rows = collect(today=TODAY, leads_store={}, watches=[], todo_items=[], hypotheses=[], briefs=None,
                       reading_needs_reread=None, layer_note_reread=None, candidates=candidates,
                       thesis_due=None, loaders=loaders)
        return next(r for r in rows if r.key == "todo.hero")

    found = cell(board)
    assert found.count == 1 and found.work == "AAA"
    missing = cell(None)
    assert missing.count is None and "未讀到" in missing.reason
    old = cell({"holdings": {"status": "ok"}, "groups": {"open": [{"ticker": "AAA", "group": "open"}]}})
    assert old.count is None and "舊版" in old.reason


def test_the_coverage_map_knows_every_hero_state() -> None:
    from alpha.providers.stories import HERO_STATES
    from engine_b import todo_ledger

    mapping = next(v for k, v in vars(todo_ledger).items() if isinstance(v, dict) and "hero:not_written" in v)
    assert {f"hero:{s}" for s in HERO_STATES} <= set(mapping)
    assert mapping["hero:not_written"] == "todo.hero" and mapping["hero:no_story"] == "todo.story"


# ---------------------------------------------------------------------------
# 讀取端：read model、逐句核對、前端
# ---------------------------------------------------------------------------

def test_the_read_model_carries_the_hero_as_one_datum_not_a_slot() -> None:
    from briefing.alpha_view.builder import _story_slots

    brief = _brief()
    record = {"story_id": "st_" + "1" * 16, "brief_id": brief.brief_id, "created_at": "2026-11-27T08:00:00+00:00",
              "slots": _spec(brief)["slots"], "evidence": {"revenue": ["graph://x"], "events": ["graph://x"]},
              "hero": HERO}
    told = {d.key: d for d in _story_slots(record, brief, {}, today=TODAY)}
    assert told["story:hero"].value == {"title": HERO["title"], "paragraphs": HERO["paragraphs"]}
    assert not isinstance(told["story:hero"].value, str)       # 短故事那一段只收字串的格，不會印第二次
    assert "沒有對外蒐證" in told["story:hero"].reason
    no_hero = {k: v for k, v in record.items() if k != "hero"}
    assert "story:hero" not in {d.key for d in _story_slots(no_hero, brief, {}, today=TODAY)}


def test_the_fact_check_reads_the_hero_sentences_without_the_source_marks() -> None:
    from alpha.narrative.fact_check import brief_text_from_record, build_sentences, where_label

    brief = _brief()
    story = {"story_id": "st_x", "slots": {}, "evidence": {}, "candidate": {}, "hero": HERO}
    rows = [s for s in build_sentences(brief_text_from_record(brief), story=story) if s.where == "story:hero"]
    assert len(rows) >= 6 and not any("〔" in s.text for s in rows)
    assert where_label("story:hero") == "故事：淺寫頁首"


def test_the_stock_page_prints_the_hero_before_the_short_story_and_the_die_line_above_the_lamps() -> None:
    app = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    page = app[app.index("function stockPage("):app.index("function storyRules(")]
    assert page.index("heroBlock(view)") < page.index("shortStory(view)")
    hero = app[app.index("function heroBlock("):app.index("function storyRules(")]
    assert "story:hero" in hero and "storyLegend()" in hero and "淺寫" in hero
    system = app[app.index("function systemBlock("):app.index("function eventBlock(")]
    assert system.index("lampLine(view)") < system.index("lampsBlock(view, true)")
    css = (ROOT / "webapp" / "static" / "story.css").read_text(encoding="utf-8")
    assert ".story-hero span.src" in css


def test_a_story_page_gets_the_slim_system_section_and_a_page_without_one_keeps_the_full_block() -> None:
    """2026-11-28 使用者：「瘦身」「原本 old 還存在的那一段，就融合進去現在新的敘事頁面」。有故事頁的檔走
    `storySystemBlock`：故事講過或頁首已印的不再印（押什麼那一句、坐的層與路徑、這條鏈怎麼走、四盞燈逐盞、反證的展開與
    時間表、股價圖）；系統帳上會自己變的照程式填。沒有故事頁的檔照舊整塊——它沒有故事，這一塊就是主內容。"""
    app = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")

    def body(name: str) -> str:
        start = app.index(f"function {name}(")
        return app[start:app.index("\n}\n", start)]

    full, slim = body("systemBlock"), body("storySystemBlock")
    assert "if (sp) return storySystemBlock(payload, view, sp);" in full
    kept = ("candidateLine(view, true, true)", "sharedBetLines(row)", "rideReadingLine(payload, view)",
            "pageDiagrams(payload, view)", "lampLine(view)", "wordsBlock(view, ['priced_in', 'in_numbers'])",
            "systemNumbers(payload, view)", "disproofBrief(view)", "confirmBrief(row)", "eventBlock(payload)",
            "storyGapLines(sp)")
    for call in kept:
        assert call in slim, call
    dropped = ("betLines(", "seatsSentence(", "pathSentences(", "chainDetail(", "unitGlossary(", "seatsDetail(",
               "lampsBlock(", "downsideDetail(", "timelineDetail(", "priceFigure(")
    for call in dropped:
        assert call not in slim, call
        assert call in full, call            # 沒有故事頁的檔一樣都不少
    # 沒有故事頁：示意圖在 stockPage（短故事後面）、「這一頁和系統對不上的」只有故事頁有
    assert "pageDiagrams(" not in full and "storyGapLines(" not in full
    assert "candidateLine(view, true)" in full and "'和其他檔一起看（公司）→'" in body("candidateLine")
    css = (ROOT / "webapp" / "static" / "story.css").read_text(encoding="utf-8")
    assert ".story-page .system-in-story {" in css


def test_the_cli_hero_only_takes_ticker_and_hero_and_nothing_else(tmp_path, monkeypatch, capsys) -> None:
    import alpha.providers.stories as stories_mod
    from alpha.cli import build_parser

    seen: list[dict] = []
    monkeypatch.setattr(stories_mod, "hero_only_spec",
                        lambda ticker, hero, **_kw: {"ticker": ticker, "brief_id": "ib_a", "hero": hero})
    monkeypatch.setattr(stories_mod, "prepare_story", lambda ticker, spec, **_kw: (seen.append(spec) or {"ticker": ticker}, []))
    run = lambda *argv: (lambda a: a.func(a))(build_parser().parse_args(["stories", *argv]))   # noqa: E731
    good = tmp_path / "good.json"
    good.write_text(json.dumps([{"ticker": T, "hero": HERO}], ensure_ascii=False), encoding="utf-8")
    assert run("--check", str(good), "--hero-only") == 0 and seen[-1]["hero"] == HERO
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([{"ticker": T, "hero": HERO, "bet": BET}], ensure_ascii=False), encoding="utf-8")
    assert run("--check", str(bad), "--hero-only") == 2
    capsys.readouterr()
    # 兩個旗標一起給：要擋在「一次只用一個」，不是碰巧被賭注句那一關擋掉
    assert run("--check", str(good), "--hero-only", "--bet-only") == 2
    assert "一次只用一個" in capsys.readouterr().err
