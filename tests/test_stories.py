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
             "when": "下一個檢核點是 {next_checkpoint_date} 的六吋磷化銦產能倍增。",
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
    """不擋的：年份與季度的粒度、型號縮寫、短的引號、「什麼時候知道」那一格的檢核日、反證這個詞。"""
    assert story_problems("demand", "2027 年第一季開始出貨 HBM4 用的 CW DFB 雷射；客戶說「產能不夠」。") == []
    assert story_problems("when", "下一次知道是 {next_checkpoint_date} 的財報。") == []
    assert story_problems("what_must_be_true", "錯的訊號（反證）是降價。") == []


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
