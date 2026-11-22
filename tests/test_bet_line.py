"""賭注句與對帳日曆（A0；使用者 2026-11-22「A0 1b 2B 3b，S1–S3 做」；提案 docs/brainstorms/2026-11-22-a0-bet-line-proposal.md）。

使用者 2026-11-20：「難把敘事組成一個我們在賭的東西」。一檔一句四格：押什麼｜翻倍要什麼｜下一個對帳日｜認錯看哪一條。
- 寫的人只寫前兩格的字與「第幾條反證」，住故事紀錄的選填鍵 `bet`（不換敘事版本）；
- 押哪一層照抄敘事的 rides；對帳日由程式讀「什麼時候知道」那一格自己寫到的日子（只認有年份或確切月日）；
- 它不 gate、不改候選狀態、不排序。
全部用注入的輸入：tmp 目錄的 ledger、手做的敘事、測試用名冊——不讀真實 ledger。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest

from alpha.errors import ContractViolation
from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record
from alpha.narrative.contracts import BRIEF_FRAME_V2
from alpha.narrative.story import bet_problems, doubling_kind
from alpha.providers.stories import bet_only_spec, current_stories, read_records, story_id, write_story

TODAY = date(2026, 11, 22)
CO, T = "co:coherent", "COHR"
READ = "sr_" + "a" * 16
D1 = {"condition": "客戶的申報文件列出第二家供應商", "check_frequency": "每季", "action_48h": "重寫", "entities": [CO],
      "expires": "2027-03-31", "source": "self", "link_source_ref": None}
D2 = {"condition": "2026 年底合約負債沒有維持在 30 億元以上", "check_frequency": "一次", "action_48h": "重寫", "entities": [CO],
      "expires": "2027-05-31", "source": "self", "link_source_ref": None}
WHEN = ("第三季財報已讀：9 月底合約負債 52 億元。固定的裁決點：每月 10 日前的月營收（11 月營收在 2026-12-10 前）——交機認列的節奏；"
        "2026 年度財報（法定期限 2027-03-31）——年底合約負債與第四季毛利率。")
BET = {"stake": "含浸機這一層的量——高階基板擴產還沒停，預收貨款照排程交機、新單接得上",
       "doubling": "單季營收到 12 億，最晚 2027 年第二季的季報看得到", "disproof": 2}


class _Registry:
    def company_id_for_ticker(self, ticker: str) -> str | None:
        return {T: CO}.get(ticker)


def _slots(when: str = WHEN) -> dict:
    ev = ["graph://x"]
    return {"demand": {"text": "客戶預付產能。", "evidence_refs": ev},
            "position": {"text": "坐在設備層，年增 {in_numbers_latest}（{in_numbers_as_of}）。", "evidence_refs": ev},
            "bottleneck": {"text": "圖上只有它一家。", "evidence_refs": ev},
            "priced_in": {"text": "自家三年 {own_history_basis} 第 {own_history_pctile} 百分位。", "evidence_refs": ev},
            "our_bet": {"text": "賭層的量。", "evidence_refs": ev},
            "what_must_be_true": {"text": "要從 {market_cap} 翻倍：近四季營收 {revenue_ttm} 要再大幅成長。", "evidence_refs": ev},
            "when": {"text": when, "evidence_refs": ev}}


def _brief(*, disproof=(D1, D2), when: str = WHEN, created=datetime(2026, 11, 16, tzinfo=timezone.utc)):
    rec = brief_record(company_id=CO, ticker=T, slots=_slots(when), record_version=RECORD_VERSION_V2,
                       rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}], disproof=list(disproof),
                       answers={"priced_in": "yes", "in_numbers": "yes"},
                       candidate_state={"state": "open", "watch_id": None, "reason": None}, created_at=created)
    return parse_brief_record(rec)


def _spec(brief, **over) -> dict:
    slots = {"demand": "基板廠預付設備款，鎖住它的產能。",
             "position": "它做含浸機；最新一季營收年增 {in_numbers_latest}。",
             "bottleneck": "圖上這一層只有它一家，買方在申報裡具名向它買。",
             "priced_in": "已定價：自家三年 {own_history_basis} 第 {own_history_pctile} 百分位。",
             "our_bet": "賭的是量：擴產還沒停，預收貨款照排程交機。",
             "what_must_be_true": "要從 {market_cap} 翻倍：預收貨款照排程交機、毛利率守在三成上下。",
             "when": "每月上旬的月營收看交機節奏；2027 年 3 月底前的年度財報看年底預收。",
             "revenue": "設備交機認列，客戶集中在一兩家基板廠。",
             "events": "最近沒有會改變判斷的事。"}
    spec = {"brief_id": brief.brief_id, "slots": slots,
            "evidence": {"revenue": ["graph://x"], "events": ["graph://x"]},
            "candidate": {"story": "邊緣小公司，這一層圖上只有它一家。"}}
    spec.update(over)
    return spec


def _write(tmp_path, brief, spec):
    return write_story(brief.ticker, spec, path=tmp_path / "stories.jsonl", registry=_Registry(), today=TODAY,
                       brief_loader=lambda t: ([brief], []))


# ---------------------------------------------------------------------------
# S1：寫入規則
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,kind", [
    ("單季營收到 12 億，最晚 2027 年第二季的季報看得到", "number"),
    ("近四季營收從 {revenue_ttm} 翻倍，2027 年度財報看得到", "number"),
    ("無法量：缺產能與單價", "unmeasurable"),
    ("近四季營收要再大幅成長", "vague"),
    ("2027 年要再大幅成長", "vague"),               # 年份不是條件的數字
    ("單季營收到 12 億", "vague"),                  # 有數字、沒有時點
    ("近四季營收 {revenue_ttm} 要再成長，2027 年看得到", "vague"),   # 起點的佔位字不算條件的數字
])
def test_the_doubling_sentence_is_sorted_into_three_kinds_mechanically(text, kind) -> None:
    """只標不擋：「翻倍條件還沒寫成數字」是會自己出現的計數，不是寫入的門。"""
    assert doubling_kind(text) == kind


def test_a_bet_line_passes_and_each_way_of_going_wrong_is_named() -> None:
    assert bet_problems(BET, disproof_count=2) == []
    # 序號指不到這一版敘事的反證
    assert any("超出範圍" in p for p in bet_problems({**BET, "disproof": 3}, disproof_count=2))
    assert any("超出範圍" in p for p in bet_problems({**BET, "disproof": 0}, disproof_count=2))
    assert any("整數" in p for p in bet_problems({**BET, "disproof": True}, disproof_count=2))
    assert any("整數" in p for p in bet_problems({**BET, "disproof": "2"}, disproof_count=2))
    # 價格不得出現（G3）：佔位字與字樣都擋
    assert any("{price}" in p for p in bet_problems({**BET, "doubling": "從 {price} 漲到 2027 年的 12 億"}, disproof_count=2))
    assert any("已定價" in p or "own_history_pctile" in p
               for p in bet_problems({**BET, "stake": "第 {own_history_pctile} 百分位的量"}, disproof_count=2))
    assert any("股價" in p for p in bet_problems({**BET, "doubling": "股價在 2027 年翻倍"}, disproof_count=2))
    assert any("目標價" in p for p in bet_problems({**BET, "doubling": "2027 年目標價 300"}, disproof_count=2))
    # 它是故事：確切日期、內部編號照故事的規則擋
    assert any("日期" in p for p in bet_problems({**BET, "doubling": "單季營收到 12 億，2027-06-30 前看得到"}, disproof_count=2))
    assert any("內部編號" in p for p in bet_problems({**BET, "stake": "ew_1452 那一條的量"}, disproof_count=2))
    # 無法量要寫缺什麼
    assert any("缺什麼" in p for p in bet_problems({**BET, "doubling": "無法量"}, disproof_count=2))
    assert bet_problems({**BET, "doubling": "無法量：缺產能與單價"}, disproof_count=2) == []
    # 不認得的鍵（押哪一層、對帳日都不是寫的人寫的）
    assert any("不認得" in p for p in bet_problems({**BET, "next_check": "2026-12-10"}, disproof_count=2))
    assert any("必須是" in p for p in bet_problems("押量", disproof_count=2))


def test_a_story_without_a_bet_keeps_the_id_it_always_had_and_old_records_read_back(tmp_path) -> None:
    """選填鍵：沒寫賭注句的故事，紀錄裡沒有 `bet` 這個鍵、id 照舊算——舊紀錄一筆都不變。"""
    brief = _brief()
    record = _write(tmp_path, brief, _spec(brief))
    assert "bet" not in record
    body = {k: record[k] for k in ("slots", "evidence", "candidate")}
    assert record["story_id"] == story_id(brief.brief_id, record["created_at"], body)
    records, errors = read_records(path=tmp_path / "stories.jsonl")
    assert errors == [] and [r["story_id"] for r in records] == [record["story_id"]]


def test_the_bet_line_is_written_into_the_story_and_points_at_a_disproof_of_this_brief(tmp_path) -> None:
    brief = _brief()
    first = _write(tmp_path, brief, _spec(brief))
    second = _write(tmp_path, brief, _spec(brief, bet=BET))
    assert second["bet"] == BET and second["supersedes_id"] == first["story_id"]
    assert current_stories(path=tmp_path / "stories.jsonl")[0][brief.brief_id]["bet"]["disproof"] == 2
    with pytest.raises(ContractViolation, match="一樣"):
        _write(tmp_path, brief, _spec(brief, bet=BET))
    with pytest.raises(ContractViolation, match="超出範圍"):
        _write(tmp_path, brief, _spec(brief, bet={**BET, "disproof": 3}))
    # 改故事的字卻沒帶賭注句＝悄悄把那一句拿掉：拒收
    changed = _spec(brief)
    changed["slots"]["events"] = "最近沒有新的事。"
    with pytest.raises(ContractViolation, match="有賭注句"):
        _write(tmp_path, brief, changed)


def test_bet_only_reuses_the_current_story_word_for_word(tmp_path) -> None:
    brief = _brief()
    path = tmp_path / "stories.jsonl"
    with pytest.raises(ContractViolation, match="還沒有故事"):
        bet_only_spec(T, BET, path=path, today=TODAY, brief_loader=lambda t: ([brief], []))
    first = _write(tmp_path, brief, _spec(brief))
    spec = bet_only_spec(T, BET, path=path, today=TODAY, brief_loader=lambda t: ([brief], []))
    assert spec["slots"] == first["slots"] and spec["candidate"] == first["candidate"] and spec["bet"] == BET
    record = _write(tmp_path, brief, spec)
    assert record["slots"] == first["slots"] and record["bet"] == BET


def test_the_cli_bet_only_takes_ticker_and_bet_and_nothing_else(tmp_path, monkeypatch) -> None:
    import alpha.providers.stories as stories_mod
    from alpha.cli import build_parser

    seen: list[dict] = []
    monkeypatch.setattr(stories_mod, "bet_only_spec", lambda ticker, bet, **_kw: {"ticker": ticker, "brief_id": "ib_a", "bet": bet})
    monkeypatch.setattr(stories_mod, "prepare_story", lambda ticker, spec, **_kw: (seen.append(spec) or {"ticker": ticker}, []))
    run = lambda *argv: (lambda a: a.func(a))(build_parser().parse_args(["stories", *argv]))   # noqa: E731
    good = tmp_path / "good.json"
    good.write_text(json.dumps([{"ticker": T, "bet": BET}]), encoding="utf-8")
    assert run("--check", str(good), "--bet-only") == 0 and seen[-1]["bet"] == BET
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([{"ticker": T, "bet": BET, "slots": {}}]), encoding="utf-8")
    assert run("--check", str(bad), "--bet-only") == 2


def test_the_when_slot_now_asks_for_a_dated_document_not_the_registry_placeholder() -> None:
    """何時格的寫作指示（2026-11-22）：原本叫人「日期用 {next_checkpoint_date}」——可開 17 檔在檢核點名冊沒有未來的檢核點，
    10 檔用了它、印「（尚無）」。對帳日讀的是這一格自己寫出的日子，所以指示改成寫出帶年份的日期與那一份文件。"""
    rule = BRIEF_FRAME_V2["when"]["do_not"]
    assert "帶年份" in rule and "那一份文件" in rule
    assert "日期用 {next_checkpoint_date}" not in rule


def test_the_bet_sentences_go_through_the_sentence_by_sentence_check() -> None:
    """賭注句是故事——寫了就跟故事其他句一起進逐句核對（「不比依據多主張」的機械補償：故事換了就再核）。"""
    from alpha.narrative.fact_check import build_sentences, brief_text_from_record, where_label

    brief = _brief()
    story = {**_spec(brief), "bet": BET}
    wheres = [s.where for s in build_sentences(brief_text_from_record(brief), story=story)]
    assert "story:bet.stake" in wheres and "story:bet.doubling" in wheres
    assert where_label("story:bet.doubling") == "故事：賭注句：翻倍要"
    without = [s.where for s in build_sentences(brief_text_from_record(brief), story=_spec(brief))]
    assert not any(w.startswith("story:bet.") for w in without)
