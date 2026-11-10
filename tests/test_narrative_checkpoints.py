"""何時格的裁決點已過就叫重寫（2026-11-10，failure log #150；使用者「#150 … 照推薦做」）。

PSIX 的何時格 10-28 寫「最近的裁決點是第三季 10-Q」，10-Q 11-05 交了，這一格照舊到 11-10 換版；AAOI 寫
「{next_checkpoint_date} 的第三季財報」，第三季 11-06 過了、名冊上沒有更晚的日子，畫面印「（尚無）的第三季財報」。

守的事：
①三種「過了」：寫的日子（寫下那天還在未來的最近一個）過了、點名的 SEC 定期報告在寫下之後交了、佔位字寫成某件事的日子而
  寫下那天它指的那一件過了——只從日期判，不判文字的意思；
②「寫下那天」＝何時格這段文字最早出現的那一版（照抄的換版不重算）；
③8-K、6-K 有事就交，點名它們不核（恆亮，L14）；單獨寫的佔位字會自己更新，不核；
④進候選列 `rewrite[]`（首屏幾個字「裁決點過了」）、整板清單 kind=checkpoint、counts、⑤ 點名；輸入讀不到＝那一半沒核（INV-3）；
⑤寫入端照抄了已過的何時格、或把佔位字寫成某件事的日子——只印、不擋。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from alpha.candidates import CHECKPOINT_PASSED_PREFIX, assemble_board, rewrite_words
from alpha.narrative import parse_brief_record
from alpha.narrative.checkpoints import (checkpoint_passed, checkpoint_reason, placeholder_as_event, when_dates,
                                         when_forms, when_spans, when_text_since)
from alpha.providers.briefs import write_brief
from alpha.providers.candidates import board_rewrite, checkpoint_check, checkpoint_inputs, derive_row

from test_narrative_literals import _ctx as _write_ctx, _slots as _write_slots
from test_narrative_stale_24 import CO, EDGE, HELD_NONE, NEW, T, _record, _slots

D = date


# ---------------------------------------------------------------------------
# ① 日期
# ---------------------------------------------------------------------------

def test_dates_are_read_in_every_style_the_narratives_use() -> None:
    text = ("年報（法定期限 2027-04-30）；半期報告書法定期限 11 月 14 日；（10-29）的新聞稿；"
            "2026 年 12 月 10 日前的 11 月營收；約 2027 年 2 月上旬；2027 年 3 月；2026 年 11 月下旬")
    assert when_dates(text, written_on=D(2026, 11, 9)) == [
        D(2026, 10, 29), D(2026, 11, 14), D(2026, 11, 30), D(2026, 12, 10), D(2027, 2, 10), D(2027, 3, 31),
        D(2027, 4, 30)]


@pytest.mark.parametrize("text", [
    "兩到三家（2-3 家）", "1-3 月的營收", "3-5 GW 的燃料電池", "Q3-4 的毛利率", "2027-2029 年的擴產", "第三季 10-Q",
    "20-F 年報", "營收 19–20 億美元", "第 3-4 季", "5-10% 的成長", "8-10x 的倍數",
])
def test_ranges_and_form_names_are_not_dates(text: str) -> None:
    assert when_dates(text, written_on=D(2026, 11, 9)) == []


@pytest.mark.parametrize("text, written, expected", [
    ("到 7 月 10 日 6 月營收公布為止", D(2026, 11, 6), D(2027, 7, 10)),   # 3363.TWO 11-06：明年的，不是今年已過
    ("第三季報（10 月 27 日）已讀", D(2026, 11, 9), D(2026, 10, 27)),       # 剛讀過的
    ("1 月 15 日前的 12 月營收", D(2026, 11, 10), D(2027, 1, 15)),
    ("上一份是 8 月 12 日", D(2026, 10, 8), D(2026, 8, 12)),
])
def test_a_yearless_date_lands_back_two_months_forward_ten(text: str, written: date, expected: date) -> None:
    assert when_dates(text, written_on=written) == [expected]


def test_a_ten_day_period_is_a_span_and_a_bare_month_is_not_a_date() -> None:
    assert when_spans("第三季季報（約 10 月底到 11 月初，日期以公司公告為準）", written_on=D(2026, 10, 18)) == [
        (D(2026, 10, 21), D(2026, 10, 31)), (D(2026, 11, 1), D(2026, 11, 10))]
    assert when_spans("約 11 月中、12 月下旬", written_on=D(2026, 10, 18)) == [
        (D(2026, 11, 11), D(2026, 11, 20)), (D(2026, 12, 21), D(2026, 12, 31))]
    assert when_dates("11 月營收（12 月 10 日前）；4 月中國的出口", written_on=D(2026, 11, 10)) == [D(2026, 12, 10)]


def test_a_period_the_writer_was_already_in_is_the_one_just_past() -> None:
    """MOD 11-07：「照前兩季 7 月底、11 月初的節奏，約 2027 年 2 月初」——11 月初講的是剛交的那一份，不是在等的。"""
    text = "下一個是第三季 10-Q（照前兩季 7 月底、11 月初的節奏，約 2027 年 2 月初）。"
    assert checkpoint_passed(text, written_on=D(2026, 11, 7), today=D(2026, 11, 20)) is None
    aaon = "最近的觀測點是 2026 年第三季 10-Q（約 11 月初，日期以公司公告為準）。"              # AAON 10-08 寫的
    assert checkpoint_passed(aaon, written_on=D(2026, 10, 8), today=D(2026, 11, 10)) is None
    assert checkpoint_passed(aaon, written_on=D(2026, 10, 8), today=D(2026, 11, 11))["checkpoint"] == "2026-11-10"


def test_the_earliest_date_still_ahead_when_written_flags_once_it_has_passed() -> None:
    text = "第三季財報 11 月 5 日已讀；查到 2026-11-09；10 月營收 11 月 10 日前；年報 2027-04-30。"
    written = D(2026, 11, 9)
    # 寫下當天的「查到 11-09」是查過的那一刻、11-05 是讀過的——等的是 11-10
    assert checkpoint_passed(text, written_on=written, today=D(2026, 11, 10)) is None
    assert checkpoint_passed(text, written_on=written, today=D(2026, 11, 11)) == {
        "kind": "date", "since": "2026-11-09", "checkpoint": "2026-11-10"}


# ---------------------------------------------------------------------------
# ① 申報
# ---------------------------------------------------------------------------

PSIX_WHEN = "最近的裁決點是第三季 10-Q（約 2026 年 11 月上旬）：資料中心相關銷售有沒有出現。{next_checkpoint_date}。"
PSIX_FILINGS = [{"form": "10-Q", "filed": "2026-08-06", "lead_id": "lead_q2"},
                {"form": "10-Q", "filed": "2026-11-05", "lead_id": "lead_q3"}]


def test_psix_replay_the_10q_filed_after_the_text_was_written_flags_with_its_lead() -> None:
    written = D(2026, 10, 28)
    assert checkpoint_passed(PSIX_WHEN, written_on=written, today=D(2026, 11, 4), filings=PSIX_FILINGS) is None
    for today in (D(2026, 11, 5), D(2026, 11, 9)):                  # 申報當天起，到 11-10 換版前
        assert checkpoint_passed(PSIX_WHEN, written_on=written, today=today, filings=PSIX_FILINGS) == {
            "kind": "filing", "since": "2026-10-28", "form": "10-Q", "filed": "2026-11-05", "lead_id": "lead_q3"}
    # 「約 2026 年 11 月上旬」也過了（11-10），回最早過的那一件——申報
    assert checkpoint_passed(PSIX_WHEN, written_on=written, today=D(2026, 11, 12),
                             filings=PSIX_FILINGS)["kind"] == "filing"


@pytest.mark.parametrize("text, form", [
    ("等第三季 6-K。", "6-K"),                # EFXT：6-K 有事就交，三個月 8 份
    ("等第三季財報 8-K。", "8-K"),
    ("下一個是 2026 年 10-K。", "10-Q"),       # 點名的是 10-K，交的是 10-Q
])
def test_event_type_forms_and_other_forms_do_not_flag(text: str, form: str) -> None:
    filings = [{"form": form, "filed": "2026-11-05", "lead_id": "x"}]
    assert checkpoint_passed(text, written_on=D(2026, 10, 28), today=D(2026, 11, 10), filings=filings) is None


def test_the_lead_pool_gives_only_monitored_periodic_reports(monkeypatch) -> None:
    """lead 池只收 `edgar:` 來源的定期報告：指名抓的（`directed:`）company_id 是研究對象、不一定是申報人；6-K、8-K、4 不收。"""
    from alpha.providers import checkpoints as provider
    from engine_b import leads as leads_mod

    pool = {"leads": {
        "a": {"source": "edgar:PSIX", "form_type": "10-Q", "company_id": CO, "published_at": "2026-11-05", "lead_id": "a"},
        "b": {"source": "edgar:PSIX", "form_type": "10-K/A", "company_id": CO, "published_at": "2026-03-01", "lead_id": "b"},
        "c": {"source": "edgar:EFXT", "form_type": "6-K", "company_id": "co:efxt", "published_at": "2026-10-29"},
        "d": {"source": "edgar:PSIX", "form_type": "8-K", "company_id": CO, "published_at": "2026-11-05"},
        "e": {"source": "directed:x", "form_type": "10-K", "company_id": "co:research", "published_at": "2026-02-09"},
        "f": {"source": "edgar:PSIX", "form_type": "10-Q", "company_id": None, "published_at": "2026-11-05"},
    }}
    monkeypatch.setattr(leads_mod, "load", lambda: pool)
    assert provider.sec_filings_by_company() == ({CO: [
        {"form": "10-Q", "filed": "2026-11-05", "lead_id": "a"}, {"form": "10-K/A", "filed": "2026-03-01", "lead_id": "b"}]},
        None)

    def boom():
        raise OSError("壞了")

    monkeypatch.setattr(leads_mod, "load", boom)
    filings, note = provider.sec_filings_by_company()
    assert filings == {} and note.startswith("lead 池讀不到（OSError")


def test_an_amendment_counts_as_its_form_and_a_filing_before_the_text_does_not() -> None:
    filings = [{"form": "10-Q/A", "filed": "2026-11-05", "lead_id": "x"}]
    assert when_forms("第三季 10-Q 與 10-K") == ["10-Q", "10-K"]
    assert checkpoint_passed("第三季 10-Q。", written_on=D(2026, 10, 28), today=D(2026, 11, 10),
                             filings=filings)["form"] == "10-Q"
    assert checkpoint_passed("第三季 10-Q。", written_on=D(2026, 11, 6), today=D(2026, 11, 10), filings=filings) is None


# ---------------------------------------------------------------------------
# ① 佔位字
# ---------------------------------------------------------------------------

AAOI_WHEN = "最近的裁決點是 {next_checkpoint_date} 的第三季財報：800G／1.6T 的量與第四季指引。"
AAOI_CALENDAR = [{"date": D(2026, 8, 7), "what": "Q2 2026 財報"}, {"date": D(2026, 11, 6), "what": "Q3 2026 財報"}]


def test_aaoi_replay_a_placeholder_written_as_an_event_flags_once_that_event_passed() -> None:
    written = D(2026, 10, 5)
    assert placeholder_as_event(AAOI_WHEN)
    assert checkpoint_passed(AAOI_WHEN, written_on=written, today=D(2026, 11, 6),
                             calendar_checkpoints=AAOI_CALENDAR) is None
    assert checkpoint_passed(AAOI_WHEN, written_on=written, today=D(2026, 11, 7), calendar_checkpoints=AAOI_CALENDAR) == {
        "kind": "placeholder", "since": "2026-10-05", "checkpoint": "2026-11-06", "what": "Q3 2026 財報"}


@pytest.mark.parametrize("text", [
    "下半年營收有沒有超過去年。{next_checkpoint_date}。",                    # PSIX 11-10：單獨寫，每天自己換
    "下一個裁決點是 Q3 FY27 季報（{next_checkpoint_date}；照 Q1 8-10 的節奏約 2027 年 2 月上旬）。",
    "它出來時（名冊上最近的檢核點 {next_checkpoint_date}）看合約條款。",
])
def test_a_placeholder_standing_on_its_own_updates_itself_and_never_flags(text: str) -> None:
    assert not placeholder_as_event(text)
    assert checkpoint_passed(text, written_on=D(2026, 10, 5), today=D(2026, 11, 7),
                             calendar_checkpoints=AAOI_CALENDAR) is None


# ---------------------------------------------------------------------------
# ② 寫下那天＝這段文字最早出現的那一版
# ---------------------------------------------------------------------------

def _version(when: str, at: datetime, supersedes: str | None = None):
    slots = _slots()
    slots["when"] = {"text": when, "evidence_refs": ["graph://x"]}
    return parse_brief_record(_record(slots=slots, stamp=at, supersedes=supersedes))


def test_the_text_dates_from_its_first_version_and_a_rewrite_resets_it() -> None:
    t0 = datetime(2026, 10, 28, 5, tzinfo=timezone.utc)
    first = _version(PSIX_WHEN, t0)
    again = _version(PSIX_WHEN, t0 + timedelta(days=3), first.brief_id)          # 10-31 只改別格
    assert when_text_since([first, again], again) == t0
    changed = _version("下一個裁決點是 2027 年 3 月上旬的第四季財報。", t0 + timedelta(days=13), again.brief_id)
    assert when_text_since([first, again, changed], changed) == changed.created_at


# ---------------------------------------------------------------------------
# ④ 候選列、整板清單、計數、⑤ 的字
# ---------------------------------------------------------------------------

def _row(records, *, today: date, filings=None, calendar=None):
    rows = {("tech:npo", "layer"): {"node": "tech:npo", "unit": "layer", "reading_id": NEW, "status": "current",
                                    "kind": "neither"}}
    return derive_row(T, CO, records=records, today=today, reading_rows=rows, watches=[], lifecycle={}, edge=EDGE,
                      three_questions=None, held=HELD_NONE, company_filings=filings, calendar_checkpoints=calendar)


def test_the_row_the_board_list_and_the_count_carry_a_passed_checkpoint() -> None:
    t0 = datetime(2026, 10, 28, 5, tzinfo=timezone.utc)
    records = [_version(PSIX_WHEN, t0)]
    row = _row(records, today=D(2026, 11, 6), filings=PSIX_FILINGS)
    assert row["checkpoint_passed"]["kind"] == "filing"
    reason = next(r for r in row["rewrite"] if r.startswith(CHECKPOINT_PASSED_PREFIX))
    assert "10-Q" in reason and "2026-11-05" in reason and "lead_q3" in reason
    assert "裁決點過了" in row["rewrite_words"]
    items = [i for i in board_rewrite([row], []) if i["kind"] == "checkpoint"]
    assert items == [{"kind": "checkpoint", "ticker": T, "company_id": CO, "brief_id": records[0].brief_id,
                      "checkpoint_kind": "filing", "since": "2026-10-28", "form": "10-Q", "filed": "2026-11-05",
                      "lead_id": "lead_q3"}]
    board = assemble_board([row], universe=[T], held=HELD_NONE, narrative_rewrite=board_rewrite([row], []))
    assert board["counts"]["checkpoint_passed"] == 1


def test_inputs_not_loaded_check_only_the_dates() -> None:
    t0 = datetime(2026, 10, 5, 5, tzinfo=timezone.utc)
    assert _row([_version(PSIX_WHEN, t0)], today=D(2026, 11, 6), filings=None)["checkpoint_passed"] is None
    assert _row([_version(AAOI_WHEN, t0)], today=D(2026, 11, 7), calendar=None)["checkpoint_passed"] is None
    dated = _row([_version("半期報告書法定期限 11 月 14 日。", t0)], today=D(2026, 11, 15))
    assert dated["checkpoint_passed"]["checkpoint"] == "2026-11-14"


def test_the_context_says_which_half_was_not_checked() -> None:
    ok = {"sec_filings": {CO: PSIX_FILINGS}, "sec_filings_note": None,
          "calendar_checkpoints": {T: AAOI_CALENDAR}, "calendar_checkpoints_note": None}
    assert checkpoint_inputs(ok, T, CO) == {"company_filings": PSIX_FILINGS, "calendar_checkpoints": AAOI_CALENDAR}
    assert checkpoint_inputs(ok, "OTHER", "co:other") == {"company_filings": [], "calendar_checkpoints": []}
    assert checkpoint_check(ok) == {"status": "ok", "filings": "ok", "calendar": "ok", "reason": None}
    down = dict(ok, sec_filings={}, sec_filings_note="lead 池讀不到（OSError: x）")
    assert checkpoint_inputs(down, T, CO)["company_filings"] is None          # 沒核，不是沒有申報
    assert checkpoint_check(down) == {"status": "partial", "filings": "unavailable", "calendar": "ok",
                                      "reason": "lead 池讀不到（OSError: x）"}
    assert checkpoint_check({})["status"] == "partial"                         # 舊 context 沒有這兩格


def test_all_three_reasons_read_as_one_word_on_the_card() -> None:
    reasons = [checkpoint_reason({"kind": "date", "since": "2026-10-16", "checkpoint": "2026-11-05"}),
               checkpoint_reason({"kind": "filing", "since": "2026-10-28", "form": "10-Q", "filed": "2026-11-05",
                                  "lead_id": "lead_q3"}),
               checkpoint_reason({"kind": "placeholder", "since": "2026-10-05", "checkpoint": "2026-11-06",
                                  "what": "Q3 2026 財報"})]
    assert all(r.startswith(CHECKPOINT_PASSED_PREFIX) for r in reasons)
    assert "「Q3 2026 財報」" in reasons[2] and "{next_checkpoint_date}" in reasons[2]
    assert rewrite_words(reasons) == ["裁決點過了 × 3"]                        # 不被「已到」「到期」那幾條先吃掉


def test_the_artifact_carries_the_check_and_an_old_board_reads_as_not_checked() -> None:
    from webapp.materialize import build_candidates_artifact

    old = build_candidates_artifact({"counts": {}, "groups": {}, "side_groups": {}})
    assert old["checkpoint_check"]["status"] == "unavailable" and old["checkpoint_check"]["reason"] == "板上沒有這一格"
    check = {"status": "ok", "filings": "ok", "calendar": "ok", "reason": None}
    assert build_candidates_artifact({"counts": {}, "checkpoint_check": check})["checkpoint_check"] == check


# ---------------------------------------------------------------------------
# ⑤ 寫入端：只印、不擋
# ---------------------------------------------------------------------------

def _write_pair(tmp_path: Path, when: str, *, second_when: str | None = None, filings=None, calendar=None):
    from alpha.narrative import RECORD_VERSION_V2, brief_record

    ctx, wid = _write_ctx()
    ctx.filings, ctx.calendar_checkpoints = filings, calendar
    now = datetime.now(timezone.utc)

    def record(text: str, at: datetime, supersedes: str | None = None) -> dict:
        return brief_record(company_id="co:axt", ticker="AXTI", slots=_write_slots(when=text),
                            record_version=RECORD_VERSION_V2,
                            rides=[{"node": "tech:x", "unit": "layer", "reading_id": "sr_" + "b" * 16}],
                            answers={"priced_in": "no", "in_numbers": "yes"},
                            candidate_state={"state": "missing", "watch_id": wid, "reason": "缺：客戶沒具名"},
                            supersedes_id=supersedes, created_at=at)

    kw = {"ctx": ctx, "directory": tmp_path / "b", "watches_path": tmp_path / "w.json"}
    first = write_brief(record(when, now - timedelta(days=10)), **kw)
    return write_brief(record(second_when or when, now, first["brief_id"]), **kw)


def test_a_restated_when_slot_whose_checkpoint_passed_is_printed_not_refused(tmp_path: Path) -> None:
    due = (date.today() - timedelta(days=5)).isoformat()
    out = _write_pair(tmp_path, f"等 {due} 的季報。")
    notes = [n for n in out["notices"] if n.startswith("when：")]
    assert out["brief_id"] and len(notes) == 1
    assert "照抄了舊的何時格" in notes[0] and CHECKPOINT_PASSED_PREFIX in notes[0] and due in notes[0]


def test_a_restated_when_slot_naming_a_filed_10q_is_printed(tmp_path: Path) -> None:
    filed = (date.today() - timedelta(days=2)).isoformat()
    out = _write_pair(tmp_path, "下一個裁決點是第三季 10-Q。", filings=[{"form": "10-Q", "filed": filed, "lead_id": "lead_q3"}])
    assert [n for n in out["notices"] if "點名的 10-Q 已在" in n and "lead_q3" in n]


def test_a_rewritten_when_slot_is_quiet_and_a_placeholder_as_an_event_is_printed(tmp_path: Path) -> None:
    due = (date.today() - timedelta(days=5)).isoformat()
    out = _write_pair(tmp_path, f"等 {due} 的季報。", second_when="等 2027-04-30 的年報。")
    assert not [n for n in out["notices"] if n.startswith("when：")]
    out = _write_pair(tmp_path / "p", "最近的裁決點是 {next_checkpoint_date} 的第三季財報。")
    assert [n for n in out["notices"] if "寫成某件事的日子" in n]
