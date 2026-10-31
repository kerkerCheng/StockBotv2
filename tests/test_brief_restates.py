"""只改字面值的換版宣告 `restates`（2026-10-31 使用者「修吧」；failure log #121）。

守的事：判斷日（`judgment_version`）與正文版（`body_version`）的鍵含已定價那一格與正文原文，只改字也會歸零——10-31 清燈色
與收盤價的 13 份換版把 11 份的判斷日重設成當天、STLTECH.NS 的已回落叫醒消失。宣告 `restates` 的那一版沿用被重述那一版的
鍵：中間沒宣告的字面值換版不算改判，之後照抄同一段文字的版本也一樣；真的改判照常歸零。滯留不變。寫入端核對：只能重述
同一條鏈上的祖先、中間沒有撤回、候選狀態／answers／歷史不可比宣告都沒變。沒寫 `restates` 的紀錄 id 一位不變。
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from alpha.candidates import body_version, judgment_version, stall_version
from alpha.errors import ContractViolation
from alpha.narrative import RECORD_VERSION_V2, brief_record, parse_brief_record
from alpha.narrative.contracts import new_brief_id
from alpha.providers.briefs import restates_problems, write_brief

from test_narrative_literals import CO, PRICED, READ, T, _ctx, _slots

O = PRICED + "寫這句的 2026-10-06：調整後收盤由 1 月 2 日 10.00 美元漲到 6 月 22 日 40.00 美元。"
L = PRICED + "寫這句的 2026-10-06：股價上半年大漲、6 月見高點後回落。"
M = PRICED + "寫這句的 2026-11-06：價格已經回到年初的水準，不再是已定價。"


def _at(day: str, hour: int = 4) -> datetime:
    return datetime.fromisoformat(f"{day}T{hour:02d}:00:00+00:00")


def _brief(at: datetime, *, priced: str = O, supersedes=None, restates: str | None = None,
           state: str = "missing", answers: dict | None = None, bet: str = "賭層的量。"):
    rec = brief_record(company_id=CO, ticker=T, slots=_slots(priced_in=priced, our_bet=bet),
                       record_version=RECORD_VERSION_V2, rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}],
                       answers=answers or {"priced_in": "yes", "in_numbers": "yes"},
                       candidate_state={"state": state, "watch_id": "ew_1_2026-10-06", "reason": "缺：客戶沒具名"},
                       supersedes_id=supersedes.brief_id if supersedes is not None else None,
                       restates=restates, created_at=at)
    return parse_brief_record(rec)


def _chain():
    a = _brief(_at("2026-10-06"))                                         # 判斷日
    b = _brief(_at("2026-10-19"), supersedes=a, bet="賭層的量，客戶開始具名。")  # 只改正文：判斷日不動、正文版移到 b
    c = _brief(_at("2026-10-31"), priced=L, supersedes=b, bet=b.slot("our_bet").text)  # 沒宣告的字面值換版
    d = _brief(_at("2026-10-31", 5), priced=L, supersedes=c, bet=b.slot("our_bet").text, restates=b.brief_id)
    return a, b, c, d


def test_a_literal_rewrite_without_restates_resets_the_judgment_day() -> None:
    """#121 的事發形狀：只改字面值也算改判（不宣告就照舊歸零——這條是現狀的對照組）。"""
    a, b, c, _d = _chain()
    assert judgment_version([a, b, c], c) is c and body_version([a, b, c], c) is c


def test_a_restating_version_keeps_the_judgment_day_and_the_body_version() -> None:
    a, b, c, d = _chain()
    records = [a, b, c, d]
    assert judgment_version(records, d) is a
    assert body_version(records, d) is b
    assert stall_version(records, d) is a          # 滯留本來就不看文字，不受影響


def test_a_later_copy_of_the_restated_text_still_walks_back_and_a_real_change_resets() -> None:
    a, b, c, d = _chain()
    e = _brief(_at("2026-11-05"), priced=L, supersedes=d, bet=b.slot("our_bet").text)
    assert judgment_version([a, b, c, d, e], e) is a and body_version([a, b, c, d, e], e) is b
    f = _brief(_at("2026-11-06"), priced=M, supersedes=e, bet=b.slot("our_bet").text)
    assert judgment_version([a, b, c, d, e, f], f) is f


def test_restates_must_be_an_ancestor_with_the_same_structured_judgment() -> None:
    a, b, c, d = _chain()
    assert restates_problems(d, [a, b, c]) == []
    stranger = _brief(_at("2026-10-07"), bet="另一條鏈。")
    lost = _brief(_at("2026-10-31", 6), priced=L, supersedes=c, restates=stranger.brief_id)
    assert "不在這一版的 supersedes 鏈上" in restates_problems(lost, [a, b, c, stranger])[0]
    flipped = _brief(_at("2026-10-31", 6), priced=L, supersedes=c, restates=a.brief_id,
                     answers={"priced_in": "no", "in_numbers": "yes"})
    assert any("結構化的判斷變了" in p for p in restates_problems(flipped, [a, b, c]))


def test_a_retraction_after_the_restated_version_is_refused() -> None:
    a, b, c, d = _chain()
    pulled = parse_brief_record({**brief_record(
        company_id=CO, ticker=T, slots=_slots(priced_in=O), record_version=RECORD_VERSION_V2,
        rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}], answers={"priced_in": "yes", "in_numbers": "yes"},
        candidate_state={"state": "missing", "watch_id": "ew_1_2026-10-06", "reason": "缺：客戶沒具名"},
        supersedes_id=b.brief_id, retracted=True, created_at=_at("2026-10-25"))})
    assert any("撤回打斷連續" in p for p in restates_problems(d, [a, b, pulled, c]))
    assert restates_problems(d, [a, b, c]) == []            # 被重述那一版之前的撤回不相干（a 之前沒有撤回）


def test_records_without_restates_keep_their_ids() -> None:
    a, *_ = _chain()
    raw = brief_record(company_id=CO, ticker=T, slots=_slots(), record_version=RECORD_VERSION_V2,
                       rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}],
                       answers={"priced_in": "yes", "in_numbers": "yes"},
                       candidate_state={"state": "missing", "watch_id": "ew_x", "reason": "缺：客戶沒具名"},
                       created_at=_at("2026-10-06"))
    assert "restates" not in raw and new_brief_id({**raw, "restates": None}) == raw["brief_id"]
    with pytest.raises(ContractViolation, match="restates"):
        brief_record(company_id=CO, ticker=T, slots=_slots(), restates=a.brief_id)     # v1 不收


def test_the_write_path_runs_the_restates_check(tmp_path: Path) -> None:
    ctx, wid = _ctx()
    first = brief_record(company_id=CO, ticker=T, slots=_slots(priced_in=O), record_version=RECORD_VERSION_V2,
                         rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}],
                         answers={"priced_in": "yes", "in_numbers": "yes"},
                         candidate_state={"state": "missing", "watch_id": wid, "reason": "缺：客戶沒具名"},
                         created_at=datetime.now(timezone.utc))
    kw = {"ctx": ctx, "directory": tmp_path / "b", "watches_path": tmp_path / "w.json"}
    write_brief(first, **kw)
    bad = brief_record(company_id=CO, ticker=T, slots=_slots(priced_in=L), record_version=RECORD_VERSION_V2,
                       rides=[{"node": "tech:x", "unit": "layer", "reading_id": READ}],
                       answers={"priced_in": "no", "in_numbers": "yes"},
                       candidate_state={"state": "missing", "watch_id": wid, "reason": "缺：客戶沒具名"},
                       supersedes_id=first["brief_id"], restates=first["brief_id"], created_at=datetime.now(timezone.utc))
    with pytest.raises(ContractViolation, match="restates"):
        write_brief(bad, **kw)
