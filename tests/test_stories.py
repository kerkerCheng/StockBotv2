"""個股頁的故事層（2026-10-29；ROADMAP 旁支「個股頁：故事層與依據層」B 段驗收②：舊寫法寫入被拒）。

規則在 `alpha.narrative.story`（純規則），ledger 在 `alpha.providers.stories`。COHR 的原文（依據）整格拿來當故事要被拒收、
照寫法守則改寫的版本要收——這是「寫法不會慢慢爛回去」的機械保證（使用者：「這個會記在哪裡？之後才不會又慢慢爛掉？」）。
全部用注入的輸入：tmp 目錄的 ledger、手做的敘事、測試用名冊——不讀真實 ledger。
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from alpha.errors import ContractViolation
from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record
from alpha.narrative.story import (CANDIDATE_STORY_MAX, STORY_MAX, missing_label_problems, story_length,
                                   story_problems)
from alpha.providers.stories import current_stories, story_gaps, write_story

TODAY = date(2026, 10, 29)

#: COHR 現行敘事 bottleneck 那一格的原文（依據；2026-10-29 讀，節錄開頭兩句）——日期、英文原文、系統用語都在
COHR_BOTTLENECK_BASIS = (
    "我們騎的讀圖判這一層是量的賭注，窗口在關（2026-10-27 版）：供給側圖上 11 家——穩懋（仍在合格）、Ligent（自製兼外售）、"
    "光環（自述已在做）是 2025–2026 年才開始補的產能；NVIDIA 自己的技術部落格把 Lumentum、住友電工和它並列為外部光源的"
    "組裝、對位與測試廠商（「Lumentum, Sumitomo, and Coherent: These vendors provide ELS assembly, optical alignment, "
    "and test with the silicon photonics engine.」）")
#: 照寫法守則改寫的故事（同一件事：卡的是層的量、不是它；它和別家不同在哪；什麼會讓它被換掉）
COHR_BOTTLENECK_STORY = (
    "卡的是這一層的量，不是它：做這種雷射的有十來家，補產能的速度量不到；NVIDIA 把它和 Lumentum、住友並列，協議也是非獨家。"
    "它和別家不同在六吋磷化銦產線；會讓它被換掉的是買家自己做。")


class _Registry:
    def company_id_for_ticker(self, ticker: str) -> str | None:
        return {"COHR": "co:coherent", "AXTI": "co:axt"}.get(ticker)


def _slots() -> dict:
    """敘事那一格的依據（形狀照 `tests/test_candidates.py::_slots`：v2 寫入規則要的 placeholder 都在）。"""
    ev = ["graph://x"]
    return {"demand": {"text": "客戶預付產能。", "evidence_refs": ev},
            "position": {"text": "坐在雷射層，年增 {in_numbers_latest}（{in_numbers_as_of}）。", "evidence_refs": ev},
            "bottleneck": {"text": COHR_BOTTLENECK_BASIS, "evidence_refs": ev},
            "priced_in": {"text": "自家三年 {own_history_basis} 第 {own_history_pctile} 百分位。", "evidence_refs": ev},
            "our_bet": {"text": "不賭它。", "evidence_refs": ev},
            "what_must_be_true": {"text": "它不是邊緣公司。", "evidence_refs": ev},
            "when": {"text": "{next_checkpoint_date} 檢核點。", "evidence_refs": ev}}


def _brief(*, state="pass", ticker="COHR", company="co:coherent", created=datetime(2026, 10, 27, tzinfo=timezone.utc)):
    rec = brief_record(company_id=company, ticker=ticker, slots=_slots(), record_version=RECORD_VERSION_V2,
                       rides=[{"node": "tech:cw", "unit": "layer", "reading_id": "sr_" + "a" * 16}],
                       answers={"priced_in": "yes", "in_numbers": "yes"},
                       candidate_state={"state": state, "watch_id": "ew_1" if state in ("missing", "priced_wait") else None,
                                        "reason": "理由的依據"},
                       created_at=created)
    return parse_brief_record(rec)


def _spec(brief, **over) -> dict:
    slots = {"demand": "NVIDIA 用 20 億美元入股、承諾數十億美元採購，鎖住它的產能。",
             "position": "它做 CPO 外部光源用的連續波雷射；資料中心與通訊約占營收四分之三，最新一季營收年增 {in_numbers_latest}。",
             "bottleneck": COHR_BOTTLENECK_STORY,
             "priced_in": "已定價：自家三年 {own_history_basis} 第 {own_history_pctile} 百分位；{analyst_count} 位分析師在追。",
             "our_bet": "不賭它：這一層賭的是量，量分給多家；它是大廠，倍率不會出在它身上。",
             "what_must_be_true": "不要的理由只有一條：它不是邊緣公司。錯的訊號是雷射降價、訂單遞延。",
             "when": "下一個檢核點是 12 月初的六吋磷化銦產能倍增。",
             "revenue": "資料中心與通訊約占營收四分之三，雷射那一塊沒有單獨揭露。",
             "events": "最近沒有會改變判斷的事。"}
    spec = {"brief_id": brief.brief_id, "slots": slots,
            "evidence": {"revenue": ["graph://x"], "events": ["graph://x"]},
            "candidate": {"story": "非邊緣：市值和分析師人數都超過門檻，倍率不會出在它身上。"}}
    spec.update(over)
    return spec


def _write(tmp_path, brief, spec, **kw):
    return write_story(brief.ticker, spec, path=tmp_path / "stories.jsonl", registry=_Registry(), today=TODAY,
                       brief_loader=lambda t: ([brief], []), **kw)


def test_the_cohr_basis_is_rejected_as_a_story_and_the_rewrite_is_accepted() -> None:
    """驗收②：舊寫法（依據原文）寫成故事會被擋——日期、整段英文、長引文、系統用語、字數；改寫的版本收。"""
    problems = story_problems("bottleneck", COHR_BOTTLENECK_BASIS)
    joined = "\n".join(problems)
    for kind in ("含日期", "整段英文", "長引文", "系統用語「讀圖」", "上限"):
        assert kind in joined, (kind, problems)
    assert story_problems("bottleneck", COHR_BOTTLENECK_STORY) == []


@pytest.mark.parametrize("text, kind", [
    ("10 月 28 日法說會說要擴產。", "含日期"),
    ("今年營收會翻倍。", "相對年份"),
    ("寫這句的當天股價在高檔。", "系統用語「寫這句」"),
    ("等 ew_1452 叫醒再看。", "內部編號"),
    ("券商報告 [806] 沒有寫到它。", "內部編號"),
    ("營收年增 {in_numbers_latest}（{in_numbers_as_of}）。", "會填出日期"),
    ("下一次是 {next_checkpoint_date} 的財報。", "會填出日期"),
    ("坐在 tech:cw_dfb_laser 這一層。", "首屏禁字"),
    ("差異看法來自 {bet_assumption:margin[x]}。", "帶參數"),
])
def test_each_basis_habit_is_caught(text, kind) -> None:
    problems = story_problems("demand", text)
    assert any(kind in p for p in problems), problems


def test_what_a_story_may_keep() -> None:
    """不擋的：年份與季度的粒度、型號縮寫、短的引號、「什麼時候知道」那一格的月份字、反證這個詞。"""
    assert story_problems("demand", "2027 年第一季開始出貨 HBM4 用的 CW DFB 雷射；客戶說「產能不夠」。") == []
    assert story_problems("when", "下一次知道是 11 月中的第三季財報。") == []
    assert story_problems("what_must_be_true", "錯的訊號（反證）是降價。") == []


def test_the_checkpoint_placeholder_is_refused_even_in_the_when_slot() -> None:
    """`{next_checkpoint_date}` 填的是名冊上最近的未來催化劑日，日子一過就換人或變「（尚無）」——2026-10-29 寫完
    85 份當天，用了它的 5 份裡 2 份頁上已印「最近的觀測點是（尚無）的第三季報」（brainstorm F17）。「什麼時候知道」
    那一格也一樣擋，錯誤訊息要講得出為什麼、該怎麼寫。"""
    problems = story_problems("when", "最近的觀測點是 {next_checkpoint_date} 的第三季報。")
    assert any("會填出日期" in p and "最近的未來催化劑日" in p and "月份字" in p for p in problems), problems


def test_length_counts_placeholders_as_their_filled_width() -> None:
    assert story_length("年增 {in_numbers_latest}") == len("年增") + 8
    assert story_problems("demand", "字" * STORY_MAX) == []
    assert any("上限" in p for p in story_problems("demand", "字" * (STORY_MAX + 1)))
    assert any("上限" in p for p in story_problems("candidate", "字" * (CANDIDATE_STORY_MAX + 1),
                                                    limit=CANDIDATE_STORY_MAX))


def test_missing_label_is_a_short_noun_phrase() -> None:
    assert missing_label_problems("二代占比") == []
    assert any("上限" in p for p in missing_label_problems("第二代低介電布的營收占比"))
    assert any("標點" in p for p in missing_label_problems("占比、客戶"))
    assert any("不必再寫" in p for p in missing_label_problems("缺占比"))


def test_a_story_is_written_for_the_current_brief_only_and_every_slot_must_be_there(tmp_path) -> None:
    brief = _brief()
    with pytest.raises(ContractViolation, match="現行那一版"):
        _write(tmp_path, brief, _spec(brief, brief_id="ib_" + "0" * 16))
    partial = _spec(brief)
    del partial["slots"]["events"]
    with pytest.raises(ContractViolation, match="少了"):
        _write(tmp_path, brief, partial)
    no_refs = _spec(brief, evidence={"revenue": ["graph://x"]})
    with pytest.raises(ContractViolation, match="evidence.events"):
        _write(tmp_path, brief, no_refs)
    record = _write(tmp_path, brief, _spec(brief))
    assert record["brief_id"] == brief.brief_id and record["company_id"] == "co:coherent"
    assert current_stories(path=tmp_path / "stories.jsonl")[0][brief.brief_id]["story_id"] == record["story_id"]
    with pytest.raises(ContractViolation, match="一樣"):
        _write(tmp_path, brief, _spec(brief))


def test_the_missing_label_belongs_to_missing_only(tmp_path) -> None:
    """缺 X 才寫短標（首頁卡片「缺：<短標>」）；別的狀態帶短標＝一個欄位兩種意思（L12），拒收。"""
    missing = _brief(state="missing", ticker="AXTI", company="co:axt")
    spec = _spec(missing, candidate={"story": "缺：押的那一塊占營收多少量不到。"})
    with pytest.raises(ContractViolation, match="短標"):
        _write(tmp_path, missing, spec)
    spec["candidate"]["missing_label"] = "基板占比"
    assert _write(tmp_path, missing, spec)["candidate"]["missing_label"] == "基板占比"
    passed = _brief()
    with pytest.raises(ContractViolation, match="不寫 missing_label"):
        _write(tmp_path, passed, _spec(passed, candidate={"story": "非邊緣。", "missing_label": "占比"}))


def test_a_new_brief_version_makes_the_old_story_stale_by_itself(tmp_path) -> None:
    """故事對的是一版敘事：換版後舊故事不算數，⑤ 的判定分「從沒寫過」與「敘事換版、故事過期」（L14：會自己出現的計數）。"""
    old = _brief()
    _write(tmp_path, old, _spec(old))
    stories, _ = current_stories(path=tmp_path / "stories.jsonl")
    assert story_gaps([old], stories=stories) == []
    new = _brief(created=datetime(2026, 10, 29, tzinfo=timezone.utc))
    written = {bid: rec["company_id"] for bid, rec in stories.items()}
    gaps = story_gaps([new, _brief(ticker="AXTI", company="co:axt")], stories=stories, all_story_briefs=written)
    assert [(g["ticker"], g["kind"]) for g in gaps] == [("AXTI", "never"), ("COHR", "stale")]


# ---------------------------------------------------------------------------
# 讀取端（B-2）：read model 的 `story:<格>`、候選的短標、首屏合約、前端、CLI
# ---------------------------------------------------------------------------

def test_story_mode_values_drop_date_notes_and_say_the_checkpoint_in_words() -> None:
    """故事模式只改格式、不算數：值尾端的日期括號拿掉（日期是依據的字）、檢核日印成「11 月 14 日」，別年才帶年份。"""
    from alpha.narrative.story import fill_story, story_values

    shown = story_values({"market_cap": "37.6 億 USD（2026-10-02）", "revenue_ttm": "1.2 億 USD（近四季，快照 2026-10-02）",
                          "next_checkpoint_date": "2026-11-14", "analyst_count": "5", "cohort_median": None},
                         today=TODAY)
    assert shown == {"market_cap": "37.6 億 USD", "revenue_ttm": "1.2 億 USD", "next_checkpoint_date": "11 月 14 日",
                     "analyst_count": "5", "cohort_median": None}
    assert story_values({"next_checkpoint_date": "2027-03-31"}, today=TODAY)["next_checkpoint_date"] == "2027 年 3 月 31 日"
    text, gaps = fill_story("市值 {market_cap}、同組 {cohort_median}。", shown, absent="（尚無）")
    assert text == "市值 37.6 億 USD、同組（尚無）。" and gaps == ["{cohort_median}"]


def test_the_read_model_carries_the_story_of_the_current_brief_only() -> None:
    """`story:<格>` 只認寫給現行那一版敘事的故事；七格的引用＝依據那一格的引用，只有故事的兩格帶自己的引用。"""
    from briefing.alpha_view.builder import _story_slots

    brief = _brief()
    spec = _spec(brief)
    # 2026-10-29 以前寫的故事可能帶檢核日 placeholder：寫入端已不收，讀取端照填（as-of 回看也要讀得出當時那一句）
    legacy = {**spec["slots"], "when": "下一個檢核點是 {next_checkpoint_date} 的六吋磷化銦產能倍增。"}
    record = {"story_id": "st_" + "1" * 16, "brief_id": brief.brief_id, "created_at": "2026-10-29T08:00:00+00:00",
              "slots": legacy, "evidence": {"revenue": ["library/raw/x.txt"], "events": ["graph://source/y"]}}
    values = {"own_history_basis": "P/S", "own_history_pctile": "94", "analyst_count": "16",
              "in_numbers_latest": "+17.4%", "next_checkpoint_date": "2026-12-31"}
    told = {d.key: d for d in _story_slots(record, brief, values, today=TODAY)}
    assert list(told) == [f"story:{k}" for k in ("demand", "position", "bottleneck", "priced_in", "our_bet",
                                                  "what_must_be_true", "when", "revenue", "events")]
    assert told["story:when"].value == "下一個檢核點是 12 月 31 日的六吋磷化銦產能倍增。"
    assert told["story:priced_in"].value.startswith("已定價：自家三年 P/S 第 94 百分位")
    assert told["story:revenue"].evidence_refs == ("library/raw/x.txt",)
    assert told["story:bottleneck"].evidence_refs == ("graph://x",)
    assert told["story:bottleneck"].dependencies["basis_line"] == "brief:bottleneck"
    assert told["story:events"].dependencies["basis_line"] is None
    assert _story_slots({**record, "brief_id": "ib_" + "0" * 16}, brief, values, today=TODAY) == ()
    assert _story_slots(None, brief, values, today=TODAY) == ()


def test_looking_back_never_sees_a_story_written_later(tmp_path) -> None:
    """INV-6：回看 T 那天的頁，只拿 T 以前寫的故事；不給 as_of＝現行那一筆。"""
    from alpha.providers.stories import story_at

    path = tmp_path / "stories.jsonl"
    brief = _brief(state="missing", ticker="AXTI", company="co:axt")
    early = _spec(brief, candidate={"story": "缺：第一版。", "missing_label": "基板占比"})
    _write(tmp_path, brief, early, now=datetime(2026, 10, 20, 9, tzinfo=timezone.utc))
    late = _spec(brief, candidate={"story": "缺：第二版。", "missing_label": "基板占比"})
    _write(tmp_path, brief, late, now=datetime(2026, 10, 28, 9, tzinfo=timezone.utc))
    assert story_at(brief.brief_id, as_of=date(2026, 10, 25), path=path)["candidate"]["story"] == "缺：第一版。"
    assert story_at(brief.brief_id, path=path)["candidate"]["story"] == "缺：第二版。"
    assert story_at(brief.brief_id, as_of=date(2026, 10, 19), path=path) is None


def test_the_candidate_row_carries_the_reason_story_and_the_missing_label() -> None:
    """首頁卡片「缺：<短標>」與首屏的短理由照抄故事 ledger；敘事換版（故事寫給別版）就兩格都沒有、理由照印原文。"""
    from alpha.providers.candidates import _reason_story

    missing = _brief(state="missing", ticker="AXTI", company="co:axt")
    story = {"story_id": "st_" + "2" * 16, "candidate": {"story": "缺：基板占比量不到。", "missing_label": "基板占比"}}
    assert _reason_story(missing, {missing.brief_id: story}) == {
        "reason_story": "缺：基板占比量不到。", "missing_label": "基板占比", "story_id": "st_" + "2" * 16}
    assert _reason_story(missing, {"ib_other": story}) == {"reason_story": None, "missing_label": None, "story_id": None}
    passed = _brief()
    assert _reason_story(passed, {passed.brief_id: story})["missing_label"] is None   # 不是缺 X 就不印短標
    assert _reason_story(None, {missing.brief_id: story})["reason_story"] is None


def test_the_first_screen_contract_places_each_story_only_slot_once() -> None:
    from alpha.narrative.story import STORY_ONLY_KEYS
    from briefing.analyst_view.page_schema import check_schema, schema_payload

    assert check_schema() == []
    readings = schema_payload()["first_screen"]["readings"]
    placed = [s for r in readings.values() for s in r["story_slots"]]
    assert sorted(placed) == sorted(STORY_ONLY_KEYS)
    assert readings["B3"]["story_slots"] == ["revenue"] and readings["B5"]["story_slots"] == ["events"]
    # 沒寫故事時那一塊照舊宣告缺席（pending 是那一格沒寫時的那一句）
    assert readings["B3"]["pending"] and readings["B5"]["pending"]


def test_the_front_end_prints_the_story_first_and_keeps_the_basis_one_click_away() -> None:
    """app.js：每塊先找 `story:<格>`、沒有才印依據；依據併進那一塊的展開；只有故事的格照合約的 story_slots；
    首頁卡片印缺 X 的短標；候選理由先印故事。"""
    from pathlib import Path

    js = (Path(__file__).resolve().parents[1] / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    for token in ("lines['story:' + slot]", "reading.story_slots", "function basisRow", "basis.push(basisRow(said))",
                  "cand.missing_label", "row.reason_story"):
        assert token in js, token


def test_the_cli_writes_a_batch_only_when_every_story_passes(tmp_path, monkeypatch) -> None:
    """`python -m alpha stories --add`：先全部核對、全過才寫；`--check` 永遠不寫。"""
    import json

    import alpha.providers.stories as stories_mod
    from alpha.cli import build_parser

    written: list[str] = []

    def fake_prepare(ticker, spec, **_kw):
        return {"ticker": ticker}, (["故事〔需求〕 約 200 字，上限 160"] if ticker == "BAD" else [])

    def fake_write(ticker, spec, **_kw):
        written.append(ticker)
        return {"ticker": ticker, "story_id": "st_x", "brief_id": spec.get("brief_id")}

    monkeypatch.setattr(stories_mod, "prepare_story", fake_prepare)
    monkeypatch.setattr(stories_mod, "write_story", fake_write)
    batch = tmp_path / "batch.json"
    batch.write_text(json.dumps([{"ticker": "COHR", "brief_id": "ib_a"}, {"ticker": "BAD", "brief_id": "ib_b"}]),
                     encoding="utf-8")
    run = lambda *argv: (lambda a: a.func(a))(build_parser().parse_args(["stories", *argv]))   # noqa: E731
    assert run("--add", str(batch)) == 2 and written == []
    assert run("--check", str(batch)) == 2 and written == []
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"items": [{"ticker": "COHR", "brief_id": "ib_a"}]}), encoding="utf-8")
    assert run("--check", str(good)) == 0 and written == []
    assert run("--add", str(good)) == 0 and written == ["COHR"]
