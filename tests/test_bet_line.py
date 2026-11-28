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
    ("近四季營收翻倍，2027 年度財報看得到", "number"),
    ("無法量：缺產能與單價", "unmeasurable"),
    ("近四季營收要再大幅成長", "vague"),
    ("2027 年要再大幅成長", "vague"),               # 年份不是條件的數字
    ("單季營收到 12 億", "vague"),                  # 有數字、沒有時點
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
    # 佔位字一個都不收：這一句也印在沒有值表的地方（依層頁、日曆），同一句不能有填了與沒填兩種樣子
    assert any("{revenue_ttm}" in p and "佔位字" in p
               for p in bet_problems({**BET, "doubling": "近四季營收從 {revenue_ttm} 翻倍，2027 年度財報看得到"}, disproof_count=2))
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


# ---------------------------------------------------------------------------
# S2：導出與計數——對帳日、認錯那一條的 watch、候選列的兩個加法欄、待做清單三格
# ---------------------------------------------------------------------------

WRITTEN_ON = date(2026, 11, 16)
HELD = {"status": "ok", "by_company": {CO: {"sheet_ticker": T}}, "unresolved": [], "beta_excluded": 0, "zero_shares": 0}
HELD_NONE = {"status": "ok", "by_company": {}, "unresolved": [], "beta_excluded": 0, "zero_shares": 0}
EDGE = {"state": "edge", "label": "邊緣", "reasons": ["within_edge"], "market_cap_usd": 4.8e9, "analyst_count": 5}
LABELS = {"tech:x": "含浸機"}


def _watch(wid: str, ref: str, *, expires: str, status: str = "active", confirm: bool = False) -> dict:
    from engine_b import event_watch as ew

    watch = {"watch_id": wid, "kind": ew.SEMANTIC_KIND, "status": status, "source_ref": ref, "disproof_ref": ref,
             "expires": expires, "condition": "x", "entities": [CO]}
    if confirm:
        watch["condition_role"] = ew.CONFIRM_ROLE
    return watch


def _row(records, *, held=HELD, stories=None, watches=(), calendar=None, today=TODAY):
    from alpha.providers.candidates import derive_row

    return derive_row(T, CO, records=list(records), today=today, reading_rows={}, watches=list(watches), lifecycle={},
                      edge=EDGE, three_questions=None, held=held, stories=stories, calendar_checkpoints=calendar,
                      node_labels=LABELS)


def test_a_reckoning_day_needs_a_year_or_an_exact_month_and_day() -> None:
    """對帳日印給人看、還排進日曆，所以比「裁決點過了沒」認得窄：沒寫年份又只寫到旬的不認。"""
    from alpha.narrative.checkpoints import reckoning_days, when_spans

    days = reckoning_days(WHEN, written_on=WRITTEN_ON)
    assert [(d["date"].isoformat(), d["yearless"]) for d in days] == [("2026-12-10", False), ("2027-03-31", False)]
    assert days[0]["sentence"] == "固定的裁決點：每月 10 日前的月營收（11 月營收在 2026-12-10 前）——交機認列的節奏"
    assert days[1]["sentence"] == "2026 年度財報（法定期限 2027-03-31）——年底合約負債與第四季毛利率"
    # 同一段文字，「裁決點過了沒」那一邊照舊把回頭講的「9 月底」推成明年 9 月——這正是對帳日不認它的原因
    assert any(start == date(2027, 9, 21) for start, _ in when_spans(WHEN, written_on=WRITTEN_ON))
    assert not any(d["date"].month == 9 for d in days)
    # 寫得出確切月日、沒寫年份：寫下那天之後一季以內的認，年份照寫下那天推，而且標出來
    assert [(d["date"].isoformat(), d["yearless"]) for d in
            reckoning_days("實施規則在 12-24 另一筆叫醒。", written_on=date(2026, 11, 10))] == [("2026-12-24", True)]
    # 推出來落在一季以後的不認——2026-11-22 逐檔看過的三筆讀錯都是這個形狀（回頭講的日子被推成明年）
    for text, written in (("港交所的清單仍列它（只有 03-06 第一次呈交）。", date(2026, 11, 10)),
                          ("照 Q1 8-10 的節奏。", date(2026, 11, 11)),
                          ("9 月 15 日寫 1b 在試車。", date(2026, 11, 15))):
        assert reckoning_days(text, written_on=written) == [], text
        assert when_spans(text, written_on=written)[0][0].year == 2027       # 「裁決點過了沒」那一邊照舊認、推成明年
    # 有年份、只寫到旬：取那一段的最後一天
    assert reckoning_days("約 2027 年 2 月上旬的法說。", written_on=date(2026, 11, 6))[0]["date"] == date(2027, 2, 10)
    # 寫下當天的日子是「查到哪一天」，不是在等的事
    assert reckoning_days("查到 2026-11-16，還沒公告。", written_on=WRITTEN_ON) == []
    # 同一句兩個日子各一列；同一天同一句只留一列
    two = reckoning_days("2026-12-10 與 2026-12-10 之前看月營收，2027-01-10 再看一次。", written_on=WRITTEN_ON)
    assert [d["date"].isoformat() for d in two] == ["2026-12-10", "2027-01-10"]


def test_the_disproof_a_bet_points_at_is_found_by_its_source_key() -> None:
    from engine_b.disproof import disproof_pointers

    linked = {**D2, "link_source_ref": f"reading:{READ}#1"}
    brief = _brief(disproof=(D1, linked))
    watches = [_watch("ew_0001", f"brief:{brief.brief_id}#1", expires="2027-04-30"),
               _watch("ew_0002", f"reading:{READ}#1", expires="2027-06-30", status="fired"),
               _watch("ew_0003", f"brief:{brief.brief_id}#c1", expires="2027-01-31", confirm=True),
               _watch("ew_0004", "brief:ib_someone_else#1", expires="2027-01-31")]
    rows = disproof_pointers(brief, watches)
    assert [(r["n"], r["watch_id"], r["expires"], r["state"]) for r in rows] == [
        (1, "ew_0001", "2027-04-30", "active"), (2, "ew_0002", "2027-06-30", "fired")]
    assert rows[0]["condition"] == D1["condition"] and rows[1]["linked"] is True
    # 沒有處理中的 watch：未盯，到期日退回敘事那一條自己寫的（不留白，INV-3）
    assert [(r["watch_id"], r["expires"], r["state"]) for r in disproof_pointers(brief, [])] == [
        (None, "2027-03-31", "unwatched"), (None, "2027-05-31", "unwatched")]
    assert disproof_pointers(None, watches) == []


def test_the_calendar_is_by_date_and_the_next_check_is_a_document_not_an_expiry() -> None:
    from alpha.bet_line import check_calendar, next_check

    cal = check_calendar(
        today=TODAY,
        when_days=[{"date": date(2026, 12, 10), "sentence": "月營收", "yearless": False},
                   {"date": date(2026, 11, 1), "sentence": "已經過了", "yearless": False}],
        registry_days=[{"date": "2026-12-10", "what": "法說"}, {"date": "2026-12-01", "what": "年會"}],
        disproof=[{"n": 1, "condition": "第二家", "watch_id": "ew_0001", "expires": "2026-11-25", "state": "active"}],
        confirm=[{"index": 1, "condition": "長約", "watch_id": "ew_0009", "until": "2026-12-10", "state": "active"},
                 {"index": 2, "condition": "收掉的", "watch_id": "ew_0010", "until": "2026-12-05", "state": "closed"}])
    assert [(r["date"], r["kind"]) for r in cal] == [
        ("2026-11-25", "disproof_expiry"), ("2026-12-01", "checkpoint_registry"), ("2026-12-10", "when_slot"),
        ("2026-12-10", "checkpoint_registry"), ("2026-12-10", "confirm_expiry")]      # 過了的、收掉的不列
    assert cal[0]["kind_label"] == "反證到期" and cal[0]["watch_id"] == "ew_0001"
    # 下一個對帳日：最早的「文件」——反證到期更早也不取（到期是重問，不是哪一份文件出來）
    assert next_check(cal) == {"date": "2026-12-01", "sentence": "年會", "source": "checkpoint_registry",
                               "source_label": "名冊檢核點", "yearless": False}
    assert next_check([r for r in cal if r["kind"].endswith("_expiry")]) is None
    # 同一天：取何時格那一列（它帶著寫的人的原句）
    assert next_check([r for r in cal if r["date"] == "2026-12-10"])["source"] == "when_slot"


def test_the_row_says_not_written_and_still_carries_the_next_check_day() -> None:
    """還沒寫賭注句的可開／已持有：印「還沒寫賭注句」；下一個對帳日不靠寫的人，照樣帶得出來。"""
    brief = _brief()
    row = _row([brief], stories={brief.brief_id: _spec(brief)})
    bet = row["bet_line"]
    assert (bet["state"], bet["owed"], bet["stake"], bet["doubling"], bet["disproof"]) == ("not_written", True, None, None, None)
    assert bet["next_check"]["date"] == "2026-12-10" and bet["next_check"]["source"] == "when_slot"
    assert bet["lines"] == ["還沒寫賭注句",
                            "下一個對帳日：2026-12-10｜「固定的裁決點：每月 10 日前的月營收（11 月營收在 2026-12-10 前）"
                            "——交機認列的節奏」（何時格寫的日子）"]
    assert [(r["date"], r["kind"]) for r in row["check_calendar"]] == [
        ("2026-12-10", "when_slot"), ("2027-03-31", "when_slot"), ("2027-03-31", "disproof_expiry"),
        ("2027-05-31", "disproof_expiry")]
    # 名冊的檢核點比何時格的日子早：取名冊那一個
    early = _row([brief], calendar=[{"date": "2026-12-03", "what": "第三季法說"}])["bet_line"]["next_check"]
    assert (early["date"], early["source"], early["sentence"]) == ("2026-12-03", "checkpoint_registry", "第三季法說")
    # 不欠的列（沒持有、起始門沒過所以不在可開）：沒寫就不印這一塊，計數也不數它
    other = _row([brief], held=HELD_NONE)
    assert other["group"] != "open" and other["bet_line"]["owed"] is False and other["bet_line"]["lines"] == []


def test_the_written_bet_line_is_four_sentences_with_the_layer_the_day_and_the_watch() -> None:
    brief = _brief()
    stories = {brief.brief_id: {**_spec(brief), "bet": BET}}
    watches = [_watch("ew_0002", f"brief:{brief.brief_id}#2", expires="2027-05-31")]
    bet = _row([brief], stories=stories, watches=watches)["bet_line"]
    assert bet["state"] == "written" and bet["doubling"]["kind"] == "number"
    assert bet["rides"] == [{"node": "tech:x", "label": "含浸機", "unit_label": "層"}]
    assert bet["disproof"] == {"n": 2, "condition": D2["condition"], "watch_id": "ew_0002", "expires": "2027-05-31",
                               "state": "active", "state_label": "在盯"}
    assert bet["lines"] == [
        "押：含浸機（層）——含浸機這一層的量——高階基板擴產還沒停，預收貨款照排程交機、新單接得上",
        "翻倍要：單季營收到 12 億，最晚 2027 年第二季的季報看得到",
        "下一個對帳日：2026-12-10｜「固定的裁決點：每月 10 日前的月營收（11 月營收在 2026-12-10 前）——交機認列的節奏」（何時格寫的日子）",
        "認錯看：第 2 條——2026 年底合約負債沒有維持在 30 億元以上（ew_0002，2027-05-31 到期）"]
    # 翻倍條件沒寫成數字：照印、後面標出來；沒有 watch：寫未盯與敘事自己的到期日
    vague = {brief.brief_id: {**_spec(brief), "bet": {**BET, "doubling": "近四季營收要再大幅成長"}}}
    lines = _row([brief], stories=vague)["bet_line"]["lines"]
    assert lines[1] == "翻倍要：近四季營收要再大幅成長（翻倍條件還沒寫成數字）"
    assert lines[3] == "認錯看：第 2 條——2026 年底合約負債沒有維持在 30 億元以上（未盯；敘事寫的到期日 2027-05-31）"
    # 不欠的列寫了照印（寫了就是寫了）
    assert len(_row([brief], stories=stories, held=HELD_NONE)["bet_line"]["lines"]) == 4
    # 層沒有中文名：用圖上的名字（「是不是新賭注」那一份 names），都沒有才印節點 id——不臨時翻譯
    from alpha.providers.candidates import derive_row

    def named(bets):
        return derive_row(T, CO, records=[brief], today=TODAY, reading_rows={}, watches=[], lifecycle={}, edge=EDGE,
                          three_questions=None, held=HELD, stories=stories, node_labels={}, bets=bets)["bet_line"]

    assert named({"names": {"tech:x": "Impregnation treater line"}})["lines"][0].startswith("押：Impregnation treater line（層）——")
    assert named(None)["lines"][0].startswith("押：tech:x（層）——")


def test_a_new_brief_version_makes_the_bet_line_stale_and_no_narrative_is_its_own_state() -> None:
    old = _brief()
    new = _brief(created=datetime(2026, 11, 20, tzinfo=timezone.utc),
                 when=WHEN + "補：2027-01-10 前的 12 月營收。")
    stories = {old.brief_id: {**_spec(old), "bet": BET}}
    assert new.brief_id != old.brief_id
    bet = _row([old, new], stories=stories)["bet_line"]
    assert bet["state"] == "stale" and bet["lines"][0] == "賭注句過期了：敘事換版，照新的一版重寫"
    # 已持有、沒有敘事：先要有敘事（不是「還沒寫」同一種）
    none = _row([])["bet_line"]
    assert (none["state"], none["owed"], none["next_check"], none["lines"]) == (
        "no_narrative", True, None, ["還沒寫賭注句：先要有敘事"])


def test_the_registry_placeholder_in_the_sentence_is_said_in_words_not_left_raw() -> None:
    """何時格那一句若帶名冊佔位字：個股頁填的日子另含催化劑，這裡不另填一個可能不同的日子——寫成字。"""
    brief = _brief(when="最近的裁決點是 {next_checkpoint_date} 的第三季財報，最晚 2026-12-15 前。")
    sentence = _row([brief])["bet_line"]["next_check"]["sentence"]
    assert "{" not in sentence and sentence == "最近的裁決點是 名冊上的下一個檢核點 的第三季財報，最晚 2026-12-15 前"


def test_the_three_counts_read_the_board_rows() -> None:
    from alpha.bet_line import bet_gap_rows, doubling_rows, no_check_day_rows

    def row(ticker, state, *, kind=None, check=True):
        return {"ticker": ticker, "bet_line": {"state": state, "doubling": {"kind": kind} if kind else None,
                                               "next_check": {"date": "2026-12-10"} if check else None}}

    groups = {"open": [row("A", "written", kind="number"), row("B", "written", kind="vague"),
                       row("C", "not_written", check=False), row("D", "written", kind="unmeasurable")],
              "held": [row("E", "stale"), row("F", "no_narrative", check=False)],
              "missing": [row("G", "not_written", check=False), row("H", "written", kind="vague")]}
    assert [r["ticker"] for r in bet_gap_rows(groups)] == ["C", "E", "F"]             # 缺 X 不欠
    assert [r["ticker"] for r in doubling_rows(groups, "vague")] == ["B"]
    assert [r["ticker"] for r in doubling_rows(groups, "unmeasurable")] == ["D"]      # 現況，不是待做
    assert [r["ticker"] for r in no_check_day_rows(groups)] == ["C"]                  # 沒有敘事的已在第一格，不重複數


def test_the_todo_ledger_carries_three_cells_and_unread_is_not_zero() -> None:
    """⑤ 多三格：賭注句還沒寫｜翻倍條件還沒寫成數字（只數「還沒寫成數字」，「無法量」另印成現況）｜沒有對帳日。"""
    from test_todo_ledger import CHECKPOINT_OK, _collect

    def row(ticker, state, *, kind=None, check=True):
        return {"ticker": ticker, "addon_unchecked": [], "deadline_disproof": 1,
                "bet_line": {"state": state, "doubling": {"kind": kind} if kind else None,
                             "next_check": {"date": "2026-12-10"} if check else None}}

    def board(**groups):
        return {"counts": {}, "groups": groups, "holdings": {"status": "ok"}, "new_edges_check": {"status": "ok"},
                "reading_change_check": {"status": "ok", "unchecked": 0}, "checkpoint_check": CHECKPOINT_OK}

    cells = _collect(candidates=board(
        open=[row("A", "written", kind="number"), row("B", "written", kind="vague"), row("C", "not_written", check=False),
              row("D", "written", kind="unmeasurable")],
        held=[row("E", "stale"), row("F", "no_narrative", check=False)]))
    assert (cells["todo.bet_line"].count, cells["todo.bet_line"].work) == (3, "從沒寫 1；敘事換版 1；沒有敘事 1")
    assert (cells["todo.bet_vague"].count, cells["todo.bet_vague"].work) == (1, "B")
    assert "無法量」1 檔（D）" in cells["todo.bet_vague"].note and "不是待做" in cells["todo.bet_vague"].note
    assert (cells["todo.no_check_day"].count, cells["todo.no_check_day"].work) == (1, "C")
    # 三格都不推 drain：清掉它們不讓任何一檔離決定更近（整批寫 2026-11-28 已放行），它們只是會自己出現的計數
    from engine_b import todo_ledger as tl

    assert not {"todo.bet_line", "todo.bet_vague", "todo.no_check_day"} & set(tl.PROGRESS_LABELS)
    # 沒讀到不是 0：板沒讀到、持股沒讀到、舊板（列上沒有這一格）各說各的
    keys = ("todo.bet_line", "todo.bet_vague", "todo.no_check_day")
    for candidates, why in ((None, "候選板未讀到"),
                            ({**board(open=[row("A", "written", kind="number")]), "holdings": {"status": "failed"}}, "持股沒讀到"),
                            (board(open=[{"ticker": "OLD", "addon_unchecked": [], "deadline_disproof": 1}]), "舊版")):
        cells = _collect(candidates=candidates)
        assert all(cells[k].count is None and why in cells[k].reason for k in keys), why
    # 全部寫了、都有數字、都有對帳日：三格歸零
    cells = _collect(candidates=board(open=[row("A", "written", kind="number")]))
    assert [cells[k].count for k in keys] == [0, 0, 0]


# ---------------------------------------------------------------------------
# S3：畫面——候選面板的那一行、頁面合約 B13、前端照印
# ---------------------------------------------------------------------------

def _panel(row):
    from briefing.analyst_view.compose import _candidate_panel

    return _candidate_panel({"row": row, "three_words": {}, "today": TODAY.isoformat()})


def _bet_datum(row):
    return next(line.datum for line in _panel(row).lines if line.key == "candidate:bet_line")


def test_the_candidate_panel_line_says_written_owed_or_not_owed_by_itself() -> None:
    """頁面合約 B13 讀這一行自己宣告的缺席（L16）：寫了＝那四句；欠而沒寫＝還沒寫；不欠＝不適用（已定的缺席，不是待做）。"""
    brief = _brief()
    story = {brief.brief_id: {**_spec(brief), "bet": BET}}
    written = _bet_datum(_row([brief], stories=story))
    assert written.status == "available" and len(written.value) == 4 and written.value[0].startswith("押：")
    owed = _bet_datum(_row([brief]))
    assert (owed.status, owed.absence_kind, owed.reason) == ("missing", "not_yet_recorded", "還沒寫賭注句")
    free = _bet_datum(_row([brief], held=HELD_NONE))
    assert (free.status, free.absence_kind) == ("not_applicable", "method_not_applicable")
    # 舊候選列（沒有這一欄）不印這一行——不是「還沒寫」
    old = {k: v for k, v in _row([brief]).items() if k != "bet_line"}
    assert all(line.key != "candidate:bet_line" for line in _panel(old).lines)


def test_page_block_b13_is_filled_from_that_line_and_names_each_absence() -> None:
    from briefing.analyst_view import page_schema as ps

    def fill(lines):
        view = {"candidate": {"lines": lines}}
        return next(r for r in ps.fill_table(view) if r["element"] == "B13.bet_line")

    def line(status, kind=None):
        return {"key": "candidate:bet_line", "datum": {"status": status, "absence_kind": kind}}

    assert fill([line("available")])["state"] == "value"
    assert fill([line("missing", "not_yet_recorded")])["absence_kind"] == "not_yet_recorded"
    assert fill([line("not_applicable", "method_not_applicable")])["absence_kind"] == "method_not_applicable"
    assert fill([])["absence_kind"] == "not_yet_recorded"                      # 沒有候選列＝沒有敘事：合約宣告的預設
    assert ps.check_schema() == []


def test_the_front_end_prints_the_sentences_as_given_and_builds_none() -> None:
    """前端照印 materialize 端組好的句子：不在瀏覽器組「押：…」、不排序；依層頁每檔印同一份。"""
    import re
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    code = re.sub(r"(?m)//.*$", "", re.sub(r"/\*.*?\*/", "", source, flags=re.S))
    assert "function betLines(" in code and "function betList(" in code and "function calendarRow(" in code
    # 2026-11-28 舊版個股頁（十三塊的 `questionPart`）刪除：賭注句印在沒做深的檔短故事「我們賭什麼」那一格的灰框
    # （`systemPieces` 的 bet、`SYSTEM_PLACES`）；做過故事頁的檔不印（故事的第 11、12 題就是長版）
    pieces = source.split("function systemPieces(", 1)[1].split("\n}\n", 1)[0]
    assert "bet: story ? [] : betLines(row)," in pieces and "['bet', null, ['our_bet']]" in source
    for built in ("押：", "翻倍要：", "下一個對帳日：", "認錯看：", "還沒寫賭注句"):
        assert built not in code, built                                        # 這幾個字只住 alpha.bet_line（L16）
    assert ".sort(" not in code
